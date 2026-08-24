from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from ..config import settings


@dataclass(frozen=True)
class ChEMBLMolecule:
    molecule_chembl_id: str
    preferred_name: str | None
    canonical_smiles: str | None
    max_phase: float | None


@dataclass(frozen=True)
class ChEMBLActivityPage:
    records: list[dict[str, Any]]
    release: str
    request_urls: list[str]


class ChEMBLConnector:
    """Read-only connector to the official ChEMBL Web Services API."""

    base_url = "https://www.ebi.ac.uk/chembl/api/data"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=settings.public_connector_timeout_seconds,
            follow_redirects=True,
        )

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": settings.public_connector_user_agent}

    def search_molecules(self, query: str, limit: int = 20) -> list[ChEMBLMolecule]:
        url = f"{self.base_url}/molecule/search.json?q={quote(query)}&limit={min(limit, 100)}"
        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        records: list[ChEMBLMolecule] = []
        for item in payload.get("molecules", []):
            structures = item.get("molecule_structures") or {}
            records.append(
                ChEMBLMolecule(
                    molecule_chembl_id=item["molecule_chembl_id"],
                    preferred_name=item.get("pref_name"),
                    canonical_smiles=structures.get("canonical_smiles"),
                    max_phase=item.get("max_phase"),
                )
            )
        return records

    def similar_molecules(
        self,
        smiles: str,
        *,
        minimum_similarity_percent: int = 60,
        limit: int = 50,
    ) -> list[ChEMBLMolecule]:
        """Return ChEMBL molecules from its documented structure-similarity endpoint."""

        threshold = min(100, max(40, minimum_similarity_percent))
        encoded = quote(smiles, safe="")
        url = (
            f"{self.base_url}/similarity/{encoded}/{threshold}.json"
            f"?limit={min(limit, 100)}"
        )
        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        records: list[ChEMBLMolecule] = []
        for item in payload.get("molecules", []):
            structures = item.get("molecule_structures") or {}
            records.append(
                ChEMBLMolecule(
                    molecule_chembl_id=item["molecule_chembl_id"],
                    preferred_name=item.get("pref_name"),
                    canonical_smiles=structures.get("canonical_smiles"),
                    max_phase=item.get("max_phase"),
                )
            )
        return records

    def activity_records(
        self,
        *,
        target_chembl_id: str,
        standard_type: str,
        max_records: int,
        assay_type: str = "B",
        minimum_assay_confidence: int = 8,
    ) -> ChEMBLActivityPage:
        """Retrieve a bounded, deterministic ChEMBL activity slice.

        The service deliberately keeps the complete returned dictionaries for
        immutable provenance, then the model-lab layer performs exact-relation,
        unit, structure, duplicate and threshold filtering locally.
        """

        remaining = min(max(1, max_records), 10_000)
        url: str | None = f"{self.base_url}/activity.json"
        params: dict[str, str | int] | None = {
            "target_chembl_id": target_chembl_id,
            "standard_type": standard_type,
            "assay_type": assay_type,
            "assay__confidence_score__gte": min(9, max(0, minimum_assay_confidence)),
            "pchembl_value__isnull": "false",
            "canonical_smiles__isnull": "false",
            "order_by": "activity_id",
            "limit": min(1000, remaining),
        }
        records: list[dict[str, Any]] = []
        request_urls: list[str] = []
        while url and remaining > 0:
            response = self.client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            request_urls.append(str(response.request.url))
            payload: dict[str, Any] = response.json()
            page = payload.get("activities") or []
            if not isinstance(page, list):
                raise ValueError("ChEMBL activity response has no activities list")
            records.extend(item for item in page[:remaining] if isinstance(item, dict))
            remaining = max_records - len(records)
            next_url = (payload.get("page_meta") or {}).get("next")
            if not next_url or remaining <= 0:
                break
            url = str(next_url)
            if url.startswith("/"):
                url = f"https://www.ebi.ac.uk{url}"
            params = None

        return ChEMBLActivityPage(
            records=records[:max_records],
            release=self.database_version(),
            request_urls=request_urls,
        )

    def database_version(self) -> str:
        try:
            response = self.client.get(f"{self.base_url}/status.json", headers=self.headers)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            return str(
                payload.get("chembl_db_version")
                or payload.get("database_version")
                or payload.get("version")
                or "unresolved-live-release"
            )
        except Exception:
            return "unresolved-live-release"
