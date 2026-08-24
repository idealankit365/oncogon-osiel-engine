# OSIEL AI Professor — actual governed engine

## Plain-language description

Professor AI is no longer a scripted chatbot. It is a Python evidence system:

1. an instructor uploads a paper, SOP or approved teaching document;
2. OSIEL verifies the declared rights status and file type;
3. it stores the original bytes by SHA-256 and never edits them;
4. it extracts page text and creates a second immutable normalized manifest;
5. it splits each page into reviewable chunks;
6. SQLite FTS5 always provides BM25 lexical search;
7. when Ollama is enabled, Qwen3-Embedding adds local semantic retrieval;
8. Qwen3-8B receives only the retrieved evidence and must return exact citation IDs;
9. invented citations or uncited non-abstaining answers are rejected;
10. questions, answers, evidence, execution traces and faculty corrections are audited.

The LLM writes the explanation. RDKit, the calibrated endpoint model and Vina remain the quantitative engines.

## Implemented controls

- PDF, UTF-8 TXT and Markdown ingestion.
- Full-text indexing only when `rights_status=approved` and a licence note is recorded.
- Exact project/course filtering and optional per-query document selection.
- Raw-file and normalized-manifest SHA-256 identifiers.
- Page number, document version, source URL and document hash on every retrieved chunk.
- Prompt-like document quarantine; quarantined chunks never enter FTS or dense retrieval.
- FTS5/BM25 retrieval with optional local Qwen3 dense embeddings and hybrid fusion.
- Structured Qwen output; citations must be from supplied evidence.
- Patient-specific clinical and prompt-override blocks.
- Evidence-sufficiency gate and explicit abstention.
- Persisted conversations and visible retrieval/generation trace.
- Instructor/reviewer correction with no automatic retraining.
- Faculty-authored citation and abstention evaluation sets.
- Configurable retention with dry-run and admin-only deletion.

Project/course strings are logical filters in this reference implementation. A university production deployment must map them to verified OIDC/SSO group claims; clients must not be trusted to assign their own institutional membership.

## Local setup for the supplied RTX 4070 Ti 12 GB workstation

Install Ollama, then pull the two bounded local models:

```bash
ollama pull qwen3:8b
ollama pull qwen3-embedding:0.6b
```

Copy `.env.example` to `.env` and set:

```dotenv
OSIEL_DEMO_MODE=false
OSIEL_API_KEY=replace-with-a-secret-or-use-university-oidc
OSIEL_OLLAMA_ENABLED=true
OSIEL_OLLAMA_MODEL=qwen3:8b
OSIEL_OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
OSIEL_PROFESSOR_INGESTION_ENABLED=true
OSIEL_PROFESSOR_RETENTION_DAYS=180
```

Start the full application:

```bash
docker compose up --build
```

The 8B generator and 0.6B embedding model are intentionally selected for the existing 12 GB GPU. Keep large-model escalation on a separate server; do not try to keep a 30B model, Vina workload and both retrieval models resident concurrently on this card.

## API workflow

| Purpose | Route | Required role |
|---|---|---|
| Capability and model state | `GET /v1/assistant/capabilities` | public metadata |
| Ingest approved source | `POST /v1/assistant/documents` | instructor/reviewer/admin in production |
| List scoped documents | `GET /v1/assistant/documents` | authenticated user |
| Create/list consultations | `POST/GET /v1/assistant/conversations` | authenticated user |
| Ask with citations | `POST /v1/assistant/query` | authenticated user |
| Read consultation turns | `GET /v1/assistant/conversations/{id}/turns` | owner or faculty |
| Record correction | `POST /v1/assistant/answers/{id}/feedback` | instructor/reviewer/admin |
| Run faculty evaluation | `POST /v1/assistant/evaluations` | instructor/reviewer/admin |
| Inspect evaluations | `GET /v1/assistant/evaluations` | authenticated user |
| Dry-run/apply retention | `POST /v1/assistant/maintenance/retention` | admin |

## Reproducible checks

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/e2e_professor.py
backend/.venv/bin/python -m pytest backend/tests -q
```

When Ollama is disabled, the E2E workflow still verifies immutable ingestion, retrieval evidence IDs, answer/conversation persistence, correction and quarantine. It deliberately abstains from LLM synthesis, so citation coverage is correctly zero rather than fabricated. When Ollama is enabled, the same script exercises the real local Qwen generation and embedding endpoints.

## Scientific qualification milestone

The repository also contains the requested higher-value milestone:

- one bounded EGFR/IC50 ChEMBL endpoint pipeline with exact relation filtering, duplicate/conflict removal, immutable raw/normalized snapshots, Bemis–Murcko scaffold separation, held-out calibration and frozen test metrics;
- content-addressed checksum verification for every retained scientific artifact; and
- official AutoDock Vina execution followed by atom-order-preserving heavy-atom Kabsch redocking RMSD against the prepared reference ligand.

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/e2e_model_lab.py --live --max-records 1000
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/fetch_vina_example.py
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/e2e_vina.py --exhaustiveness 8
```

A passing internal scaffold test is not independent or prospective biological validation. A redocking RMSD below 2 Å validates pose recovery for one prepared complex, not affinity ranking, cellular activity, safety or efficacy.

## Executed qualification evidence — 22 August 2026

| Artifact | Executed result | Boundary |
|---|---|---|
| `OSIEL_AI_Professor_E2E_Report.json` | Approved text ingested; immutable hashes verified; evidence retrieved; consultation persisted; faculty feedback recorded; adversarial document quarantined. Local model disabled, therefore answer abstained. | Software-control qualification, not biomedical answer accuracy. |
| `OSIEL_Live_ChEMBL_Model_Lab_Report.json` | Real bounded ChEMBL 37 EGFR/IC50 snapshot; 603 unique structures; zero scaffold overlap; frozen-test AUROC 0.9526; promotion blocked. | Internal source/scaffold evaluation, not independent or prospective validation. |
| `OSIEL_Formal_Redocking_Benchmark_Report.json` | Vina 1.2.7, exhaustiveness 8; best heavy-atom RMSD 0.8636 Å; 2.0 Å pose-recovery gate passed; scoring qualification false. | One prepared complex only; not affinity or activity validation. |
| `OSIEL_3D_Conformer_E2E_Report.json` | Eight deterministic ETKDGv3/MMFF94 conformers regenerated and checksum-read from immutable storage. | Identity visualization, not experimental or bound structures. |

## Scale-out path

SQLite FTS5 is appropriate for a workstation or teaching pilot. For institutional scale, retain the same API contracts and move chunks/embeddings to Milvus or OpenSearch, raw files to retention-locked object storage, conversations to PostgreSQL with row-level security, Qwen serving to vLLM/Ray Serve, and ingestion to isolated workers. Before one million users, add verified SSO claims, per-tenant encryption keys, queue back-pressure, abuse/rate limits, evaluation dashboards and regional capacity tests.
