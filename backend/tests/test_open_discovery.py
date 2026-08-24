from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.open_discovery import OpenDiscoveryService
from app.repository import Repository
from app.schemas import OpenDiscoveryRequest


def test_open_discovery_computes_ranked_trace_without_fake_docking(
    repository: Repository,
) -> None:
    service = OpenDiscoveryService(
        repository,
        allow_public_connectors=False,
        detect_vina=False,
    )
    run = service.run(OpenDiscoveryRequest(candidate_limit=6))

    assert run.execution_mode == "local-python"
    assert [event.stage for event in run.events] == [
        "target-evidence",
        "structure-resolution",
        "seed-resolution",
        "analogue-search",
        "standardization",
        "medchem-alerts",
        "transparent-ranking",
        "docking-readiness",
        "procurement-handoff",
        "review-gate",
    ]
    assert len(run.candidates) == 6
    assert [candidate.rank for candidate in run.candidates] == list(range(1, 7))
    assert all(0 <= candidate.similarity_to_seed <= 1 for candidate in run.candidates)
    assert all(0 <= candidate.priority_score <= 100 for candidate in run.candidates)
    assert all(candidate.inchikey != run.seed.inchikey for candidate in run.candidates)
    assert run.docking.status == "not-run"
    assert run.docking.result_score_kcal_mol is None
    assert run.docking.run_manifest["execute"] is False
    assert "does not predict target binding" in run.claim_boundary

    stored = repository.get_open_discovery_run(run.run_id)
    assert stored is not None
    assert stored["run_id"] == run.run_id


def test_disabled_server_gate_never_calls_requested_public_connectors(
    repository: Repository,
) -> None:
    service = OpenDiscoveryService(
        repository,
        allow_public_connectors=False,
        detect_vina=False,
    )
    run = service.run(OpenDiscoveryRequest(public_connectors=True, candidate_limit=3))

    assert run.execution_mode == "local-python"
    target = next(event for event in run.events if event.stage == "target-evidence")
    assert target.status == "completed-with-warning"
    assert "disabled by the server operator" in target.message


def test_unknown_local_seed_requires_structure_or_public_connector(
    repository: Repository,
) -> None:
    service = OpenDiscoveryService(
        repository,
        allow_public_connectors=False,
        detect_vina=False,
    )
    with pytest.raises(ValueError, match="Supply seed_smiles"):
        service.run(OpenDiscoveryRequest(seed_compound_name="not-a-real-local-record"))


def test_open_discovery_api_create_and_retrieve() -> None:
    client = TestClient(app)
    created = client.post(
        "/v1/open-discovery/runs",
        json={
            "disease": "Non-small cell lung cancer",
            "target_symbol": "EGFR",
            "seed_compound_name": "Gefitinib",
            "candidate_limit": 3,
            "public_connectors": False,
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert len(payload["candidates"]) == 3
    assert payload["docking"]["result_score_kcal_mol"] is None

    retrieved = client.get(f"/v1/open-discovery/runs/{payload['run_id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["run_id"] == payload["run_id"]

