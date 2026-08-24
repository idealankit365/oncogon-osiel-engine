from __future__ import annotations

from pathlib import Path

from app.connectors.chembl import ChEMBLActivityPage
from app.immutable_storage import ImmutableObjectStore
from app.model_lab import ModelLabService
from app.repository import Repository
from app.schemas import (
    ActiveLearningRequest,
    ActivityModelPredictionRequest,
    ChEMBLActivitySnapshotRequest,
    ModelPredictionItem,
    ModelTrainingRequest,
)


def activity_page(repository: Repository) -> ChEMBLActivityPage:
    compounds = repository.list_compounds(limit=190)
    scaffolds: dict[str, int] = {}
    records = []
    for index, compound in enumerate(compounds, start=1):
        scaffold = ModelLabService._scaffold(compound.canonical_smiles, compound.inchikey)
        if scaffold not in scaffolds:
            scaffolds[scaffold] = len(scaffolds)
        active = scaffolds[scaffold] % 2 == 0
        records.append(
            {
                "activity_id": f"ACT-{index}",
                "molecule_chembl_id": f"CHEMBL{100000 + index}",
                "assay_chembl_id": f"CHEMBL{200000 + index}",
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
        release="CHEMBL_TEST_SOFTWARE_FIXTURE",
        request_urls=["https://www.ebi.ac.uk/chembl/api/data/activity.json?software-test"],
    )


def test_scaffold_training_prediction_and_active_learning(
    repository: Repository,
    tmp_path: Path,
) -> None:
    store = ImmutableObjectStore(tmp_path / "objects")
    service = ModelLabService(repository, store=store, enabled=True)
    snapshot_request = ChEMBLActivitySnapshotRequest(max_records=190)
    snapshot = service.create_snapshot_from_page(
        snapshot_request,
        activity_page(repository),
        "test-researcher",
    )
    assert snapshot.status == "ready"
    assert snapshot.record_count >= 100
    assert snapshot.active_count > 0
    assert snapshot.inactive_count > 0
    assert store.get(snapshot.normalized_object_uri)

    run = service.train(
        ModelTrainingRequest(snapshot_id=snapshot.snapshot_id, minimum_records=80),
        "test-ml-reviewer",
    )
    assert run.status == "completed"
    assert run.scaffold_overlap_count == 0
    assert run.metrics is not None
    assert run.metrics.test_count == run.test_count
    assert run.promotion_eligible is False
    assert run.artifact_object_uri
    assert store.get(run.artifact_object_uri)

    candidates = [
        ModelPredictionItem(
            candidate_id=compound.compound_id,
            display_name=compound.display_name,
            smiles=compound.canonical_smiles,
        )
        for compound in repository.list_compounds(limit=16)
    ]
    predictions = service.predict(
        ActivityModelPredictionRequest(model_id=run.model_id, candidates=candidates)
    )
    assert len(predictions) == len(candidates)
    assert all(0 <= item.active_probability <= 1 for item in predictions)
    assert all(item.endpoint == "IC50" for item in predictions)

    batch = service.propose_active_learning(
        ActiveLearningRequest(
            model_id=run.model_id,
            candidates=candidates,
            batch_size=5,
            maximum_pair_similarity=0.90,
        ),
        "test-researcher",
    )
    assert batch.status == "proposed"
    assert 2 <= len(batch.suggestions) <= 5
    assert batch.approval_required is True
    assert batch.experiment_started is False


def test_snapshot_removes_grey_zone_and_conflicting_duplicates(
    repository: Repository,
    tmp_path: Path,
) -> None:
    compound = repository.list_compounds(limit=1)[0]
    base = {
        "molecule_chembl_id": "CHEMBL1",
        "assay_chembl_id": "CHEMBL2",
        "target_chembl_id": "CHEMBL203",
        "canonical_smiles": compound.canonical_smiles,
        "standard_type": "IC50",
        "standard_relation": "=",
        "standard_units": "nM",
        "assay_type": "B",
        "assay_confidence_score": 9,
    }
    page = ChEMBLActivityPage(
        records=[
            {**base, "activity_id": "A1", "pchembl_value": 7.0},
            {**base, "activity_id": "A2", "pchembl_value": 4.0},
            {**base, "activity_id": "A3", "pchembl_value": 5.5},
        ],
        release="TEST",
        request_urls=[],
    )
    service = ModelLabService(
        repository,
        store=ImmutableObjectStore(tmp_path / "objects"),
        enabled=True,
    )
    snapshot = service.create_snapshot_from_page(
        ChEMBLActivitySnapshotRequest(max_records=100),
        page,
        "test",
    )
    assert snapshot.status == "blocked"
    assert snapshot.ambiguous_removed == 1
    assert snapshot.conflict_removed == 2
    assert snapshot.record_count == 0
