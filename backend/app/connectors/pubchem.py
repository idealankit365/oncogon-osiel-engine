from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from ..config import settings


@dataclass(frozen=True)
class PubChemRecord:
    cid: int
    title: str
    canonical_smiles: str
    isomeric_smiles: str | None
    inchikey: str
    molecular_formula: str
    molecular_weight: str


class PubChemConnector:
    """Small-record enrichment through the official PUG REST service.

    Bulk training ingestion must use PubChem bulk channels and immutable release
    manifests rather than issuing millions of per-record calls.
    """

    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=settings.public_connector_timeout_seconds,
            follow_redirects=True,
        )

    def compound_by_name(self, name: str) -> PubChemRecord:
        properties = (
            "Title,CanonicalSMILES,IsomericSMILES,InChIKey,"
            "MolecularFormula,MolecularWeight"
        )
        url = f"{self.base_url}/compound/name/{quote(name, safe='')}/property/{properties}/JSON"
        response = self.client.get(
            url,
            headers={"User-Agent": settings.public_connector_user_agent},
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()["PropertyTable"]["Properties"][0]
        return PubChemRecord(
            cid=int(payload["CID"]),
            title=payload.get("Title", name),
            canonical_smiles=payload["ConnectivitySMILES"],
            isomeric_smiles=payload.get("SMILES"),
            inchikey=payload["InChIKey"],
            molecular_formula=payload["MolecularFormula"],
            molecular_weight=str(payload["MolecularWeight"]),
        )
