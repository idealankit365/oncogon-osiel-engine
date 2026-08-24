from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from ..config import settings


@dataclass(frozen=True)
class OpenTargetsHit:
    entity_id: str
    name: str
    entity: str
    description: str | None


class OpenTargetsConnector:
    """Minimal read-only client for the official Open Targets GraphQL API.

    Search results resolve identifiers and labels only. They are not converted into
    target validation claims or association scores by OSIEL.
    """

    endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

    _search_query = """
    query Search($queryString: String!) {
      search(queryString: $queryString, page: {index: 0, size: 10}) {
        hits { id name entity description }
      }
    }
    """

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=settings.public_connector_timeout_seconds,
            follow_redirects=True,
        )

    def search(self, query: str, *, entity: str | None = None) -> list[OpenTargetsHit]:
        response = self.client.post(
            self.endpoint,
            json={"query": self._search_query, "variables": {"queryString": query}},
            headers={"User-Agent": settings.public_connector_user_agent},
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        if payload.get("errors"):
            raise ValueError(f"Open Targets GraphQL error: {payload['errors'][0].get('message', 'unknown')}")
        hits = ((payload.get("data") or {}).get("search") or {}).get("hits") or []
        records = [
            OpenTargetsHit(
                entity_id=str(item["id"]),
                name=str(item.get("name") or item["id"]),
                entity=str(item.get("entity") or "unknown"),
                description=item.get("description"),
            )
            for item in hits
            if item.get("id")
        ]
        if entity:
            expected = entity.casefold()
            records = [item for item in records if item.entity.casefold() == expected]
        return records

