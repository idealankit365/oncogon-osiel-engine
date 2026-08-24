from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.config import settings
from app.open_discovery import OpenDiscoveryService
from app.repository import Repository
from app.schemas import OpenDiscoveryRequest


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="osiel-open-discovery-") as temporary:
        repository = Repository(Path(temporary) / "verification.db")
        reference_count = repository.seed(settings.seed_path)
        service = OpenDiscoveryService(
            repository,
            allow_public_connectors=False,
            detect_vina=False,
        )
        run = service.run(
            OpenDiscoveryRequest(
                disease="Non-small cell lung cancer",
                target_symbol="EGFR",
                seed_compound_name="Gefitinib",
                candidate_limit=8,
                public_connectors=False,
            ),
            actor="e2e-verifier",
        )

        assert reference_count >= 180
        assert len(run.events) == 10
        assert len(run.candidates) == 8
        assert run.docking.status == "not-run"
        assert run.docking.result_score_kcal_mol is None
        assert repository.get_open_discovery_run(run.run_id) is not None

        report = {
            "scenario": "OSIEL public-source open-discovery verification",
            "run_id": run.run_id,
            "status": run.status,
            "reference_compounds": reference_count,
            "execution_mode": run.execution_mode,
            "workflow_stages": [
                {
                    "sequence": event.sequence,
                    "stage": event.stage,
                    "status": event.status,
                    "duration_ms": event.duration_ms,
                }
                for event in run.events
            ],
            "top_candidates": [
                {
                    "rank": candidate.rank,
                    "compound_id": candidate.compound_id,
                    "display_name": candidate.display_name,
                    "similarity_to_seed": candidate.similarity_to_seed,
                    "priority_score": candidate.priority_score,
                    "disposition": candidate.disposition,
                }
                for candidate in run.candidates
            ],
            "docking": {
                "status": run.docking.status,
                "result_score_kcal_mol": run.docking.result_score_kcal_mol,
                "missing_inputs": run.docking.missing_inputs,
            },
            "claim_boundary": run.claim_boundary,
            "verified": True,
        }
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

