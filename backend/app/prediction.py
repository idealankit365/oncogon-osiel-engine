from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime

from .chemistry import chemistry
from .config import settings
from .repository import Repository
from .schemas import ADMETEndpoint, AnalogEvidence, Compound, Prediction


def _stable_unit_interval(*parts: str) -> float:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / (2**64 - 1)


class ADMETService:
    """A transparent Phase-1 rule panel; replaceable by the isolated ADMET-AI adapter.

    The adapter intentionally reports predicted screening signals rather than safety claims.
    """

    version = "osiel-admet-rule-panel-1.0.0"

    def evaluate(self, compound: Compound) -> list[ADMETEndpoint]:
        d = compound.descriptors
        domain_penalty = self._domain_penalty(compound)
        domain = "outside" if domain_penalty > 0.5 else "borderline" if domain_penalty > 0.2 else "inside"
        confidence = round(max(0.35, 0.9 - domain_penalty), 3)

        absorption_score = max(
            0.05,
            min(0.98, 0.92 - max(d.molecular_weight - 420, 0) / 650 - max(d.tpsa - 100, 0) / 220),
        )
        solubility_score = max(
            0.03,
            min(0.98, 0.86 - max(d.clogp - 2, 0) * 0.12 - max(d.molecular_weight - 380, 0) / 1000),
        )
        herg_risk = max(0.03, min(0.95, 0.10 + max(d.clogp - 3, 0) * 0.13 + d.ring_count * 0.025))
        liver_signal = max(
            0.04,
            min(0.92, 0.12 + max(d.clogp - 3.5, 0) * 0.11 + max(d.molecular_weight - 500, 0) / 900),
        )
        bbb = max(0.02, min(0.95, 0.78 - d.tpsa / 180 + max(d.clogp, 0) / 14))

        def endpoint(code: str, label: str, value: float, positive: str, negative: str) -> ADMETEndpoint:
            classification = positive if value >= 0.62 else negative if value < 0.38 else "Moderate"
            return ADMETEndpoint(
                code=code,
                label=label,
                predicted_value=round(value, 3),
                unit="probability",
                classification=classification,
                confidence=confidence,
                applicability_domain=domain,
                model_version=self.version,
            )

        return [
            endpoint("absorption", "Predicted absorption", absorption_score, "High", "Low"),
            endpoint("solubility", "Predicted solubility", solubility_score, "Favourable", "Low"),
            endpoint("herg", "Predicted hERG signal", herg_risk, "Higher risk", "Lower risk"),
            endpoint("liver", "Predicted liver-toxicity signal", liver_signal, "Higher signal", "Lower signal"),
            endpoint("bbb", "Predicted BBB permeation", bbb, "Likely", "Unlikely"),
        ]

    @staticmethod
    def _domain_penalty(compound: Compound) -> float:
        d = compound.descriptors
        penalties = [
            max(0.0, (d.molecular_weight - 650) / 600),
            max(0.0, (-2.0 - d.clogp) / 5),
            max(0.0, (d.clogp - 7.0) / 5),
            max(0.0, (d.tpsa - 180) / 180),
            max(0.0, (d.rotatable_bonds - 15) / 15),
        ]
        return min(1.0, sum(penalties))


class DemoPredictionService:
    """Deterministic research-workflow simulator used until a validated model is mounted.

    This service is deliberately labelled as a demo model. It exercises structure,
    uncertainty, ADMET, evidence, ranking, experiment and governance contracts without
    pretending that descriptor heuristics are validated oncology efficacy models.
    """

    dataset_version = "nci-reference-structures-demo-1.0.0"

    def __init__(self, repository: Repository, admet_service: ADMETService | None = None) -> None:
        self.repository = repository
        self.admet_service = admet_service or ADMETService()

    def predict(
        self,
        compound: Compound,
        cancer_type: str,
        cell_line: str | None = None,
        endpoint: str = "activity_probability",
    ) -> Prediction:
        d = compound.descriptors
        hashed = _stable_unit_interval(compound.inchikey, cancer_type.lower(), cell_line or "")
        druglike = min(1.0, max(0.0, d.qed))
        property_fit = 1.0 - min(
            0.85,
            abs(d.clogp - 2.4) / 8
            + max(d.molecular_weight - 520, 0) / 1000
            + max(d.tpsa - 145, 0) / 300,
        )
        activity = min(0.97, max(0.12, 0.26 + 0.34 * druglike + 0.24 * property_fit + 0.16 * hashed))
        domain_penalty = ADMETService._domain_penalty(compound)
        uncertainty = min(0.72, 0.12 + 0.36 * domain_penalty + 0.12 * abs(hashed - 0.5))
        confidence = 1.0 - uncertainty
        domain = "outside" if domain_penalty > 0.5 else "borderline" if domain_penalty > 0.2 else "inside"
        log_ic50 = 1.25 - 2.35 * activity + 0.32 * uncertainty
        ic50 = max(0.004, min(200.0, 10**log_ic50))
        selectivity = max(1.0, min(40.0, 1.5 + 26 * activity * property_fit * (0.65 + hashed * 0.35)))
        width = max(0.08, uncertainty * 0.9)
        analogs = self._nearest_analogs(compound)
        admet = self.admet_service.evaluate(compound)

        prediction = Prediction(
            prediction_id=self.repository.new_id("PRD"),
            compound_id=compound.compound_id,
            display_name=compound.display_name,
            cancer_type=cancer_type,
            cell_line=cell_line,
            endpoint=endpoint,
            predicted_activity=round(activity, 4),
            predicted_ic50_um=round(ic50, 4),
            predicted_selectivity_index=round(selectivity, 3),
            uncertainty=round(uncertainty, 4),
            confidence=round(confidence, 4),
            applicability_domain=domain,
            interval_low=round(max(0.0, activity - width), 4),
            interval_high=round(min(1.0, activity + width), 4),
            model_version=settings.model_version,
            dataset_version=self.dataset_version,
            feature_version=settings.feature_version,
            standardization_version=settings.standardization_version,
            nearest_analogs=analogs,
            admet=admet,
            evidence_summary=(
                f"{compound.source_name} reference structure; {compound.evidence_grade}-grade "
                f"identity evidence. Activity value is produced by the OSIEL demo adapter, not "
                "by a validated oncology model or laboratory assay."
            ),
            created_at=datetime.now(UTC),
        )
        self.repository.save_json_record(
            "prediction",
            "prediction_id",
            prediction.prediction_id,
            prediction.model_dump(mode="json"),
            compound_id=compound.compound_id,
        )
        self.repository.audit(
            "demo-researcher",
            "prediction.completed",
            "prediction",
            prediction.prediction_id,
            {
                "compound_id": compound.compound_id,
                "model_version": settings.model_version,
                "demo_mode": True,
            },
        )
        return prediction

    def _nearest_analogs(self, query: Compound, limit: int = 3) -> list[AnalogEvidence]:
        candidates = self.repository.list_compounds(limit=80)
        similarities: list[tuple[float, Compound]] = []
        for candidate in candidates:
            if candidate.compound_id == query.compound_id:
                continue
            try:
                similarity = chemistry.similarity(query.canonical_smiles, candidate.canonical_smiles)
            except Exception:
                continue
            similarities.append((similarity, candidate))
        similarities.sort(key=lambda item: item[0], reverse=True)
        return [
            AnalogEvidence(
                compound_id=candidate.compound_id,
                display_name=candidate.display_name,
                tanimoto_similarity=round(similarity, 4),
                source_name=candidate.source_name,
            )
            for similarity, candidate in similarities[:limit]
        ]


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))

