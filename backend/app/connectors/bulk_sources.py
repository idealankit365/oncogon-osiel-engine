from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse

import httpx

from ..config import settings
from ..immutable_storage import object_store


RELEASE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class SourceConnectorError(RuntimeError):
    pass


class SourceConnectorDisabled(SourceConnectorError):
    pass


class SourceConnectorConfigurationError(SourceConnectorError):
    pass


@dataclass(frozen=True)
class BulkSourceSpec:
    code: str
    name: str
    landing_url: str
    purpose: str
    licence_note: str
    download_url: str
    expected_sha256: str


def configured_bulk_sources() -> dict[str, BulkSourceSpec]:
    return {
        "nci60": BulkSourceSpec(
            "nci60", "NCI-60 / CellMiner", "https://discover.nci.nih.gov/cellminer/loadDownload.do",
            "Cancer-cell-line compound response data", "Keep NCI assay domains and release metadata separate.",
            settings.nci60_bulk_url, settings.nci60_bulk_sha256,
        ),
        "coconut": BulkSourceSpec(
            "coconut", "COCONUT 2.0", "https://coconut.naturalproducts.net/download",
            "Natural-product structures and annotations", "Preserve upstream source, organism and release provenance.",
            settings.coconut_bulk_url, settings.coconut_bulk_sha256,
        ),
        "npass": BulkSourceSpec(
            "npass", "NPASS", "https://bidd.group/NPASS/downloadnpass.html",
            "Natural-product structures, activities, targets and species", "Confirm the selected NPASS release terms before use.",
            settings.npass_bulk_url, settings.npass_bulk_sha256,
        ),
        "anpdb": BulkSourceSpec(
            "anpdb", "African Natural Products Database", "https://african-compounds.org",
            "African natural products, organisms, uses and literature", "Preserve biological-source and traditional-use provenance.",
            settings.anpdb_bulk_url, settings.anpdb_bulk_sha256,
        ),
        "lotus": BulkSourceSpec(
            "lotus", "LOTUS", "https://lotus.naturalproducts.net/download",
            "Natural-product occurrence and organism provenance", "Record export licence, release and organism evidence.",
            settings.lotus_bulk_url, settings.lotus_bulk_sha256,
        ),
        "tox21": BulkSourceSpec(
            "tox21", "Tox21", "https://tripod.nih.gov/tox21/pubdata",
            "Public high-throughput toxicity assay data", "Retain assay protocol, endpoint and sample QC identifiers.",
            settings.tox21_bulk_url, settings.tox21_bulk_sha256,
        ),
        "toxcast": BulkSourceSpec(
            "toxcast", "EPA ToxCast", "https://www.epa.gov/comptox-tools/exploring-toxcast-data",
            "EPA invitrodb bioactivity and toxicity endpoints", "Retain invitrodb version, assay flags and EPA citation.",
            settings.toxcast_bulk_url, settings.toxcast_bulk_sha256,
        ),
    }


class BulkDatasetConnector:
    """Bounded, immutable downloader for publisher-selected bulk releases.

    URLs are supplied only by the server operator through environment variables;
    API callers cannot submit arbitrary URLs. Missing or mismatched checksums keep
    the artifact quarantined rather than silently accepting it as scientific data.
    """

    def __init__(
        self,
        spec: BulkSourceSpec,
        *,
        client: httpx.Client | None = None,
        max_bytes: int | None = None,
    ) -> None:
        self.spec = spec
        self.client = client or httpx.Client(
            timeout=settings.public_connector_timeout_seconds,
            follow_redirects=True,
        )
        self.max_bytes = max_bytes or settings.source_connector_max_bytes

    def capability(self) -> dict[str, Any]:
        return {
            "source_code": self.spec.code,
            "source_name": self.spec.name,
            "connector_type": "approved-bulk-release",
            "configured": bool(self.spec.download_url),
            "checksum_configured": bool(self.spec.expected_sha256),
            "live_enabled": settings.source_connectors_enabled,
            "landing_url": self.spec.landing_url,
            "purpose": self.spec.purpose,
            "licence_note": self.spec.licence_note,
        }

    def fetch(self, release_id: str, *, max_records: int = 100) -> dict[str, Any]:
        if not settings.source_connectors_enabled:
            raise SourceConnectorDisabled("Extended source connectors are disabled by the operator")
        if not RELEASE_PATTERN.fullmatch(release_id):
            raise SourceConnectorConfigurationError("release_id contains unsupported characters")
        url = self.spec.download_url.strip()
        if not url:
            raise SourceConnectorConfigurationError(
                f"No approved direct download URL is configured for {self.spec.name}"
            )
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise SourceConnectorConfigurationError("Bulk source URL must be an absolute credential-free HTTPS URL")

        content = bytearray()
        headers = {"User-Agent": settings.public_connector_user_agent, "Accept": "*/*"}
        with self.client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            final = urlparse(str(response.url))
            if final.scheme != "https" or final.hostname != parsed.hostname:
                raise SourceConnectorConfigurationError("Bulk source redirected outside its configured host")
            declared = int(response.headers.get("content-length", "0") or 0)
            if declared > self.max_bytes:
                raise SourceConnectorError("Bulk source exceeds the configured response-size limit")
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > self.max_bytes:
                    raise SourceConnectorError("Bulk source exceeded the configured response-size limit")

        raw = bytes(content)
        digest = hashlib.sha256(raw).hexdigest()
        expected = self.spec.expected_sha256.strip().lower()
        checksum_verified = bool(expected) and digest == expected
        checksum_mismatch = bool(expected) and digest != expected
        filename = PurePosixPath(parsed.path).name or f"{self.spec.code}-{release_id}.bin"
        preview = _preview(raw, filename, max_records=max_records)
        object_digest, object_uri = object_store.put(
            raw,
            filename,
            {
                "source_code": self.spec.code,
                "source_name": self.spec.name,
                "release_id": release_id,
                "retrieval_url": url,
                "expected_sha256": expected or None,
                "checksum_verified": checksum_verified,
                "licence_note": self.spec.licence_note,
                "data_class": "raw-source-release",
            },
        )
        status = (
            "quarantined-checksum-mismatch" if checksum_mismatch
            else "accepted-raw-release" if checksum_verified
            else "quarantined-checksum-required"
        )
        return {
            "source_code": self.spec.code,
            "source_name": self.spec.name,
            "release_id": release_id,
            "status": status,
            "filename": filename,
            "byte_count": len(raw),
            "sha256": object_digest,
            "expected_sha256": expected or None,
            "checksum_verified": checksum_verified,
            "object_uri": object_uri,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "record_preview": preview,
            "training_eligible": False,
            "next_gate": "source-specific parser, canonical mapping, QC and scientific approval",
        }


def _preview(raw: bytes, filename: str, *, max_records: int) -> dict[str, Any]:
    sample = raw
    inner_name = filename
    archive_members: list[str] = []
    try:
        if zipfile.is_zipfile(io.BytesIO(raw)):
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                safe = [
                    item for item in archive.infolist()
                    if not item.is_dir() and item.file_size <= 20_000_000
                    and ".." not in PurePosixPath(item.filename).parts
                ]
                archive_members = [item.filename for item in safe[:50]]
                candidate = next(
                    (item for item in safe if item.filename.lower().endswith((".csv", ".tsv", ".txt", ".json", ".jsonl", ".sdf"))),
                    safe[0] if safe else None,
                )
                if candidate is not None:
                    sample = archive.read(candidate)[:20_000_000]
                    inner_name = candidate.filename
        elif filename.lower().endswith(".gz"):
            sample = gzip.GzipFile(fileobj=io.BytesIO(raw)).read(20_000_001)
            if len(sample) > 20_000_000:
                sample = sample[:20_000_000]
            inner_name = filename[:-3]
    except (OSError, EOFError, zipfile.BadZipFile):
        return {"format": "binary", "records": [], "record_count_estimate": None, "archive_members": archive_members}

    lower = inner_name.lower()
    if lower.endswith(".sdf") or b"$$$$" in sample[:2_000_000]:
        count = sample.count(b"$$$$")
        return {"format": "sdf", "records": [], "record_count_estimate": count, "archive_members": archive_members}
    text = sample[:2_000_000].decode("utf-8", errors="replace")
    if lower.endswith((".json", ".jsonl")):
        try:
            payload = json.loads(text)
            records = payload if isinstance(payload, list) else [payload]
            return {"format": "json", "records": records[:max_records], "record_count_estimate": len(records), "archive_members": archive_members}
        except json.JSONDecodeError:
            records = []
            for line in text.splitlines()[:max_records]:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return {"format": "jsonl", "records": records, "record_count_estimate": len(records), "archive_members": archive_members}

    delimiter = "\t" if lower.endswith((".tsv", ".txt")) and text.count("\t") >= text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    records = [dict(row) for _, row in zip(range(max_records), reader)]
    return {
        "format": "tsv" if delimiter == "\t" else "csv",
        "columns": reader.fieldnames or [],
        "records": records,
        "record_count_estimate": max(0, len(text.splitlines()) - 1),
        "archive_members": archive_members,
    }
