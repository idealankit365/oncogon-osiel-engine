from __future__ import annotations

import json
import math
import statistics
from datetime import UTC, datetime
from typing import Any

import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from .chemistry import ChemistryService, StructureError, chemistry
from .config import settings
from .connectors.chembl import ChEMBLActivityPage, ChEMBLConnector
from .immutable_storage import ImmutableObjectStore, object_store
from .repository import Repository
from .schemas import (
    ActiveLearningBatch,
    ActiveLearningRequest,
    ActiveLearningSuggestion,
    ActivityDatasetSnapshot,
    ActivityModelPrediction,
    ActivityModelPredictionRequest,
    ActivityModelRun,
    ChEMBLActivitySnapshotRequest,
    ModelEvaluationMetrics,
    ModelTrainingRequest,
)


MODEL_BOUNDARY = (
    "This is a research-use baseline trained on a bounded, endpoint-specific public ChEMBL "
    "snapshot. Scaffold separation reduces structural leakage but does not establish prospective "
    "performance, cellular efficacy, safety, clinical benefit, or institutional validation."
)

ACTIVE_LEARNING_BOUNDARY = (
    "This batch is an information-gain proposal. It does not start an experiment, order a compound, "
    "or replace medicinal-chemistry, biosafety, assay-feasibility and supervisor review."
)


class ModelLabDisabled(RuntimeError):
    pass


class ModelLabInputError(ValueError):
    pass


class ModelTrainingError(ValueError):
    pass


class ModelLabService:
    """Immutable ChEMBL snapshot, leakage-safe baseline and acquisition service."""

    def __init__(
        self,
        repository: Repository,
        *,
        store: ImmutableObjectStore | None = None,
        connector: ChEMBLConnector | None = None,
        chemistry_service: ChemistryService = chemistry,
        enabled: bool | None = None,
    ) -> None:
        self.repository = repository
        self.store = store or object_store
        self.connector = connector
        self.chemistry = chemistry_service
        self.enabled = settings.model_lab_enabled if enabled is None else enabled

    @property
    def remote(self) -> ChEMBLConnector:
        if self.connector is None:
            self.connector = ChEMBLConnector()
        return self.connector

    def capability(self) -> dict[str, object]:
        return {
            "operator_enabled": self.enabled,
            "source": "ChEMBL official Web Services",
            "supported_tasks": ["IC50", "EC50", "Ki", "Kd"],
            "feature_definition": settings.feature_version,
            "baseline": "Morgan ECFP4 2048-bit + class-balanced logistic regression",
            "calibration": "separate scaffold calibration split with Platt scaling",
            "evaluation": "frozen scaffold test split; AUROC, AP, balanced accuracy, Brier and ECE",
            "active_learning": "uncertainty + distance-to-training + QED; greedy diversity",
            "automatic_promotion": False,
            "max_source_records": settings.model_lab_max_records,
            "max_candidate_pool": settings.model_lab_max_candidates,
            "scientific_boundary": MODEL_BOUNDARY,
        }

    def create_snapshot(
        self,
        request: ChEMBLActivitySnapshotRequest,
        actor: str,
    ) -> ActivityDatasetSnapshot:
        if not self.enabled:
            raise ModelLabDisabled(
                "The model laboratory is disabled. Set OSIEL_MODEL_LAB_ENABLED=true only after "
                "reviewing current ChEMBL terms and configuring a contact-bearing User-Agent."
            )
        if request.max_records > settings.model_lab_max_records:
            raise ModelLabInputError(
                f"requested max_records exceeds the server limit of {settings.model_lab_max_records}"
            )
        page = self.remote.activity_records(
            target_chembl_id=request.target_chembl_id,
            standard_type=request.standard_type,
            max_records=request.max_records,
            assay_type=request.assay_type,
            minimum_assay_confidence=request.minimum_assay_confidence,
        )
        return self.create_snapshot_from_page(request, page, actor)

    def create_snapshot_from_page(
        self,
        request: ChEMBLActivitySnapshotRequest,
        page: ChEMBLActivityPage,
        actor: str,
    ) -> ActivityDatasetSnapshot:
        """Normalize a connector page; public for deterministic adapter tests."""

        snapshot_id = self.repository.new_id("ADS")
        raw_payload = {
            "source": "ChEMBL",
            "source_release": page.release,
            "retrieval_request": request.model_dump(mode="json"),
            "request_urls": page.request_urls,
            "records": page.records,
        }
        raw_bytes = json.dumps(
            raw_payload,
            default=str,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        raw_sha, raw_uri = self.store.put(
            raw_bytes,
            f"{snapshot_id}-chembl-raw.json",
            {
                "kind": "chembl-activity-source-snapshot",
                "snapshot_id": snapshot_id,
                "actor": actor,
                "source_release": page.release,
            },
        )

        normalized, counts, warnings = self._normalize_records(request, page.records)
        normalized_bytes = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        normalized_sha, normalized_uri = self.store.put(
            normalized_bytes,
            f"{snapshot_id}-normalized.json",
            {
                "kind": "model-ready-normalized-records",
                "snapshot_id": snapshot_id,
                "actor": actor,
                "raw_sha256": raw_sha,
                "feature_version": settings.feature_version,
            },
        )
        active_count = sum(record["label"] == "active" for record in normalized)
        inactive_count = len(normalized) - active_count
        scaffold_count = len({record["scaffold"] for record in normalized})
        ready = (
            len(normalized) >= 40
            and active_count >= 10
            and inactive_count >= 10
            and scaffold_count >= 6
        )
        if not ready:
            warnings.append(
                "Snapshot is blocked: at least 40 retained records, 10 per class and 6 scaffolds are required."
            )
        if any(record.get("assay_confidence_score") is None for record in normalized):
            warnings.append(
                "ChEMBL did not return assay confidence for every row; the server-side confidence filter remains recorded in the source query."
            )

        snapshot = ActivityDatasetSnapshot(
            snapshot_id=snapshot_id,
            status="ready" if ready else "blocked",
            source_release=page.release,
            target_chembl_id=request.target_chembl_id,
            target_label=request.target_label,
            standard_type=request.standard_type,
            assay_type=request.assay_type,
            active_pchembl_threshold=request.active_pchembl_threshold,
            inactive_pchembl_threshold=request.inactive_pchembl_threshold,
            record_count=len(normalized),
            active_count=active_count,
            inactive_count=inactive_count,
            unique_scaffold_count=scaffold_count,
            ambiguous_removed=counts["ambiguous_removed"],
            invalid_removed=counts["invalid_removed"],
            duplicate_removed=counts["duplicate_removed"],
            conflict_removed=counts["conflict_removed"],
            raw_sha256=raw_sha,
            raw_object_uri=raw_uri,
            normalized_sha256=normalized_sha,
            normalized_object_uri=normalized_uri,
            request_urls=page.request_urls,
            warnings=warnings,
            training_eligible=ready,
            created_at=datetime.now(UTC),
        )
        self.repository.save_activity_snapshot(
            snapshot_id,
            snapshot.status,
            {"snapshot": snapshot.model_dump(mode="json"), "records": normalized},
        )
        self.repository.audit(
            actor,
            "activity_dataset.snapshot_created",
            "activity_dataset_snapshot",
            snapshot_id,
            {
                "status": snapshot.status,
                "target_chembl_id": request.target_chembl_id,
                "endpoint": request.standard_type,
                "record_count": len(normalized),
                "active_count": active_count,
                "inactive_count": inactive_count,
                "scaffold_count": scaffold_count,
                "raw_sha256": raw_sha,
                "normalized_sha256": normalized_sha,
            },
        )
        return snapshot

    def train(
        self,
        request: ModelTrainingRequest,
        actor: str,
    ) -> ActivityModelRun:
        if not self.enabled:
            raise ModelLabDisabled("The model laboratory is disabled by the server operator.")
        stored = self.repository.get_activity_snapshot(request.snapshot_id)
        if not stored:
            raise KeyError("Activity dataset snapshot not found")
        snapshot = ActivityDatasetSnapshot.model_validate(stored["snapshot"])
        records: list[dict[str, Any]] = stored["records"]
        if snapshot.status != "ready" or not snapshot.training_eligible:
            raise ModelTrainingError("Snapshot is blocked and cannot enter model training")
        if len(records) < request.minimum_records:
            raise ModelTrainingError(
                f"Snapshot has {len(records)} records; this run requires {request.minimum_records}"
            )

        model_id = self.repository.new_id("MDL")
        x = np.vstack([self._fingerprint_array(record["canonical_smiles"]) for record in records])
        y = np.asarray([1 if record["label"] == "active" else 0 for record in records], dtype=np.int8)
        groups = np.asarray([record["scaffold"] for record in records], dtype=object)
        train_idx, calibration_idx, test_idx = self._three_way_scaffold_split(
            y,
            groups,
            request.test_fraction,
            request.calibration_fraction,
            request.random_seed,
        )

        base = LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            solver="liblinear",
            random_state=request.random_seed,
        )
        base.fit(x[train_idx], y[train_idx])
        calibration_decision = base.decision_function(x[calibration_idx]).reshape(-1, 1)
        calibrator = LogisticRegression(
            max_iter=1000,
            solver="lbfgs",
            random_state=request.random_seed,
        )
        calibrator.fit(calibration_decision, y[calibration_idx])
        test_decision = base.decision_function(x[test_idx]).reshape(-1, 1)
        probability = calibrator.predict_proba(test_decision)[:, 1]
        predicted = (probability >= 0.5).astype(np.int8)
        metrics = self._metrics(y[test_idx], probability, predicted)

        train_scaffolds = set(groups[train_idx])
        calibration_scaffolds = set(groups[calibration_idx])
        test_scaffolds = set(groups[test_idx])
        overlap = (
            train_scaffolds.intersection(calibration_scaffolds)
            | train_scaffolds.intersection(test_scaffolds)
            | calibration_scaffolds.intersection(test_scaffolds)
        )
        gate_passed = (
            not overlap
            and metrics.test_count >= 20
            and metrics.auroc >= 0.65
            and metrics.expected_calibration_error <= 0.20
        )
        version = f"0.1.{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        artifact = {
            "schema_version": "osiel-activity-linear-1",
            "model_id": model_id,
            "model_name": f"osiel-{snapshot.target_label.lower()}-{snapshot.standard_type.lower()}-baseline",
            "model_version": version,
            "snapshot_id": snapshot.snapshot_id,
            "target_chembl_id": snapshot.target_chembl_id,
            "target_label": snapshot.target_label,
            "endpoint": snapshot.standard_type,
            "feature_version": settings.feature_version,
            "fingerprint_bits": 2048,
            "base_coefficients": base.coef_[0].astype(float).tolist(),
            "base_intercept": float(base.intercept_[0]),
            "platt_coefficient": float(calibrator.coef_[0][0]),
            "platt_intercept": float(calibrator.intercept_[0]),
            "training_smiles": [records[index]["canonical_smiles"] for index in train_idx],
            "training_inchikeys": [records[index]["inchikey"] for index in train_idx],
            "class_threshold": 0.5,
            "created_at": datetime.now(UTC).isoformat(),
        }
        artifact_bytes = json.dumps(
            artifact,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        artifact_sha, artifact_uri = self.store.put(
            artifact_bytes,
            f"{model_id}-linear-model.json",
            {
                "kind": "activity-model-artifact",
                "model_id": model_id,
                "snapshot_id": snapshot.snapshot_id,
                "actor": actor,
            },
        )
        warnings = [
            MODEL_BOUNDARY,
            "Reference gate is an engineering threshold, not institutional or scientific approval.",
            "Promotion remains blocked until a locked external set, independent review and prospective evidence exist.",
        ]
        run = ActivityModelRun(
            model_id=model_id,
            status="completed",
            model_name=artifact["model_name"],
            model_version=version,
            model_type="ECFP4-2048 + class-balanced logistic regression + Platt calibration",
            snapshot_id=snapshot.snapshot_id,
            target_chembl_id=snapshot.target_chembl_id,
            target_label=snapshot.target_label,
            endpoint=snapshot.standard_type,
            feature_version=settings.feature_version,
            split_strategy="three-way Bemis-Murcko scaffold split",
            train_count=len(train_idx),
            calibration_count=len(calibration_idx),
            test_count=len(test_idx),
            train_scaffolds=len(train_scaffolds),
            calibration_scaffolds=len(calibration_scaffolds),
            test_scaffolds=len(test_scaffolds),
            scaffold_overlap_count=len(overlap),
            metrics=metrics,
            artifact_sha256=artifact_sha,
            artifact_object_uri=artifact_uri,
            evaluation_gate="passed-reference-gate" if gate_passed else "failed-reference-gate",
            promotion_eligible=False,
            warnings=warnings,
            created_at=datetime.now(UTC),
        )
        self.repository.save_activity_model(
            model_id,
            run.status,
            snapshot.snapshot_id,
            {"run": run.model_dump(mode="json"), "artifact_object_uri": artifact_uri},
        )
        with self.repository.connection() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO model_version
                (model_id, name, version, alias, status, metrics_json, dataset_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model_id,
                    run.model_name,
                    run.model_version,
                    "challenger",
                    "evaluated-research-use",
                    metrics.model_dump_json(),
                    snapshot.snapshot_id,
                    datetime.now(UTC).isoformat(),
                ),
            )
        self.repository.audit(
            actor,
            "activity_model.training_completed",
            "activity_model_run",
            model_id,
            {
                "snapshot_id": snapshot.snapshot_id,
                "split_strategy": run.split_strategy,
                "scaffold_overlap_count": len(overlap),
                "metrics": metrics.model_dump(),
                "evaluation_gate": run.evaluation_gate,
                "promotion_eligible": False,
                "artifact_sha256": artifact_sha,
            },
        )
        return run

    def predict(
        self,
        request: ActivityModelPredictionRequest,
    ) -> list[ActivityModelPrediction]:
        if len(request.candidates) > settings.model_lab_max_candidates:
            raise ModelLabInputError(
                f"candidate pool exceeds the server limit of {settings.model_lab_max_candidates}"
            )
        stored = self.repository.get_activity_model(request.model_id)
        if not stored:
            raise KeyError("Activity model not found")
        artifact = self._load_artifact(stored["artifact_object_uri"])
        coefficient = np.asarray(artifact["base_coefficients"], dtype=np.float64)
        train_fingerprints = [
            self.chemistry.fingerprint(smiles).value for smiles in artifact["training_smiles"]
        ]
        output: list[ActivityModelPrediction] = []
        for candidate in request.candidates:
            try:
                standardized = self.chemistry.standardize(candidate.smiles)
            except StructureError as exc:
                raise ModelLabInputError(
                    f"candidate {candidate.candidate_id} has an invalid structure: {exc}"
                ) from exc
            vector = self._fingerprint_array(standardized.canonical_smiles)
            base_decision = float(np.dot(coefficient, vector) + artifact["base_intercept"])
            calibrated_decision = (
                artifact["platt_coefficient"] * base_decision + artifact["platt_intercept"]
            )
            probability = self._sigmoid(calibrated_decision)
            query_fingerprint = self.chemistry.fingerprint(standardized.canonical_smiles).value
            similarities = DataStructs.BulkTanimotoSimilarity(query_fingerprint, train_fingerprints)
            nearest = float(max(similarities, default=0.0))
            domain = "inside" if nearest >= 0.40 else "borderline" if nearest >= 0.25 else "outside"
            entropy = self._binary_entropy(probability)
            uncertainty = min(1.0, 0.70 * entropy + 0.30 * (1.0 - nearest))
            warnings = [MODEL_BOUNDARY]
            if domain != "inside":
                warnings.append(
                    f"{domain.capitalize()} applicability domain: nearest training similarity is {nearest:.3f}."
                )
            output.append(
                ActivityModelPrediction(
                    candidate_id=candidate.candidate_id,
                    display_name=candidate.display_name or candidate.candidate_id,
                    canonical_smiles=standardized.canonical_smiles,
                    inchikey=standardized.inchikey,
                    active_probability=round(probability, 4),
                    predicted_class="active" if probability >= artifact["class_threshold"] else "inactive",
                    uncertainty=round(uncertainty, 4),
                    nearest_training_similarity=round(nearest, 4),
                    applicability_domain=domain,
                    model_id=request.model_id,
                    endpoint=artifact["endpoint"],
                    warnings=warnings,
                )
            )
        return output

    def propose_active_learning(
        self,
        request: ActiveLearningRequest,
        actor: str,
    ) -> ActiveLearningBatch:
        predictions = self.predict(
            ActivityModelPredictionRequest(
                model_id=request.model_id,
                candidates=request.candidates,
            )
        )
        by_id = {candidate.candidate_id: candidate for candidate in request.candidates}
        ranked: list[tuple[float, ActivityModelPrediction, object, float]] = []
        for prediction in predictions:
            candidate = by_id[prediction.candidate_id]
            standardized = self.chemistry.standardize(candidate.smiles)
            fingerprint = self.chemistry.fingerprint(standardized.canonical_smiles).value
            acquisition = (
                0.60 * prediction.uncertainty
                + 0.25 * (1.0 - prediction.nearest_training_similarity)
                + 0.15 * standardized.descriptors.qed
            )
            ranked.append((acquisition, prediction, fingerprint, standardized.descriptors.qed))
        ranked.sort(key=lambda item: item[0], reverse=True)

        selected: list[tuple[float, ActivityModelPrediction, object, float, float]] = []
        for acquisition, prediction, fingerprint, qed in ranked:
            max_similarity = max(
                (
                    float(DataStructs.TanimotoSimilarity(fingerprint, chosen[2]))
                    for chosen in selected
                ),
                default=0.0,
            )
            if selected and max_similarity > request.maximum_pair_similarity:
                continue
            selected.append((acquisition, prediction, fingerprint, qed, 1.0 - max_similarity))
            if len(selected) >= request.batch_size:
                break

        suggestions = [
            ActiveLearningSuggestion(
                priority=index,
                candidate_id=prediction.candidate_id,
                display_name=prediction.display_name,
                canonical_smiles=prediction.canonical_smiles,
                active_probability=prediction.active_probability,
                uncertainty=prediction.uncertainty,
                nearest_training_similarity=prediction.nearest_training_similarity,
                diversity_to_selected=round(diversity, 4),
                acquisition_score=round(acquisition * 100, 2),
                reason=(
                    f"High information value: uncertainty {prediction.uncertainty:.2f}, nearest-training "
                    f"similarity {prediction.nearest_training_similarity:.2f}, QED {qed:.2f}, and "
                    f"diversity contribution {diversity:.2f}."
                ),
            )
            for index, (acquisition, prediction, _, qed, diversity) in enumerate(selected, start=1)
        ]
        batch = ActiveLearningBatch(
            batch_id=self.repository.new_id("ALB"),
            model_id=request.model_id,
            candidate_count=len(request.candidates),
            requested_batch_size=request.batch_size,
            suggestions=suggestions,
            selection_policy=(
                "0.60 uncertainty + 0.25 distance-to-training + 0.15 QED; greedy Morgan-fingerprint "
                f"diversity with maximum pair similarity {request.maximum_pair_similarity:.2f}"
            ),
            created_at=datetime.now(UTC),
            scientific_boundary=ACTIVE_LEARNING_BOUNDARY,
        )
        self.repository.save_active_learning_batch(
            batch.batch_id,
            request.model_id,
            batch.model_dump(mode="json"),
        )
        self.repository.audit(
            actor,
            "active_learning.batch_proposed",
            "active_learning_batch",
            batch.batch_id,
            {
                "model_id": request.model_id,
                "candidate_count": len(request.candidates),
                "selected_count": len(suggestions),
                "experiment_started": False,
                "approval_required": True,
            },
        )
        return batch

    def _normalize_records(
        self,
        request: ChEMBLActivitySnapshotRequest,
        records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
        counts = {
            "ambiguous_removed": 0,
            "invalid_removed": 0,
            "duplicate_removed": 0,
            "conflict_removed": 0,
        }
        grouped: dict[str, list[dict[str, Any]]] = {}
        warnings: list[str] = []
        for item in records:
            if str(item.get("target_chembl_id") or "") != request.target_chembl_id:
                counts["invalid_removed"] += 1
                continue
            if str(item.get("standard_type") or "") != request.standard_type:
                counts["invalid_removed"] += 1
                continue
            relation = str(item.get("standard_relation") or "=").strip()
            if relation not in {"=", ""}:
                counts["invalid_removed"] += 1
                continue
            try:
                pchembl_value = float(item["pchembl_value"])
            except (KeyError, TypeError, ValueError):
                counts["invalid_removed"] += 1
                continue
            if pchembl_value >= request.active_pchembl_threshold:
                label = "active"
            elif pchembl_value <= request.inactive_pchembl_threshold:
                label = "inactive"
            else:
                counts["ambiguous_removed"] += 1
                continue
            raw_smiles = item.get("canonical_smiles")
            if not isinstance(raw_smiles, str):
                counts["invalid_removed"] += 1
                continue
            try:
                standardized = self.chemistry.standardize(raw_smiles)
            except StructureError:
                counts["invalid_removed"] += 1
                continue
            confidence_raw = item.get("assay_confidence_score")
            try:
                confidence = int(confidence_raw) if confidence_raw is not None else None
            except (TypeError, ValueError):
                confidence = None
            if confidence is not None and confidence < request.minimum_assay_confidence:
                counts["invalid_removed"] += 1
                continue
            grouped.setdefault(standardized.inchikey, []).append(
                {
                    "source_record_id": str(item.get("activity_id") or "unresolved"),
                    "molecule_chembl_id": str(item.get("molecule_chembl_id") or "unresolved"),
                    "assay_chembl_id": str(item.get("assay_chembl_id") or "unresolved"),
                    "target_chembl_id": request.target_chembl_id,
                    "canonical_smiles": standardized.canonical_smiles,
                    "inchikey": standardized.inchikey,
                    "pchembl_value": pchembl_value,
                    "standard_value": item.get("standard_value"),
                    "standard_units": item.get("standard_units"),
                    "standard_relation": relation or "=",
                    "standard_type": request.standard_type,
                    "assay_type": str(item.get("assay_type") or request.assay_type),
                    "assay_confidence_score": confidence,
                    "label": label,
                    "scaffold": self._scaffold(standardized.canonical_smiles, standardized.inchikey),
                }
            )

        normalized: list[dict[str, Any]] = []
        for values in grouped.values():
            labels = {value["label"] for value in values}
            if len(labels) > 1:
                counts["conflict_removed"] += len(values)
                continue
            median = statistics.median(value["pchembl_value"] for value in values)
            representative = min(values, key=lambda value: abs(value["pchembl_value"] - median))
            representative = {**representative, "pchembl_value": round(float(median), 4)}
            normalized.append(representative)
            counts["duplicate_removed"] += len(values) - 1
        normalized.sort(key=lambda value: (value["inchikey"], value["source_record_id"]))
        if not normalized:
            warnings.append("No exact, threshold-separated, standardizable records were retained.")
        return normalized, counts, warnings

    @staticmethod
    def _scaffold(smiles: str, inchikey: str) -> str:
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            return f"INVALID-{inchikey}"
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=molecule, includeChirality=True)
        return scaffold or f"ACYCLIC-{inchikey[:14]}"

    def _fingerprint_array(self, smiles: str) -> np.ndarray:
        fingerprint = self.chemistry.fingerprint(smiles).value
        array = np.zeros((2048,), dtype=np.float64)
        DataStructs.ConvertToNumpyArray(fingerprint, array)
        return array

    @staticmethod
    def _three_way_scaffold_split(
        y: np.ndarray,
        groups: np.ndarray,
        test_fraction: float,
        calibration_fraction: float,
        seed: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        indices = np.arange(len(y))
        if len(set(groups)) < 6:
            raise ModelTrainingError("At least six unique scaffolds are required")
        outer = GroupShuffleSplit(n_splits=64, test_size=test_fraction, random_state=seed)
        for train_cal_idx, test_idx in outer.split(indices, y, groups):
            if len(set(y[test_idx])) < 2 or len(test_idx) < 6:
                continue
            relative_calibration = calibration_fraction / (1.0 - test_fraction)
            inner = GroupShuffleSplit(
                n_splits=64,
                test_size=relative_calibration,
                random_state=seed + 17,
            )
            inner_indices = np.arange(len(train_cal_idx))
            inner_y = y[train_cal_idx]
            inner_groups = groups[train_cal_idx]
            for train_local, calibration_local in inner.split(
                inner_indices,
                inner_y,
                inner_groups,
            ):
                train_idx = train_cal_idx[train_local]
                calibration_idx = train_cal_idx[calibration_local]
                if min(len(train_idx), len(calibration_idx)) < 6:
                    continue
                if len(set(y[train_idx])) < 2 or len(set(y[calibration_idx])) < 2:
                    continue
                return train_idx, calibration_idx, test_idx
        raise ModelTrainingError(
            "Could not create class-complete, non-overlapping train/calibration/test scaffold splits"
        )

    @staticmethod
    def _metrics(
        truth: np.ndarray,
        probability: np.ndarray,
        predicted: np.ndarray,
    ) -> ModelEvaluationMetrics:
        matrix = confusion_matrix(truth, predicted, labels=[0, 1])
        tn, fp, fn, tp = (int(value) for value in matrix.ravel())
        sensitivity = tp / max(1, tp + fn)
        specificity = tn / max(1, tn + fp)
        return ModelEvaluationMetrics(
            auroc=round(float(roc_auc_score(truth, probability)), 4),
            average_precision=round(float(average_precision_score(truth, probability)), 4),
            balanced_accuracy=round(float(balanced_accuracy_score(truth, predicted)), 4),
            sensitivity=round(sensitivity, 4),
            specificity=round(specificity, 4),
            brier_score=round(float(brier_score_loss(truth, probability)), 4),
            expected_calibration_error=round(
                ModelLabService._expected_calibration_error(truth, probability),
                4,
            ),
            test_prevalence=round(float(np.mean(truth)), 4),
            test_count=len(truth),
        )

    @staticmethod
    def _expected_calibration_error(
        truth: np.ndarray,
        probability: np.ndarray,
        bins: int = 10,
    ) -> float:
        total = len(truth)
        error = 0.0
        boundaries = np.linspace(0.0, 1.0, bins + 1)
        for index in range(bins):
            lower, upper = boundaries[index], boundaries[index + 1]
            selected = (probability >= lower) & (
                probability <= upper if index == bins - 1 else probability < upper
            )
            count = int(np.sum(selected))
            if count == 0:
                continue
            confidence = float(np.mean(probability[selected]))
            accuracy = float(np.mean(truth[selected]))
            error += count / total * abs(confidence - accuracy)
        return error

    def _load_artifact(self, uri: str) -> dict[str, Any]:
        content = self.store.get(uri)
        payload = json.loads(content)
        if payload.get("schema_version") != "osiel-activity-linear-1":
            raise ModelLabInputError("Unsupported activity-model artifact schema")
        return payload

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0:
            return 1.0 / (1.0 + math.exp(-value))
        exponential = math.exp(value)
        return exponential / (1.0 + exponential)

    @staticmethod
    def _binary_entropy(probability: float) -> float:
        bounded = min(1.0 - 1e-12, max(1e-12, probability))
        return float(
            -(
                bounded * math.log(bounded)
                + (1.0 - bounded) * math.log(1.0 - bounded)
            )
            / math.log(2.0)
        )
