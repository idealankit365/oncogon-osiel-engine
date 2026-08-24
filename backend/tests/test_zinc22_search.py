from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.connectors.cartblanche import CartBlancheConnector, SmallWorldMap, SmallWorldResult
from app.main import app
from app.repository import Repository
from app.schemas import ZincSearchRequest
from app.zinc22_search import Zinc22SearchService, ZincSearchDisabled


class FakeCartBlanche:
    base_url = "https://sw.example.test"

    def __init__(self, result: SmallWorldResult) -> None:
        self.result = result
        self.submissions: list[tuple[str, int, int, int]] = []

    def search(self, smiles: str, graph_distance: int, anonymous_distance: int, limit: int) -> SmallWorldResult:
        self.submissions.append((smiles, graph_distance, anonymous_distance, limit))
        return self.result


def request() -> ZincSearchRequest:
    return ZincSearchRequest(
        seed_smiles="CC(=O)Oc1ccccc1C(=O)O",
        graph_distance=2,
        anonymous_distance=1,
        max_results=10,
    )


def test_zinc_search_persists_remote_task_and_rdkit_shortlist(repository: Repository) -> None:
    result = SmallWorldResult(
        SmallWorldMap(
            key="REALDB-2025-07.smi.anon",
            name="REALDB-25Q3-9.4B",
            num_entries=10_102_659_506,
            num_mapped=9_425_750_819,
            enabled=True,
            status="Available",
        ),
        [
            {"remote_id": "ZINCA", "smiles": "CC(=O)Oc1ccccc1C(=O)O"},
            {"remote_id": "ZINCB", "smiles": "O=C(O)c1ccccc1O"},
            {"remote_id": "ZINCB-DUP", "smiles": "O=C(O)c1ccccc1O"},
            {"remote_id": "BAD", "smiles": "not-a-smiles"},
        ],
        "a" * 64,
    )
    connector = FakeCartBlanche(result)
    service = Zinc22SearchService(
        repository,
        enabled=True,
        connector=connector,  # type: ignore[arg-type]
        min_poll_seconds=0,
    )
    submitted = service.submit(request(), "student@example.edu")
    assert submitted.status == "completed"
    assert connector.submissions[0][1:] == (2, 1, 10)
    assert submitted.remote_returned_count == 4
    assert submitted.quarantined_count == 1
    assert len(submitted.candidates) == 2
    assert submitted.candidates[0].similarity_to_seed == 1
    assert submitted.index_entries == 10_102_659_506
    assert submitted.remote_result_sha256 == "a" * 64
    assert service.get(submitted.job_id) is not None


def test_zinc_refresh_does_not_resubmit_completed_query(repository: Repository) -> None:
    connector = FakeCartBlanche(
        SmallWorldResult(
            SmallWorldMap("test-map", "test-10B", 10_000_000_000, 9_000_000_000, True, "Available"),
            [{"remote_id": "A", "smiles": "CCO"}],
            "b" * 64,
        )
    )
    service = Zinc22SearchService(
        repository,
        enabled=True,
        connector=connector,  # type: ignore[arg-type]
        min_poll_seconds=0,
    )
    job = service.submit(request(), "student")
    refreshed = service.refresh(job.job_id, "student")
    assert refreshed.status == "completed"
    assert refreshed.remote_query_id == job.remote_query_id
    assert len(connector.submissions) == 1


def test_zinc_operator_gate(repository: Repository) -> None:
    service = Zinc22SearchService(repository, enabled=False)
    with pytest.raises(ZincSearchDisabled, match="disabled by the operator"):
        service.submit(request(), "student")


def test_cartblanche_connector_verifies_map_and_parses_direct_search() -> None:
    calls: list[httpx.Request] = []

    def handler(incoming: httpx.Request) -> httpx.Response:
        calls.append(incoming)
        if incoming.url.path == "/search/maps":
            return httpx.Response(200, json={
                "REALDB-2025-07.smi.anon": {
                    "name": "REALDB-25Q3-9.4B",
                    "numEntries": 10_102_659_506,
                    "numMapped": 9_425_750_819,
                    "enabled": True,
                    "status": "Available",
                }
            })
        assert incoming.url.params["db"] == "REALDB-2025-07.smi.anon"
        return httpx.Response(200, text=(
            "Smiles\tScore\tScore\tDist\tAnonDist\n"
            "CCO ZINCA\t1.0\t1.0\t0\t0\n"
        ))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    connector = CartBlancheConnector(base_url="https://example.test", client=client)
    result = connector.search("CCO", 1, 0, 25)
    assert result.map.num_entries == 10_102_659_506
    assert result.records[0]["remote_id"] == "ZINCA"
    assert calls[0].method == "GET"


def test_zinc_api_reports_disabled_default() -> None:
    client = TestClient(app)
    capability = client.get("/v1/zinc22/capabilities")
    assert capability.status_code == 200
    assert capability.json()["local_full_index"] is False
    response = client.post("/v1/zinc22/searches", json=request().model_dump(mode="json"))
    assert response.status_code == 503
