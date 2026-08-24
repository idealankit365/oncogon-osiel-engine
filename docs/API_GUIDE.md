# OSIEL API guide

Interactive Swagger documentation is served at `/v1/docs`; the generated
contract is committed as `contracts/openapi.json` and served at
`/v1/openapi.json`.

## Request identity

Reference requests use:

```text
X-OSIEL-Actor: researcher@example.edu
X-OSIEL-Role: researcher
```

Allowed roles are student, researcher, technician, reviewer, instructor and
admin. Demo mode is not production authentication; university operation needs
OIDC/SSO and server-enforced RBAC/RLS.

## Endpoint groups

- `/health`, `/v1/system/*` — service status and production blockers.
- `/v1/compounds`, `/v1/predictions`, `/v1/rankings` — registry and hypotheses.
- `/v1/open-discovery/*`, `/v1/zinc22/*` — bounded discovery and remote search.
- `/v1/docking/*` — Vina execution and redocking qualification.
- `/v1/experiments`, `/v1/plate-reader/*`, `/v1/results/*` — governed experiment loop.
- `/v1/assistant/*` — AI Professor documents, conversations, citations, feedback and evaluations.
- `/v1/model-lab/*` — immutable ChEMBL snapshots, models and active-learning proposals.
- `/v1/data-connectors/*` — source capability, bounded fetch, UniProt and Chemspace.
- `/v1/multimodal/*` — five-lane evidence fusion and validated review feedback.
- `/v1/models`, `/v1/audit` — governance, promotion boundary and provenance.

## Multimodal example

```bash
curl -X POST http://localhost:8000/v1/multimodal/cases \
  -H 'Content-Type: application/json' \
  -H 'X-OSIEL-Actor: researcher@example.edu' \
  -H 'X-OSIEL-Role: researcher' \
  -d '{
    "question":"What evidence is missing before a supervised follow-up assay?",
    "cancer_type":"Non-small cell lung cancer",
    "cell_line":"A549",
    "target_name":"EGFR",
    "protein_accession":"P00533",
    "compound_ids":["CMP-CUR-0001"],
    "requested_modalities":["chemistry","protein","assay","documents","imaging"]
  }'
```

Missing assay/images/model endpoints are reported as blocked. The engine can
still return a safe abstention; it does not fabricate them.

## Feedback example

`POST /v1/multimodal/cases/{case_id}/reviews` requires reviewer, instructor or
admin role. The record is training-eligible only when approved, measured,
QC-passed, checksum-backed, citation-confirmed and non-abstaining. Even then,
`training_applied` remains false until a frozen challenger pipeline runs.

## Error interpretation

- `403` — role/identity boundary.
- `404` — unresolved immutable resource.
- `422` — invalid scientific or schema input.
- `503` — operator-disabled connector/model/compute service.
- `502` — enabled upstream failed validation.
