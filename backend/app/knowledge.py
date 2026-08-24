from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import math
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .config import settings
from .connectors.ollama import OllamaClient, OllamaUnavailable
from .immutable_storage import ImmutableObjectStore, object_store
from .repository import Repository
from .schemas import KnowledgeDocument, KnowledgeDocumentIngest


PARSER_VERSION = "OSIEL-DOCUMENT-PARSER-1.0.0"
CHUNKER_VERSION = "OSIEL-PAGE-CHUNKER-1.0.0"
WORD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9+_.-]{1,}")
PROMPT_INJECTION_PATTERNS = {
    "ignore-prior-instructions": re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    "system-prompt-exfiltration": re.compile(r"(reveal|show|print).{0,30}(system|hidden)\s+prompt", re.I),
    "role-override": re.compile(r"you\s+are\s+now.{0,80}(assistant|system|developer)", re.I),
    "safety-bypass": re.compile(r"(bypass|disable|evade).{0,40}(safety|guardrail|policy)", re.I),
    "instruction-delimiter": re.compile(r"\b(system|developer)\s*:\s*(instruction|message)", re.I),
}
SUPPORTED_EXTENSIONS = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
}


class KnowledgeIngestionDisabled(RuntimeError):
    pass


class KnowledgeInputError(ValueError):
    pass


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in WORD_PATTERN.findall(value) if len(token) > 2]


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value.replace("\x00", " "))
    normalized = re.sub(r"[\t\r ]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


class ScientificKnowledgeService:
    """Immutable scientific-document ingestion and scoped hybrid retrieval.

    SQLite FTS5 is the always-available lexical index. When local Ollama is enabled,
    Qwen3 embeddings are stored with each immutable chunk and combined with lexical
    ranking. Uploaded content is never treated as an instruction to the model.
    """

    def __init__(
        self,
        repository: Repository,
        *,
        ollama_client: OllamaClient | None = None,
        store: ImmutableObjectStore | None = None,
        ingestion_enabled: bool | None = None,
    ) -> None:
        self.repository = repository
        self.ollama = ollama_client or OllamaClient()
        self.store = store or object_store
        self.ingestion_enabled = (
            settings.professor_ingestion_enabled
            if ingestion_enabled is None
            else ingestion_enabled
        )

    def capability(self) -> dict[str, object]:
        documents = self.repository.list_knowledge_documents(limit=500)
        return {
            "ingestion_enabled": self.ingestion_enabled,
            "supported_media_types": list(SUPPORTED_EXTENSIONS),
            "document_count": len(documents),
            "indexed_document_count": sum(item.get("status") == "indexed" for item in documents),
            "chunk_count": sum(int(item.get("chunk_count", 0)) for item in documents),
            "retrieval": "SQLite FTS5 BM25 + optional Qwen3 dense embeddings with reciprocal-rank fusion",
            "embedding_model": self.ollama.embedding_model,
            "page_level_citations": True,
            "immutable_raw_and_normalized_artifacts": True,
            "document_versioning": "SHA-256 content identity plus declared source version",
            "rights_gate": "Full text is indexed only when rights_status=approved",
            "quarantine": "Prompt-like instructions are retained for audit but excluded from retrieval",
        }

    def ingest(
        self,
        request: KnowledgeDocumentIngest,
        *,
        actor: str,
        role: str,
    ) -> KnowledgeDocument:
        if not self.ingestion_enabled:
            raise KnowledgeIngestionDisabled(
                "Scientific document ingestion is disabled by the server operator"
            )
        if not settings.demo_mode and role not in {"instructor", "reviewer", "admin"}:
            raise PermissionError("Instructor, reviewer or admin role required for corpus ingestion")
        if request.rights_status != "approved":
            raise KnowledgeInputError(
                "Full-text indexing requires rights_status=approved and a recorded rights note"
            )
        if len(request.rights_note.strip()) < 4:
            raise KnowledgeInputError("A rights or licence note is required for full-text indexing")
        expected_extension = SUPPORTED_EXTENSIONS[request.media_type]
        if not request.filename.casefold().endswith(expected_extension):
            raise KnowledgeInputError(
                f"Filename extension must match {request.media_type} ({expected_extension})"
            )
        if request.source_url:
            parsed = urlparse(request.source_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise KnowledgeInputError("source_url must be an absolute HTTP(S) URL")

        content = self._decode_content(request.content_base64)
        raw_sha256 = hashlib.sha256(content).hexdigest()
        duplicate = self.repository.find_knowledge_document(
            raw_sha256,
            request.project_scope,
            request.course_scope,
        )
        if duplicate:
            return KnowledgeDocument.model_validate({**duplicate, "duplicate": True})

        raw_sha, raw_uri = self.store.put(
            content,
            request.filename,
            {
                "kind": "professor-scientific-document-raw",
                "title": request.title,
                "source_url": request.source_url,
                "source_version": request.source_version,
                "rights_status": request.rights_status,
                "project_scope": request.project_scope,
                "course_scope": request.course_scope,
                "actor": actor,
            },
        )
        pages, warnings = self._extract_pages(content, request.media_type)
        flags = self._prompt_injection_flags(pages)
        status = "quarantined" if flags else "indexed"
        chunks = self._chunk_pages(raw_sha256, pages)
        if flags:
            for chunk in chunks:
                chunk["injection_flagged"] = True
        if len(chunks) > settings.professor_max_chunks:
            raise KnowledgeInputError(
                f"Document produced {len(chunks)} chunks; configured limit is {settings.professor_max_chunks}"
            )

        embedding_model: str | None = None
        if status == "indexed" and self.ollama.enabled and chunks:
            try:
                for start in range(0, len(chunks), 32):
                    batch = chunks[start : start + 32]
                    vectors = self.ollama.embed(
                        [
                            "Represent this scientific passage for evidence retrieval:\n" + item["text"]
                            for item in batch
                        ]
                    )
                    for item, vector in zip(batch, vectors, strict=True):
                        item["embedding"] = vector
                        item["embedding_model"] = self.ollama.embedding_model
                embedding_model = self.ollama.embedding_model
            except OllamaUnavailable as exc:
                warnings.append(
                    f"Dense indexing unavailable; lexical FTS5 remains active ({exc})"
                )
        elif status == "quarantined":
            warnings.append("Document excluded from retrieval because prompt-like instructions were detected")

        normalized_manifest = {
            "raw_sha256": raw_sha256,
            "parser_version": PARSER_VERSION,
            "chunker_version": CHUNKER_VERSION,
            "pages": pages,
            "chunks": [
                {
                    "chunk_id": item["chunk_id"],
                    "page_number": item["page_number"],
                    "section": item["section"],
                    "text_sha256": item["text_sha256"],
                    "text": item["text"],
                }
                for item in chunks
            ],
        }
        normalized_bytes = json.dumps(
            normalized_manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        normalized_sha, normalized_uri = self.store.put(
            normalized_bytes,
            f"{request.filename}.normalized.json",
            {
                "kind": "professor-scientific-document-normalized",
                "raw_sha256": raw_sha256,
                "parser_version": PARSER_VERSION,
                "chunker_version": CHUNKER_VERSION,
                "actor": actor,
            },
        )
        created_at = datetime.now(UTC)
        document = KnowledgeDocument(
            document_id=self.repository.new_id("DOC"),
            title=request.title,
            filename=request.filename,
            media_type=request.media_type,
            source_url=request.source_url,
            source_version=request.source_version,
            rights_status=request.rights_status,
            rights_note=request.rights_note,
            project_scope=request.project_scope,
            course_scope=request.course_scope,
            tags=sorted({tag.strip()[:80] for tag in request.tags if tag.strip()}),
            status=status,
            raw_sha256=raw_sha,
            raw_object_uri=raw_uri,
            normalized_sha256=normalized_sha,
            normalized_object_uri=normalized_uri,
            parser_version=PARSER_VERSION,
            chunker_version=CHUNKER_VERSION,
            embedding_model=embedding_model,
            page_count=len(pages),
            chunk_count=len(chunks),
            prompt_injection_flags=flags,
            warnings=warnings,
            created_by=actor,
            created_at=created_at,
        )
        payload = document.model_dump(mode="json")
        self.repository.save_knowledge_document(payload, chunks)
        self.repository.audit(
            actor,
            "assistant.document_ingested",
            "knowledge_document",
            document.document_id,
            {
                "status": status,
                "raw_sha256": raw_sha,
                "normalized_sha256": normalized_sha,
                "page_count": len(pages),
                "chunk_count": len(chunks),
                "embedding_model": embedding_model,
                "project_scope": request.project_scope,
                "course_scope": request.course_scope,
                "prompt_injection_flags": flags,
            },
        )
        return document

    def list_documents(
        self,
        *,
        project_scope: str | None = None,
        course_scope: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeDocument]:
        return [
            KnowledgeDocument.model_validate(item)
            for item in self.repository.list_knowledge_documents(
                project_scope=project_scope,
                course_scope=course_scope,
                limit=limit,
            )
        ]

    def retrieve(
        self,
        question: str,
        *,
        project_scope: str,
        course_scope: str,
        document_ids: list[str],
        limit: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float, list[str]]:
        retrieval_limit = limit or settings.professor_retrieval_k
        query_tokens = list(dict.fromkeys(_tokens(question)))[:24]
        trace: list[dict[str, Any]] = []
        warnings: list[str] = []
        if not query_tokens:
            trace.append(
                {
                    "stage": "query-validation",
                    "status": "blocked",
                    "message": "No searchable scientific terms were found",
                    "metrics": {"query_terms": 0},
                }
            )
            return [], trace, 0.0, warnings

        fts_query = " OR ".join(f'"{token.replace(chr(34), "")}"' for token in query_tokens)
        lexical = self.repository.search_knowledge_chunks(
            fts_query,
            project_scope=project_scope,
            course_scope=course_scope,
            document_ids=document_ids,
            limit=max(retrieval_limit * 5, 25),
        )
        trace.append(
            {
                "stage": "lexical-retrieval",
                "status": "completed",
                "message": "Searched the scoped FTS5/BM25 index",
                "metrics": {"query_terms": len(query_tokens), "matches": len(lexical)},
            }
        )

        dense: list[tuple[float, dict[str, Any]]] = []
        if self.ollama.enabled:
            try:
                query_vector = self.ollama.embed(
                    [
                        "Instruct: Retrieve passages that directly answer a supervised scientific research question.\n"
                        f"Query: {question}"
                    ]
                )[0]
                candidates = self.repository.list_embedded_knowledge_chunks(
                    project_scope=project_scope,
                    course_scope=course_scope,
                    document_ids=document_ids,
                    embedding_model=self.ollama.embedding_model,
                )
                for candidate in candidates:
                    vector = candidate.get("embedding") or []
                    if len(vector) != len(query_vector):
                        continue
                    similarity = sum(a * b for a, b in zip(query_vector, vector, strict=True))
                    if math.isfinite(similarity):
                        dense.append((similarity, candidate))
                dense.sort(key=lambda item: item[0], reverse=True)
                dense = dense[: max(retrieval_limit * 5, 25)]
                trace.append(
                    {
                        "stage": "dense-retrieval",
                        "status": "completed" if dense else "completed-with-warning",
                        "message": "Searched stored Qwen3 embeddings with cosine similarity",
                        "metrics": {
                            "embedding_model": self.ollama.embedding_model,
                            "indexed_candidates": len(candidates),
                            "matches": len(dense),
                        },
                    }
                )
            except OllamaUnavailable as exc:
                warnings.append(str(exc))
                trace.append(
                    {
                        "stage": "dense-retrieval",
                        "status": "completed-with-warning",
                        "message": "Dense retrieval unavailable; lexical evidence remains active",
                        "metrics": {"reason": str(exc)},
                    }
                )
        else:
            trace.append(
                {
                    "stage": "dense-retrieval",
                    "status": "skipped",
                    "message": "Local embeddings are operator-disabled",
                    "metrics": {"embedding_model": self.ollama.embedding_model},
                }
            )

        combined: dict[str, dict[str, Any]] = {}
        for rank, item in enumerate(lexical, start=1):
            entry = combined.setdefault(item["chunk_id"], {"item": item, "rrf": 0.0})
            entry["rrf"] += 0.55 / (60 + rank)
            entry["lexical_rank"] = rank
        for rank, (similarity, item) in enumerate(dense, start=1):
            entry = combined.setdefault(item["chunk_id"], {"item": item, "rrf": 0.0})
            entry["rrf"] += 0.45 / (60 + rank)
            entry["dense_rank"] = rank
            entry["dense_similarity"] = similarity
        ranked = sorted(combined.values(), key=lambda value: value["rrf"], reverse=True)

        selected: list[dict[str, Any]] = []
        per_document: dict[str, int] = {}
        question_set = set(query_tokens)
        for entry in ranked:
            item = entry["item"]
            document = item["document"]
            count = per_document.get(item["document_id"], 0)
            if count >= 3:
                continue
            text_tokens = set(_tokens(item["text"]))
            lexical_relevance = min(
                1.0,
                len(question_set & text_tokens) / max(1, min(len(question_set), 6)),
            )
            dense_relevance = max(0.0, min(1.0, float(entry.get("dense_similarity", 0.0))))
            relevance = (
                0.55 * lexical_relevance + 0.45 * dense_relevance
                if "dense_similarity" in entry
                else lexical_relevance
            )
            evidence_id = f"{item['document_id']}:p{item['page_number']}:{item['chunk_id'][-8:]}"
            selected.append(
                {
                    "evidence_id": evidence_id,
                    "kind": "document-chunk",
                    "document_id": item["document_id"],
                    "title": document["title"],
                    "source": "university-controlled corpus",
                    "source_url": document.get("source_url"),
                    "url": document.get("source_url"),
                    "source_version": document["source_version"],
                    "page_number": int(item["page_number"]),
                    "section": item["section"],
                    "statement": item["text"],
                    "quote": item["text"],
                    "document_sha256": document["raw_sha256"],
                    "rights_status": document["rights_status"],
                    "retrieval_score": round(relevance, 4),
                    "retrieval_methods": [
                        method
                        for method, present in (
                            ("fts5-bm25", "lexical_rank" in entry),
                            ("qwen3-cosine", "dense_rank" in entry),
                        )
                        if present
                    ],
                    "embedding_model": (
                        self.ollama.embedding_model if "dense_rank" in entry else None
                    ),
                }
            )
            per_document[item["document_id"]] = count + 1
            if len(selected) >= retrieval_limit:
                break

        overall_score = (
            sum(float(item["retrieval_score"]) for item in selected[:3])
            / min(3, len(selected))
            if selected
            else 0.0
        )
        trace.append(
            {
                "stage": "hybrid-fusion",
                "status": "completed" if selected else "completed-with-warning",
                "message": "Fused and diversified reviewable evidence chunks",
                "metrics": {
                    "selected_chunks": len(selected),
                    "source_documents": len(per_document),
                    "retrieval_score": round(overall_score, 4),
                },
            }
        )
        return selected, trace, round(overall_score, 4), warnings

    @staticmethod
    def _decode_content(encoded: str) -> bytes:
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise KnowledgeInputError("Document content is not valid base64") from exc
        if not content or len(content) > settings.professor_max_document_bytes:
            raise KnowledgeInputError(
                f"Document must be between 1 byte and {settings.professor_max_document_bytes} bytes"
            )
        if b"\x00" in content[:1024] and not content.startswith(b"%PDF-"):
            raise KnowledgeInputError("Text document contains binary/NUL data")
        return content

    @staticmethod
    def _extract_pages(content: bytes, media_type: str) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        pages: list[dict[str, Any]] = []
        if media_type == "application/pdf":
            if not content.startswith(b"%PDF-"):
                raise KnowledgeInputError("PDF signature is missing")
            try:
                reader = PdfReader(io.BytesIO(content), strict=True)
                if reader.is_encrypted:
                    raise KnowledgeInputError("Encrypted PDFs are not accepted")
                if len(reader.pages) > settings.professor_max_pages:
                    raise KnowledgeInputError(
                        f"PDF has {len(reader.pages)} pages; configured limit is {settings.professor_max_pages}"
                    )
                for index, page in enumerate(reader.pages, start=1):
                    text = _normalize_text(page.extract_text() or "")
                    if len(text) > 250_000:
                        raise KnowledgeInputError(f"PDF page {index} exceeds the extracted-text limit")
                    if not text:
                        warnings.append(f"Page {index} contains no extractable text; OCR may be required")
                        continue
                    pages.append({"page_number": index, "text": text})
            except KnowledgeInputError:
                raise
            except (PdfReadError, ValueError, TypeError) as exc:
                raise KnowledgeInputError("PDF could not be parsed safely") from exc
        else:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise KnowledgeInputError("Text and Markdown documents must be UTF-8") from exc
            form_pages = text.split("\f")
            if len(form_pages) > settings.professor_max_pages:
                raise KnowledgeInputError("Text document exceeds the configured page limit")
            for index, page in enumerate(form_pages, start=1):
                normalized = _normalize_text(page)
                if normalized:
                    pages.append({"page_number": index, "text": normalized})
        if not pages:
            raise KnowledgeInputError("Document contains no extractable text")
        return pages, warnings

    @staticmethod
    def _prompt_injection_flags(pages: list[dict[str, Any]]) -> list[str]:
        found: set[str] = set()
        for page in pages:
            for name, pattern in PROMPT_INJECTION_PATTERNS.items():
                if pattern.search(page["text"]):
                    found.add(f"{name}:page-{page['page_number']}")
        return sorted(found)

    @staticmethod
    def _chunk_pages(raw_sha256: str, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        max_words = 220
        overlap_words = 40
        for page in pages:
            words = page["text"].split()
            start = 0
            while start < len(words):
                end = min(len(words), start + max_words)
                text = " ".join(words[start:end]).strip()
                if text:
                    identity = hashlib.sha256(
                        f"{raw_sha256}:{page['page_number']}:{start}:{text}".encode("utf-8")
                    ).hexdigest()
                    chunks.append(
                        {
                            "chunk_id": f"KCH-{identity[:16].upper()}",
                            "page_number": int(page["page_number"]),
                            "section": f"Page {page['page_number']}",
                            "text": text,
                            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                            "injection_flagged": False,
                            "embedding": None,
                            "embedding_model": None,
                        }
                    )
                if end >= len(words):
                    break
                start = max(start + 1, end - overlap_words)
        return chunks
