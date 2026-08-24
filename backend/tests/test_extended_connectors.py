from __future__ import annotations

import hashlib
from dataclasses import replace

import httpx

from app.config import settings as base_settings
from app.connectors import bulk_sources, chemspace as chemspace_module
from app.connectors.bulk_sources import BulkDatasetConnector, BulkSourceSpec
from app.connectors.chemspace import ChemspaceConnector
from app.connectors.uniprot import UniProtConnector
from app.immutable_storage import ImmutableObjectStore


def client_for(handler: object, *, follow_redirects: bool = True) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=follow_redirects)  # type: ignore[arg-type]


def test_bulk_connector_fetches_checksums_stores_and_previews_csv(tmp_path, monkeypatch) -> None:
    raw = b"compound_id,cell_line,gi50\nNSC-1,A549,6.2\nNSC-2,MCF7,5.8\n"
    digest = hashlib.sha256(raw).hexdigest()
    configured = replace(base_settings, source_connectors_enabled=True, source_connector_max_bytes=1_000_000)
    monkeypatch.setattr(bulk_sources, "settings", configured)
    monkeypatch.setattr(bulk_sources, "object_store", ImmutableObjectStore(tmp_path / "objects"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "official.example.test"
        return httpx.Response(200, content=raw, headers={"content-type": "text/csv"}, request=request)

    spec = BulkSourceSpec(
        code="nci60",
        name="NCI-60 / CellMiner",
        landing_url="https://official.example.test/downloads",
        purpose="Cancer-cell-line response",
        licence_note="Public research data",
        download_url="https://official.example.test/nci60-2025.csv",
        expected_sha256=digest,
    )
    result = BulkDatasetConnector(spec, client=client_for(handler), max_bytes=1_000_000).fetch(
        "2025.3", max_records=10
    )
    assert result["status"] == "accepted-raw-release"
    assert result["checksum_verified"] is True
    assert result["record_preview"]["records"][0]["cell_line"] == "A549"
    assert result["training_eligible"] is False


def test_bulk_connector_quarantines_release_without_expected_checksum(tmp_path, monkeypatch) -> None:
    configured = replace(base_settings, source_connectors_enabled=True)
    monkeypatch.setattr(bulk_sources, "settings", configured)
    monkeypatch.setattr(bulk_sources, "object_store", ImmutableObjectStore(tmp_path / "objects"))
    raw = b"id\nNP-1\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=raw, request=request)

    spec = BulkSourceSpec(
        "coconut", "COCONUT", "https://data.example.test", "Natural products", "Review release",
        "https://data.example.test/coconut.csv", "",
    )
    result = BulkDatasetConnector(spec, client=client_for(handler)).fetch("2026-01")
    assert result["status"] == "quarantined-checksum-required"
    assert result["checksum_verified"] is False


def test_uniprot_connector_parses_reviewed_entry_and_sequence() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/P00533.json")
        return httpx.Response(
            200,
            json={
                "primaryAccession": "P00533",
                "uniProtkbId": "EGFR_HUMAN",
                "entryType": "UniProtKB reviewed (Swiss-Prot)",
                "proteinDescription": {"recommendedName": {"fullName": {"value": "Epidermal growth factor receptor"}}},
                "genes": [{"geneName": {"value": "EGFR"}}],
                "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
                "sequence": {"value": "MALTV", "length": 5},
                "entryAudit": {"sequenceVersion": 2},
            },
            request=request,
        )

    record = UniProtConnector(client_for(handler)).entry("p00533")
    assert record.accession == "P00533"
    assert record.gene_names == ["EGFR"]
    assert record.sequence == "MALTV"
    assert record.reviewed is True


def test_chemspace_connector_requires_operator_key_and_uses_configured_contract(monkeypatch) -> None:
    configured = replace(
        base_settings,
        source_connectors_enabled=True,
        chemspace_api_base_url="https://api.chem-space.com",
        chemspace_search_path="v1/documented-search",
        chemspace_api_key="test-key",
    )
    monkeypatch.setattr(chemspace_module, "settings", configured)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/documented-search"
        assert request.headers["x-api-key"] == "test-key"
        return httpx.Response(200, json={"items": [{"id": "CS-1", "smiles": "CCO"}]}, request=request)

    result = ChemspaceConnector(client_for(handler, follow_redirects=False)).search("ethanol", limit=5)
    assert result["provider_response"]["items"][0]["id"] == "CS-1"
