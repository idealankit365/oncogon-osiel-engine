# OSIEL Python engine

OSIEL is the **Oncogon Scientific Intelligence & Experimental Learning Engine**. This package implements a research-use Phase-1 vertical slice: structure standardization, compound registry, deterministic RDKit 3D conformers, source contracts, immutable scientific-document retrieval, governed Professor conversations, deterministic demonstration inference, a real bounded ChEMBL endpoint baseline, uncertainty/OOD status, endpoint-level ADMET signals, transparent ranking, experiment planning, computational dry-runs, QC, Vina execution/redocking, scientific review, audit and model-governance gates.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-test.txt
cd backend
python scripts/generate_seed.py
uvicorn app.main:app --reload --port 8000
```

Open the interactive API contract at `http://localhost:8000/v1/docs`.

## Test

```bash
cd backend
pytest -q
```

The current suite contains 57 passing tests. Executable qualification reports can be reproduced with:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_professor.py
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_conformer.py
PYTHONPATH=backend .venv/bin/python backend/scripts/fetch_vina_example.py
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_vina.py --exhaustiveness 8
```

## Scientific boundary

The included scorer is a deterministic **workflow simulator**, not a validated anticancer model. The generated dose-response observations are software dry-runs, not wet-lab measurements. Simulation-only results are blocked from the training pool and demonstration models are blocked from production promotion.

## Production foundation

The API now includes server-enforced production-mode actor/role checks, an explicit readiness endpoint, content-addressed immutable raw-file storage, and a plate-reader CSV validation service. Set `OSIEL_DEMO_MODE=false` and inject `OSIEL_API_KEY` only in a protected environment. A university OIDC/JWT verifier should replace the reference API-key gate before institutional use.

`POST /v1/plate-reader/imports/validate` accepts an instrument manifest plus base64 CSV, preserves the original bytes by SHA-256, checks the required schema, plate/well uniqueness, numeric fields and vehicle/positive controls, and returns a quarantined QC-readiness decision. A successful schema validation never makes data training-eligible.

Production adapters are specified for PostgreSQL with the RDKit cartridge, S3/Iceberg/Parquet, MLflow, Prefect, Kafka/outbox, OIDC/RLS, Chemprop and ADMET-AI. Those require their own approved datasets, infrastructure, credentials, model artifacts and scientific validation.

## Extended scientific data connectors

OSIEL includes operational connectors for NCI-60/CellMiner, TDC, COCONUT,
NPASS, ANPDB, LOTUS, Tox21, EPA ToxCast, UniProt and Chemspace. Enable them
only after filling the source-specific values in `.env`; see
`docs/EXTENDED_DATA_CONNECTORS.md`.

The five-lane model gateway, evidence-fusion rules, validated-feedback gate and
production roadmap are defined in `docs/MULTIMODAL_ENGINE_AND_ML_PLAN.md`.

Bulk sources use operator-approved HTTPS URLs, response-size limits, SHA-256
verification, immutable raw storage and quarantine. UniProt uses the official
REST API. TDC is an optional pinned dependency:

```bash
pip install -r backend/requirements-connectors.txt
```

Chemspace requires a provider-issued key and its currently documented API path.
