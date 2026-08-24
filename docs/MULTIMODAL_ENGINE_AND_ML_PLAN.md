# OSIEL multimodal engine and senior ML implementation plan

## Executive decision

OSIEL is not one large language model. It is a governed ensemble:

1. A multimodal LLM plans, explains and asks for missing information.
2. Retrieval supplies approved, versioned evidence with exact citations.
3. Specialist chemistry, protein, assay and imaging models produce quantitative
   outputs with model versions, uncertainty and applicability-domain status.
4. A deterministic policy engine fuses only supported outputs.
5. A named scientist approves any laboratory action.

No biomedical system can promise 100% accuracy. OSIEL's enforceable targets are
zero unsupported claims on the acceptance set, citation precision 1.00,
calibrated uncertainty, explicit abstention, reproducible versions and external
validation by endpoint, cancer type and cell line.

## Implemented multimodal vertical slice

The FastAPI service exposes:

```text
GET  /v1/multimodal/capabilities
POST /v1/multimodal/cases
GET  /v1/multimodal/cases/{case_id}
POST /v1/multimodal/cases/{case_id}/reviews
```

| Lane | Local capability | Production adapter | Failure behaviour |
|---|---|---|---|
| Chemistry | Registered identity and RDKit descriptors | Chemprop D-MPNN / evaluated 3D model | unresolved compounds block |
| Protein / 3D | accession and artifact contract | ESM-family service plus PDB/AlphaFold context | missing versioned service blocks |
| Assay | immutable result summary, QC and checksum | qualified plate-reader parser | failed QC is excluded |
| Documents | scoped Professor AI retrieval | self-hosted Qwen composer | no cited evidence means abstention |
| Imaging | immutable microscopy artifact contract | CellProfiler/DeepProfiler-style service | no benchmarked model blocks |

The model gateway permits HTTPS or loopback HTTP only, disables redirects,
ignores environment proxies, bounds time and response size, validates structured
output and requires a model version. Final confidence is capped at 0.75 and
reduced by missing citations or cross-modality conflicts.

The workbench has a **Multimodal engine** screen with modality selection,
loader, visible operational trace, evidence package, uncertainty, abstention and
the laboratory-authorization lock. If Python is unavailable it stops safely and
does not invent a browser result.

## Public data: connectors, not indiscriminate scraping

It is not lawful or scientifically sound to scrape “all public data.” Public
visibility does not guarantee redistribution or model-training rights. Every
source uses this state machine:

```text
source registration
-> terms and licence review
-> approved API or release URL
-> rate-limited bounded acquisition
-> immutable raw bytes + SHA-256 + retrieval time
-> release-specific parser
-> canonical identifiers and units
-> duplicate/conflict/QC rules
-> quarantine or accepted dataset
-> independent data-steward approval
```

Current connector coverage includes PubChem, ChEMBL, Open Targets, UniProt,
RCSB PDB, AlphaFold DB, ZINC22/CartBlanche, NCI-60/CellMiner, TDC, COCONUT,
NPASS, ANPDB, LOTUS, Tox21, ToxCast and Chemspace. Executable bounded paths are
present for the principal API/bulk services; licensed or release-page sources
stay disabled until an operator supplies an approved URL, key and checksum.

### Priority connector backlog

| Priority | Source family | Purpose | Acceptance gate |
|---|---|---|---|
| P0 | DepMap/CCLE and GDSC | independent cell-line validation | licence, release, mapping and leakage audit |
| P0 | PRISM repurposing | orthogonal viability evidence | batch/QC provenance and held-out benchmark |
| P0 | PubMed/PMC + Crossref | Professor citations | lawful full text or link-only record, page citations |
| P1 | BindingDB and IUPHAR/BPS | binding evidence | construct, assay, units and relation normalized |
| P1 | DrugCentral/DrugBank where licensed | approved-drug context | redistribution/training rights recorded |
| P1 | SIDER/FAERS where appropriate | safety signals | signal-not-causation boundary and privacy review |
| P1 | cBioPortal/TCGA controlled use | disease context | access control, consent and no patient advice |
| P2 | vendor make-on-demand spaces | purchasability | licensed API and current form/purity verification |

Every new connector must pass tests for allowlisted host, timeout, rate limit,
pagination bound, raw checksum, release ID, schema, units, identity mapping,
duplicates/conflicts, quarantine, licence metadata and deterministic fixture.

## Feedback and learning

OSIEL does not use online reinforcement learning to discover scientific truth.
Ratings are not measured activity. The correct loop is offline, governed active
learning:

```text
raw instrument file
-> immutable checksum and parser validation
-> plate/assay QC
-> scientist correction with cited evidence
-> independent supervisor approval
-> frozen dataset snapshot
-> scaffold/time-separated challenger training
-> calibration + slice + external evaluation
-> red-team and reproducibility review
-> named promotion or rejection
-> monitored champion with rollback
```

The implemented review endpoint records corrections but always returns
`training_applied=false`. A review becomes only a `training_candidate` when it
is approved, linked to measured data, QC-passed, supplied with a raw SHA-256,
backed by case evidence and derived from a non-abstaining case. Simulations,
failed experiments, student ratings, uncited answers and unsafe cases remain
excluded.

Preference optimization may later improve explanation style only. It must not
change chemistry labels, activity values, confidence calibration, assay QC or
experiment authorization.

## Model programme

### Local workstation

For the known RTX 4070 Ti 12 GB machine, use Qwen3-8B via Hugging Face for QLoRA
experiments and Ollama for serving. Start with 4-bit NF4, BF16, LoRA rank 16/32,
batch size 1, gradient accumulation 16 and sequence length 1024. Benchmark 100
steps before a full run. Defer 14B training until at least 24 GB VRAM.

### Scientific models

- Chemistry: RDKit baselines, then Chemprop D-MPNN; add a 3D model only after
  conformer and split validation.
- Protein: sequence/structure embeddings as features, never automatic target
  causality claims.
- Imaging: CellProfiler baseline before deep phenomics, with batch correction
  and plate/domain holdouts.
- Language/vision: local Qwen for cited explanations and workflow. Numerical
  scientific predictions never come from free-form LLM text.

### Acceptance gates

| Component | Minimum production evidence |
|---|---|
| Professor AI | citation precision 1.00; unsupported-answer rate 0; faculty abstention and injection tests |
| Activity classifier | external AUROC/AUPRC and calibration; scaffold/time splits; cell-line and chemotype slices |
| Regression endpoint | external MAE/RMSE, concordance and calibrated intervals |
| Imaging | plate/batch/site holdouts, replicate retrieval, controls and drift checks |
| Docking | redocking plus enrichment benchmark; never efficacy evidence |
| Full workflow | prospective blinded pilot against manual analysis and pre-registered acceptance plan |

Thresholds are endpoint-specific and locked before viewing the final test set.
A failed gate blocks promotion; another modality cannot average it away.

## Security plan

P0 controls before shared university deployment:

- OIDC/SSO, server-enforced RBAC and PostgreSQL row-level security.
- Secrets manager; keys never enter the browser, logs, Git or prompts.
- Egress allowlist, HTTPS, DNS/IP revalidation and no redirects.
- Malware/content-type scanning for documents, images and instrument files.
- Prompt-injection quarantine and exact evidence-ID validation.
- Signed model artifacts, SBOM, dependency/container scans and reproducible builds.
- Immutable audit, retention policy, backups and restoration tests.
- Rate limits, request limits, quotas, monitoring and incident response.
- POPIA/privacy review; patient-identifiable data prohibited in teaching mode.

## Delivery roadmap

1. **Reference layer:** FastAPI/RDKit, 192 structures, Professor controls,
   experiment dry-run/QC, Vina/redocking, 10.10B remote search, ChEMBL model lab,
   3D conformers, extended connectors, multimodal orchestration and feedback gate.
2. **One credible endpoint:** approved ChEMBL plus an independent dataset,
   frozen label charter, calibrated baselines/Chemprop, scaffold/time/external
   tests and signed model card. This outranks adding more search-space claims.
3. **One qualified lab loop:** one named plate reader, immutable raw files,
   plate-map reconciliation, manual-reference comparison and supervised pilot.
4. **Phenomics:** CellProfiler baseline, reproducible perturbational images,
   batch correction, embeddings and prospective active-learning evaluation.
5. **Institutional production:** PostgreSQL/RDKit, immutable object storage,
   Prefect/Kafka, MLflow, GPU serving, OIDC/RBAC/RLS, monitoring, backups,
   penetration test, SOPs, approvals and rollback drills.

Recursion-level capability still requires large consistent proprietary
perturbational datasets, robotics and repeated wet-lab cycles. Code cannot
reproduce that moat without the data, instruments, scientists and validation.

## Definition of done

OSIEL is production-ready for one declared endpoint only when the data licence,
raw lineage, model card, external validation, calibration, security assessment,
instrument qualification, faculty acceptance test and rollback procedure are
approved. Until then it is research-use software that proposes reviewable
hypotheses and safely abstains.
