from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from ..config import settings


class ChemspaceConfigurationError(RuntimeError):
    pass


class ChemspaceConnector:
    """Licensed Chemspace adapter with operator-configured documented path.

    Chemspace issues keys and publishes an interactive contract. OSIEL therefore
    refuses to guess the path or authentication scheme; both remain explicit
    deployment configuration and are never accepted from a browser request.
    """

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=settings.public_connector_timeout_seconds,
            follow_redirects=False,
        )

    def capability(self) -> dict[str, Any]:
        return {
            "source_code": "chemspace",
            "source_name": "Chemspace",
            "connector_type": "licensed-api",
            "configured": bool(settings.chemspace_api_key and settings.chemspace_search_path),
            "live_enabled": settings.source_connectors_enabled,
            "requires_api_key": True,
            "documentation_url": "https://api.chem-space.com/docs/",
            "rate_limit_note": "Provider advertises up to 40 requests/minute; enforce the current contract.",
        }

    def search(self, query: str, *, limit: int = 25) -> dict[str, Any]:
        if not settings.source_connectors_enabled:
            raise ChemspaceConfigurationError("Extended source connectors are disabled by the operator")
        if not settings.chemspace_api_key or not settings.chemspace_search_path:
            raise ChemspaceConfigurationError("Chemspace API key and documented search path are not configured")
        base = settings.chemspace_api_base_url.rstrip("/") + "/"
        endpoint = urljoin(base, settings.chemspace_search_path.lstrip("/"))
        if urlparse(endpoint).hostname != urlparse(base).hostname:
            raise ChemspaceConfigurationError("Chemspace search path escaped the configured API host")
        response = self.client.get(
            endpoint,
            params={"query": query.strip(), "limit": min(max(limit, 1), 100)},
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {settings.chemspace_api_key}",
                "X-API-Key": settings.chemspace_api_key,
                "User-Agent": settings.public_connector_user_agent,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "source_code": "chemspace",
            "query": query,
            "provider_response": payload,
            "claim_boundary": "Availability, price, form, purity and lead time require current supplier verification.",
        }
