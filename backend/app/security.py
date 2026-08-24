from __future__ import annotations

import hmac
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from .config import settings


@dataclass(frozen=True)
class ActorContext:
    subject: str
    role: str


def require_actor(
    x_osiel_actor: str | None = Header(default=None),
    x_osiel_role: str | None = Header(default=None),
    x_osiel_api_key: str | None = Header(default=None),
) -> ActorContext:
    """Enforce machine credentials and server-side roles outside demo mode.

    Production deployments should replace the API-key check with verified OIDC JWT
    claims while preserving this role boundary at the API layer.
    """
    if settings.demo_mode:
        return ActorContext((x_osiel_actor or "demo-researcher")[:120], x_osiel_role or "researcher")
    if not settings.api_key or not x_osiel_api_key or not hmac.compare_digest(settings.api_key, x_osiel_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid API credential required")
    role = (x_osiel_role or "").lower()
    if role not in settings.allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recognized institutional role required")
    subject = (x_osiel_actor or "").strip()
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated subject required")
    return ActorContext(subject[:120], role)


def require_reviewer(context: ActorContext) -> ActorContext:
    if context.role not in {"reviewer", "instructor", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reviewer role required")
    return context
