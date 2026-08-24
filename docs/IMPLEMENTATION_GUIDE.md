# OSIEL implementation guide

## Architecture

```text
Browser / Next.js workbench
        |
        v
FastAPI scientific gateway
  |-- RDKit identity, descriptors and conformers
  |-- prediction/ranking/experiment/QC services
  |-- Professor RAG and Ollama composer
  |-- data connector and immutable acquisition services
  |-- ZINC22, Vina and model laboratory
  |-- multimodal router and evidence fusion
  |-- audit, review and challenger eligibility gates
        |
        +-- SQLite + content-addressed objects (working reference)
        +-- HTTPS specialist model endpoints (operator configured)
```

## Source map

- `app/` — frontend and server routes.
- `app/components/` — workspaces including experiments, Professor, connectors,
  model lab, Vina, 3D and multimodal engine.
- `backend/app/main.py` — API routes and service composition.
- `backend/app/schemas.py` — typed scientific contracts.
- `backend/app/repository.py` — reference persistence and audit.
- `backend/app/model_gateway.py` — secure scientific-model HTTP boundary.
- `backend/app/multimodal_engine.py` — modality routing and fusion.
- `backend/app/data_connectors.py` and `backend/app/connectors/` — sources.
- `contracts/openapi.json` — generated API contract.
- `backend/tests/` — deterministic unit/API/security tests.
- `docs/` — SRS and operational/scientific documentation.

## Developer workflow

1. Run `./start-osiel.sh`.
2. Inspect health and `/v1/system/readiness`.
3. Use `/v1/docs` to test an endpoint.
4. Change Python schemas/services and regenerate OpenAPI with
   `PYTHONPATH=backend .venv/bin/python backend/scripts/export_openapi.py`.
5. Run `npm run verify:handoff` before delivery.
6. Create the reproducible ZIP with `npm run package:handoff`.

## Adding a connector

Register source name, purpose, official endpoint, licence note and default gate;
implement bounded pagination/download, timeout, user agent, checksum and
immutable storage; normalize identifiers/units; quarantine missing licence/QC;
add deterministic fixtures and failure tests; expose capability before fetch.
Never add an unrestricted web scraper.

## Adding a scientific model

Deploy it separately behind HTTPS or loopback, pin its artifact checksum and
return `model_version`, `confidence`, `findings`, `evidence` and `warnings`.
Add external/slice/calibration tests and an applicability-domain rule. Configure
its URL only after approval. An LLM must never synthesize its numeric outputs.

## Learning pipeline

Measured raw file → checksum/parser → assay QC → scientist correction →
independent approval → immutable dataset snapshot → challenger training →
scaffold/time/external tests → promotion decision. The review APIs never mutate
production weights and simulations are permanently ineligible.

## Production migration

The included base stack is genuinely working with SQLite/local objects. Before
institutional production, implement PostgreSQL/RDKit persistence, managed object
storage, background workers, OIDC/RBAC/RLS, secrets, monitoring, backups,
security review, one qualified plate reader and external model validation.
