from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from app.config import settings
from app.connectors.chembl import ChEMBLActivityPage
from app.immutable_storage import ImmutableObjectStore
from app.model_lab import ModelLabService
from app.repository import Repository
from app.schemas import (
    ActiveLearningRequest,
    ChEMBLActivitySnapshotRequest,
    ModelPredictionItem,
    ModelTrainingRequest,
)


def software_fixture(repository: Repository) -> ChEMBLActivityPage:
    scaffolds: dict[str, int] = {}
    records = []
    for index, compound in enumerate(repository.list_compounds(limit=190), start=1):
        scaffold = ModelLabService._scaffold(compound.canonical_smiles, compound.inchikey)
        scaffolds.setdefault(scaffold, len(scaffolds))
        active = scaffolds[scaffold] % 2 == 0
        records.append(
            {
                "activity_id": f"SOFTWARE-{index}",
                "molecule_chembl_id": f"SOFTWARE-COMPOUND-{index}",
                "assay_chembl_id": "SOFTWARE-ASSAY",
                "target_chembl_id": "CHEMBL203",
                "canonical_smiles": compound.canonical_smiles,
                "pchembl_value": 7.2 if active else 4.3,
                "standard_type": "IC50",
                "standard_relation": "=",
                "standard_value": 63 if active else 50_000,
                "standard_units": "nM",
                "assay_type": "B",
                "assay_confidence_score": 9,
            }
        )
    return ChEMBLActivityPage(
        records=records,
        release="SOFTWARE_TEST_FIXTURE_NOT_EXPERIMENTAL",
        request_urls=["local://software-test-fixture"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="retrieve a bounded real ChEMBL activity slice instead of the software-only fixture",
    )
    parser.add_argument("--max-records", type=int, default=1000)
    arguments = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="osiel-model-lab-") as temporary:
        root = Path(temporary)
        repository = Repository(root / "osiel.db")
        repository.seed(settings.seed_path)
        service = ModelLabService(
            repository,
            store=ImmutableObjectStore(root / "objects"),
            enabled=True,
        )
        snapshot_request = ChEMBLActivitySnapshotRequest(
            max_records=arguments.max_records if arguments.live else 190
        )
        if arguments.live:
            snapshot = service.create_snapshot(snapshot_request, "e2e-researcher")
        else:
            snapshot = service.create_snapshot_from_page(
                snapshot_request,
                software_fixture(repository),
                "e2e-software-test",
            )
        minimum_records = 100 if arguments.live else 80
        run = service.train(
            ModelTrainingRequest(
                snapshot_id=snapshot.snapshot_id,
                minimum_records=minimum_records,
            ),
            "e2e-ml-reviewer",
        )
        candidates = [
            ModelPredictionItem(
                candidate_id=compound.compound_id,
                display_name=compound.display_name,
                smiles=compound.canonical_smiles,
            )
            for compound in repository.list_compounds(limit=18)
        ]
        batch = service.propose_active_learning(
            ActiveLearningRequest(
                model_id=run.model_id,
                candidates=candidates,
                batch_size=6,
                maximum_pair_similarity=0.80,
            ),
            "e2e-researcher",
        )
        print(
            json.dumps(
                {
                    "input_mode": "live-chembl" if arguments.live else "software-test-fixture",
                    "snapshot": {
                        "id": snapshot.snapshot_id,
                        "release": snapshot.source_release,
                        "records": snapshot.record_count,
                        "active": snapshot.active_count,
                        "inactive": snapshot.inactive_count,
                        "scaffolds": snapshot.unique_scaffold_count,
                        "normalized_sha256": snapshot.normalized_sha256,
                    },
                    "model": {
                        "id": run.model_id,
                        "split": [run.train_count, run.calibration_count, run.test_count],
                        "scaffold_overlap": run.scaffold_overlap_count,
                        "metrics": run.metrics.model_dump() if run.metrics else None,
                        "evaluation_gate": run.evaluation_gate,
                        "promotion_eligible": run.promotion_eligible,
                    },
                    "active_learning": {
                        "batch_id": batch.batch_id,
                        "proposed": len(batch.suggestions),
                        "experiment_started": batch.experiment_started,
                    },
                    "wet_lab_performed": False,
                    "claim": (
                        "Live mode uses public ChEMBL records; fixture mode tests software only. "
                        "Neither mode establishes prospective biological performance."
                    ),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
