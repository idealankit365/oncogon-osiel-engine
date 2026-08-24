from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from ..config import settings


MAX_REMOTE_RESPONSE_BYTES = 10_000_000
MAP_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,160}$")


class CartBlancheError(RuntimeError):
    """The public SmallWorld/CartBlanche service rejected a bounded query."""


@dataclass(frozen=True)
class SmallWorldMap:
    key: str
    name: str
    num_entries: int
    num_mapped: int
    enabled: bool
    status: str


@dataclass(frozen=True)
class SmallWorldResult:
    map: SmallWorldMap
    records: list[dict[str, Any]]
    response_sha256: str


class CartBlancheConnector:
    """Bounded client for the public SmallWorld search service used by CartBlanche.

    The provider owns and searches the multi-billion-scale map. OSIEL dynamically
    verifies the selected map through `/search/maps`, sends one seed structure, and
    retains at most 100 returned hits. The local workstation never stores or scans
    the full collection.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        map_key: str | None = None,
        timeout_seconds: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or settings.zinc22_base_url).rstrip("/")
        self.map_key = map_key or settings.zinc22_map
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("OSIEL_ZINC22_BASE_URL must be an absolute HTTPS URL")
        if not MAP_PATTERN.fullmatch(self.map_key):
            raise ValueError("OSIEL_ZINC22_MAP contains unsupported characters")
        self.client = client or httpx.Client(
            timeout=timeout_seconds or settings.zinc22_timeout_seconds,
            follow_redirects=True,
        )

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": settings.public_connector_user_agent,
            "Accept": "application/json,text/tab-separated-values",
        }

    def map_metadata(self) -> SmallWorldMap:
        response = self.client.get(f"{self.base_url}/search/maps", headers=self.headers)
        response.raise_for_status()
        payload = response.json()
        item = payload.get(self.map_key) if isinstance(payload, dict) else None
        if not isinstance(item, dict):
            raise CartBlancheError(
                f"Configured SmallWorld map {self.map_key!r} is not advertised by the provider"
            )
        result = SmallWorldMap(
            key=self.map_key,
            name=str(item.get("name") or self.map_key),
            num_entries=max(0, int(item.get("numEntries") or 0)),
            num_mapped=max(0, int(item.get("numMapped") or 0)),
            enabled=bool(item.get("enabled")),
            status=str(item.get("status") or "unknown"),
        )
        if not result.enabled or result.status.casefold() != "available":
            raise CartBlancheError(
                f"SmallWorld map {result.name!r} is not currently available"
            )
        return result

    def search(
        self,
        smiles: str,
        graph_distance: int,
        anonymous_distance: int,
        limit: int,
    ) -> SmallWorldResult:
        map_record = self.map_metadata()
        response = self.client.get(
            f"{self.base_url}/search/view",
            params={
                "smi": smiles,
                "db": map_record.key,
                "fmt": "tsv",
                # SmallWorld calls graph edit distance `sdist` and anonymous/topology
                # distance `dist`; this mapping matches CartBlanche's own client code.
                "sdist": max(0, min(3, graph_distance)),
                "dist": max(0, min(3, anonymous_distance)),
                "length": max(5, min(100, limit)),
            },
            headers=self.headers,
        )
        response.raise_for_status()
        if len(response.content) > MAX_REMOTE_RESPONSE_BYTES:
            raise CartBlancheError("SmallWorld result exceeded the 10 MB OSIEL safety limit")
        digest = hashlib.sha256(response.content).hexdigest()
        records = self._parse_tsv(response.text, limit)
        return SmallWorldResult(map_record, records, digest)

    @staticmethod
    def _parse_tsv(value: str, limit: int) -> list[dict[str, Any]]:
        lines = [line for line in value.splitlines() if line.strip()]
        if not lines or not lines[0].startswith("Smiles\t"):
            raise CartBlancheError("SmallWorld did not return its expected TSV header")
        output: list[dict[str, Any]] = []
        for line in lines[1 : max(5, min(100, limit)) + 1]:
            columns = line.split("\t")
            if not columns or " " not in columns[0]:
                continue
            source_smiles, remote_id = columns[0].rsplit(" ", 1)
            if not source_smiles or not remote_id:
                continue
            try:
                similarity_score = float(columns[1]) if len(columns) > 1 else None
                aligned_score = float(columns[2]) if len(columns) > 2 else None
                graph_distance = int(columns[3]) if len(columns) > 3 else None
                anonymous_distance = int(columns[4]) if len(columns) > 4 else None
            except ValueError:
                similarity_score = aligned_score = graph_distance = anonymous_distance = None
            output.append(
                {
                    "remote_id": remote_id[:240],
                    "smiles": source_smiles,
                    "provider_similarity_score": similarity_score,
                    "provider_aligned_score": aligned_score,
                    "provider_graph_distance": graph_distance,
                    "provider_anonymous_distance": anonymous_distance,
                }
            )
        return output
