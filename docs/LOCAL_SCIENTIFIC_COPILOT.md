# Local evidence-bound scientific copilot

This document is retained as the short local-model entry point. The complete engine, ingestion workflow, API table, evaluation controls and scale-out design are in [`AI_PROFESSOR_ENGINE.md`](AI_PROFESSOR_ENGINE.md).

OSIEL Professor is a Python retrieval and governance service with an optional local Qwen prose layer. It is not the chemistry, docking or activity model. RDKit, the endpoint model and AutoDock Vina perform quantitative computation; the LLM explains retrieved evidence and must abstain when it cannot support an answer.

## Current guarded path

1. An instructor/reviewer/admin uploads an approved PDF, UTF-8 TXT or Markdown source.
2. OSIEL records rights metadata and stores the original bytes and normalized manifest by SHA-256.
3. Page-preserving chunks are screened for prompt-like instructions; flagged content is quarantined from retrieval.
4. SQLite FTS5 performs lexical retrieval. Optional `qwen3-embedding:0.6b` vectors add semantic retrieval and hybrid rank fusion.
5. Project, course and selected-document filters constrain the evidence set.
6. `qwen3:8b` receives only retrieved evidence and must return schema-valid output with exact evidence IDs.
7. Unsupported IDs, patient-specific clinical requests and prompt overrides are blocked. Insufficient evidence produces an explicit abstention.
8. Conversations, answer traces, citations, faculty corrections and evaluation runs are persisted and audited.
9. Corrections never retrain or promote a model automatically.

## Recommended local setup for the RTX 4070 Ti 12 GB system

```bash
ollama pull qwen3:8b
ollama pull qwen3-embedding:0.6b
```

Configure `.env`:

```dotenv
OSIEL_OLLAMA_ENABLED=true
OSIEL_OLLAMA_BASE_URL=http://127.0.0.1:11434
OSIEL_OLLAMA_MODEL=qwen3:8b
OSIEL_OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
OSIEL_PROFESSOR_INGESTION_ENABLED=true
OSIEL_OLLAMA_TIMEOUT_SECONDS=120
```

Then start Ollama and OSIEL. Docker Compose uses `OSIEL_OLLAMA_DOCKER_BASE_URL=http://host.docker.internal:11434` so the API container can call the host model.

## Verification

```bash
curl http://localhost:8000/v1/assistant/capabilities
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/e2e_professor.py \
  --output deliverables/OSIEL_AI_Professor_E2E_Report.json
```

When Ollama is disabled or unavailable, the engine still executes ingestion, retrieval, persistence, faculty-feedback and quarantine controls, then abstains instead of inventing prose. A production university deployment must replace client-supplied project/course strings with verified OIDC claims and complete faculty evaluation, privacy, security and retention approvals.

## Official references

- [Ollama embeddings](https://docs.ollama.com/capabilities/embeddings)
- [Ollama embed API](https://docs.ollama.com/api/embed)
- [Qwen3 Embedding](https://qwenlm.github.io/blog/qwen3-embedding/)
- [SQLite FTS5](https://www.sqlite.org/fts5.html)
- [pypdf text extraction](https://pypdf.readthedocs.io/en/latest/user/extract-text.html)
