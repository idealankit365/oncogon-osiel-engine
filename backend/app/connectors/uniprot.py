from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from ..config import settings


@dataclass(frozen=True)
class UniProtRecord:
    accession: str
    entry_name: str
    protein_name: str
    gene_names: list[str]
    organism_name: str
    organism_taxon_id: int | None
    sequence: str
    sequence_length: int
    reviewed: bool
    version: int | None


class UniProtConnector:
    """Bounded read-only client for the official UniProtKB REST API."""

    base_url = "https://rest.uniprot.org/uniprotkb"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=settings.public_connector_timeout_seconds,
            follow_redirects=True,
        )

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": settings.public_connector_user_agent, "Accept": "application/json"}

    def entry(self, accession: str) -> UniProtRecord:
        normalized = accession.strip().upper()
        response = self.client.get(f"{self.base_url}/{normalized}.json", headers=self.headers)
        response.raise_for_status()
        return self._record(response.json())

    def search(self, query: str, *, limit: int = 10, reviewed_only: bool = True) -> list[UniProtRecord]:
        normalized = query.strip()
        if not normalized:
            raise ValueError("UniProt query is required")
        api_query = f"({normalized}) AND reviewed:true" if reviewed_only else normalized
        response = self.client.get(
            f"{self.base_url}/search",
            params={"query": api_query, "format": "json", "size": min(max(limit, 1), 50)},
            headers=self.headers,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return [self._record(item) for item in payload.get("results", [])]

    @staticmethod
    def _record(payload: dict[str, Any]) -> UniProtRecord:
        description = payload.get("proteinDescription") or {}
        recommended = description.get("recommendedName") or {}
        full_name = (recommended.get("fullName") or {}).get("value")
        if not full_name:
            submitted = description.get("submissionNames") or []
            full_name = ((submitted[0].get("fullName") or {}).get("value") if submitted else None)
        genes = []
        for gene in payload.get("genes") or []:
            name = (gene.get("geneName") or {}).get("value")
            if name:
                genes.append(str(name))
        organism = payload.get("organism") or {}
        sequence = payload.get("sequence") or {}
        return UniProtRecord(
            accession=str(payload.get("primaryAccession") or ""),
            entry_name=str(payload.get("uniProtkbId") or ""),
            protein_name=str(full_name or payload.get("primaryAccession") or "unknown"),
            gene_names=genes,
            organism_name=str(organism.get("scientificName") or "unknown"),
            organism_taxon_id=int(organism["taxonId"]) if organism.get("taxonId") is not None else None,
            sequence=str(sequence.get("value") or ""),
            sequence_length=int(sequence.get("length") or 0),
            reviewed=str(payload.get("entryType") or "").casefold().startswith("uniprotkb reviewed"),
            version=int(payload["entryAudit"]["sequenceVersion"]) if (payload.get("entryAudit") or {}).get("sequenceVersion") is not None else None,
        )
