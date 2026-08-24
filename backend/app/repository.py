from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .config import settings
from .schemas import Compound


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS compound (
  compound_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_name TEXT NOT NULL,
  origin TEXT NOT NULL,
  canonical_smiles TEXT NOT NULL,
  inchikey TEXT NOT NULL UNIQUE,
  descriptors_json TEXT NOT NULL,
  evidence_grade TEXT NOT NULL,
  evidence_mode TEXT NOT NULL,
  aliases_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_compound_display_name ON compound(display_name);
CREATE INDEX IF NOT EXISTS idx_compound_origin ON compound(origin);

CREATE TABLE IF NOT EXISTS prediction (
  prediction_id TEXT PRIMARY KEY,
  compound_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(compound_id) REFERENCES compound(compound_id)
);
CREATE TABLE IF NOT EXISTS ranking_run (
  ranking_run_id TEXT PRIMARY KEY,
  policy_version TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS experiment (
  experiment_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  simulation_only INTEGER NOT NULL,
  protocol_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS experiment_result (
  result_id TEXT PRIMARY KEY,
  experiment_id TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  approved_by TEXT,
  approval_reason TEXT,
  training_eligible INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(experiment_id) REFERENCES experiment(experiment_id)
);
CREATE TABLE IF NOT EXISTS dataset_snapshot (
  snapshot_id TEXT PRIMARY KEY,
  dataset_version TEXT NOT NULL UNIQUE,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS model_version (
  model_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  alias TEXT,
  status TEXT NOT NULL,
  metrics_json TEXT NOT NULL,
  dataset_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(name, version)
);
CREATE TABLE IF NOT EXISTS audit_event (
  audit_id TEXT PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  detail_json TEXT NOT NULL,
  occurred_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_sync_job (
  job_id TEXT PRIMARY KEY,
  source_code TEXT NOT NULL,
  status TEXT NOT NULL,
  detail_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS open_discovery_run (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS docking_job (
  job_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS zinc_search_job (
  job_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_dataset_snapshot (
  snapshot_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_model_run (
  model_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  snapshot_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(snapshot_id) REFERENCES activity_dataset_snapshot(snapshot_id)
);
CREATE TABLE IF NOT EXISTS active_learning_batch (
  batch_id TEXT PRIMARY KEY,
  model_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(model_id) REFERENCES activity_model_run(model_id)
);
CREATE TABLE IF NOT EXISTS docking_benchmark_run (
  benchmark_id TEXT PRIMARY KEY,
  docking_job_id TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(docking_job_id) REFERENCES docking_job(job_id)
);
CREATE TABLE IF NOT EXISTS knowledge_document (
  document_id TEXT PRIMARY KEY,
  raw_sha256 TEXT NOT NULL,
  project_scope TEXT NOT NULL,
  course_scope TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(raw_sha256, project_scope, course_scope)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_document_scope
  ON knowledge_document(project_scope, course_scope, status);
CREATE TABLE IF NOT EXISTS knowledge_chunk (
  chunk_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  page_number INTEGER NOT NULL,
  section TEXT NOT NULL,
  text TEXT NOT NULL,
  text_sha256 TEXT NOT NULL,
  embedding_model TEXT,
  embedding_json TEXT,
  injection_flagged INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(document_id) REFERENCES knowledge_document(document_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunk_document ON knowledge_chunk(document_id);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunk_fts USING fts5(
  chunk_id UNINDEXED,
  document_id UNINDEXED,
  title,
  section,
  text,
  tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS assistant_conversation (
  conversation_id TEXT PRIMARY KEY,
  owner_actor TEXT NOT NULL,
  project_scope TEXT NOT NULL,
  course_scope TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assistant_conversation_owner
  ON assistant_conversation(owner_actor, updated_at);
CREATE TABLE IF NOT EXISTS assistant_turn (
  answer_id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  actor TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(conversation_id) REFERENCES assistant_conversation(conversation_id)
);
CREATE TABLE IF NOT EXISTS assistant_feedback (
  feedback_id TEXT PRIMARY KEY,
  answer_id TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(answer_id) REFERENCES assistant_turn(answer_id)
);
CREATE TABLE IF NOT EXISTS assistant_evaluation (
  evaluation_id TEXT PRIMARY KEY,
  dataset_sha256 TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS multimodal_case (
  case_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  owner_actor TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_multimodal_case_owner
  ON multimodal_case(owner_actor, updated_at);
CREATE TABLE IF NOT EXISTS multimodal_review (
  review_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  training_candidate INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES multimodal_case(case_id)
);
"""


class Repository:
    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = Path(database_path or settings.database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(SCHEMA)

    def seed(self, seed_path: Path | None = None) -> int:
        path = Path(seed_path or settings.seed_path)
        if not path.exists():
            return 0
        payload = json.loads(path.read_text(encoding="utf-8"))
        with self._lock, self.connection() as connection:
            for item in payload:
                connection.execute(
                    """INSERT OR IGNORE INTO compound
                    (compound_id, display_name, source_id, source_name, origin,
                     canonical_smiles, inchikey, descriptors_json, evidence_grade,
                     evidence_mode, aliases_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["compound_id"],
                        item["display_name"],
                        item["source_id"],
                        item["source_name"],
                        item["origin"],
                        item["canonical_smiles"],
                        item["inchikey"],
                        json.dumps(item["descriptors"], sort_keys=True),
                        item["evidence_grade"],
                        item["evidence_mode"],
                        json.dumps(item.get("aliases", [])),
                        item.get("created_at", datetime.now(UTC).isoformat()),
                    ),
                )
        return self.count_compounds()

    def count_compounds(self) -> int:
        with self.connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM compound").fetchone()[0])

    def list_compounds(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        query: str | None = None,
        origin: str | None = None,
    ) -> list[Compound]:
        clauses: list[str] = []
        params: list[Any] = []
        if query:
            clauses.append("(LOWER(display_name) LIKE ? OR LOWER(source_id) LIKE ?)")
            value = f"%{query.lower()}%"
            params.extend((value, value))
        if origin:
            clauses.append("origin = ?")
            params.append(origin)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend((min(limit, 200), max(offset, 0)))
        with self.connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM compound {where} ORDER BY display_name LIMIT ? OFFSET ?", params
            ).fetchall()
        return [self._compound_from_row(row) for row in rows]

    def get_compound(self, compound_id: str) -> Compound | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM compound WHERE compound_id = ?", (compound_id,)
            ).fetchone()
        return self._compound_from_row(row) if row else None

    def get_compounds(self, compound_ids: list[str]) -> list[Compound]:
        if not compound_ids:
            return []
        placeholders = ",".join("?" for _ in compound_ids)
        with self.connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM compound WHERE compound_id IN ({placeholders})", compound_ids
            ).fetchall()
        by_id = {row["compound_id"]: self._compound_from_row(row) for row in rows}
        return [by_id[value] for value in compound_ids if value in by_id]

    def add_compound(self, item: Compound) -> Compound:
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO compound VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.compound_id,
                    item.display_name,
                    item.source_id,
                    item.source_name,
                    item.origin,
                    item.canonical_smiles,
                    item.inchikey,
                    item.descriptors.model_dump_json(),
                    item.evidence_grade,
                    item.evidence_mode,
                    json.dumps(item.aliases),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return item

    def save_json_record(self, table: str, id_column: str, record_id: str, payload: dict[str, Any], **columns: Any) -> None:
        allowed = {
            "prediction": ("prediction_id", ["compound_id"]),
            "ranking_run": ("ranking_run_id", ["policy_version"]),
            "dataset_snapshot": ("snapshot_id", ["dataset_version"]),
        }
        expected_id, allowed_columns = allowed[table]
        if id_column != expected_id or any(name not in allowed_columns for name in columns):
            raise ValueError("Unsupported persistence shape")
        names = [id_column, *columns.keys(), "payload_json", "created_at"]
        values = [record_id, *columns.values(), json.dumps(payload, default=str), datetime.now(UTC).isoformat()]
        placeholders = ",".join("?" for _ in values)
        with self.connection() as connection:
            connection.execute(
                f"INSERT INTO {table} ({','.join(names)}) VALUES ({placeholders})", values
            )

    def audit(self, actor: str, action: str, resource_type: str, resource_id: str, detail: dict[str, Any]) -> str:
        audit_id = f"AUD-{uuid4().hex[:12].upper()}"
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO audit_event VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    audit_id,
                    actor,
                    action,
                    resource_type,
                    resource_id,
                    json.dumps(detail, default=str, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return audit_id

    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_event ORDER BY occurred_at DESC LIMIT ?", (min(limit, 500),)
            ).fetchall()
        return [
            {
                **dict(row),
                "detail": json.loads(row["detail_json"]),
            }
            for row in rows
        ]

    def save_open_discovery_run(self, run_id: str, status: str, payload: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO open_discovery_run VALUES (?, ?, ?, ?)",
                (
                    run_id,
                    status,
                    json.dumps(payload, default=str, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def get_open_discovery_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM open_discovery_run WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def save_docking_job(self, job_id: str, status: str, payload: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO docking_job VALUES (?, ?, ?, ?)",
                (
                    job_id,
                    status,
                    json.dumps(payload, default=str, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def get_docking_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM docking_job WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def save_zinc_search_job(self, job_id: str, status: str, payload: dict[str, Any]) -> None:
        now = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO zinc_search_job
                (job_id, status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                  status = excluded.status,
                  payload_json = excluded.payload_json,
                  updated_at = excluded.updated_at""",
                (
                    job_id,
                    status,
                    json.dumps(payload, default=str, sort_keys=True),
                    now,
                    now,
                ),
            )

    def get_zinc_search_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM zinc_search_job WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def save_activity_snapshot(
        self,
        snapshot_id: str,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO activity_dataset_snapshot VALUES (?, ?, ?, ?)",
                (
                    snapshot_id,
                    status,
                    json.dumps(payload, default=str, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def get_activity_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM activity_dataset_snapshot WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_activity_snapshots(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM activity_dataset_snapshot ORDER BY created_at DESC LIMIT ?",
                (min(max(limit, 1), 100),),
            ).fetchall()
        return [json.loads(row["payload_json"])["snapshot"] for row in rows]

    def save_activity_model(
        self,
        model_id: str,
        status: str,
        snapshot_id: str,
        payload: dict[str, Any],
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO activity_model_run VALUES (?, ?, ?, ?, ?)",
                (
                    model_id,
                    status,
                    snapshot_id,
                    json.dumps(payload, default=str, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def get_activity_model(self, model_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM activity_model_run WHERE model_id = ?",
                (model_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_activity_models(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM activity_model_run ORDER BY created_at DESC LIMIT ?",
                (min(max(limit, 1), 100),),
            ).fetchall()
        return [json.loads(row["payload_json"])["run"] for row in rows]

    def save_active_learning_batch(
        self,
        batch_id: str,
        model_id: str,
        payload: dict[str, Any],
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO active_learning_batch VALUES (?, ?, ?, ?)",
                (
                    batch_id,
                    model_id,
                    json.dumps(payload, default=str, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def save_docking_benchmark(
        self,
        benchmark_id: str,
        docking_job_id: str,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO docking_benchmark_run VALUES (?, ?, ?, ?, ?)",
                (
                    benchmark_id,
                    docking_job_id,
                    status,
                    json.dumps(payload, default=str, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def get_docking_benchmark(self, benchmark_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM docking_benchmark_run WHERE benchmark_id = ?",
                (benchmark_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def find_knowledge_document(
        self,
        raw_sha256: str,
        project_scope: str,
        course_scope: str,
    ) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                """SELECT payload_json FROM knowledge_document
                WHERE raw_sha256 = ? AND project_scope = ? AND course_scope = ?""",
                (raw_sha256, project_scope, course_scope),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def save_knowledge_document(
        self,
        payload: dict[str, Any],
        chunks: list[dict[str, Any]],
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO knowledge_document
                (document_id, raw_sha256, project_scope, course_scope, status, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    payload["document_id"],
                    payload["raw_sha256"],
                    payload["project_scope"],
                    payload["course_scope"],
                    payload["status"],
                    json.dumps(payload, default=str, sort_keys=True),
                    now,
                ),
            )
            for chunk in chunks:
                connection.execute(
                    """INSERT INTO knowledge_chunk
                    (chunk_id, document_id, page_number, section, text, text_sha256,
                     embedding_model, embedding_json, injection_flagged, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        chunk["chunk_id"],
                        payload["document_id"],
                        chunk["page_number"],
                        chunk["section"],
                        chunk["text"],
                        chunk["text_sha256"],
                        chunk.get("embedding_model"),
                        json.dumps(chunk["embedding"]) if chunk.get("embedding") else None,
                        1 if chunk.get("injection_flagged") else 0,
                        now,
                    ),
                )
                if payload["status"] == "indexed" and not chunk.get("injection_flagged"):
                    connection.execute(
                        """INSERT INTO knowledge_chunk_fts
                        (chunk_id, document_id, title, section, text) VALUES (?, ?, ?, ?, ?)""",
                        (
                            chunk["chunk_id"],
                            payload["document_id"],
                            payload["title"],
                            chunk["section"],
                            chunk["text"],
                        ),
                    )

    def list_knowledge_documents(
        self,
        *,
        project_scope: str | None = None,
        course_scope: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if project_scope:
            clauses.append("project_scope = ?")
            params.append(project_scope)
        if course_scope:
            clauses.append("course_scope = ?")
            params.append(course_scope)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(min(max(limit, 1), 500))
        with self.connection() as connection:
            rows = connection.execute(
                f"SELECT payload_json FROM knowledge_document {where} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def get_knowledge_document(self, document_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM knowledge_document WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def search_knowledge_chunks(
        self,
        fts_query: str,
        *,
        project_scope: str,
        course_scope: str,
        document_ids: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        clauses = [
            "knowledge_chunk_fts MATCH ?",
            "d.project_scope = ?",
            "d.course_scope = ?",
            "d.status = 'indexed'",
            "k.injection_flagged = 0",
        ]
        params: list[Any] = [fts_query, project_scope, course_scope]
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            clauses.append(f"k.document_id IN ({placeholders})")
            params.extend(document_ids)
        params.append(min(max(limit, 1), 100))
        with self.connection() as connection:
            rows = connection.execute(
                f"""SELECT k.*, d.payload_json AS document_payload,
                    bm25(knowledge_chunk_fts) AS lexical_rank
                FROM knowledge_chunk_fts
                JOIN knowledge_chunk k ON k.chunk_id = knowledge_chunk_fts.chunk_id
                JOIN knowledge_document d ON d.document_id = k.document_id
                WHERE {' AND '.join(clauses)}
                ORDER BY lexical_rank ASC LIMIT ?""",
                params,
            ).fetchall()
        return [
            {
                **dict(row),
                "document": json.loads(row["document_payload"]),
                "embedding": json.loads(row["embedding_json"]) if row["embedding_json"] else None,
            }
            for row in rows
        ]

    def list_embedded_knowledge_chunks(
        self,
        *,
        project_scope: str,
        course_scope: str,
        document_ids: list[str],
        embedding_model: str,
        limit: int = 20_000,
    ) -> list[dict[str, Any]]:
        clauses = [
            "d.project_scope = ?",
            "d.course_scope = ?",
            "d.status = 'indexed'",
            "k.injection_flagged = 0",
            "k.embedding_model = ?",
            "k.embedding_json IS NOT NULL",
        ]
        params: list[Any] = [project_scope, course_scope, embedding_model]
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            clauses.append(f"k.document_id IN ({placeholders})")
            params.extend(document_ids)
        params.append(min(max(limit, 1), 50_000))
        with self.connection() as connection:
            rows = connection.execute(
                f"""SELECT k.*, d.payload_json AS document_payload
                FROM knowledge_chunk k
                JOIN knowledge_document d ON d.document_id = k.document_id
                WHERE {' AND '.join(clauses)} LIMIT ?""",
                params,
            ).fetchall()
        return [
            {
                **dict(row),
                "document": json.loads(row["document_payload"]),
                "embedding": json.loads(row["embedding_json"]),
            }
            for row in rows
        ]

    def create_assistant_conversation(self, payload: dict[str, Any]) -> None:
        now = payload["created_at"]
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO assistant_conversation
                (conversation_id, owner_actor, project_scope, course_scope, status,
                 payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    payload["conversation_id"],
                    payload["owner_actor"],
                    payload["project_scope"],
                    payload["course_scope"],
                    payload["status"],
                    json.dumps(payload, default=str, sort_keys=True),
                    now,
                    now,
                ),
            )

    def get_assistant_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                """SELECT c.payload_json,
                    (SELECT COUNT(*) FROM assistant_turn t WHERE t.conversation_id = c.conversation_id) AS turn_count
                FROM assistant_conversation c WHERE c.conversation_id = ?""",
                (conversation_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        payload["turn_count"] = int(row["turn_count"])
        return payload

    def list_assistant_conversations(self, owner_actor: str, limit: int = 50) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """SELECT c.payload_json,
                    (SELECT COUNT(*) FROM assistant_turn t WHERE t.conversation_id = c.conversation_id) AS turn_count
                FROM assistant_conversation c WHERE c.owner_actor = ?
                ORDER BY c.updated_at DESC LIMIT ?""",
                (owner_actor, min(max(limit, 1), 200)),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            payload["turn_count"] = int(row["turn_count"])
            result.append(payload)
        return result

    def save_assistant_turn(self, answer_id: str, conversation_id: str, actor: str, payload: dict[str, Any]) -> None:
        now = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO assistant_turn VALUES (?, ?, ?, ?, ?)",
                (answer_id, conversation_id, actor, json.dumps(payload, default=str, sort_keys=True), now),
            )
            connection.execute(
                "UPDATE assistant_conversation SET updated_at = ? WHERE conversation_id = ?",
                (now, conversation_id),
            )

    def get_assistant_answer(self, answer_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM assistant_turn WHERE answer_id = ?",
                (answer_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_assistant_turns(self, conversation_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """SELECT payload_json FROM assistant_turn WHERE conversation_id = ?
                ORDER BY created_at ASC LIMIT ?""",
                (conversation_id, min(max(limit, 1), 500)),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_assistant_feedback(self, payload: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO assistant_feedback VALUES (?, ?, ?, ?, ?)",
                (
                    payload["feedback_id"],
                    payload["answer_id"],
                    payload["reviewer"],
                    json.dumps(payload, default=str, sort_keys=True),
                    payload["created_at"],
                ),
            )

    def save_assistant_evaluation(self, payload: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO assistant_evaluation VALUES (?, ?, ?, ?)",
                (
                    payload["evaluation_id"],
                    payload["dataset_sha256"],
                    json.dumps(payload, default=str, sort_keys=True),
                    payload["created_at"],
                ),
            )

    def save_multimodal_case(
        self,
        case_id: str,
        status: str,
        owner_actor: str,
        payload: dict[str, Any],
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO multimodal_case
                (case_id, status, owner_actor, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                  status = excluded.status,
                  payload_json = excluded.payload_json,
                  updated_at = excluded.updated_at""",
                (case_id, status, owner_actor, json.dumps(payload, default=str, sort_keys=True), now, now),
            )

    def get_multimodal_case(self, case_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM multimodal_case WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def save_multimodal_review(self, payload: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO multimodal_review VALUES (?, ?, ?, ?, ?, ?)",
                (
                    payload["review_id"], payload["case_id"], payload["reviewer"],
                    1 if payload["training_candidate"] else 0,
                    json.dumps(payload, default=str, sort_keys=True), payload["created_at"],
                ),
            )

    def list_assistant_evaluations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM assistant_evaluation ORDER BY created_at DESC LIMIT ?",
                (min(max(limit, 1), 200),),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def purge_assistant_conversations(self, cutoff: str, *, dry_run: bool) -> dict[str, int]:
        with self._lock, self.connection() as connection:
            conversation_ids = [
                row["conversation_id"]
                for row in connection.execute(
                    "SELECT conversation_id FROM assistant_conversation WHERE updated_at < ?",
                    (cutoff,),
                ).fetchall()
            ]
            if not conversation_ids:
                return {"conversation_count": 0, "turn_count": 0, "feedback_count": 0}
            placeholders = ",".join("?" for _ in conversation_ids)
            answer_ids = [
                row["answer_id"]
                for row in connection.execute(
                    f"SELECT answer_id FROM assistant_turn WHERE conversation_id IN ({placeholders})",
                    conversation_ids,
                ).fetchall()
            ]
            feedback_count = 0
            if answer_ids:
                answer_placeholders = ",".join("?" for _ in answer_ids)
                feedback_count = int(
                    connection.execute(
                        f"SELECT COUNT(*) FROM assistant_feedback WHERE answer_id IN ({answer_placeholders})",
                        answer_ids,
                    ).fetchone()[0]
                )
            result = {
                "conversation_count": len(conversation_ids),
                "turn_count": len(answer_ids),
                "feedback_count": feedback_count,
            }
            if dry_run:
                return result
            if answer_ids:
                answer_placeholders = ",".join("?" for _ in answer_ids)
                connection.execute(
                    f"DELETE FROM assistant_feedback WHERE answer_id IN ({answer_placeholders})",
                    answer_ids,
                )
            connection.execute(
                f"DELETE FROM assistant_turn WHERE conversation_id IN ({placeholders})",
                conversation_ids,
            )
            connection.execute(
                f"DELETE FROM assistant_conversation WHERE conversation_id IN ({placeholders})",
                conversation_ids,
            )
            return result

    @staticmethod
    def checksum(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def new_id(prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:12].upper()}"

    @staticmethod
    def _compound_from_row(row: sqlite3.Row) -> Compound:
        return Compound(
            compound_id=row["compound_id"],
            display_name=row["display_name"],
            source_id=row["source_id"],
            source_name=row["source_name"],
            origin=row["origin"],
            canonical_smiles=row["canonical_smiles"],
            inchikey=row["inchikey"],
            descriptors=json.loads(row["descriptors_json"]),
            evidence_grade=row["evidence_grade"],
            evidence_mode=row["evidence_mode"],
            aliases=json.loads(row["aliases_json"]),
        )


repository = Repository()
