# AutoDock Vina in OSIEL

OSIEL contains a real, operator-gated AutoDock Vina 1.2.7 execution path. It is not a fabricated score generator. The API runs the official Python binding inside a bounded child process, with no shell, and records SHA-256 identities for the prepared receptor, prepared ligand, and ranked-pose output.

## What is implemented

- Official `vina==1.2.7` Python engine pinned in `backend/requirements.txt`.
- Prepared rigid-receptor and ligand PDBQT uploads.
- Strict filename, base64, size, text, atom-record, and ligand-marker validation.
- Search-box centre and size validation.
- Bounded CPU, exhaustiveness, mode count, energy range, seed, and wall timeout.
- Isolated `python -m app.vina_worker` process invoked as an argument list with `shell=False` semantics.
- Core-dump, open-file, and output-size limits in the worker.
- Immutable content-addressed storage for inputs and output poses.
- Persisted job record, audit event, command manifest, warnings, engine version, raw energy terms, and ranked affinities.
- Downloadable output PDBQT from the Next.js Open Discovery screen.
- Timeout and failed-worker states that never manufacture a score.

## What is intentionally not automated

OSIEL does not convert arbitrary PDB or SMILES input to PDBQT in the docking endpoint. That conversion requires scientific choices about:

- biological assembly and chain selection;
- missing residues and sidechains;
- waters, ions, cofactors, metals, and co-crystallized ligands;
- protonation, tautomer and charge state;
- flexible residues;
- ligand stereochemistry and conformers;
- binding-site definition and docking-box placement.

Use a qualified preparation workflow such as Meeko and inspect the result. Automatic preparation without review would make the button easier to press but the scientific result less trustworthy.

## Enable locally

```bash
cp .env.example .env
```

Set:

```bash
OSIEL_VINA_ENABLED=true
OSIEL_VINA_MAX_CPU=4
OSIEL_VINA_MAX_TIMEOUT_SECONDS=600
```

Then run:

```bash
npm run setup:local
npm run run:local
```

Open **Open discovery**, complete or load a discovery run, then use **AutoDock Vina 1.2.7 execution**. Upload a prepared receptor PDBQT and ligand PDBQT, enter a reviewed box, and start the job.

## Verify with the pinned official example

The example fetcher downloads only two files from a pinned AutoDock Vina Git commit and verifies exact SHA-256 checksums before saving them:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/fetch_vina_example.py
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_vina.py --exhaustiveness 8 \
  --output deliverables/OSIEL_Formal_Redocking_Benchmark_Report.json
```

The pinned inputs are the official 1IEP Python-scripting example. The default smoke run uses centre `(15.190, 53.903, 16.917)`, a `20 × 20 × 20 Å` box, one CPU, fixed seed `20260822`, and exhaustiveness `1`. Increase exhaustiveness only after the smoke path succeeds and a scientist approves the preparation and protocol.

On 22 August 2026 the OSIEL path completed this smoke run in approximately ten seconds and returned a top Vina score of `-13.221 kcal/mol`; output SHA-256 was `11c697e026a7b766fdd7bfe7d571c7748a0ba5e2c44fd1fcf36e73533dc8e2e4`. This confirms executable wiring and reproducibility for the pinned software example. It is not a biological validation result.

Verified checksums:

| File | SHA-256 |
|---|---|
| `1iep_receptor.pdbqt` | `761469710e3915b89b274483076dfe49754be7956661bc42f4cc36a182399d59` |
| `1iep_ligand.pdbqt` | `37a20e58e77072c6b3ff07f285a345e647dd4e564af316a06e49518b15b7aa61` |

## API routes

- `GET /v1/docking/capabilities`
- `POST /v1/docking/jobs`
- `GET /v1/docking/jobs/{job_id}`
- `POST /v1/docking/benchmarks`

The POST route accepts prepared PDBQT content as base64. In production, put this endpoint behind university SSO, queue execution on dedicated workers, enforce per-user quotas, scan inputs, and keep the API process separate from compute workers.

## Redocking RMSD qualification

After a completed Vina job, the interface accepts the exact prepared co-crystal ligand PDBQT and calls `POST /v1/docking/benchmarks`. The Python service:

1. retains the reference ligand by SHA-256;
2. requires identical heavy-atom type order to the docked input;
3. Kabsch-aligns every returned pose to the reference coordinates;
4. reports aligned heavy-atom RMSD for each compatible pose; and
5. marks pose recovery as passed when the best RMSD is at or below the requested threshold (2.0 Å by default).

This validates pose recovery for one prepared complex. `scoring_qualified` remains false because affinity ranking requires a multi-complex redocking set, decoy enrichment, sensitivity analysis and independent protocol review.

### Executed formal reference result

On 22 August 2026 the pinned official 1IEP fixture ran through OSIEL with AutoDock Vina 1.2.7, fixed seed `20260822`, one CPU, three returned modes and exhaustiveness `8`. The run completed in 81.2983 seconds. Pose 1 scored `-13.221 kcal/mol` and achieved `0.8636 Å` atom-order-preserving aligned heavy-atom RMSD, passing the predefined `2.0 Å` pose-recovery gate. The ranked-pose output SHA-256 was `ba06bbd95ca4275f1712d201c46b01c0041d12bfbbb1897deb036ebd3fb2132d`.

The generated report explicitly returns `scoring_qualified=false`. This single-complex success does not validate ligand ranking, enrichment, affinity, cellular response, safety or efficacy.

## Interpretation

A more negative Vina score can rank a pose better under the selected scoring function. It is not a measured dissociation constant, IC50, cellular response, toxicity result, or probability of clinical success. A scientifically useful docking study additionally needs co-crystal redocking, controls, repeat seeds, box and protonation sensitivity, pose inspection, orthogonal methods, and experimental validation.

Official references:

- Installation: <https://autodock-vina.readthedocs.io/en/latest/installation.html>
- Python scripting: <https://autodock-vina.readthedocs.io/en/latest/docking_python.html>
- Source/releases: <https://github.com/ccsb-scripps/AutoDock-Vina>
- Preparation requirements: <https://autodock-vina.readthedocs.io/en/latest/docking_requirements.html>
