from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from .config import settings


class ModelAdapterUnavailable(RuntimeError):
    """Raised when an optional scientific model service is disabled or invalid."""


@dataclass(frozen=True)
class ModelAdapterSpec:
    modality: str
    url: str
    model_name: str


TransportFactory = Callable[[], httpx.BaseTransport | None]


class ScientificModelGateway:
    """Bounded HTTP gateway for independently versioned scientific model services.

    Adapters return measurements about their own modality. They do not compose the
    final recommendation and cannot authorize an experiment. HTTP is accepted only
    for loopback development; remote services must use HTTPS.
    """

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        specs: dict[str, ModelAdapterSpec] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.enabled = settings.multimodal_enabled if enabled is None else enabled
        self.specs = specs or {
            "chemistry": ModelAdapterSpec("chemistry", settings.chem_model_url, settings.chem_model_name),
            "protein": ModelAdapterSpec("protein", settings.protein_model_url, settings.protein_model_name),
            "imaging": ModelAdapterSpec("imaging", settings.vision_model_url, settings.vision_model_name),
        }
        self.transport = transport

    @staticmethod
    def _validate_url(value: str) -> None:
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.hostname or parsed.username or parsed.password:
            raise ModelAdapterUnavailable("Model adapter URL must be an absolute URL without credentials")
        loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        lowered_host = parsed.hostname.casefold()
        if lowered_host in {"metadata.google.internal", "instance-data"} or lowered_host.endswith(
            (".internal", ".local", ".localhost")
        ):
            raise ModelAdapterUnavailable("Private or metadata-service model hosts are prohibited")
        try:
            literal_ip = ip_address(parsed.hostname)
        except ValueError:
            literal_ip = None
        if literal_ip and not literal_ip.is_global and not literal_ip.is_loopback:
            raise ModelAdapterUnavailable("Non-global model-service IP addresses are prohibited")
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise ModelAdapterUnavailable("Remote model adapters require HTTPS; HTTP is loopback-only")
        if parsed.query or parsed.fragment:
            raise ModelAdapterUnavailable("Model adapter URL must not contain a query or fragment")

    def capabilities(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for modality, spec in self.specs.items():
            rows.append({
                "modality": modality,
                "enabled": self.enabled and bool(spec.url),
                "configured": bool(spec.url),
                "model_name": spec.model_name,
                "endpoint_disclosed": False,
                "structured_output_required": True,
            })
        return rows

    def invoke(self, modality: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise ModelAdapterUnavailable("Multimodal model execution is disabled by the operator")
        spec = self.specs.get(modality)
        if not spec or not spec.url:
            raise ModelAdapterUnavailable(f"No {modality} model adapter is configured")
        self._validate_url(spec.url)
        headers = {"Content-Type": "application/json", "X-OSIEL-Model": spec.model_name}
        if settings.multimodal_api_token:
            headers["Authorization"] = f"Bearer {settings.multimodal_api_token}"
        try:
            with httpx.Client(
                timeout=settings.multimodal_timeout_seconds,
                transport=self.transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = client.post(spec.url, json=payload, headers=headers)
                response.raise_for_status()
                if len(response.content) > settings.multimodal_max_response_bytes:
                    raise ModelAdapterUnavailable("Model adapter response exceeded the configured limit")
                body = response.json()
        except ModelAdapterUnavailable:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ModelAdapterUnavailable(
                f"{modality} model service failed validated execution ({type(exc).__name__})"
            ) from exc
        if not isinstance(body, dict):
            raise ModelAdapterUnavailable("Model adapter response must be a JSON object")
        findings = body.get("findings")
        confidence = body.get("confidence")
        if not isinstance(findings, list) or not all(isinstance(item, str) for item in findings):
            raise ModelAdapterUnavailable("Model adapter findings must be a list of strings")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            raise ModelAdapterUnavailable("Model adapter confidence must be between zero and one")
        if not isinstance(body.get("model_version"), str) or not body["model_version"]:
            raise ModelAdapterUnavailable("Model adapter must report a model_version")
        return {
            "model_name": spec.model_name,
            "model_version": body["model_version"][:200],
            "confidence": float(confidence),
            "findings": [item[:1000] for item in findings[:20]],
            "evidence": body.get("evidence", []) if isinstance(body.get("evidence", []), list) else [],
            "warnings": body.get("warnings", []) if isinstance(body.get("warnings", []), list) else [],
        }
