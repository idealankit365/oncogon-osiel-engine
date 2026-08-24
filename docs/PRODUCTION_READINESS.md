# OSIEL production-readiness runbook

OSIEL is research software. A deployment is not laboratory-production-ready merely because the web application and Python API run. This runbook defines the evidence required to remove each enforced readiness blocker.

## Runtime topology

Deploy the Next.js interface separately from the FastAPI service. Put the API behind TLS and university SSO, use PostgreSQL plus the RDKit cartridge for operational chemical data, write original instrument files to versioned write-once object storage, and execute ingestion, feature calculation and model evaluation in durable background workers. Send structured application, audit and security events to institutional monitoring. Development, validation and production must be separate environments.

The hosted demonstration intentionally uses the embedded TypeScript adapter when `NEXT_PUBLIC_OSIEL_API_URL` is absent. A production release must point that variable to the independently deployed Python API and must fail closed when it is unavailable.

## Required release evidence

| Gate | Evidence needed to clear it | Accountable owner |
|---|---|---|
| Compound data | Source release IDs, licence decision, canonical structure pipeline, salt/stereo/duplicate policy, checksums and reconciliation report | Data steward |
| Predictive model | Frozen task definition, approved train/validation/external sets, leakage audit, baselines, calibration, subgroup metrics, uncertainty and applicability-domain report | Model owner and independent validator |
| Plate reader | Exact manufacturer/model/export versions, representative untouched exports, parser golden tests, units, plate-map reconciliation, known-control comparison and qualification signature | Laboratory manager |
| Student access | University OIDC claims, server-side RBAC/RLS tests, course/project scoping, supervisor review workflow and sandbox reset | Identity and teaching owners |
| AI Professor | Approved model endpoint, versioned faculty library, page-level citations, retrieval evaluation, injection tests, abstention/escalation thresholds, correction and retention policy | Faculty and privacy owners |
| Molecular visualization | Identity reconciliation, generated-versus-experimental structure labelling, renderer/CSP review, accessibility fallback and qualified experimental-structure provenance | Cheminformatics and security owners |
| Operations | Infrastructure-as-code review, secrets management, rate limits, vulnerability and penetration reports, alerts, backup restoration evidence, incident runbook and support rota | Platform and security owners |
| Institutional acceptance | POPIA assessment, research ethics determination, SOPs, staff training, change control, release approval and signed acceptance criteria | University governance |

The implemented ChEMBL snapshot and scaffold-separated baseline provide auditable starting evidence for the **Predictive model** gate. They do not clear it: a bounded API slice is not a faculty-approved release, the internal frozen split is not an independent external dataset, and an engineering metric threshold is not prospective validation.

The implemented Professor service provides immutable approved-document ingestion, page chunks, FTS5/optional Qwen embeddings, citation validation, abstention, conversations, faculty correction, evaluations, retention and injection quarantine. It does not clear the **AI Professor** gate until the university supplies an approved corpus/model endpoint, verified OIDC scopes, faculty-authored benchmark and signed privacy/security decisions.

The executed 1IEP redocking result (`0.8636 Å` best-pose heavy-atom RMSD at exhaustiveness 8) clears only the software pose-recovery check for that prepared fixture. It does not qualify Vina scoring. The deterministic ETKDGv3 viewer conformers are identity visualizations and must remain distinct from experimental or protein-bound structures.

## Release sequence

1. **Teaching pilot:** connect university identity; enforce student/instructor roles; validate assignments, tutorials, trace retention and sandbox reset. No authoritative wet-lab records.
2. **Laboratory pilot:** qualify one named instrument; retain immutable raw files; compare OSIEL calculations with manually analysed reference plates under supervision.
3. **Scientific validation:** mount approved real datasets and a frozen model; run independent external validation and reproducibility studies; publish the model card and limitations.
4. **Institutional production:** pass security, privacy, restoration, SOP, training and formal acceptance reviews before production data is admitted.

## Non-negotiable controls

- Simulated observations can never become training eligible.
- A model cannot promote itself; an authenticated reviewer must approve a challenger after recorded validation.
- Raw instrument bytes remain unchanged and are addressed by SHA-256.
- Unknown, out-of-domain or weak-evidence answers must abstain or escalate.
- OSIEL never makes a clinical decision and never silently replaces a supervisor or approved SOP.

`GET /v1/system/readiness` is the machine-readable release gate. Any non-empty `blockers` value means the deployment must remain labelled demonstration or supervised pilot.
