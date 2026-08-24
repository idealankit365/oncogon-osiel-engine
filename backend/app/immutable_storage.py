from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .config import settings


class ImmutableObjectStore:
    """Content-addressed, write-once reference store.

    The same SHA-256 always resolves to the same bytes. Production deployments can
    replace this adapter with versioned S3-compatible object storage and retention lock.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or settings.object_store_path)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes, filename: str, metadata: dict[str, object]) -> tuple[str, str]:
        digest = hashlib.sha256(content).hexdigest()
        folder = self.root / digest[:2] / digest
        folder.mkdir(parents=True, exist_ok=True)
        payload_path = folder / "raw.bin"
        metadata_path = folder / "metadata.json"
        if payload_path.exists() and payload_path.read_bytes() != content:
            raise ValueError("Content-address collision detected")
        if not payload_path.exists():
            payload_path.write_bytes(content)
            metadata_path.write_text(json.dumps({"filename": filename, "sha256": digest, "stored_at": datetime.now(UTC).isoformat(), **metadata}, indent=2, sort_keys=True), encoding="utf-8")
        return digest, f"immutable://sha256/{digest}"

    def get(self, uri: str) -> bytes:
        """Read and checksum-verify an object produced by :meth:`put`.

        Only the content-addressed ``immutable://sha256/<digest>`` scheme is
        accepted, so a database value can never be used as an arbitrary path.
        """

        prefix = "immutable://sha256/"
        if not uri.startswith(prefix):
            raise ValueError("Unsupported immutable object URI")
        digest = uri[len(prefix):]
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("Immutable object digest is invalid")
        payload_path = self.root / digest[:2] / digest / "raw.bin"
        if not payload_path.is_file():
            raise FileNotFoundError("Immutable object is missing")
        content = payload_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("Immutable object checksum verification failed")
        return content


object_store = ImmutableObjectStore()
