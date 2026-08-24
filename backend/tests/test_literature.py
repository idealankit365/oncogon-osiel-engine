from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_literature_registry_is_citable_and_contextual() -> None:
    response = client.get("/v1/literature")
    assert response.status_code == 200
    records = response.json()
    assert len(records) >= 12
    assert all(record["pmid"] and record["url"].startswith("https://pubmed.ncbi.nlm.nih.gov/") for record in records)
    assert all("not clinical efficacy" in record["claim_boundary"].lower() for record in records)


def test_literature_search_preserves_compound_context() -> None:
    response = client.get("/v1/literature", params={"query": "Apigenin", "evidence_level": "direct"})
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["pmid"] == "28125432"
