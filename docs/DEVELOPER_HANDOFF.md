# OSIEL complete developer handoff

This package contains the Next.js/Vinext interface, Python FastAPI engine, seeded compound registry, SQLite persistence, immutable raw-file storage, API contract, automated tests, experiment demonstration, Docker definitions, SRS and production-readiness runbook. Generated dependencies and runtime databases are intentionally not included; they are recreated from pinned manifests.

## Supported development environment

- macOS or Linux. Windows developers should use WSL2 or Docker Desktop.
- Node.js 22.13 or newer and npm 10 or newer.
- Python 3.12 or 3.13.
- Approximately 4 GB free disk space for Node, Python and RDKit dependencies.
- Optional: Docker Engine 27+ with Docker Compose v2.

## Fastest local installation

From the extracted `oncogon-osiel-engine` directory:

```bash
npm run setup:local
npm run run:local
```

Then open:

- Application: `http://localhost:3000`
- Python API health: `http://localhost:8000/health`
- Interactive API: `http://localhost:8000/v1/docs`
- Machine-readable API: `http://localhost:8000/v1/openapi.json`

The setup command copies `.env.example` to the ignored `.env` file only when `.env` does not already exist, installs the exact Node lockfile, creates `.venv`, and installs pinned Python and test dependencies.

## Docker installation

```bash
cp .env.example .env
docker compose up --build
```

The recommended one-command equivalent is `./start-osiel.sh`; add `--with-ai`
to start Ollama and pull the configured Qwen models. Windows developers can run
`.\start-osiel.ps1`. See `docs/ONE_CLICK_SETUP.md`.

Open `http://localhost:3000`. API state and immutable uploaded objects are retained in the `osiel_api_data` volume. Stop with `docker compose down`. Add `-v` only when you intentionally want to delete local OSIEL data.

## Verification

After local setup:

```bash
npm run verify:handoff
```

This validates the required-file manifest, runs frontend lint, executes the complete Python test suite and performs the deterministic governed end-to-end scenarios. The experiment dry run ranks candidates, plans an eight-dose/three-replicate simulated assay, produces 72 synthetic observations, runs QC, rejects simulated rows from training and proves that the champion model is unchanged. Open Discovery executes the ten-stage local Python/RDKit workflow and persists provenance. The model-lab software fixture executes immutable snapshotting, three-way scaffold splitting, calibration, frozen evaluation and a human-gated active-learning proposal without claiming experimental labels. Professor qualification checks immutable document ingestion, retrieval, persistence, correction and adversarial quarantine. The conformer qualification verifies deterministic ETKDGv3 coordinates and immutable reads. Unit tests separately verify the gated ZINC-22, Vina, redocking and local-model contracts without depending on network or Ollama availability.

Optional real-service/compute smoke tests:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_zinc22.py
PYTHONPATH=backend .venv/bin/python backend/scripts/fetch_vina_example.py
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_vina.py
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_model_lab.py
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_model_lab.py --live --max-records 1000
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_professor.py --output deliverables/OSIEL_AI_Professor_E2E_Report.json
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_conformer.py --output deliverables/OSIEL_3D_Conformer_E2E_Report.json
```

The first command queries the configured public SmallWorld map. The next two fetch checksum-pinned official Vina example files and execute the real local engine. The model-lab command without `--live` uses an explicitly non-experimental software fixture; `--live` retrieves a bounded real ChEMBL slice. Network/provider and CPU-dependent checks are intentionally excluded from the deterministic core suite.

## Environment variables

| Variable | Local default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_OSIEL_API_URL` | `http://localhost:8000` | Browser-visible Python API base URL; it is embedded during frontend build. |
| `OSIEL_DATABASE_PATH` | `./backend/data/osiel.db` | SQLite reference database. |
| `OSIEL_OBJECT_STORE_PATH` | `./backend/data/objects` | Content-addressed immutable raw-file directory. |
| `OSIEL_SEED_PATH` | `./backend/app/data/compounds.json` | Packaged development compound seed. |
| `OSIEL_CORS_ORIGINS` | local frontend origins | Comma-separated allowed browser origins. |
| `OSIEL_DEMO_MODE` | `true` | Keeps reference simulation enabled and relaxes institutional authentication. |
| `OSIEL_API_KEY` | empty | Reference production machine credential. Use a secret manager; never commit it. |
| `OSIEL_PUBLIC_CONNECTORS_ENABLED` | `false` | Server-side safety gate for supported official public APIs. |
| `OSIEL_PUBLIC_CONNECTOR_TIMEOUT_SECONDS` | `12` | Per-request timeout for official-source clients. |
| `OSIEL_PUBLIC_CONNECTOR_USER_AGENT` | contact placeholder | Identifies the research deployment; replace with an institutional contact before enabling outbound APIs. |
| `OSIEL_ZINC22_ENABLED` | `false` | Operator gate for the real bounded SmallWorld remote search. |
| `OSIEL_ZINC22_BASE_URL` | `https://sw.docking.org` | HTTPS service used for live map metadata and graph search. |
| `OSIEL_ZINC22_MAP` | `REALDB-2025-07.smi.anon` | Provider map verified at each execution; map availability and counts can change. |
| `OSIEL_ZINC22_TIMEOUT_SECONDS` | `45` | Map/search request timeout. |
| `OSIEL_MODEL_LAB_ENABLED` | `false` | Operator gate for immutable ChEMBL snapshots, training and active-learning APIs. |
| `OSIEL_MODEL_LAB_MAX_RECORDS` | `2000` | Maximum ChEMBL source records retrieved per model-lab snapshot. |
| `OSIEL_MODEL_LAB_MAX_CANDIDATES` | `500` | Maximum candidate pool for model prediction or active-learning selection. |
| `OSIEL_VINA_ENABLED` | `false` | Operator gate for real local Vina CPU work. |
| `OSIEL_VINA_MAX_CPU` | `4` | Server-side Vina CPU ceiling. |
| `OSIEL_VINA_MAX_TIMEOUT_SECONDS` | `600` | Server-side Vina wall-time ceiling. |
| `OSIEL_OLLAMA_ENABLED` | `false` | Operator gate for the local evidence composer. |
| `OSIEL_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama endpoint outside Docker; Compose defaults to the host bridge. |
| `OSIEL_OLLAMA_DOCKER_BASE_URL` | `http://host.docker.internal:11434` | Host bridge used by the API container. |
| `OSIEL_OLLAMA_MODEL` | `qwen3:8b` | Local model tag; output remains evidence-bound and unvalidated. |
| `OSIEL_OLLAMA_EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | Optional local dense-retrieval model. |
| `OSIEL_PROFESSOR_INGESTION_ENABLED` | `false` | Operator gate for approved PDF/TXT/Markdown ingestion. |
| `OSIEL_PROFESSOR_MAX_DOCUMENT_BYTES` | `20000000` | Server-enforced document-size ceiling. |
| `OSIEL_PROFESSOR_MAX_PAGES` | `500` | Server-enforced PDF page ceiling. |
| `OSIEL_PROFESSOR_MAX_CHUNKS` | `2000` | Maximum page chunks retained from one approved document. |
| `OSIEL_PROFESSOR_RETRIEVAL_K` | `8` | Maximum evidence chunks returned to one consultation. |
| `OSIEL_PROFESSOR_RETENTION_DAYS` | `180` | Reference conversation-retention window; deletion is admin-only. |

When `NEXT_PUBLIC_OSIEL_API_URL` is empty or unreachable, the interface displays “Backend unavailable” and does not invent scientific data. Set the URL to the FastAPI service for development and client showcases.

## Repository map

```text
app/                         Next.js research workbench and API routes
backend/app/                 FastAPI scientific workflow engine
backend/app/connectors/      PubChem, ChEMBL, Open Targets, RCSB and AlphaFold clients
backend/app/data/            192 development/reference structures
backend/tests/               Automated backend tests
backend/scripts/             Seed generator and executable E2E scenario
3D conformers               Fetched from FastAPI; unavailable state on failure
contracts/openapi.json       Generated API specification
backend/app/                 Sole scientific/domain persistence implementation
docs/                        SRS, handoff and production-readiness documents
deliverables/                SRS and experiment report artifacts
scripts/                     Setup, run, test, build and packaging commands
Dockerfile.web               Frontend production container
docker-compose.yml           Complete local web/API stack
```

The Open Discovery architecture and score formula are in `docs/OPEN_DISCOVERY_WORKFLOW.md`. Live multi-billion search, Vina, the model laboratory, Professor AI, result-linked 3D compounds, and the detailed Recursion capability/funding gap are documented in `docs/ZINC22_BILLION_SCALE_SEARCH.md`, `docs/VINA_DOCKING.md`, `docs/MODEL_LAB_AND_ACTIVE_LEARNING.md`, `docs/AI_PROFESSOR_ENGINE.md`, `docs/INTERACTIVE_3D_COMPOUNDS.md`, and `docs/RECURSION_FREE_ALTERNATIVES_ROADMAP.md`.

## Production-mode warning

Do not switch `OSIEL_DEMO_MODE=false` and call the result laboratory production. The reference API-key layer is a deployment boundary, not university SSO. Institutional operation additionally requires an approved dataset and validated model, qualified instrument parser, university OIDC, managed PostgreSQL/RDKit and object storage, background workers, monitoring, restoration tests, POPIA/security review, SOPs and faculty acceptance. The exact release evidence is listed in `docs/PRODUCTION_READINESS.md`.

The default cockpit IC50/activity outputs are deterministic research hypotheses. Model-lab probabilities are endpoint-specific baseline estimates from the selected snapshot. Neither is a physical measurement, validated efficacy prediction, clinical evidence or medical advice.
