from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .config import settings
from .connectors.bulk_sources import BulkDatasetConnector, configured_bulk_sources
from .connectors.chemspace import ChemspaceConnector
from .connectors.tdc import TDCConnector
from .connectors.uniprot import UniProtConnector
from .repository import Repository


class ScientificDataConnectorService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def capabilities(self) -> list[dict[str, Any]]:
        capabilities = [BulkDatasetConnector(spec).capability() for spec in configured_bulk_sources().values()]
        capabilities.extend([
            {
                "source_code": "tdc",
                "source_name": "Therapeutics Data Commons",
                "connector_type": "official-python-library",
                "configured": TDCConnector.available(),
                "live_enabled": settings.source_connectors_enabled,
                "landing_url": "https://tdcommons.ai/",
                "purpose": "Versioned drug-discovery benchmark datasets",
                "licence_note": "Terms vary by dataset; every snapshot remains quarantined until reviewed.",
            },
            {
                "source_code": "uniprot",
                "source_name": "UniProt",
                "connector_type": "official-rest-api",
                "configured": True,
                "live_enabled": settings.source_connectors_enabled,
                "landing_url": "https://rest.uniprot.org/",
                "purpose": "Protein identity, sequence and cross-reference resolution",
                "licence_note": "Retain accession, entry/sequence version and retrieval timestamp.",
            },
            ChemspaceConnector().capability(),
        ])
        return capabilities

    def fetch_bulk(self, source_code: str, release_id: str, max_records: int, actor: str) -> dict[str, Any]:
        spec = configured_bulk_sources().get(source_code)
        if spec is None:
            raise KeyError(source_code)
        job_id = self.repository.new_id("SYNC")
        try:
            detail = BulkDatasetConnector(spec).fetch(release_id, max_records=max_records)
            status = str(detail["status"])
        except Exception as exc:
            detail = {
                "source_code": source_code,
                "release_id": release_id,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "training_eligible": False,
            }
            status = "failed"
        payload = {"job_id": job_id, **detail}
        self._save(job_id, source_code, status, payload)
        self.repository.audit(actor, "source.fetch", "source_sync_job", job_id, {
            "source_code": source_code,
            "status": status,
            "sha256": detail.get("sha256"),
        })
        return payload

    def fetch_tdc(self, group: str, dataset: str, max_records: int, actor: str) -> dict[str, Any]:
        if not settings.source_connectors_enabled:
            raise RuntimeError("Extended source connectors are disabled by the operator")
        job_id = self.repository.new_id("SYNC")
        detail = TDCConnector().fetch(group, dataset, max_records=max_records)
        payload = {"job_id": job_id, **detail}
        self._save(job_id, "tdc", str(detail["status"]), payload)
        self.repository.audit(actor, "source.fetch", "source_sync_job", job_id, {"source_code": "tdc", "status": detail["status"]})
        return payload

    def uniprot_search(self, query: str, limit: int, reviewed_only: bool) -> list[dict[str, Any]]:
        if not settings.source_connectors_enabled:
            raise RuntimeError("Extended source connectors are disabled by the operator")
        return [record.__dict__ for record in UniProtConnector().search(query, limit=limit, reviewed_only=reviewed_only)]

    def chemspace_search(self, query: str, limit: int) -> dict[str, Any]:
        return ChemspaceConnector().search(query, limit=limit)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.repository.connection() as connection:
            row = connection.execute(
                "SELECT detail_json FROM source_sync_job WHERE job_id = ?", (job_id,)
            ).fetchone()
        return json.loads(row["detail_json"]) if row else None

    def _save(self, job_id: str, source_code: str, status: str, detail: dict[str, Any]) -> None:
        with self.repository.connection() as connection:
            connection.execute(
                "INSERT INTO source_sync_job VALUES (?, ?, ?, ?, ?)",
                (job_id, source_code, status, json.dumps(detail, default=str, sort_keys=True), datetime.now(UTC).isoformat()),
            )
