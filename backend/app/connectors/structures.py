from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from ..config import settings


@dataclass(frozen=True)
class RCSBEntry:
    pdb_id: str
    title: str
    resolution_angstrom: float | None


@dataclass(frozen=True)
class AlphaFoldPrediction:
    uniprot_accession: str
    entry_id: str
    model_created_date: str | None
    pdb_url: str


class RCSBConnector:
    """Read-only metadata lookup through the official RCSB Data API."""

    base_url = "https://data.rcsb.org/rest/v1/core/entry"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=settings.public_connector_timeout_seconds,
            follow_redirects=True,
        )

    def entry(self, pdb_id: str) -> RCSBEntry:
        normalized = pdb_id.upper()
        response = self.client.get(
            f"{self.base_url}/{normalized}",
            headers={"User-Agent": settings.public_connector_user_agent},
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        resolutions = (payload.get("rcsb_entry_info") or {}).get("resolution_combined") or []
        return RCSBEntry(
            pdb_id=normalized,
            title=str((payload.get("struct") or {}).get("title") or normalized),
            resolution_angstrom=float(resolutions[0]) if resolutions else None,
        )


class AlphaFoldConnector:
    """Read-only AlphaFold DB prediction metadata lookup by UniProt accession."""

    base_url = "https://alphafold.ebi.ac.uk/api/prediction"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=settings.public_connector_timeout_seconds,
            follow_redirects=True,
        )

    def prediction(self, uniprot_accession: str) -> AlphaFoldPrediction:
        accession = uniprot_accession.upper()
        response = self.client.get(
            f"{self.base_url}/{accession}",
            headers={"User-Agent": settings.public_connector_user_agent},
        )
        response.raise_for_status()
        records: list[dict[str, Any]] = response.json()
        if not records:
            raise LookupError(f"No AlphaFold DB prediction found for {accession}")
        item = records[0]
        return AlphaFoldPrediction(
            uniprot_accession=accession,
            entry_id=str(item.get("entryId") or f"AF-{accession}-F1"),
            model_created_date=item.get("modelCreatedDate"),
            pdb_url=str(item.get("pdbUrl") or f"https://alphafold.ebi.ac.uk/files/AF-{accession}-F1-model_v4.pdb"),
        )

