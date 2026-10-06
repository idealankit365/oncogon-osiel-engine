# Phase 1 client showcase audit

Baseline: clean `main` at `c3cfb2e` from `idealankit365/oncogon-osiel-engine`. The supplied local directory was empty, so the repository was cloned there before creating `refactor/client-showcase-backend-driven`.

## Classification of demo, embedded, fallback, mock, fixture and synthetic references

| Class | Findings | Decision |
|---|---|---|
| A — remove | `app/lib/demo-data.ts`, `app/lib/compound-library.ts`, `app/lib/literature-data.ts`, `public/demo-conformers.json`, frontend fake ranking, discovery, Professor answers, experiment history, audit timeline, model metrics and feature bars | Removed production data and UI dependencies. |
| B — replace with API | `/api/compounds`, `/api/experiments`, D1/Drizzle persistence, registry, literature, audit, governance, experiments, capability and readiness displays | FastAPI endpoints now provide domain values. |
| C — legitimate fixture | `backend/tests/**`, `backend/app/data/**`, `backend/scripts/e2e_*`, `OSIEL_DEMO_MODE` | Retained for deterministic backend development and computational tests. Client showcase config explicitly selects backend demonstration mode. |
| D — scientific boundary | “Research use only”, “computational hypothesis”, “not clinical guidance”, “human review”, “simulation only”, out-of-domain and efficacy limitations | Retained. These describe valid scientific constraints. |

Remaining static values in production UI: `app/page.tsx` contains assay defaults, research task choices, and the 7-step workflow labels; these are UI configuration, not runtime measurements. `app/components/model-lab.tsx` and `app/components/recursion-roadmap.tsx` mention historical provider map sizes as narrative provenance rather than live measurements. `app/components/open-discovery-workspace.tsx` has example input placeholders. The backend registry itself contains reference structures and an unvalidated demo adapter, which the frontend labels as development reference. The backend retains deterministic simulation labels and scientific disclaimers.

The frontend uses `GET /health`, `/v1/system/capabilities`, `/v1/system/readiness`, `/v1/compounds`, `/v1/literature`, `/v1/models`, `/v1/audit`, `/v1/experiments`, `/v1/assistant/*`, `/v1/open-discovery/*`, `/v1/rankings`, and `/v1/compounds/{id}/conformer-3d`. No Next.js scientific API route or frontend domain persistence remains. Cloudflare Worker image handling and deployment packaging remain.

The backend's `OSIEL_DEMO_MODE=true` is acceptable only for development, tests, and a clearly labelled client showcase. It relaxes reference authentication and exposes deterministic research workflows. Production requires `OSIEL_DEMO_MODE=false` plus institutional OIDC, PostgreSQL/RDKit, managed object storage, validated oncology models and datasets, qualified laboratory instruments, observability, backups, and approval records.

## Phase 2 extraction map

- `oncogon-osiel-web`: `app/`, `public/`, `worker/`, `build/`, frontend `scripts/`, Next/Vite/Cloudflare config, `package*.json`, frontend tests.
- `oncogon-osiel-api`: `backend/app/`, `backend/tests/`, `backend/scripts/`, backend requirements and API container files.
- Shared/generated contract: `contracts/openapi.json` generated and versioned from FastAPI; frontend response types should be generated from that contract during CI. Cross-repository contract tests should compare generated OpenAPI with the pinned frontend version.
