> Historical assessment before the backend-driven client showcase refactor. References below to frontend D1, embedded fixtures, and browser fallbacks describe the earlier architecture and are superseded by README.md.

# OSIEL — Technical Completion Guide

**Audience:** the engineer(s) taking this from reference implementation to production.
**Method:** every claim below was verified against the running code and the live API on
2026-08-24, not from the README. Where the README and the code disagree, the code wins.

---

## 0. The one-paragraph answer

The **plumbing is essentially finished; the science is not started.** You have 10,396 lines
of backend Python, 55 API paths / 60 operations, 24 database tables, 16 external data-source
connectors, real RDKit chemistry, and a governance/audit layer that already works. What you
do **not** have is a predictive model — the thing the product exists to provide. The current
"activity probability" is a SHA-256 hash mixed with drug-likeness descriptors. No amount of
DB wiring changes that. Budget roughly **15% of remaining effort for engineering and 85% for
data + model + institutional qualification.**

---

## 1. Honest current state

### 1.1 What is genuinely real

| Component | Status | Evidence |
|---|---|---|
| RDKit standardisation & descriptors | **Real** | `/v1/compounds` returns computed formula, cLogP, TPSA, QED |
| 192-compound reference registry | **Real** | `/health` → `compound_count: 192` |
| Immutable content-addressed object store | **Real** | SHA-256 addressing in `immutable_storage.py` |
| Audit / lineage events | **Real** | `audit_event` table, written on every governed action |
| Model laboratory (ChEMBL baseline) | **Real** | `model_lab.py` uses `LogisticRegression`, `GroupShuffleSplit`, `roc_auc_score` |
| 16 external connectors | **Real code**, gated off | `backend/app/connectors/`, 1,212 LOC |
| AutoDock Vina execution | **Real**, needs x86_64 | `vina_docking.py` runs a bounded child process |
| Governance gates (promotion, review, QC) | **Real** | `governance.py`, champion/challenger boundary |

### 1.2 What is a placeholder — read this carefully

**The core predictor is not a model.** From `backend/app/prediction.py:103-113`:

```python
hashed = _stable_unit_interval(compound.inchikey, cancer_type.lower(), cell_line or "")
activity = min(0.97, max(0.12,
    0.26 + 0.34 * druglike + 0.24 * property_fit + 0.16 * hashed))
```

`_stable_unit_interval` is `sha256(...)` normalised to `[0,1]`. So:

- **16% of every activity score is hash noise.**
- The remaining 84% is QED + property-fit — **pure drug-likeness, containing zero target,
  pathway or assay information.**
- `cancer_type` and `cell_line` enter **only through the hash**. Switching A549 → MDA-MB-231
  changes the number pseudo-randomly with no biological meaning.
- `IC50`, `selectivity` and the confidence interval are algebraic transforms of that same
  number, so they inherit the same emptiness.

The ADMET panel (`ADMETService`) is more defensible — deterministic rules over real
descriptors — but it is a screening heuristic, explicitly "not safety claims."

Also placeholder:

| Item | Reality |
|---|---|
| Dashboard `10.10B` tile | Hardcoded string literal in `app/page.tsx:192`, repeated in 5 components |
| Dashboard first paint | `app/page.tsx` has **zero `useEffect`** — nothing fetches until you click "run" |
| `TOP-5 MEAN SCORE` | Real arithmetic over the hardcoded `demoCandidates` array |
| 72 dose-response observations | Synthetic, generated in `experiments.py` |
| Auth | `demo_mode=true` bypasses everything (`security.py:27`) |

---

## 2. Databases — how many, and what to do with each

**Answer: 4 stores today, 3 in the production target.**

### 2.1 DB #1 — SQLite (backend system of record) ✅ working

- **Location:** `/app/data/osiel.db` in the container, on the `osiel_api_data` volume.
- **Env:** `OSIEL_DATABASE_PATH`
- **Driver:** stdlib `sqlite3`, `check_same_thread=False` (`repository.py:248`)
- **24 tables:**

```
active_learning_batch      docking_benchmark_run    open_discovery_run
activity_dataset_snapshot  docking_job              prediction
activity_model_run         experiment               ranking_run
assistant_conversation     experiment_result        source_sync_job
assistant_evaluation       knowledge_chunk          zinc_search_job
assistant_feedback         knowledge_document       compound
assistant_turn             model_version            dataset_snapshot
audit_event                multimodal_case          multimodal_review
```

- Also hosts the **FTS5 full-text index** for Professor AI retrieval, plus optional
  Qwen3 embedding vectors stored per chunk.

### 2.2 DB #2 — Cloudflare D1 (frontend) ⚠️ orphaned

- **Schema:** `db/schema.ts` — a **single** table, `experiments` (13 columns).
- **Migration:** `drizzle/0000_romantic_hemingway.sql`
- **Binding:** `DB`, declared in `.openai/hosting.json`, accessed via `db/index.ts`.
- **Problem:** this duplicates the backend's `experiment` table. Two systems of record for
  the same entity is a bug waiting to happen.
- **Decision required:** either delete D1 and let the Worker proxy to FastAPI (recommended),
  or formally scope D1 to edge-cache/session state only. Do not leave it ambiguous.

### 2.3 DB #3 — Object store ✅ working, needs swap

- **Now:** filesystem, content-addressed by SHA-256, at `OSIEL_OBJECT_STORE_PATH`.
- **Target:** MinIO/S3 (`minio` service already defined under the `future-infra` profile).
- **Work:** implement an S3 backend behind the existing `ImmutableObjectStore` interface.
  The interface is already the right shape, so this is a genuinely small change.

### 2.4 DB #4 — PostgreSQL + RDKit cartridge ❌ not connected

Defined in `docker-compose.yml` under profile `future-infra`, image `postgres:17`. **Nothing
in the Python code references PostgreSQL — there is no driver, no DSN, no ORM.** The service
exists as a placeholder only.

#### How to actually connect it

```bash
# 1. Add deps
echo "sqlalchemy==2.0.*" >> backend/requirements.txt
echo "psycopg[binary]==3.2.*" >> backend/requirements.txt

# 2. Use an RDKit-cartridge image instead of stock postgres:17
#    docker-compose.yml -> postgres.image: informaticsmatters/rdkit-cartridge-debian:latest

# 3. Introduce a DSN setting in backend/app/config.py
#    database_url: str = os.getenv("OSIEL_DATABASE_URL", "")   # empty => SQLite

# 4. Enable the cartridge inside the DB
#    CREATE EXTENSION IF NOT EXISTS rdkit;
#    ALTER TABLE compound ADD COLUMN mol mol;
#    CREATE INDEX idx_compound_mol ON compound USING gist(mol);
```

**The real work is `repository.py`.** It is ~1,000 lines of hand-written SQL with SQLite
idioms that do not port cleanly:

| SQLite idiom | PostgreSQL equivalent |
|---|---|
| `INSERT OR REPLACE` | `INSERT ... ON CONFLICT (pk) DO UPDATE` |
| `AUTOINCREMENT` | `GENERATED ALWAYS AS IDENTITY` |
| Dynamic typing (JSON in `TEXT`) | `JSONB` (and migrate the payloads) |
| `FTS5` virtual table | `tsvector` + GIN, **or** `pgvector` for dense retrieval |
| `datetime('now')` | `now()` |

**Recommended path:** introduce SQLAlchemy Core as a dialect-neutral layer, keep SQLite for
local dev and CI, and let `OSIEL_DATABASE_URL` select Postgres in staging/production. Do
**not** attempt a big-bang rewrite — port table-group by table-group behind the existing
`Repository` method signatures, which are already a clean seam.

**Estimate: 3–5 engineer-weeks**, including the FTS5 → tsvector/pgvector migration.

---

## 3. External APIs — the 16 sources

All connector code **already exists and is real**. Every one is **fail-closed**: disabled by
default, and switched on by an env gate. You are enabling and qualifying these, not writing
them.

### 3.1 Public APIs — gate: `OSIEL_PUBLIC_CONNECTORS_ENABLED=true`

| # | Source | Endpoint | Auth | Purpose |
|---|---|---|---|---|
| 1 | PubChem PUG REST | `https://pubchem.ncbi.nlm.nih.gov/rest/pug` | none | Compound identity |
| 2 | ChEMBL | `https://www.ebi.ac.uk/chembl/api/data` | none | Bioactivity, pChEMBL |
| 3 | Open Targets | `https://api.platform.opentargets.org/api/v4/graphql` | none | Disease→target |
| 4 | RCSB PDB | `https://data.rcsb.org/rest/v1/core/entry` | none | Structures |
| 5 | AlphaFold DB | `https://alphafold.ebi.ac.uk/api/prediction` | none | Predicted structures |
| 6 | UniProt | `https://rest.uniprot.org/uniprotkb` | none | Protein metadata |

> **Before enabling:** set a real contact address in
> `OSIEL_PUBLIC_CONNECTOR_USER_AGENT`. NCBI and EBI throttle or ban anonymous
> bulk callers. This is a condition of use, not a nicety.

### 3.2 Remote search & licensed

| # | Source | Endpoint | Auth | Gate |
|---|---|---|---|---|
| 7 | ZINC-22 / SmallWorld | `https://sw.docking.org` | none | `OSIEL_ZINC22_ENABLED` |
| 8 | Chemspace | `https://api.chem-space.com` | **API key** | `OSIEL_CHEMSPACE_API_KEY` + `_SEARCH_PATH` |

Chemspace needs registration; the search path is supplied with the key. The code
deliberately refuses to guess the route.

### 3.3 Bulk releases — gate: `OSIEL_SOURCE_CONNECTORS_ENABLED=true`

Each needs a `*_BULK_URL` **and** a `*_BULK_SHA256`. Without the checksum the payload is
retained but marked `quarantined-checksum-required` and can never become training data.

| # | Source | Where to get the release |
|---|---|---|
| 9 | NCI-60 / CellMiner | `https://discover.nci.nih.gov/cellminer/loadDownload.do` |
| 10 | COCONUT | `https://coconut.naturalproducts.net/download` |
| 11 | NPASS | `https://bidd.group/NPASS/downloadnpass.html` |
| 12 | LOTUS | `https://lotus.naturalproducts.net/download` |
| 13 | ANPDB | `https://african-compounds.org` |
| 14 | Tox21 | `https://tripod.nih.gov/tox21/pubdata` |
| 15 | EPA ToxCast | `https://www.epa.gov/comptox-tools/exploring-toxcast-data` |
| 16 | TDC (PyTDC) | Python library — `pip install -r backend/requirements-connectors.txt` |

> **arm64 note:** PyTDC pins `cellxgene-census==1.15.0`, which is not published for arm64.
> On Apple Silicon either build the API image for `linux/amd64` or leave
> `OSIEL_INSTALL_OPTIONAL_CONNECTORS=false` (current setting).

### 3.4 Model adapters — you must supply these

Three HTTP endpoints are **contract-defined but unimplemented**. This is where you write new
services, not just configure them.

| Adapter | Env var | Expected |
|---|---|---|
| Chemistry | `OSIEL_CHEM_MODEL_URL` | Chemprop D-MPNN or equivalent |
| Protein | `OSIEL_PROTEIN_MODEL_URL` | ESM or equivalent |
| Imaging | `OSIEL_VISION_MODEL_URL` | CellProfiler-style features |

Contract: return structured findings + confidence + evidence + an **exact model version**.
Gate with `OSIEL_MULTIMODAL_ENABLED=true`, auth via `OSIEL_MULTIMODAL_API_TOKEN`.

Plus **Ollama** for Professor AI (`OSIEL_OLLAMA_ENABLED`) — already wired,
`./start-osiel.sh --with-ai` starts it.

---

## 4. Internal API — 55 paths, 60 operations

You do **not** need to write new CRUD. The surface is complete. Breakdown:

| Domain | Ops | State |
|---|---|---|
| assistant (Professor AI) | 11 | Real; needs Ollama enabled |
| model-lab | 7 | **Real ML**; gate `OSIEL_MODEL_LAB_ENABLED` |
| data-connectors | 6 | Real; needs source gates |
| compounds | 4 | Real RDKit |
| docking | 4 | Real Vina; x86_64 only |
| zinc22 | 4 | Real; needs gate |
| multimodal | 4 | Contract only — **needs your adapters** |
| experiments | 3 | **Synthetic observations** |
| models (governance) | 3 | Real |
| open-discovery | 3 | Real local compute |
| system, sources | 4 | Real |
| predictions, rankings, literature, audit, plate-reader, results, health | 7 | `predictions` is the **hash placeholder** |

**Endpoints needing real work: 2** — `POST /v1/predictions` (replace the hash) and the
multimodal group (write the adapters). Everything else is enable-and-qualify.

---

## 5. Work breakdown

### Phase 1 — Engineering (~6–10 engineer-weeks)

1. **Decide the D1 question.** Delete or scope it. *(2 days)*
2. **SQLite → PostgreSQL + RDKit cartridge.** Port `repository.py` behind SQLAlchemy.
   *(3–5 weeks)*
3. **Object store → S3/MinIO** behind the existing interface. *(3–5 days)*
4. **Turn off demo mode.** Set `OSIEL_DEMO_MODE=false`, replace the API-key check in
   `security.py:27` with university OIDC JWT validation, keep the role boundary.
   *(1–2 weeks)*
5. **Wire the frontend to load on mount.** Add the missing `useEffect`; remove the
   hardcoded `10.10B` tile or bind it to live map metadata. *(2–3 days)*
6. **Observability**: structured logs, metrics, alerts, tested backup restore. *(1 week)*

### Phase 2 — Data (~4–8 weeks, mostly waiting on licences)

7. Set a real contact User-Agent; enable public connectors.
8. Obtain each bulk release URL **+ its published SHA-256**; clear quarantine.
9. Register for Chemspace if commercial availability matters.
10. Build the approved task dataset with a **locked external evaluation set**.

### Phase 3 — The actual science (the long pole, 6–18 months)

11. **Replace `prediction.py` with a trained model.** The `model_lab.py` pipeline is your
    starting point — it already does scaffold splitting, calibration and frozen metrics
    correctly. Promote that pattern to the main predictor.
12. Leakage audit, baselines, subgroup metrics, uncertainty, applicability domain.
13. **Prospective wet-lab validation.** Nothing substitutes for this.
14. Qualify a **named** plate reader against untouched real exports.
15. POPIA assessment, ethics determination, SOPs, faculty sign-off.

### The gates, from the live API

`GET /v1/system/readiness` returns, right now:

```json
{
  "blockers": [
    "OSIEL_DEMO_MODE must be false",
    "Production API credential or OIDC integration is not configured",
    "Validated oncology model and approved dataset are not mounted",
    "Institutional security, POPIA and scientific approvals are not recorded",
    "Specific plate-reader adapter must be qualified against real exports"
  ]
}
```

Use this endpoint as your definition of done. It is honest by design and does not hide
blockers.

---

## 6. Order of attack

```
Week 1     Decide D1. Set User-Agent. Enable public connectors. See real data flow.
Week 2-6   PostgreSQL + RDKit cartridge migration.
Week 4-6   OIDC, demo mode off, S3 object store.  (parallel)
Week 6-10  Bulk releases + checksums; build the approved dataset.
Month 3+   Model development. This is the project.
```

**Do not** start the Postgres migration and the model work at the same time with one
engineer. The DB migration is well-defined and finishable; the model is open-ended. Finish
the former first so it stops being a distraction.

---

## 7. The thing to keep saying out loud

Every number this system currently shows for **activity, IC50, or selectivity is a
placeholder**, and the UI is already honest about it (`Updated: deterministic demo`,
`RNK-EMBEDDED-DEMO`, the scientific-boundary banners). Preserve that honesty through the
rebuild. The single most damaging thing anyone could do is connect a real database, watch
real compounds appear, and conclude the *scores* became real at the same moment. They will
not. They become real only after step 11 — and only for the endpoint, cell line and
chemical space the training data actually covers.
