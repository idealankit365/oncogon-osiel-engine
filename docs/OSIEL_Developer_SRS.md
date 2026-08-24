# Oncogon AI
## OSIEL — Scientific Intelligence & Experimental Learning Engine
### Developer-Grade Software Requirements Specification

Document ID: ONCOGON-OSIEL-SRS-001
Version: 1.2 — Governed Professor, qualified model/redocking, and interactive 3D implementation
Date: 22 August 2026
Classification: Research use only
Status: Scope freeze and implementation baseline

---

## 1. Executive decision

OSIEL is the scientific intelligence core of Oncogon AI. Its Phase 1 product question is:

> Which compounds should a research team prioritize for laboratory validation, why, and with what uncertainty?

OSIEL is not one monolithic AI model. It is a governed evidence-to-experiment system:

scientific data → chemical identity → biological context → assay meaning → governed task → prediction and uncertainty → ADMET screening → evidence → transparent ranking → experiment design → result QC → scientific approval → immutable dataset snapshot → challenger evaluation → approved champion deployment.

This specification freezes 67 core requirements. Requirements 1–60 define the original scientific engine scope. Requirements 61–67 add the developer contracts, product workbench, security, reproducibility, and end-to-end acceptance conditions needed to make that scope implementable. Version 1.2 also defines separately numbered Open Discovery, model-laboratory, active-learning, docking-qualification, governed-Professor and 3D-visualization addenda without rewriting the frozen core identifiers.

The accompanying source is an executable developer reference. It includes a FastAPI backend; RDKit structure processing and deterministic 3D conformers; a registry of 192 local reference structures; live bounded search against a provider-reported 10.10B-entry REALDB map; deterministic cockpit predictions; real AutoDock Vina execution; redocking RMSD; immutable ChEMBL endpoint snapshots; three-way scaffold-separated baseline training, calibration and evaluation; applicability-domain reporting; active-learning proposals; an evidence-bound Professor with controlled document ingestion, retrieval, citations, conversations and faculty correction; transparent ranking; experiment planning; a computational dose-response dry-run; QC gates; audit records; and a connected Next.js workbench with interactive result-linked molecular visualization. It does not claim to be a clinically validated system, a wet laboratory, Recursion's proprietary platform, or an institutionally approved oncology model.

## 2. Document purpose

The multimodal execution, public-source onboarding and validated-feedback
requirements in `docs/MULTIMODAL_ENGINE_AND_ML_PLAN.md` are normative. They
prohibit automatic reinforcement learning from simulations, ratings, uncited
answers, failed QC and unapproved measurements.

This SRS is the binding technical baseline for product, data engineering, cheminformatics, machine learning, frontend, backend, DevOps, QA, and scientific-review teams. It defines:

- system scope and non-goals;
- user roles and governed decisions;
- 67 frozen core requirements plus uniquely testable implementation addenda;
- data entities and provenance rules;
- model-development and ranking logic;
- API and event contracts;
- security and deployment expectations;
- acceptance tests and release gates;
- the exact status of the current reference implementation.

Where a scientific or production capability is not fully implemented, this document labels it adapter-ready or deferred. No interface text, demo output, or API response may silently upgrade a hypothesis into measured evidence.

## 3. Product boundaries

### 3.1 In scope for Phase 1

- Compound identity ingestion and standardization.
- Natural-product and synthetic-compound source registries.
- Assay and endpoint normalization without collapsing unlike endpoints.
- Versioned, leakage-aware dataset construction.
- Classical molecular models and graph-model comparison on identical splits.
- Uncertainty, calibration, applicability-domain, and analog evidence.
- Endpoint-specific ADMET screening.
- Explainable multi-objective prioritization and diversity selection.
- Experiment protocol planning and result capture.
- QC, named scientific review, audit, snapshot, and champion/challenger gates.
- A research workbench for compound review and computational software-flow experiments.

### 3.2 Explicit non-goals for Phase 1

- Clinical diagnosis, prognosis, or treatment recommendation.
- Patient-specific decision support or storage of identifiable health data.
- Autonomous wet-lab execution.
- Presentation of simulated observations as experimental efficacy evidence.
- Automatic retraining or automatic replacement of a production model.
- De novo molecular generation, retrosynthesis, or autonomous synthesis planning.
- Docking score presented as proof of efficacy.
- Full multi-omics or digital-twin modeling.
- Internet-wide indiscriminate scraping that ignores licences, robots controls, provenance, or source release identifiers.

### 3.3 Claim boundary

Every ranking, prediction, assistant answer, and dry-run result shall display a research-use notice. Predictions are hypotheses requiring experimental validation and qualified scientific review. A computational experiment validates software orchestration only; it does not perform a physical assay.

## 4. Stakeholders and roles

| Role | Primary responsibility | Authority |
|---|---|---|
| Research scientist | Define biological context, inspect evidence, propose experiments | Create tasks and protocols; review hypotheses |
| Medicinal chemist | Review structure identity, feasibility, novelty, and analogs | Apply or approve chemistry flags |
| Assay scientist | Define endpoint semantics, controls, units, and QC | Approve assay mappings and result QC |
| Data curator | Register sources, resolve identity, normalize records | Curate and quarantine; cannot deploy models |
| ML scientist | Build snapshots, train and evaluate challengers | Propose models; cannot self-approve |
| Scientific reviewer | Approve eligible experimental results and model decisions | Named approval or rejection |
| Platform administrator | Operate access, retention, infrastructure, and audit | Administrative actions; no scientific override |
| Auditor | Inspect immutable lineage, approvals, releases, and access | Read-only evidence access |
| Product user | Search, compare, rank, export, and plan | Limited to authorised projects |

No role may bypass required gates by combining UI actions. Upload is not approval; approval is not retraining; retraining is not deployment.

## 5. Primary use cases

### UC-01: Build a traceable compound registry

The curator registers an approved source release, ingests raw records, computes checksums, standardizes structures, quarantines invalid entries, resolves duplicates at explicit identity levels, and publishes a versioned identity snapshot.

### UC-02: Define an oncology prediction task

The scientist chooses cancer type, cell line or biological system, assay endpoint, units, relation operator, inclusion criteria, and evaluation policy. IC50, GI50, viability, and activity probability remain distinct tasks unless a documented scientific transform is approved.

### UC-03: Prioritize compounds

OSIEL resolves candidates, predicts activity, uncertainty, selectivity proxies, and ADMET endpoints, labels model-domain status, retrieves analog evidence, applies hard filters, calculates transparent weighted and Pareto views, and selects a diverse shortlist.

### UC-04: Inspect one candidate

The user sees chemical identity, source provenance, descriptor values, model and dataset versions, nearest analogs, prediction interval, uncertainty, applicability domain, ADMET endpoint details, score contributions, flags, and claim boundary.

### UC-05: Plan and dry-run an experiment

The scientist creates a protocol containing cell line, assay, dose range, controls, replicates, and duration. The reference simulator generates deterministic synthetic observations solely to test workflow, plate-plan logic, result storage, QC, and audit.

### UC-06: Review a real experimental result

An authorised reviewer checks raw data, controls, replicate consistency, exclusions, provenance, and QC. The reviewer records a named decision and reason. Negative results are preserved.

### UC-07: Govern learning

Only scientifically approved, training-eligible real results may enter an immutable dataset snapshot. Training runs offline. A challenger is evaluated on frozen tests, calibration, domain slices, and regression gates. A different named reviewer approves promotion; rollback remains possible.

## 6. Requirements catalogue — 67-point scope freeze

Status legend:

- Implemented: executable in the included reference code.
- Partial: working reference behavior with a production adapter still required.
- Contract: interfaces and guardrails exist; production service not bundled.
- Deferred: intentionally excluded from Phase 1 or requires scientific validation.

### 6.1 Mission, tenancy, and system boundaries

| ID | Requirement | Acceptance criterion | Reference status |
|---|---|---|---|
| OSIEL-REQ-001 | The system shall optimize research prioritization, not clinical decisions. | Every prediction and experiment response carries a research-use notice; prohibited claims are absent. | Implemented |
| OSIEL-REQ-002 | The system shall partition data and actions by organisation, workspace, project, and study. | Production queries enforce tenant and project scope; cross-tenant access tests fail closed. | Contract |
| OSIEL-REQ-003 | The system shall maintain a governed task registry. | Each task records biological context, endpoint, unit, label rule, split policy, and version. | Partial |
| OSIEL-REQ-004 | Cancer types, cell lines, tissues, organisms, and assay systems shall use controlled identifiers with aliases. | Unknown terms are mapped, flagged, or quarantined; raw values remain preserved. | Contract |
| OSIEL-REQ-005 | Compound origin shall be stored separately from chemical identity. | The same standardized parent can carry distinct source and origin records without creating false structural uniqueness. | Implemented |
| OSIEL-REQ-006 | Online inference and offline ingestion/training shall be separate execution paths. | No inference endpoint can mutate a dataset, start training, or replace a model. | Implemented boundary |

### 6.2 Source acquisition and provenance

| ID | Requirement | Acceptance criterion | Reference status |
|---|---|---|---|
| OSIEL-REQ-007 | The system shall maintain a source registry covering owner, purpose, endpoint, mode, licence, and citation. | GET /v1/sources returns registered metadata. | Implemented |
| OSIEL-REQ-008 | Each ingestion shall bind to an immutable source release or retrieval timestamp. | The release identifier is present in the manifest and lineage. | Contract |
| OSIEL-REQ-009 | Raw files and API payloads shall be protected by checksums and manifests. | A changed payload produces a different checksum and cannot silently overwrite a release. | Contract |
| OSIEL-REQ-010 | Acquisition shall prefer official APIs or approved bulk releases. | PubChem and ChEMBL connectors use their official interfaces; bulk-only sources require approved manifests. | Partial |
| OSIEL-REQ-011 | Raw source data shall be preserved before transformation. | A curator can trace a standardized record back to the immutable raw record. | Contract |
| OSIEL-REQ-012 | Source refresh shall support idempotent incremental synchronization. | Reprocessing the same manifest does not duplicate identity or assay records. | Contract |
| OSIEL-REQ-013 | Every derived record shall retain source-to-standardized field lineage. | Lineage resolves source record, transform version, timestamp, and actor. | Partial |
| OSIEL-REQ-014 | Licence, attribution, redistribution, and export restrictions shall be enforced per source. | A source cannot be synchronized or exported without an approved licence policy. | Contract |

### 6.3 Chemical identity and standardization

| ID | Requirement | Acceptance criterion | Reference status |
|---|---|---|---|
| OSIEL-REQ-015 | The engine shall parse SMILES and supported structure formats. | Valid SMILES produces a molecule and descriptors; invalid input returns a structured error. | Implemented |
| OSIEL-REQ-016 | Invalid or chemically ambiguous records shall be quarantined with reasons. | Quarantine audit records include the submitted value and machine-readable reason. | Implemented |
| OSIEL-REQ-017 | Salt, solvent, counter-ion, and fragment handling shall be explicit and versioned. | Raw and parent structures are both retained with transformation notes. | Implemented |
| OSIEL-REQ-018 | Charge, aromaticity, hydrogen, and valence normalization shall be deterministic. | Repeated processing under the same standardization version yields identical identity. | Implemented |
| OSIEL-REQ-019 | Stereochemistry shall be preserved and its completeness reported. | Defined, undefined, and absent stereo states are distinguishable. | Implemented |
| OSIEL-REQ-020 | Canonical SMILES, InChI, InChIKey, formula, and descriptors shall be calculated for the standardized parent. | Standardization response contains all required fields and a version. | Implemented |
| OSIEL-REQ-021 | Duplicate resolution shall distinguish exact, connectivity, tautomer, and possible-related identity levels. | Deduplication never silently merges stereoisomers or uncertain tautomers. | Partial |
| OSIEL-REQ-022 | Users shall search by name, alias, identifier, structure, substructure, and similarity. | Text search works in the reference; production RDKit cartridge supports structure queries. | Partial |

### 6.4 Assay semantics and biological context

| ID | Requirement | Acceptance criterion | Reference status |
|---|---|---|---|
| OSIEL-REQ-023 | The system shall maintain an endpoint dictionary. | IC50, GI50, EC50, viability, inhibition, and activity probability have distinct definitions. | Contract |
| OSIEL-REQ-024 | Biological context shall include cancer type, tissue, cell line, organism, assay format, and protocol references where available. | A measurement is unusable for training until minimum context is satisfied. | Partial |
| OSIEL-REQ-025 | Units and relation operators shall be normalized without losing raw values. | Values such as greater-than and less-than remain censored rather than converted to exact measurements. | Contract |
| OSIEL-REQ-026 | Unlike endpoints shall not be merged into one target by default. | IC50 and GI50 build separate task views unless an approved transform is versioned. | Implemented boundary |
| OSIEL-REQ-027 | Assay records shall carry protocol completeness and quality grades. | Low-quality or missing-context records are flagged and their eligibility is policy controlled. | Contract |
| OSIEL-REQ-028 | Replicates, summaries, conflicts, and outliers shall remain traceable. | Aggregated values link to all underlying observations and exclusion reasons. | Contract |

### 6.5 Dataset construction and leakage control

| ID | Requirement | Acceptance criterion | Reference status |
|---|---|---|---|
| OSIEL-REQ-029 | Training views shall be task-specific and reproducible. | A task definition and snapshot recreate the same eligible records. | Contract |
| OSIEL-REQ-030 | Datasets shall be immutable, checksummed snapshots. | A published snapshot cannot be edited; corrections create a new version. | Implemented gate |
| OSIEL-REQ-031 | Only policy-eligible, scientifically approved records shall enter a production training snapshot. | Simulation-only and unapproved records are rejected. | Implemented |
| OSIEL-REQ-032 | Exclusions shall carry machine-readable and human-readable reasons. | Leakage, identity, context, QC, and licence exclusions are auditable. | Partial |
| OSIEL-REQ-033 | Standardization, features, labels, split policy, and dataset versions shall be frozen together. | A model card resolves all five versions. | Implemented metadata |
| OSIEL-REQ-034 | Leakage audits shall detect exact duplicates, close analogs, scaffold overlap, and entity overlap across splits. | A challenger cannot pass with unresolved prohibited overlap. | Contract |

### 6.6 Features, models, uncertainty, and evidence

| ID | Requirement | Acceptance criterion | Reference status |
|---|---|---|---|
| OSIEL-REQ-035 | Classical features shall include validated circular fingerprints and molecular descriptors. | Feature generation is versioned and deterministic. | Implemented descriptors; fingerprint contract |
| OSIEL-REQ-036 | Classical baselines shall include suitable linear, tree, and boosted models. | Baselines are evaluated on frozen splits and retained when superior. | Contract |
| OSIEL-REQ-037 | Graph models such as Chemprop shall be compared on the identical split and task definition. | No graph-model claim is accepted from a different or easier split. | Adapter-ready |
| OSIEL-REQ-038 | Evaluation shall report task-appropriate discrimination, error, enrichment, calibration, and slice metrics. | The model card contains all required metrics and confidence intervals where applicable. | Contract |
| OSIEL-REQ-039 | Every prediction shall include uncertainty. | API returns uncertainty, confidence, and interval bounds. | Implemented |
| OSIEL-REQ-040 | Probabilities shall be calibrated and calibration quality monitored. | Expected calibration error or equivalent is reported by release and slice. | Contract |
| OSIEL-REQ-041 | Every prediction shall include applicability-domain status. | Inside, borderline, or outside is returned and affects ranking policy. | Implemented |
| OSIEL-REQ-042 | Predictions shall include nearest-analog and evidence context. | Analog identity, source, and similarity are returned without implying causal explanation. | Implemented |
| OSIEL-REQ-043 | Models shall be versioned with model cards, registry state, owner, approvals, and rollback metadata. | A served model resolves immutable artifacts and a named approved alias. | Partial |
| OSIEL-REQ-044 | Online inference shall be deterministic for a fixed input and model version and shall not train. | Repeated requests match within defined tolerance; storage mutations are limited to audit and run records. | Implemented |

### 6.7 ADMET and multi-objective prioritization

| ID | Requirement | Acceptance criterion | Reference status |
|---|---|---|---|
| OSIEL-REQ-045 | ADMET shall be modeled as separate endpoints with units, confidence, and domain status. | No single unexplained ADMET score replaces endpoint-level results. | Implemented demo panel; adapter-ready |
| OSIEL-REQ-046 | Hard filters shall be explicit, justified, versioned, and overrideable only by authorised review. | Excluded and flagged candidates retain reasons. | Implemented |
| OSIEL-REQ-047 | Ranking shall combine activity, selectivity, ADMET, novelty, feasibility, evidence, and uncertainty penalty. | Each component exposes value, weight, contribution, and explanation. | Implemented |
| OSIEL-REQ-048 | The system shall expose Pareto-front information in addition to a weighted score. | Candidates can be inspected without assuming one universal utility function. | Implemented reference |
| OSIEL-REQ-049 | Uncertainty and out-of-domain risk shall reduce priority or trigger review. | Higher risk cannot silently increase a candidate’s score. | Implemented |
| OSIEL-REQ-050 | Shortlist selection shall manage structural diversity and redundancy. | High-similarity candidates are flagged or clustered under the selected policy. | Implemented reference |
| OSIEL-REQ-051 | Ranking weights, thresholds, filters, tie-breakers, and diversity rules shall be versioned as a policy. | Exported rankings identify the exact policy version. | Implemented |

### 6.8 Experiments, results, and continuous learning

| ID | Requirement | Acceptance criterion | Reference status |
|---|---|---|---|
| OSIEL-REQ-052 | The system shall create versioned experiment plans from ranked candidates. | Protocol records include task, candidates, assay, endpoint, doses, controls, replicates, duration, and source ranking. | Implemented |
| OSIEL-REQ-053 | Experiment records shall support batches, plates, wells, controls, replicates, raw files, observations, and protocol deviations. | Every observation resolves to its experimental context. | Partial |
| OSIEL-REQ-054 | Negative, null, conflicting, and failed results shall be retained. | Users cannot selectively delete valid negative evidence from an approved study. | Contract |
| OSIEL-REQ-055 | QC shall be automated where possible and reviewable. | Control presence, ranges, replicate consistency, completeness, and protocol checks are stored. | Implemented reference |
| OSIEL-REQ-056 | Scientific approval shall be a named, reasoned, auditable action. | Approval/rejection records reviewer, timestamp, reason, and training eligibility. | Implemented |
| OSIEL-REQ-057 | Active-learning suggestions shall balance utility, uncertainty, diversity, feasibility, and experiment cost. | The policy explains why each suggested experiment adds information. | Contract |
| OSIEL-REQ-058 | Retraining shall start only from an approved immutable snapshot and execute offline. | Uploading or approving one result never changes the online model. | Implemented gate |
| OSIEL-REQ-059 | Challenger models shall be evaluated against the champion on frozen gates before promotion. | Promotion requires comparable metrics, slice checks, calibration, lineage, and named approval. | Implemented boundary |
| OSIEL-REQ-060 | Model promotion shall support deprecation and rollback without loss of historical predictions. | A former champion remains resolvable; rollback restores a prior approved alias. | Contract |

### 6.9 Platform, experience, security, and acceptance

| ID | Requirement | Acceptance criterion | Reference status |
|---|---|---|---|
| OSIEL-REQ-061 | The platform shall publish versioned REST/OpenAPI and asynchronous event contracts. | API schemas validate requests/responses and event envelopes carry idempotency and lineage keys. | Implemented REST/OpenAPI; event contract |
| OSIEL-REQ-062 | The Next.js workbench shall support task context, search, candidate comparison, evidence, ADMET, ranking, experiment planning, governance, and audit views. | Core research cockpit is usable on desktop and responsive layouts. | Implemented |
| OSIEL-REQ-063 | The scientific assistant shall be evidence-bound and uncertainty-aware. | Answers cite available evidence, identify missing information, recommend a next research action, and avoid clinical claims. | Implemented reference |
| OSIEL-REQ-064 | Authentication, RBAC, tenant isolation, and least privilege shall protect every data and action path. | OIDC and database row-level security pass positive and negative access tests. | Contract |
| OSIEL-REQ-065 | Security-sensitive and scientific actions shall create tamper-evident audit and provenance records. | Actor, action, object, timestamp, reason, and relevant versions are queryable. | Implemented reference |
| OSIEL-REQ-066 | The platform shall meet reproducibility, availability, observability, backup, SBOM, secret-management, and disaster-recovery controls. | Release evidence includes test, scan, lineage, backup-restore, and runbook results. | Contract |
| OSIEL-REQ-067 | Release acceptance shall execute a complete identity-to-ranking-to-experiment-to-review-to-governance scenario and verify claim boundaries. | Automated E2E tests pass; no simulated result becomes training eligible; no approval mutates the champion. | Implemented reference |

## 7. Functional architecture

### 7.1 Logical layers

1. Experience layer — Next.js research cockpit and evidence-bound assistant.
2. API layer — FastAPI request validation, resource contracts, actor context, and OpenAPI.
3. Domain layer — chemistry, prediction, ADMET, ranking, experiment, QC, governance, and audit services.
4. Data layer — PostgreSQL with RDKit cartridge for production; object storage and Parquet/Iceberg for immutable analytical data; SQLite in the developer reference.
5. ML and workflow layer — offline feature/training pipelines, MLflow registry, DVC or equivalent snapshot lineage, and Prefect orchestration.
6. Integration layer — official data-source connectors and transactional outbox or Kafka event delivery.
7. Control layer — OIDC, RBAC, row-level security, policy versions, audit, observability, secrets, backups, and deployment approvals.

### 7.2 Mandatory separation

Online path:

- validate actor and project;
- resolve standardized compounds;
- load one approved model version;
- calculate or load features;
- predict;
- calculate uncertainty and domain status;
- retrieve analog evidence and endpoint ADMET;
- apply a versioned ranking policy;
- store immutable run/audit metadata;
- return results.

Offline path:

- register source releases;
- ingest and curate raw records;
- build task-specific views;
- create immutable snapshots;
- audit leakage;
- train baselines and challengers;
- evaluate and calibrate;
- create model cards;
- seek independent approval;
- promote or reject.

No online request may invoke the offline path.

## 8. Data model

| Entity | Required identity and purpose | Key relationships |
|---|---|---|
| organisation | Tenant boundary | workspaces, users |
| workspace | Research domain and access boundary | projects, policies |
| project | Program-level container | studies, tasks, experiments |
| source_registry | Owner, endpoint, acquisition mode, licence, citation | source_releases |
| source_release | Immutable release, manifest, checksum, retrieval time | raw_records |
| raw_record | Preserved source payload and source-native ID | lineage_edges |
| compound_record | Source-specific compound occurrence | standardized_compound |
| standardized_compound | Canonical parent, InChIKey, descriptors, stereo, version | aliases, measurements |
| compound_alias | Name or external identifier with provenance | standardized_compound |
| assay_definition | Assay type, protocol, biological system, quality | measurements |
| endpoint_definition | Endpoint meaning, unit policy, relation policy | measurements, tasks |
| measurement | Raw and normalized value, relation, unit, context | assay, compound |
| task_definition | Label rule, endpoint, context, eligibility, split policy | dataset_snapshots |
| dataset_snapshot | Immutable eligible record set and checksum | training_runs |
| feature_snapshot | Feature version and artifacts | training_runs |
| split_assignment | Group/scaffold/time split membership and reason | dataset_snapshot |
| model_version | Artifact, task, features, dataset, code, metrics, state | predictions |
| prediction_run | Actor, inputs, versions, policy, timestamp | predictions |
| prediction | Value, interval, uncertainty, domain, analogs | ranking_items |
| admet_prediction | Endpoint-level value, confidence, domain, model | prediction |
| ranking_policy | Weights, filters, thresholds, diversity, version | ranking_runs |
| ranking_run | Candidate set, task, policy, timestamp | ranking_items |
| experiment | Protocol, controls, candidates, status, ranking source | experiment_results |
| observation | Dose, replicate, measured value, raw reference | experiment_result |
| experiment_result | QC status, review status, simulation flag | review_decisions |
| review_decision | Reviewer, reason, eligibility, timestamp | dataset_snapshot proposal |
| audit_event | Actor, action, object, context, timestamp, integrity chain | all governed objects |

All scientific entities use globally unique stable identifiers. Mutable convenience labels do not serve as identities.

## 9. Chemistry and identity rules

The reference implementation uses RDKit to parse and sanitize SMILES, select a parent fragment, normalize charge where safe, assign stereochemistry state, calculate canonical SMILES and InChI/InChIKey, and calculate formula, molecular weight, cLogP, TPSA, hydrogen-bond donors/acceptors, rotatable bonds, ring count, fraction Csp3, and QED.

Production standardization must additionally freeze:

- RDKit version and standardization configuration;
- metal and organometallic policy;
- isotope policy;
- salt/solvate dictionaries;
- tautomer canonicalization policy;
- stereo acceptance and unknown-stereo rules;
- sanitization and quarantine reason codes;
- exact, connectivity, tautomer, and near-duplicate identity tiers.

The raw submitted structure, source structure, standardized parent, transformations, and quality flags must all remain available.

## 10. Dataset and model-development specification

### 10.1 Eligibility pipeline

1. Resolve source release and licence policy.
2. Resolve standardized chemical identity.
3. Resolve endpoint dictionary entry.
4. Normalize value, unit, and relation operator.
5. Resolve biological and assay context.
6. Apply protocol and evidence-quality policy.
7. Aggregate only under an approved replicate/conflict rule.
8. Freeze eligible and excluded record IDs with reasons.
9. Apply group-aware split policy.
10. Run duplicate, analog, scaffold, entity, and time leakage audits.
11. Freeze dataset, features, labels, split assignment, code, and environment.

### 10.2 Baselines and graph model

At minimum, each classification task evaluates:

- regularized logistic regression;
- random forest or extra trees;
- gradient-boosted trees;
- a Chemprop message-passing neural network when data volume supports it.

Each regression task uses appropriate linear, ensemble, boosted, and graph baselines. All models share the identical frozen split. Model selection considers discrimination/error, enrichment, calibration, uncertainty, domain performance, robustness slices, inference cost, and reproducibility—not a single headline metric.

### 10.3 Uncertainty and applicability domain

The production design may use deep ensembles, conformal prediction, calibrated probabilities, bootstrap estimates, or an approved alternative. The model card must state the method and coverage assumptions.

Applicability domain uses training-space similarity, descriptor range, learned density, and task coverage. The API exposes inside, borderline, or outside. Outside-domain predictions remain visible but are penalized or routed for review.

### 10.4 Demonstration model boundary

The included model is deterministic and versioned for integration testing. It derives stable hypotheses from chemical descriptors, task context, and a cryptographic seed. It is not trained on a validated oncology dataset and must not be represented as efficacy prediction. Its purpose is to make the full API, UI, uncertainty, ranking, experiment, QC, and governance flow executable.

## 11. ADMET specification

ADMET remains endpoint-specific. A production endpoint record includes:

- endpoint code and definition;
- numeric value and unit or categorical class;
- confidence and calibration;
- applicability-domain status;
- model and dataset version;
- evidence or analog context;
- policy effect;
- timestamp and actor/run.

Phase 1 target endpoints may include aqueous solubility, permeability, microsomal stability, clearance, CYP inhibition, hERG risk, hepatotoxicity, genotoxicity, and oral-bioavailability proxies. The included reference panel is rule-based and labelled as such. Production integration targets validated models such as ADMET-AI or internally qualified endpoint models.

## 12. Ranking algorithm

The default policy computes:

priority = activity contribution + selectivity contribution + ADMET contribution + novelty contribution + feasibility contribution + evidence contribution − uncertainty penalty.

Default reference weights:

| Component | Weight | Meaning |
|---|---:|---|
| Predicted activity | 0.34 | Task-specific activity hypothesis |
| Predicted selectivity | 0.14 | Normalized selectivity hypothesis |
| ADMET panel | 0.18 | Endpoint-specific developability screen |
| Structural novelty | 0.10 | Distance from known or training chemistry |
| Feasibility | 0.10 | Chemist-reviewable synthesis/source proxy |
| Evidence quality | 0.09 | Identity and provenance quality, not efficacy |
| Uncertainty penalty | 0.05 | Confidence and model-domain risk |

Weights are not scientific constants. Every run identifies the policy version and returns each component, weight, contribution, and explanation. Hard filters run before or alongside the score and preserve reasons. Pareto fronts and diversity flags prevent one scalar score from hiding trade-offs or redundant chemistry.

## 13. Experiment and learning controls

### 13.1 Protocol minimum

An experiment plan includes title, task, candidate IDs, cell line or biological system, assay type, endpoint, dose minimum and maximum, dose points, replicates, duration, positive control, negative control, source ranking, creator, and protocol version.

### 13.2 Result minimum

A real result includes raw-file reference, plate/batch/well context where relevant, dose, replicate, observation, units, control observations, deviations, QC checks, derived summaries, analyst, and timestamps.

### 13.3 Computational dry-run

The simulator generates deterministic sigmoid dose-response observations with bounded noise. It checks observation ranges, replicate consistency, controls, and minimum replicates. Every generated result is marked simulation_only=true. The review service rejects any request that makes a simulated result training eligible.

### 13.4 Continuous-learning state machine

planned → results uploaded → QC passed or failed → scientific review → approved or rejected → eligible snapshot proposal → approved snapshot → offline challenger training → evaluation → model approval or rejection → controlled promotion → monitoring or rollback.

Transitions are append-only governed events. A UI upload cannot skip states.

## 14. REST API

Base production prefix: /v1

| Method and path | Purpose | Key guard |
|---|---|---|
| GET /health | Liveness and reference compound count | No sensitive detail |
| GET /v1/system/capabilities | Implemented, adapter-ready, and excluded capabilities | Truthful claims |
| GET /v1/sources | Source registry | Licence metadata |
| POST /v1/sources/{source}/sync | Request a manifest-bound sync | Curator role; no blind crawl |
| GET /v1/compounds | Search and page compound registry | Project scope |
| GET /v1/compounds/{id} | Retrieve identity and evidence grade | Project scope |
| POST /v1/compounds/standardize | Standardize one submitted structure | Quarantine invalid |
| POST /v1/predictions | Create task-specific hypotheses | Approved model only in production |
| POST /v1/rankings | Rank a candidate set | Versioned policy |
| POST /v1/experiments | Create a protocol | Scientist role |
| GET /v1/experiments | List authorised experiments | Project scope |
| POST /v1/experiments/{id}/simulate | Run computational software-flow test | Always simulation-only |
| POST /v1/results/{id}/review | Record a named review | Reviewer role; separation of duties |
| GET /v1/models | List champion/challenger states | Model metadata |
| POST /v1/models/challenger/evaluate | Evaluate reference challenger boundary | Frozen gates |
| POST /v1/models/{id}/approve | Approve promotion | Named independent reviewer |
| GET /v1/audit | Retrieve authorised audit records | Auditor/admin role |
| GET /v1/assistant/capabilities | Report deterministic and optional local-LLM assistant modes | Operator configuration only; no secrets |
| POST /v1/assistant/query | Evidence-bound research answer | No clinical advice |
| GET /v1/zinc22/capabilities | Report configured public chemical-space map and operator gate | No claim until provider metadata is verified |
| POST /v1/zinc22/searches | Run one bounded live SmallWorld structural query and local RDKit triage | Operator gate; maximum 100 imported hits |
| GET /v1/zinc22/searches/{job_id} | Retrieve persisted search evidence and shortlist | Exact job identifier |
| POST /v1/zinc22/searches/{job_id}/refresh | Stable refresh contract for provider task modes | Never fabricates pending or completed hits |
| GET /v1/docking/capabilities | Report pinned Vina worker readiness and resource policy | No score implied by readiness |
| POST /v1/docking/jobs | Execute a qualified AutoDock Vina 1.2.7 job | Prepared PDBQT; operator gate; bounded child process |
| GET /v1/docking/jobs/{job_id} | Retrieve immutable docking status, logs and completed pose content/checksum | Exact job identifier |
| POST /v1/docking/benchmarks | Compare completed poses with the exact prepared co-crystal ligand | Matching heavy-atom order; RMSD is pose recovery, not affinity validation |
| GET /v1/model-lab/capabilities | Report dataset, feature, baseline, evaluation and operator gates | No outbound retrieval or training |
| GET /v1/model-lab/snapshots | List immutable activity snapshots | Authorised workspace only in production |
| POST /v1/model-lab/chembl/snapshots | Retrieve and freeze one bounded ChEMBL endpoint slice | Operator gate; exact target/endpoint/assay; server ceiling |
| GET /v1/model-lab/models | List completed research-use activity baselines | No production alias implied |
| POST /v1/model-lab/models | Train, calibrate and evaluate one scaffold-separated baseline | Approved snapshot; no automatic promotion |
| POST /v1/model-lab/predictions | Apply a retained baseline to a bounded candidate pool | Uncertainty and applicability domain required |
| POST /v1/model-lab/active-learning-batches | Propose a diverse high-information next-test batch | Human approval required; no experiment or procurement starts |
| GET /v1/openapi.json | Machine-readable contract | Versioned release |

Production APIs shall add pagination cursors, idempotency keys, correlation IDs, structured error codes, OAuth scopes, tenant context, request limits, export controls, and signed object references.

## 15. Asynchronous event contract

The production outbox publishes events only after the database transaction commits. Event envelope fields:

- event_id;
- event_type and schema_version;
- occurred_at;
- actor_id, organisation_id, workspace_id, project_id;
- aggregate_type and aggregate_id;
- correlation_id and causation_id;
- idempotency_key;
- source and environment;
- payload;
- lineage references;
- integrity checksum.

Core event types include source.sync.requested, source.release.registered, compound.standardized, record.quarantined, dataset.snapshot.approved, model.training.completed, model.evaluation.completed, model.promotion.approved, ranking.completed, experiment.created, result.qc.completed, result.reviewed, and audit.exported.

## 16. Source and repository plan

The platform shall learn from open-source implementations without copying incompatible code or obscuring licence obligations. Production source acquisition must use official interfaces and approved snapshots.

| Source or project | Intended use | Integration rule |
|---|---|---|
| PubChem PUG REST | Compound identity and public chemical properties | Cache with CID and retrieval timestamp; respect service limits |
| ChEMBL API and approved releases | Bioactivity, assay, target, and compound records | Preserve activity relation, units, assay and document lineage |
| NCI-60 / CellMiner | Cancer-cell-line response data | Register exact release and endpoint semantics |
| Therapeutics Data Commons | Curated benchmark and task tooling | Pin dataset and code versions; verify original-source licences |
| COCONUT | Natural-product structures and source metadata | Use official download and preserve upstream attribution |
| NPASS | Natural-product activities, species, and targets | Use approved downloads; inspect licence and citation conditions |
| ANPDB | African natural-product records | Use official access and attribution terms |
| LOTUS | Natural-product occurrence knowledge | Bind structures to organism/source provenance |
| Tox21 and ToxCast | Toxicology endpoints | Keep assay endpoints distinct and versioned |
| RDKit | Cheminformatics and PostgreSQL cartridge | Pin version and standardization policy |
| Datamol | Optional ergonomic chemistry workflows | Use only where it improves reproducibility |
| Chemprop | Message-passing molecular models | Compare on frozen identical splits |
| ADMET-AI | Production ADMET adapter candidate | Validate endpoint fit, version, licence, and calibration |
| MLflow | Registry, model versions, aliases, and evaluations | Approval controls remain outside a self-service alias change |
| Prefect | Offline pipeline orchestration | Deploy ingestion/training flows separately from inference |
| 3Dmol.js | Optional structure visualisation | Visual aid only; not evidence |

The included 192-record registry is a legal, deterministic development seed: curated recognisable structures plus RDKit-distributed NCI reference structures. Reference-structure presence does not establish oncology activity.

The reference implementation includes operational acquisition connectors for NCI-60, TDC, COCONUT, NPASS, ANPDB, LOTUS, Tox21, ToxCast, UniProt and Chemspace. Download-oriented sources require an operator-approved direct HTTPS release URL and SHA-256; raw bytes are stored immutably and remain quarantined until a source-specific parser, canonical mapping and QC complete. UniProt uses its official REST API, TDC uses an optional pinned PyTDC dependency, and Chemspace requires a provider-issued key and documented API path. See `docs/EXTENDED_DATA_CONNECTORS.md`.

## 17. Frontend requirements

The Next.js workbench shall:

- show current workspace, project/task context, and research-use state;
- let users choose cancer context, cell line, endpoint, and candidate origin;
- display registry size, candidate count, domain coverage, policy score, and experiment queue;
- visualize the seven-stage evidence-to-experiment loop;
- search, filter, sort, select, and compare compounds;
- show formula, origin, evidence grade, activity, confidence, uncertainty, score, and domain;
- show a candidate’s prediction interval, analog/evidence context, ADMET endpoints, and score contributions;
- create a governed computational experiment from selected candidates;
- show protocol, stage progress, synthetic observation count, QC, and no-model-mutation state;
- expose champion/challenger boundaries and required gates;
- remain usable at desktop, tablet, and mobile widths;
- degrade to a clearly labelled embedded deterministic demo when the Python URL is not configured.

The production deployment shall route the frontend to the FastAPI service through an authenticated private binding or approved API gateway. The embedded fallback is for preview resilience only.

## 18. Security and privacy

### 18.1 Identity and authorization

- OIDC/OAuth 2.1 with short-lived tokens.
- Role and project scopes enforced in API and database.
- PostgreSQL row-level security for tenant isolation.
- Separation of duties for curation, result approval, model proposal, and promotion.
- Service identities for pipelines and model serving.
- No shared production user accounts.

### 18.2 Data protection

- TLS in transit and managed encryption at rest.
- Secret manager; no credentials in repository or logs.
- Signed, time-limited object access.
- Source licence and export-control policies.
- No patient-identifiable data in Phase 1.
- Configurable retention for raw, curated, model, audit, and export artifacts.

### 18.3 Audit

Audit events include actor, role, action, object, before/after summary where applicable, reason, timestamp, correlation, environment, and relevant versions. High-value events should use an append-only integrity chain and immutable retention.

### 18.4 Supply chain

- Locked dependencies and reproducible images.
- Software bill of materials.
- Licence and vulnerability scanning.
- Signed images and provenance attestations.
- Protected branches and reviewed migrations.
- Secrets and personal data detection in CI.

## 19. Non-functional requirements

| Category | Production requirement |
|---|---|
| Availability | 99.9% monthly for interactive APIs excluding planned maintenance |
| Latency | p95 under 500 ms for cached single-compound retrieval; p95 under 5 s for ranking up to 100 compounds excluding cold model load |
| Throughput | Horizontally scalable stateless API; offline bulk work queued |
| Reliability | Idempotent ingestion and experiment commands; transactional outbox |
| Reproducibility | Same snapshot, features, code, environment, and seed recreate metrics within declared tolerance |
| Observability | Structured logs, traces, metrics, correlation IDs, data-quality and model monitors |
| Accessibility | Keyboard operability, visible focus, labelled controls, WCAG 2.2 AA target |
| Portability | Containerized services; environment-specific configuration |
| Backup | Point-in-time database recovery and versioned object storage |
| DR | Documented RPO/RTO and tested restore exercises |
| Maintainability | Typed contracts, modular services, migrations, unit/integration/E2E tests |
| Explainability | Every prioritization resolves inputs, versions, components, uncertainty, domain, and evidence |

## 20. Deployment architecture

Recommended production topology:

- Next.js web application behind managed edge and OIDC.
- FastAPI service deployed as stateless containers.
- PostgreSQL with RDKit cartridge for operational chemical search.
- S3-compatible object storage and Iceberg/Parquet for immutable analytical snapshots.
- Redis only for bounded cache or distributed coordination.
- Prefect workers for offline ingestion, curation, feature, training, and evaluation flows.
- MLflow tracking and model registry.
- Kafka or a managed equivalent fed through a transactional outbox when event volume justifies it.
- OpenTelemetry, logs, metrics, alerting, and lineage integration.
- Separate development, test, staging, and production environments.

The Phase 1 reference uses a modular monolith because scientific boundaries matter more than premature microservice count. Components can be extracted after load, ownership, or security boundaries demonstrate the need.

## 21. Repository specification

Key reference paths:

| Path | Responsibility |
|---|---|
| app/page.tsx | Next.js research cockpit and interaction state |
| app/lib/osiel-client.ts | Typed Python API client with labelled demo fallback |
| app/lib/demo-data.ts | Embedded deterministic UI reference data |
| backend/app/main.py | FastAPI routes and system boundaries |
| backend/app/chemistry.py | RDKit standardization and descriptors |
| backend/app/repository.py | SQLite reference persistence, audit, and seed |
| backend/app/prediction.py | Deterministic hypothesis, uncertainty, domain, analogs, ADMET |
| backend/app/ranking.py | Seven-component transparent ranking and diversity flags |
| backend/app/experiments.py | Protocol, simulation, QC, review, snapshot gate |
| backend/app/governance.py | Champion/challenger and promotion boundary |
| backend/app/model_lab.py | Immutable ChEMBL endpoint snapshots, scaffold-separated baseline, prediction and active-learning proposals |
| backend/app/docking_benchmark.py | Heavy-atom redocking alignment and RMSD qualification gate |
| backend/app/assistant.py | Evidence-bound research assistant |
| backend/app/connectors | Official-source adapter examples |
| backend/app/data/compounds.json | 192 validated development structures |
| backend/tests | Unit, API, governance, and experiment tests |
| contracts/openapi.json | Generated API contract |
| docs/OSIEL_Developer_SRS.md | Authoritative developer specification |

## 22. Verification and acceptance plan

### 22.1 Automated tests

- Chemistry: valid parsing, invalid quarantine, salt parent selection, deterministic identity.
- Repository: seed count at least 150, unique stable IDs, searchable records.
- Prediction: bounded values, intervals, uncertainty, domain state, model and dataset metadata.
- Ranking: component transparency, score order, uncertainty penalty, flags, policy version.
- Experiment: protocol validation, deterministic observation count, dose range, replicates, QC.
- Governance: simulation-only result cannot become training eligible; demo model cannot be promoted.
- API: health, compounds, standardization, ranking, experiment, assistant, model-lab, active-learning, docking benchmark, and governance routes.
- Model lab: exact endpoint retention, grey-zone removal, duplicate/conflict handling, immutable hashes, no scaffold overlap, calibration, metrics, domain and proposal gating.
- Docking qualification: matching heavy-atom order, rigid-body alignment, RMSD pass/fail and permanent `scoring_qualified=false` for a single-complex check.
- Frontend: production build, rendered HTML, eight-row fallback, no viewport-level overflow.

### 22.2 Reference end-to-end scenario

1. Health response reports a healthy service and at least 150 compounds.
2. Resolve at least six compounds from the registry.
3. Rank them for non-small cell lung cancer and A549 with policy version 1.0.
4. Verify every ranked item includes prediction, interval, uncertainty, domain, ADMET, evidence, and component contributions.
5. Select three candidates.
6. Create a CellTiter-Glo IC50 protocol with eight doses and three replicates.
7. Run the computational dry-run.
8. Verify 72 synthetic observations, QC checks, controls, and simulation-only notice.
9. Attempt training eligibility and confirm rejection.
10. Confirm the champion version did not change.
11. Confirm audit events cover ranking, experiment creation, simulation, and rejected governance mutation.

### 22.3 Release gates

A production release requires:

- all tests passing;
- database migrations reviewed and reversible;
- contract compatibility checked;
- security and licence scans passing;
- model card and snapshot lineage complete;
- calibration and slice gates passing;
- named scientific and model approvals;
- backup/restore and rollback verified;
- no unresolved critical data-quality or security findings;
- user-facing claim review completed.

## 23. Current implementation evaluation

### 23.1 What is complete in the developer reference

- FastAPI application with typed Pydantic contracts and generated OpenAPI.
- RDKit parsing, parent selection, standardized identifiers, stereo state, and descriptors.
- Seed registry of 192 RDKit-validated structures.
- Official PubChem and ChEMBL connector examples and a governed source registry.
- Deterministic task-specific demonstration prediction with confidence, uncertainty, interval, and domain status.
- Nearest-analog evidence and endpoint-level demonstration ADMET.
- Transparent seven-component ranking, hard flags, Pareto label, and diversity policy.
- Experiment protocol creation and deterministic computational dose-response dry-run.
- QC, named review, audit, immutable snapshot gate, and simulation training prohibition.
- Champion/challenger governance boundary.
- Evidence-bound deterministic assistant plus an opt-in local Ollama/Qwen3 composer with supplied-ID citation validation, abstention and safe fallback.
- Bounded live SmallWorld query against a provider-advertised multi-billion chemical map, with map counts, result checksum and local RDKit triage.
- Operator-gated AutoDock Vina 1.2.7 child-process execution with immutable prepared inputs, downloadable poses and a co-crystal redocking RMSD gate.
- Operator-gated ChEMBL endpoint retrieval with immutable raw and normalized snapshots, exact-relation filtering, pChEMBL grey-zone removal, duplicate aggregation, label-conflict removal and scaffold accounting.
- ECFP4 logistic-regression baseline with class balancing, disjoint train/calibration/test scaffold groups, Platt calibration, frozen-test AUROC/AP/balanced-accuracy/Brier/ECE metrics, and portable immutable JSON artifact.
- Model-lab predictions with entropy/domain uncertainty, nearest-training similarity and explicit inside/borderline/outside status.
- Active-learning proposals using uncertainty, distance-to-training, QED and greedy fingerprint diversity; no experiment, procurement or model promotion starts automatically.
- Connected, responsive Next.js research cockpit with embedded fallback.
- Dockerfiles, Compose configuration, test suite, and developer documentation.

On 22 August 2026, the live model-lab smoke run retrieved ChEMBL 37 EGFR binding IC50 records, retained 603 unique threshold-separated structures across 200 scaffolds, created a 325/121/157 train/calibration/test split with zero scaffold overlap, and completed local baseline evaluation. The internal frozen-test metrics were AUROC 0.9526, average precision 0.9948, balanced accuracy 0.7841, Brier score 0.0706, and ECE 0.0771. Promotion remained false. These figures prove executable wiring for that bounded retrieval and split; they are not a locked external or prospective biological validation.

### 23.2 What is adapter-ready but not falsely claimed as complete

- Production PostgreSQL plus RDKit cartridge.
- Object-store lakehouse and immutable release pipelines.
- Prefect orchestration and Kafka/outbox delivery.
- MLflow-backed model registry and aliases.
- Real Chemprop and ADMET-AI serving.
- OIDC, RBAC, RLS, production audit integrity, and secret management.
- Full source-specific canonical parsing and accepted curated-table ingestion for PubChem, ChEMBL, NCI-60, TDC, COCONUT, NPASS, ANPDB, LOTUS, Tox21, and ToxCast beyond the implemented acquisition/quarantine connectors and bounded ChEMBL endpoint snapshot.
- Independently validated, production-approved oncology task models beyond the implemented research baseline.
- Laboratory information management or robotic instrument integration.

### 23.3 Overall judgement

The reference is suitable as a developer handoff, architecture demonstrator, contract baseline, investor/product demo, and controlled foundation for Phase 1 implementation. It is not suitable for therapeutic decisions or scientific claims of compound efficacy. Production scientific credibility depends on curated task data, leakage-safe evaluation, calibrated models, domain validation, and qualified laboratory evidence.

### 23.4 Open Discovery implementation addendum

The public-source Open Discovery extension adds the following developer contracts without changing the frozen numbering of OSIEL-REQ-001 through OSIEL-REQ-067:

| Addendum ID | Requirement | Acceptance condition | Disposition |
|---|---|---|---|
| OSIEL-OD-001 | The system shall accept disease, target, seed name/SMILES, optional PDB/UniProt identifiers, candidate limit, and connector mode. | Invalid identifiers and missing seed inputs return typed validation errors. | Implemented |
| OSIEL-OD-002 | Outbound public connectors shall be disabled by default and require both request and server-operator gates. | A client request cannot override `OSIEL_PUBLIC_CONNECTORS_ENABLED=false`. | Implemented |
| OSIEL-OD-003 | Supported live retrieval shall use official Open Targets, PubChem, ChEMBL, RCSB, and AlphaFold interfaces. | Connector code records mode, URL, source record, status, retrieval time, and licence note. | Implemented |
| OSIEL-OD-004 | Shared/search services without an approved bulk contract shall not be crawled. | ZINC22 uses one bounded provider-side query with a 100-hit ceiling; Chemspace remains a hand-off. No bulk enumeration occurs. | Implemented |
| OSIEL-OD-005 | Candidate chemistry shall be computed locally with versioned RDKit standardization and fingerprints. | Canonical parent, InChIKey, descriptors, QED, similarity, and identity flags are returned. | Implemented |
| OSIEL-OD-006 | PAINS, Brenk, NIH, and Rule-of-Five matches shall be visible review flags, not silently destructive filters. | Each candidate retains named alert lists and a human-readable disposition reason. | Implemented |
| OSIEL-OD-007 | Candidate priority shall use a transparent, component-level chemistry heuristic and shall not be labelled activity, affinity, IC50, or probability of success. | Every weighted contribution and explanation is returned and bounded. | Implemented |
| OSIEL-OD-008 | Docking shall emit no score until a real qualified process completes. | Readiness emits null; the separate gated job endpoint returns scores only after `vina==1.2.7` completes with validated prepared PDBQT inputs and persists output/checksums. | Implemented execution contract |
| OSIEL-OD-009 | Scientists shall see an operational trace rather than hidden chain-of-thought. | Ten ordered stages show status, message, duration, metrics, and evidence IDs. | Implemented |
| OSIEL-OD-010 | Every run shall be persisted and audited, and end at a human review gate. | POST/GET round trip, audit record, E2E scenario, and no automatic procurement/lab execution. | Implemented reference |
| OSIEL-OD-011 | A multi-billion search claim shall be tied to provider-reported map metadata, not local row count. | The service verifies the configured `/search/maps` record, records index and mapped counts, sends one seed, imports at most 100 hits, and stores response SHA-256. | Implemented |
| OSIEL-OD-012 | Remote chemical-space hits shall be standardized and assessed locally before display. | Invalid structures are quarantined; parent identity is deduplicated; Morgan similarity, QED, Rule-of-Five and named alerts are returned. | Implemented |
| OSIEL-OD-013 | Long or external scientific operations shall expose genuine pending/failure states and shall never substitute fabricated results. | ZINC/Vina/frontend errors preserve the boundary; no embedded remote hit or docking score is generated. | Implemented |
| OSIEL-OD-014 | Optional local LLM prose shall be restricted to retrieved evidence and validated citations. | Operator gate, evidence-only system instruction, JSON schema, allowed-ID citation check, abstention, prompt-override/clinical screen and deterministic fallback are tested. | Implemented reference |
| OSIEL-OD-015 | LLM output shall not be represented as a scientific prediction or final experiment authorization. | Maximum model confidence is medium, warnings and sources are visible, and named supervisor review remains required. | Implemented reference |

The extension remains a public-source chemistry triage workflow. A real multi-billion structural query and real docking process do not turn it into a target-activity model or wet laboratory. It is not a substitute for proprietary phenomics, validated compound-protein interaction prediction, generative medicinal chemistry, robotic laboratory execution, or prospective experimental validation. The source-level design and Recursion capability/funding gap are maintained in `docs/OPEN_DISCOVERY_WORKFLOW.md` and `docs/RECURSION_FREE_ALTERNATIVES_ROADMAP.md`.

### 23.5 Model laboratory, active learning, and docking qualification addendum

| Addendum ID | Requirement | Acceptance condition | Disposition |
|---|---|---|---|
| OSIEL-ML-001 | Public activity retrieval shall be operator-gated, bounded and directed only at the official configured service. | `OSIEL_MODEL_LAB_ENABLED=false` returns 503; maximum source records are server-enforced; request URLs are retained. | Implemented |
| OSIEL-ML-002 | A dataset task shall freeze one target, target label, endpoint and assay type with separate active and inactive pChEMBL thresholds. | Inactive threshold must be below active threshold; the grey zone is counted and excluded. | Implemented |
| OSIEL-ML-003 | Exact source bytes and normalized model rows shall be independently content-addressed. | Both object URIs and SHA-256 values are returned and checksum-verified on read. | Implemented reference storage |
| OSIEL-ML-004 | Structure, relation, assay-confidence, duplicate and conflicting-label controls shall execute before training. | Invalid/non-exact rows are excluded; same-label duplicates aggregate by median; opposite labels for one parent are removed. | Implemented |
| OSIEL-ML-005 | Train, calibration and test rows shall be separated by Bemis–Murcko scaffold. | Each split contains both classes; scaffold overlap count is exactly zero or training fails. | Implemented |
| OSIEL-ML-006 | The first accepted model shall be a transparent baseline with separate calibration. | Class-balanced ECFP4 logistic regression trains only on train scaffolds; Platt scaling fits only on calibration scaffolds. | Implemented |
| OSIEL-ML-007 | Final metrics shall be calculated once on the frozen scaffold test split. | AUROC, average precision, balanced accuracy, sensitivity, specificity, Brier score, ECE, prevalence and count are persisted. | Implemented |
| OSIEL-ML-008 | Model inference shall expose confidence limitations and training-space proximity. | Each candidate returns probability, uncertainty, nearest-training similarity and inside/borderline/outside domain. | Implemented |
| OSIEL-ML-009 | Active learning shall balance information gain with chemical diversity. | Acquisition combines uncertainty, distance-to-training and QED, then applies a maximum pair-similarity selection rule. | Implemented reference |
| OSIEL-ML-010 | Active-learning output shall be a proposal only. | `approval_required=true`, `experiment_started=false`, and no order, assay or model mutation is invoked. | Implemented |
| OSIEL-DBM-001 | Completed Vina poses shall support a redocking pose-recovery check against the exact prepared reference ligand. | Compatible heavy atoms are Kabsch-aligned and per-pose RMSD plus best-pose pass/fail is persisted. | Implemented |
| OSIEL-DBM-002 | A single successful redocking check shall never qualify affinity scoring. | Every benchmark returns `scoring_qualified=false` and the multi-complex/enrichment limitation. | Implemented |

The bounded model-lab baseline is scientifically more credible than the deterministic cockpit scorer, but it remains a research hypothesis generator. Promotion requires a faculty-approved inclusion protocol, a locked external dataset, independent reproduction, prospective assays, a signed model card and institutional acceptance. Detailed operation is in `docs/MODEL_LAB_AND_ACTIVE_LEARNING.md`.

### 23.6 Governed AI Professor and 3D visualization addendum

| Addendum ID | Requirement | Acceptance condition | Disposition |
|---|---|---|---|
| OSIEL-PROF-001 | Only explicitly approved PDF, TXT and Markdown sources shall enter the controlled full-text corpus. | Rights status and note are mandatory; original bytes and normalized manifest receive independent SHA-256 identities. | Implemented reference |
| OSIEL-PROF-002 | Document retrieval shall preserve source version and page provenance. | Every document chunk retains document ID, page, section, source URL/version and hash. | Implemented |
| OSIEL-PROF-003 | Retrieved documents shall be untrusted data, never executable model instructions. | Prompt-like patterns quarantine affected documents/chunks; adversarial fixture is excluded from lexical and dense retrieval. | Implemented first layer |
| OSIEL-PROF-004 | Retrieval shall work without a language model and optionally support local semantic search. | SQLite FTS5/BM25 is always available; optional Qwen3 embeddings and reciprocal-rank fusion are reported transparently. | Implemented reference |
| OSIEL-PROF-005 | Generated answers shall be grounded in supplied evidence IDs or abstain. | Unknown citations, unsupported non-abstaining output, clinical requests and prompt overrides are rejected; missing Ollama yields no invented answer. | Implemented |
| OSIEL-PROF-006 | Consultations and faculty review shall be governed records. | Conversations, turns, evidence, trace, corrections, evaluation datasets/results and retention actions are persisted and audited; correction applies no automatic training. | Implemented reference |
| OSIEL-PROF-007 | Course/project scope shall become an institutional authorization boundary before production. | Reference logical filters are replaced with verified university OIDC claims and row-level enforcement before acceptance. | Adapter required |
| OSIEL-3D-001 | A result compound shall be visualized only from its registered canonical molecular identity. | Python resolves the compound ID and generates coordinates from canonical SMILES; unknown IDs return 404 and no substitute structure. | Implemented |
| OSIEL-3D-002 | Generated conformers shall be reproducible and content-addressed. | ETKDGv3 uses seed `20260822`; MMFF94/UFF method, convergence, energy, RDKit version, atoms, SHA-256 and immutable URI are returned. | Implemented |
| OSIEL-3D-003 | Scientists shall be able to interactively inspect result-linked geometry. | The experiment tab supports candidate switching, rotation, wheel/pinch and button zoom, movement, spin/reset, representations, hydrogen visibility, hover identity and four colour schemes. | Implemented |
| OSIEL-3D-004 | Generated, experimental and docked structures shall never be conflated. | Every generated conformer states that it is not a crystal structure, conformational ensemble, bound pose, docking result or activity evidence; colour changes are explicitly visual only. | Implemented |

Executed acceptance artifacts on 22 August 2026:

| Artifact | Acceptance evidence |
|---|---|
| `deliverables/OSIEL_AI_Professor_E2E_Report.json` | Immutable approved-source ingestion, scoped retrieval, persisted consultation, faculty correction and prompt-attack quarantine executed; model-unavailable path abstained. |
| `deliverables/OSIEL_Live_ChEMBL_Model_Lab_Report.json` | Real bounded ChEMBL 37 EGFR/IC50 retrieval and local model evaluation executed; 603 structures, zero scaffold overlap, promotion blocked. |
| `deliverables/OSIEL_Formal_Redocking_Benchmark_Report.json` | Official pinned 1IEP fixture executed with Vina 1.2.7/exhaustiveness 8; 0.8636 Å best RMSD passed; scoring qualification remained false. |
| `deliverables/OSIEL_3D_Conformer_E2E_Report.json` | Eight ETKDGv3/MMFF94 conformers and immutable reads verified; repeated generation produced the same mol block and SHA-256. |

## 24. Risks and controls

| Risk | Consequence | Control |
|---|---|---|
| Endpoint conflation | Invalid labels and misleading performance | Governed endpoint dictionary and separate tasks |
| Duplicate/analog leakage | Inflated model metrics | Identity tiers, scaffold/group splits, leakage audit |
| Source licence breach | Legal and redistribution exposure | Source registry, manifest approval, export policy |
| Missing assay context | Non-comparable measurements | Minimum context eligibility and quarantine |
| Domain extrapolation | Confident wrong predictions | Applicability domain and uncertainty penalty |
| One-score bias | Hidden trade-offs | Component view, Pareto fronts, adjustable policy |
| Simulated evidence confusion | False efficacy interpretation | simulation_only flag and training prohibition |
| Automatic model replacement | Uncontrolled scientific change | Offline challenger and named promotion gate |
| Assistant hallucination | Unsupported research claims | Evidence-bound response, missing-information list |
| Cross-tenant exposure | Confidentiality breach | OIDC, RBAC, RLS, scoped object references |
| Premature architecture complexity | Slow delivery and fragile operations | Modular monolith first; extract by proven need |

## 25. Definition of done for Phase 1

Phase 1 is complete only when:

- all 67 frozen core requirements and every versioned addendum have an owner, test, and implementation disposition;
- at least one approved oncology task has curated, licensed, traceable data;
- baseline and graph models are compared on the same leakage-safe split;
- predictions show uncertainty, calibration, domain, analogs, evidence, and versions;
- ranking is transparent and produces a diverse, reviewable shortlist;
- real laboratory results can be ingested with raw provenance, QC, and named approval;
- approved results can create an immutable snapshot without automatic training;
- an independently evaluated challenger can be promoted and rolled back;
- frontend, API, data, model, security, and operations acceptance gates pass;
- research-use and simulation claim boundaries are verified in every surface.

## Appendix A — Official technical references

- RDKit: https://github.com/rdkit/rdkit
- Datamol: https://github.com/datamol-io/datamol
- Chemprop: https://github.com/chemprop/chemprop
- ADMET-AI: https://github.com/swansonk14/admet_ai
- Therapeutics Data Commons: https://github.com/mims-harvard/TDC
- PubChem PUG REST: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
- ChEMBL API: https://www.ebi.ac.uk/chembl/api/data/docs
- ZINC-22: https://doi.org/10.1021/acs.jcim.2c01253
- CartBlanche22: https://github.com/docking-org/cartblanche22
- AutoDock Vina: https://github.com/ccsb-scripps/AutoDock-Vina
- Ollama API: https://docs.ollama.com/api/generate
- Ollama embeddings: https://docs.ollama.com/capabilities/embeddings
- Qwen3: https://qwenlm.github.io/blog/qwen3/
- Qwen3 Embedding: https://qwenlm.github.io/blog/qwen3-embedding/
- COCONUT: https://coconut.naturalproducts.net/download
- NPASS: https://bidd.group/NPASS/
- ANPDB: https://african-compounds.org
- LOTUS: https://lotus.naturalproducts.net/download
- Tox21: https://tripod.nih.gov/tox21/pubdata
- EPA ToxCast: https://www.epa.gov/comptox-tools/exploring-toxcast-data
- UniProt programmatic access: https://www.uniprot.org/help/programmatic_access
- Chemspace API: https://chem-space.com/purchasing-saas/chemspace-api
- MLflow Model Registry: https://mlflow.org/docs/latest/ml/model-registry/
- Prefect deployments: https://docs.prefect.io/v3/concepts/deployments
- 3Dmol.js: https://3dmol.csb.pitt.edu/doc/GLViewer.html

## Appendix B — Scientific handoff checklist

- Confirm first production cancer task and endpoint.
- Confirm permitted source releases and licences.
- Confirm data-curation and assay-review owners.
- Freeze standardization and identity policies.
- Define split and leakage prohibitions.
- Define primary, calibration, enrichment, and slice metrics.
- Define ADMET endpoints and validation expectations.
- Approve default ranking weights and hard filters.
- Define laboratory protocol and control minimums.
- Define result QC and training-eligibility review.
- Define champion/challenger approval committee.
- Approve research-use language and prohibited claims.
- Approve security, retention, recovery, and audit controls.
