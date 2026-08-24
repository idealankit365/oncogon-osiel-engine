# Recursion gap and almost-zero-budget roadmap

Status date: 22 August 2026  
Scope: research-use OSIEL developer reference, not a claim of equivalence to Recursion.

## The honest answer

OSIEL can reproduce much of the **software pattern** visible in Recursion LOWE: a natural-language workspace, public evidence retrieval, typed workflows, inspectable steps, remote chemical-space search, local chemistry calculations, docking execution, experiment planning, QC, audit and guarded learning decisions.

It cannot reproduce Recursion's core data and operating advantage for free. Recursion reports more than 50 petabytes of multimodal biological and chemical data, an automated laboratory capable of up to 2.2 million samples per week, proprietary PhenoMap and MatchMaker systems, BioHive-2 supercomputing, physical compound/synthesis operations, cross-functional drug-discovery teams and prospective experimental programmes. Those are not UI features that ChatGPT can manufacture.

The correct goal is therefore: build the strongest public-source, scientifically honest orchestration platform possible; prove one narrow workflow with a university partner; and leave proprietary, physical and institutionally validated steps visibly blocked.

## Evidence for the comparison

Recursion's own current materials state that:

- LOWE orchestrates workflows using proprietary PhenoMap data, MatchMaker, generative chemistry, ADMET and commercial-compound procurement: [LOWE](https://www.recursion.com/lowe).
- the Recursion OS spans target identification through clinical-trial enrollment and its labs can process up to 2.2 million samples per week: [platform](https://www.recursion.com/platform).
- Recursion reports more than 50 PB of multimodal data and BioHive-2 as a Top500-ranked supercomputer in 2025: [mission](https://www.recursion.com/mission).
- MatchMaker predicts small-molecule/protein-pocket compatibility at a scale described as less computationally intensive than traditional docking: [MatchMaker release](https://ir.recursion.com/news-releases/news-release-details/recursion-bridges-protein-and-chemical-space-massive-protein/).
- Recursion says its six public RxRx datasets represent less than 1% of its proprietary dataset: [FAQ](https://www.recursion.com/faq).

These are corporate descriptions and should be interpreted as company-reported capabilities, not independent validation of every performance claim.

## Priority ledger

| Priority | Capability | OSIEL status | No-/low-cost action | Funding boundary |
|---|---|---|---|---|
| P0 | Inspectable workflow orchestration | Built | Extend typed adapters behind the ten-stage trace | None for small local use |
| P0 | Chemical identity and RDKit triage | Built | Freeze versions; add identity regression cases | Expert review still needed |
| P0 | Public target/structure/evidence retrieval | Built | Cache official APIs and snapshot releases | Data curation labour |
| P0 | Multi-billion analogue search | Built | Public SmallWorld query of live 10.10B-entry map; bounded local shortlist | Physical compounds and bulk campaigns cost money |
| P0 | AutoDock Vina execution | Built | Prepared PDBQT inputs, bounded worker, checksums, real poses and redocking RMSD | Multi-complex enrichment and protocol qualification need expertise |
| P0 | Audit, simulation barrier and human review | Built | Move to authenticated append-only PostgreSQL for shared use | Managed operations later |
| P0 | Experiment planning and QC simulation | Built | Use only for teaching until one real instrument is qualified | Physical assay is funded/partner work |
| P1 | Local Professor/RAG | Built reference | Qwen3-8B/Ollama with supplied-ID citations, abstention and fallback | Faculty library/evaluation and governance remain |
| P1 | Bounded public bioactivity snapshot | Built | Exact-endpoint ChEMBL retrieval, immutable raw/normalized checksums and conflict controls | Full releases and expert assay curation remain heavy |
| P1 | Baseline activity model | Built reference | Scaffold-separated ECFP4 baseline, held-out calibration, frozen metrics and domain | Locked external and prospective validation remain external work |
| P1 | Endpoint-specific ADMET | Free build | Add versioned ADMET-AI adapter and applicability domain | Independent endpoint qualification |
| P1 | Background job workers | Free build | Prefect/Celery, Redis/PostgreSQL, cancellation and quotas | Multi-user operations and hardware later |
| P2 | Public phenomics starter | Free but heavy | JUMP-Cell Painting/RxRx subset, CellProfiler and reproducible benchmark | Downloads, storage, GPU time and expert analysis |
| P2 | Active-learning software | Built reference | Uncertainty, distance-to-training, QED and diversity create a human-gated proposal | Useful learning needs real measured outcomes |
| P2 | Generative chemistry research | Free but heavy | REINVENT/DrugEx only after validated objectives and SA/IP checks | Medicinal chemistry and synthesis validation |
| P3 | Proprietary phenomic map | Funding required—paused | Public datasets are research substitutes, not equivalents | Cells, plates, reagents, imaging, staff, QC and years of data |
| P3 | Robotic wet laboratory | Funding required—paused | Partner with a university core/CRO before buying robots | Instruments, integration, calibration, service and consumables |
| P3 | Physical compounds and synthesis | Funding required—paused | Very small supervised informer set through a partner | Purchase, customs, synthesis, analytical QC and storage |
| P3 | Prospective biological validation | Funding required—paused | One preregistered university assay with controls | Cells, reagents, instruments and scientific supervision |
| P3 | Million-user operation | Funding required—paused | Start with one lab and measured value | GPUs, hosting, SRE, security, support and compliance |
| P3 | IP/legal/regulatory operation | Funding/institution required—paused | Use university ethics, biosafety, legal and technology-transfer offices | ChatGPT cannot grant approvals, licences or FTO |

## What has now been implemented without licence spending

1. Optional official Open Targets, PubChem, ChEMBL, RCSB PDB and AlphaFold DB connectors.
2. RDKit parent standardization, InChIKey identity, descriptors, Morgan similarity, QED, Lipinski and catalogue-alert checks.
3. A live SmallWorld connector that verifies a provider map and searches a provider-reported 10.10B-entry chemical index without downloading it.
4. A real AutoDock Vina 1.2.7 process with prepared-input validation, CPU/timeout limits, immutable inputs/outputs, downloadable poses and heavy-atom redocking RMSD.
5. A local Qwen3-8B/Ollama adapter restricted to retrieved evidence with structured output, supplied-ID citation validation, abstention, prompt-override screen and deterministic fallback.
6. Experiment design, visible simulation logs, dose-response/QC output, plate-reader import quarantine, immutable raw-file checksum, roles, audit and model-promotion gates.
7. Immutable bounded ChEMBL activity snapshots with exact endpoint/assay rules, grey-zone exclusion, duplicate aggregation, label-conflict removal and scaffold accounting.
8. A three-way scaffold-separated ECFP4 baseline with held-out calibration, frozen evaluation metrics, applicability-domain warnings and immutable model artifact.
9. A human-gated active-learning proposal balancing uncertainty, distance-to-training, QED and chemical diversity.
10. A visible in-product capability ledger separating built, free-build, free-heavy and funding-required work.

These prove software execution. They do not prove biological performance.

## Next implementation order

### Now: stabilize and benchmark

- Freeze the current API contract and add live-connector smoke tests outside the deterministic unit suite.
- Add caching, service-specific rate limits and provider outage states.
- Expand the implemented single-complex redocking RMSD gate into a multi-complex and decoy-enrichment benchmark.
- Load an approved small document set and measure Professor retrieval/citation accuracy.

### Next: one real modelling task

- Choose and faculty-approve one target, endpoint, assay inclusion rule and prediction horizon.
- Run the implemented immutable ChEMBL pipeline on that frozen task and preserve its release/terms record.
- Add a locked external or temporal set that is never used for calibration or model selection.
- Compare Chemprop against the implemented fingerprint baseline under the identical split.
- Publish discrimination, calibration, uncertainty, applicability domain and failure slices in a signed model card.

### Then: one public phenomics benchmark

- Use a manageable JUMP-CP or RxRx subset.
- Reproduce one published benchmark before building a custom representation model.
- Link perturbation identities and batch metadata; never merge unmatched assays silently.

### Partner: one prospective assay

- Pre-register candidates, controls, plate map, exclusion criteria and QC thresholds.
- Have a qualified university laboratory execute the physical work.
- Return original instrument files, metadata, deviations and blinded outcomes.
- Compare prospective results against the frozen model without retraining on the answer.

### Only after evidence: scale or fundraise

Use reproducibility, prospective enrichment and time/cost saved as the evidence. Do not use a larger compound count, a more animated interface or an LLM answer as proof of drug-discovery performance.

## Final boundary

This project can become a strong university research-orchestration and teaching platform at low software cost. It cannot become Recursion merely by adding code because Recursion's differentiator is the coupled system of proprietary measured data, validated models, automated physical experiments, compounds, people, compute and repeated prospective learning.
