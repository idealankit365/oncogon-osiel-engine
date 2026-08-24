# Oncogon AI OSIEL — consolidated project-thread record

Date consolidated: 24 August 2026  
Scope: decisions, requirements, implementation and unresolved work discussed in
the OSIEL/Recursion-style drug-discovery thread. This is a structured project
record, not a claim that private Recursion technology was copied.

## Product objective

Build an end-to-end university research platform where a student can define a
cancer/compound question, search public chemical space, inspect evidence,
prioritize candidates, run a transparent computational experiment, understand
success/failure, receive evidence-grounded next-step guidance, inspect a 3D
compound and feed qualified laboratory results into a governed learning loop.

## Requirements accumulated through the thread

1. Next.js frontend connected to a real Python/FastAPI engine.
2. Working tabs and complete user flow rather than static screens.
3. Visible loader, experiment stages, debugger-style logs and outputs.
4. Success report, failure reason and ranked next-compound recommendation.
5. Large chemical search through provider-hosted spaces rather than fabricated
   local billions; bounded ZINC22/CartBlanche results are imported for RDKit.
6. Compound/source registry with PubChem, ChEMBL and natural-product evidence.
7. AutoDock Vina execution plus formal redocking benchmark.
8. Endpoint-specific model laboratory, calibration, applicability domain and
   human-gated active-learning proposals.
9. AI Professor with controlled document ingestion, citations, abstention,
   prompt-injection protection, feedback and faculty evaluation.
10. Multimodal orchestration across chemistry, protein/3D, assay tables,
    documents and microscopy.
11. Interactive 3D molecule after an experiment with zoom, rotation,
    representations and colour schemes.
12. Immutable raw files/checksums, QC, audit, roles and no automatic retraining.
13. University path for Stellenbosch/Cape Town or another institution with
    POPIA/security/SOP/SSO and instrument qualification.
14. Self-hosted model plan for the i9-14900K, RTX 4070 Ti 12 GB, 128 GB RAM and
    2 TB NVMe workstation. Qwen3-8B is the local target; Hugging Face is for
    training/checkpoints and Ollama for serving.
15. Complete downloadable developer package with no missing source,
    environments, API contracts or instructions.

## Major implementation milestones

- Developer SRS froze the original 60 requirements and implementation addenda.
- FastAPI/RDKit backend, 192 reference structures, deterministic hypothesis
  scorer, uncertainty/domain reporting, ranking and experiment/QC pipeline.
- Next.js research cockpit and experiment laboratory with simulation watermark.
- Public-source open discovery, PubChem/ChEMBL/Open Targets/structure adapters.
- Bounded 10.10B-map ZINC22 search and local shortlist triage.
- Operator-gated Vina and immutable redocking RMSD qualification.
- Professor AI RAG, optional Ollama/Qwen, PDF/TXT/Markdown ingestion, page/chunk
  citations, adversarial quarantine, conversations, corrections and evaluation.
- ChEMBL snapshot/model laboratory with scaffold-separated train/calibration/test
  partitions and active-learning batch proposal.
- Deterministic RDKit ETKDGv3 conformers and interactive 3D result viewer.
- Extended connectors for NCI-60, TDC, COCONUT, NPASS, ANPDB, LOTUS, Tox21,
  ToxCast, UniProt and Chemspace with checksum/quarantine rules.
- Five-lane multimodal engine, secure model gateway, evidence fusion,
  confidence ceiling, abstention and validated-feedback candidate gate.
- One-command Docker/Compose handoff, optional Ollama profile, complete
  environment templates and consolidated documentation.

## Non-negotiable scientific boundaries

- “100% accurate” is not a valid biomedical claim.
- Results are research-use hypotheses until prospective validation.
- Docking score is not efficacy evidence.
- Public visibility is not permission to scrape, redistribute or train.
- LLM prose cannot invent IC50, binding, toxicity or laboratory measurements.
- No patient-specific diagnosis, treatment, prescribing or dosing.
- Simulations, failed QC, uncited answers and ratings never become labels.
- Feedback is stored; only independently approved measured data may enter a
  frozen challenger snapshot, and promotion remains a named human decision.

## Recursion comparison

OSIEL can reproduce public-source orchestration patterns, transparent ranking,
bounded chemical search, docking, evidence retrieval, active-learning software,
experiment planning and audit. It does not possess Recursion's proprietary
phenomics maps, industrial-scale perturbational datasets, robotic laboratories,
compound inventory, repeated wet-lab cycles or independently validated models.
Those gaps require funding, partnerships, instruments, scientists and time—not
additional interface code.

## Current validation state

The most recent complete gate before this packaging milestone passed the Python
test suite, frontend lint, production build, OpenAPI export and handoff checks.
The system remains an advanced research/developer reference until one endpoint,
one external dataset and one real instrument workflow are independently
qualified.

## Canonical related documents

Use `docs/INDEX.md` as the documentation entry point. The SRS,
`MULTIMODAL_ENGINE_AND_ML_PLAN.md`, connector guide, Professor guide, model-lab
guide, production-readiness report and this record together form the developer
handoff baseline.
