# OSIEL Open Discovery Workflow

## Purpose

`Open discovery` is a developer-grade, research-use workflow that connects public scientific interfaces to local Python/RDKit computation. It is inspired by the orchestration pattern visible in Recursion LOWE, but it does **not** reproduce Recursion's proprietary PhenoMap, MatchMaker, generative models, datasets, robotic laboratory, or experimental evidence.

The workflow is designed to make every executed, deferred, failed, and human-controlled step visible to a scientist.

## What runs today

1. Resolve disease and target identifiers through an optional official Open Targets GraphQL client or prepare an authoritative link-out.
2. Resolve experimental RCSB PDB or predicted AlphaFold DB structure metadata when a PDB ID or UniProt accession is supplied.
3. Resolve the seed from the versioned OSIEL registry, user-supplied SMILES, or optional PubChem PUG REST lookup.
4. Scan the local registry and optionally call the official ChEMBL structure-similarity service.
5. Parent-standardize, uncharge, canonicalize, derive InChI/InChIKey, and deduplicate structures with RDKit.
6. Calculate molecular formula, molecular weight, cLogP, TPSA, HBD, HBA, rotatable bonds, ring count, fraction Csp3, and QED.
7. Calculate chiral Morgan-fingerprint Tanimoto similarity to the seed.
8. Surface Lipinski, PAINS, Brenk, NIH, and identity-quality flags without silently deleting records.
9. Apply a transparent chemistry-priority formula and retain every component.
10. Create an AutoDock Vina readiness manifest; execute only through the separate operator-gated worker with prepared PDBQT files and a reviewed box.
11. Optionally submit the standardized seed to a verified public SmallWorld map, import at most 100 remote analogues, and run local RDKit triage.
12. Prepare Chemspace/supplier hand-offs without crawling or purchasing.
13. Stop at a mandatory human scientific-review gate.

## Source and software integrations

| Component | Implemented connection | Default mode | Scientific boundary |
|---|---|---|---|
| Open Targets | Official GraphQL search client | Link-out / opt-in API | Resolves identifiers; does not infer target validity |
| PubChem | Official PUG REST name resolver | Local registry / opt-in API | Small-record enrichment only; bulk use needs release ingestion |
| ChEMBL | Official molecule search and similarity service | Opt-in API | Retrieved structure is not target activity evidence |
| RCSB PDB | Official entry metadata API | Link-out / opt-in API | Structure still needs biological and preparation review |
| AlphaFold DB | Official prediction metadata API | Link-out / opt-in API | pLDDT and pocket suitability must be reviewed |
| ZINC22 / CartBlanche22 / SmallWorld | Real one-seed bounded remote query with live map metadata and response checksum | Operator-gated | Provider searches its multi-billion map; OSIEL imports at most 100 structures and never stores the full index |
| CellMiner, TDC, COCONUT, NPASS, ANPDB, LOTUS, Tox21, ToxCast | Versioned source registry contracts | Deferred bulk import | Each release needs licence, checksum, parser, QC, and provenance |
| RDKit | Local Python computation | Enabled | Heuristics and alerts are not efficacy predictions |
| AutoDock Vina | Real `vina==1.2.7` child-process worker with immutable inputs/outputs | Operator-gated | A real score still requires qualified PDBQT preparation, box review, redocking and scientific interpretation |
| Chemspace | Supplier link/API contract | Link-out | No availability, price, purity, form, or order is claimed |

## Priority formula

The candidate score is a screening-priority heuristic:

```text
priority = 100 × (
    0.45 × Morgan-Tanimoto similarity
  + 0.20 × QED
  + 0.15 × Rule-of-Five adherence
  + 0.10 × structural-alert adherence
  + 0.10 × source-provenance completeness
)
```

It is intentionally named `priority_score`, not activity, affinity, IC50, or probability of success. Disease and target labels do not change the score because no validated disease- or target-specific model runs in this workflow.

## Run locally

```bash
npm run setup:local
npm run run:local
```

Open `http://localhost:3000`, select **Open discovery**, and run the default Gefitinib/EGFR example.

The frontend calls the Python service when this value is present:

```bash
NEXT_PUBLIC_OSIEL_API_URL=http://localhost:8000
```

Live outbound sources require both the request toggle and an operator-controlled environment gate:

```bash
OSIEL_PUBLIC_CONNECTORS_ENABLED=true
OSIEL_PUBLIC_CONNECTOR_USER_AGENT="Oncogon-OSIEL/0.2 research-use (contact: lab@example.edu)"
```

Keep the gate disabled for offline tests and teaching fixtures. Before enabling it on shared infrastructure, confirm provider usage policies, configure caching and rate limits, and replace the example contact.

Enable the separate live SmallWorld and Vina paths only when needed:

```bash
OSIEL_ZINC22_ENABLED=true
OSIEL_ZINC22_BASE_URL=https://sw.docking.org
OSIEL_ZINC22_MAP=REALDB-2025-07.smi.anon
OSIEL_VINA_ENABLED=true
```

See `docs/ZINC22_BILLION_SCALE_SEARCH.md` and `docs/VINA_DOCKING.md` for exact commands and boundaries.

## API example

```bash
curl -X POST http://localhost:8000/v1/open-discovery/runs \
  -H 'Content-Type: application/json' \
  -H 'X-OSIEL-Actor: developer@example.edu' \
  -d '{
    "disease": "Non-small cell lung cancer",
    "target_symbol": "EGFR",
    "seed_compound_name": "Gefitinib",
    "pdb_id": "4WKQ",
    "candidate_limit": 8,
    "public_connectors": false
  }'
```

Related routes:

- `GET /v1/open-discovery/connectors`
- `POST /v1/open-discovery/runs`
- `GET /v1/open-discovery/runs/{run_id}`
- `GET /v1/zinc22/capabilities`
- `POST /v1/zinc22/searches`
- `GET /v1/zinc22/searches/{job_id}`
- `GET /v1/docking/capabilities`
- `POST /v1/docking/jobs`
- `GET /v1/docking/jobs/{job_id}`
- `GET /v1/sources`
- `GET /v1/docs`

## What is still missing to become Recursion-like

| Capability | OSIEL now | Recursion-like requirement |
|---|---|---|
| Phenomic maps | None | Large proprietary cellular imaging and perturbation datasets, standardized assays, image models, batch correction, and years of wet-lab generation |
| Target discovery | Public identifier/evidence retrieval | Validated multimodal target-discovery models connecting genetic, phenomic, omics, literature, and disease evidence |
| Interaction prediction | Chemistry similarity only | Independently validated compound-protein interaction models trained on large, leakage-controlled experimental datasets |
| Search space | 192 local structures, optional ChEMBL, and real bounded search against a provider-reported 10.10B-entry SmallWorld map | Recursion-scale target-conditioned prediction across huge chemical spaces, private data, procurement integration and validation |
| Generative chemistry | Explicitly absent | Constrained molecular generation, retrosynthesis, synthesizability, novelty/IP checks, uncertainty, and medicinal-chemist review |
| Docking / physics | Real bounded Vina 1.2.7 worker; preparation remains manual/qualified | Automated preparation, co-crystal redocking, ensemble docking, rescoring, distributed workers, and experimental correlation studies |
| ADMET | Demonstration rule panel elsewhere in OSIEL | Calibrated endpoint models with task-specific datasets, applicability domains, external validation, and prospective monitoring |
| Robotic laboratory | Computational simulation only | Real LIMS/ELN, liquid handlers, compound stores, plate readers, scheduling, calibration, maintenance, sample chain of custody, and instrument-qualified parsers |
| Closed-loop learning | Governance gates exist; no approved real rows | Prospective measured data at scale, QC, dataset snapshots, active-learning policies, challenger training, independent review, and safe promotion |
| Procurement | Link-out only | Supplier/API contracts, entity/form matching, stock and lead-time updates, approvals, budgets, receiving, and inventory integration |
| Scientific validation | Software tests only | Baselines, scaffold/time splits, external validation, calibration, prospective studies, reproducibility, negative controls, faculty review, and publication |
| Production platform | Developer reference | Multi-tenant cloud/HPC platform, job queues, GPU scheduling, lakehouse, chemical search, observability, backups, disaster recovery, SSO, RLS, audit, and incident response |
| Legal and institutional readiness | Claim boundaries and adapter contracts | Dataset/software licences, IP/FTO review, POPIA/privacy, biosafety, chemical safety, ethics, SOP qualification, vendor contracts, and university acceptance |

The shortest credible path is not to copy Recursion feature-for-feature. It is to choose one disease, one target class, one assay, one plate reader, and one prospective study; prove identity, reproducibility, calibration, and wet-lab value there; then expand.

## Verification

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_open_discovery.py
npm run lint
npm run build
```

Optional live/compute smoke tests:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_zinc22.py
PYTHONPATH=backend .venv/bin/python backend/scripts/fetch_vina_example.py
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_vina.py
```

The tests verify that the trace is complete, the seed is excluded from analogues, scores remain bounded, an operator-disabled public-API request never performs network calls, runs are persisted, and no fake docking score is emitted.

## Authoritative references

- Recursion LOWE: <https://www.recursion.com/lowe>
- Open Targets Platform API: <https://platform-docs.opentargets.org/data-access/graphql-api>
- PubChem PUG REST: <https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest>
- ChEMBL Web Services: <https://chembl.gitbook.io/chembl-interface-documentation/web-services>
- RCSB Data API: <https://data.rcsb.org/>
- AlphaFold DB API: <https://alphafold.ebi.ac.uk/api-docs>
- ZINC22 / CartBlanche22: <https://cartblanche22.docking.org/>
- RDKit: <https://www.rdkit.org/>
- AutoDock Vina documentation: <https://autodock-vina.readthedocs.io/>
- SmallWorld public maps: <https://sw.docking.org/search/maps>
- CartBlanche22 source: <https://github.com/docking-org/cartblanche22>
- Detailed no-/low-budget Recursion gap: `docs/RECURSION_FREE_ALTERNATIVES_ROADMAP.md`
