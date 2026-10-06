from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from statistics import mean

from .prediction import DemoPredictionService
from .repository import Repository
from .schemas import (
    DatasetSnapshot,
    Experiment,
    ExperimentCreate,
    ExperimentResult,
    ResultApproval,
    SimulatedObservation,
)


class ExperimentService:
    def __init__(self, repository: Repository, predictor: DemoPredictionService) -> None:
        self.repository = repository
        self.predictor = predictor

    def create(self, protocol: ExperimentCreate, actor: str = "demo-researcher") -> Experiment:
        if protocol.dose_max_um <= protocol.dose_min_um:
            raise ValueError("dose_max_um must be greater than dose_min_um")
        if len(self.repository.get_compounds(protocol.compound_ids)) != len(protocol.compound_ids):
            raise ValueError("One or more compounds could not be resolved")
        experiment = Experiment(
            experiment_id=self.repository.new_id("EXP"),
            status="planned",
            simulation_only=True,
            protocol=protocol,
            created_at=datetime.now(UTC),
            created_by=actor,
        )
        with self.repository.connection() as connection:
            connection.execute(
                "INSERT INTO experiment VALUES (?, ?, ?, ?, ?, ?)",
                (
                    experiment.experiment_id,
                    experiment.status,
                    1,
                    protocol.model_dump_json(),
                    experiment.created_at.isoformat(),
                    actor,
                ),
            )
        self.repository.audit(
            actor,
            "experiment.created",
            "experiment",
            experiment.experiment_id,
            {"simulation_only": True, "compound_count": len(protocol.compound_ids)},
        )
        return experiment

    def get(self, experiment_id: str) -> Experiment | None:
        with self.repository.connection() as connection:
            row = connection.execute(
                "SELECT * FROM experiment WHERE experiment_id = ?", (experiment_id,)
            ).fetchone()
        if not row:
            return None
        return Experiment(
            experiment_id=row["experiment_id"],
            status=row["status"],
            simulation_only=bool(row["simulation_only"]),
            protocol=ExperimentCreate.model_validate_json(row["protocol_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            created_by=row["created_by"],
        )

    def list(self, limit: int = 50) -> list[Experiment]:
        with self.repository.connection() as connection:
            ids = [
                row[0]
                for row in connection.execute(
                    "SELECT experiment_id FROM experiment ORDER BY created_at DESC LIMIT ?",
                    (min(limit, 200),),
                ).fetchall()
            ]
        return [item for item in (self.get(value) for value in ids) if item]

    def results(self, experiment_id: str) -> list[ExperimentResult]:
        if self.get(experiment_id) is None:
            raise KeyError("Experiment not found")
        with self.repository.connection() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM experiment_result WHERE experiment_id = ? ORDER BY created_at DESC",
                (experiment_id,),
            ).fetchall()
        return [ExperimentResult.model_validate_json(row["payload_json"]) for row in rows]

    def simulate(self, experiment_id: str) -> ExperimentResult:
        experiment = self.get(experiment_id)
        if experiment is None:
            raise KeyError("Experiment not found")
        protocol = experiment.protocol
        compounds = self.repository.get_compounds(protocol.compound_ids)
        doses = self._logspace(protocol.dose_min_um, protocol.dose_max_um, protocol.dose_points)
        observations: list[SimulatedObservation] = []
        ic50s: dict[str, float] = {}

        for compound in compounds:
            prediction = self.predictor.predict(compound, protocol.cancer_type, protocol.cell_line, protocol.endpoint)
            ic50 = max(protocol.dose_min_um, min(protocol.dose_max_um, prediction.predicted_ic50_um))
            ic50s[compound.compound_id] = round(ic50, 4)
            for dose in doses:
                for replicate in range(1, protocol.replicates + 1):
                    noise = self._noise(experiment_id, compound.compound_id, dose, replicate)
                    hill = 1.05 + (replicate - 1) * 0.03
                    viability = 100 / (1 + (dose / max(ic50, 1e-6)) ** hill)
                    observations.append(
                        SimulatedObservation(
                            compound_id=compound.compound_id,
                            dose_um=round(dose, 6),
                            replicate=replicate,
                            viability_percent=round(max(0.0, min(100.0, viability + noise)), 3),
                        )
                    )

        per_dose_groups: dict[tuple[str, float], list[float]] = {}
        for observation in observations:
            per_dose_groups.setdefault(
                (observation.compound_id, observation.dose_um), []
            ).append(observation.viability_percent)
        consistency = all(
            max(values) - min(values) <= 18 for values in per_dose_groups.values() if len(values) > 1
        )
        range_check = all(0 <= value <= 100 for values in per_dose_groups.values() for value in values)
        result = ExperimentResult(
            result_id=self.repository.new_id("RES"),
            experiment_id=experiment_id,
            simulation_only=True,
            observations=observations,
            estimated_ic50_um=ic50s,
            qc_status="passed" if consistency and range_check else "failed",
            qc_checks={
                "replicate_consistency": consistency,
                "viability_range": range_check,
                "positive_control_present": bool(protocol.positive_control),
                "negative_control_present": bool(protocol.negative_control),
                "minimum_replicates": protocol.replicates >= 2,
            },
            created_at=datetime.now(UTC),
            disclaimer=(
                "Computational dry-run only. No physical assay, biological sample or wet-lab "
                "measurement was performed. These observations test software flow and must never "
                "be used as efficacy evidence."
            ),
        )
        with self.repository.connection() as connection:
            connection.execute(
                "INSERT INTO experiment_result VALUES (?, ?, ?, ?, NULL, NULL, 0, ?)",
                (
                    result.result_id,
                    experiment_id,
                    "qc-passed" if result.qc_status == "passed" else "qc-failed",
                    result.model_dump_json(),
                    result.created_at.isoformat(),
                ),
            )
            connection.execute(
                "UPDATE experiment SET status = ? WHERE experiment_id = ?",
                ("simulated", experiment_id),
            )
        self.repository.audit(
            "osiel-simulator",
            "experiment.simulated",
            "experiment_result",
            result.result_id,
            {"experiment_id": experiment_id, "simulation_only": True, "qc": result.qc_status},
        )
        return result

    def approve(self, result_id: str, approval: ResultApproval) -> DatasetSnapshot | dict[str, str]:
        with self.repository.connection() as connection:
            row = connection.execute(
                "SELECT * FROM experiment_result WHERE result_id = ?", (result_id,)
            ).fetchone()
        if not row:
            raise KeyError("Result not found")
        payload = ExperimentResult.model_validate_json(row["payload_json"])
        if payload.simulation_only and approval.training_eligible:
            raise ValueError("Simulation-only results can never become training eligible")

        status = "approved" if approval.decision == "approve" else "rejected"
        with self.repository.connection() as connection:
            connection.execute(
                """UPDATE experiment_result SET status = ?, approved_by = ?,
                approval_reason = ?, training_eligible = ? WHERE result_id = ?""",
                (
                    status,
                    approval.reviewer,
                    approval.reason,
                    int(approval.training_eligible),
                    result_id,
                ),
            )
        self.repository.audit(
            approval.reviewer,
            f"experiment.result.{status}",
            "experiment_result",
            result_id,
            {"training_eligible": approval.training_eligible, "simulation_only": payload.simulation_only},
        )
        if not approval.training_eligible:
            return {"status": status, "training_eligible": "false", "model_mutated": "false"}
        return self.create_snapshot([result_id])

    def create_snapshot(self, result_ids: list[str]) -> DatasetSnapshot:
        with self.repository.connection() as connection:
            rows = connection.execute(
                f"SELECT result_id, payload_json, training_eligible FROM experiment_result WHERE result_id IN ({','.join('?' for _ in result_ids)})",
                result_ids,
            ).fetchall()
        eligible = [row for row in rows if row["training_eligible"]]
        if len(eligible) != len(result_ids):
            raise ValueError("All source results must be scientifically approved and training eligible")
        version_number = 1
        with self.repository.connection() as connection:
            version_number += int(connection.execute("SELECT COUNT(*) FROM dataset_snapshot").fetchone()[0])
        checksum = self.repository.checksum([json.loads(row["payload_json"]) for row in eligible])
        snapshot = DatasetSnapshot(
            snapshot_id=self.repository.new_id("DSN"),
            dataset_version=f"osiel-experimental-v{version_number}",
            source_result_ids=result_ids,
            status="proposed",
            record_count=sum(
                len(ExperimentResult.model_validate_json(row["payload_json"]).observations)
                for row in eligible
            ),
            checksum=checksum,
            created_at=datetime.now(UTC),
            model_mutated=False,
        )
        self.repository.save_json_record(
            "dataset_snapshot",
            "snapshot_id",
            snapshot.snapshot_id,
            snapshot.model_dump(mode="json"),
            dataset_version=snapshot.dataset_version,
        )
        return snapshot

    @staticmethod
    def _logspace(start: float, stop: float, count: int) -> list[float]:
        low = math.log10(start)
        high = math.log10(stop)
        return [10 ** (low + (high - low) * index / (count - 1)) for index in range(count)]

    @staticmethod
    def _noise(experiment_id: str, compound_id: str, dose: float, replicate: int) -> float:
        digest = hashlib.sha256(
            f"{experiment_id}|{compound_id}|{dose:.8f}|{replicate}".encode()
        ).digest()
        return (int.from_bytes(digest[:2], "big") / 65535 - 0.5) * 5.0


def summarize_observations(result: ExperimentResult) -> dict[str, float]:
    groups: dict[str, list[float]] = {}
    for observation in result.observations:
        groups.setdefault(observation.compound_id, []).append(observation.viability_percent)
    return {compound_id: round(mean(values), 3) for compound_id, values in groups.items()}
