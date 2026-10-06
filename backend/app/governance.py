from __future__ import annotations

import json
from datetime import UTC, datetime

from .repository import Repository


class ModelGovernanceService:
    """Champion/challenger registry with an explicit human approval boundary."""

    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self._ensure_demo_models()

    def _ensure_demo_models(self) -> None:
        now = datetime.now(UTC).isoformat()
        records = [
            (
                "MDL-RESEARCH-SIM-1",
                "OSIEL Research Activity Model",
                "1.0",
                "research",
                "active-research-simulation",
                {"validated": False, "model_class": "synthetic_research_simulation", "validation_status": "unvalidated", "intended_use": "research_showcase"},
                "reference-molecular-registry",
            ),
            (
                "MDL-DEMO-CHAMPION",
                "osiel-demo-baseline",
                "1.0.0",
                "champion",
                "approved-demo",
                {"auprc": 0.0, "calibration_error": 0.0, "validated": False, "demo_adapter": True},
                "nci-reference-structures-demo-1.0.0",
            ),
            (
                "MDL-DEMO-CHALLENGER",
                "osiel-demo-baseline",
                "1.1.0-candidate",
                "challenger",
                "evaluation-required",
                {"auprc": 0.0, "calibration_error": 0.0, "validated": False, "demo_adapter": True},
                "nci-reference-structures-demo-1.0.0",
            ),
        ]
        with self.repository.connection() as connection:
            for model_id, name, version, alias, status, metrics, dataset, in records:
                connection.execute(
                    """INSERT OR IGNORE INTO model_version
                    (model_id, name, version, alias, status, metrics_json, dataset_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (model_id, name, version, alias, status, json.dumps(metrics), dataset, now),
                )

    def list_models(self) -> list[dict[str, object]]:
        with self.repository.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM model_version ORDER BY created_at, version"
            ).fetchall()
        return [
            {
                **dict(row),
                "metrics": json.loads(row["metrics_json"]),
                "research_use_only": True,
            }
            for row in rows
        ]

    def evaluate_challenger(self) -> dict[str, object]:
        report = {
            "evaluation_id": self.repository.new_id("EVAL"),
            "challenger_model_id": "MDL-DEMO-CHALLENGER",
            "champion_model_id": "MDL-DEMO-CHAMPION",
            "frozen_external_set": False,
            "prospective_results": False,
            "leakage_audit": "not-run",
            "calibration_gate": "not-run",
            "subgroup_gate": "not-run",
            "decision": "promotion-blocked",
            "reason": (
                "The demonstration adapter has no validated endpoint labels, locked external set or "
                "prospective evidence. A production model cannot be promoted from this dry-run."
            ),
            "model_mutated": False,
        }
        self.repository.audit(
            "ml-reviewer",
            "model.challenger_evaluated",
            "model_version",
            "MDL-DEMO-CHALLENGER",
            report,
        )
        return report

    def approve(self, model_id: str, reviewer: str, reason: str) -> dict[str, object]:
        if model_id.startswith("MDL-DEMO"):
            return {
                "model_id": model_id,
                "approved": False,
                "deployment_started": False,
                "reason": "Demonstration adapters cannot be promoted to a production scientific model.",
            }
        with self.repository.connection() as connection:
            row = connection.execute(
                "SELECT * FROM model_version WHERE model_id = ?", (model_id,)
            ).fetchone()
            if not row:
                raise KeyError("Model version not found")
            connection.execute(
                "UPDATE model_version SET status = ? WHERE model_id = ?",
                ("approved-awaiting-deployment", model_id),
            )
        self.repository.audit(
            reviewer,
            "model.approved",
            "model_version",
            model_id,
            {"reason": reason, "deployment_started": False},
        )
        return {
            "model_id": model_id,
            "approved": True,
            "deployment_started": False,
            "reason": reason,
        }
