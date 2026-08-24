# OSIEL evidence-backed model laboratory

## What is implemented

OSIEL now has an executable Python workflow for one narrow molecular-activity task:

1. retrieve a bounded activity slice from the official ChEMBL Web Services API;
2. retain the exact raw response in content-addressed immutable storage;
3. require one target, one endpoint and one assay type;
4. standardize structures with the pinned RDKit pipeline;
5. remove non-exact relations, invalid structures, the pChEMBL grey zone, duplicates and label conflicts;
6. freeze the normalized records and their SHA-256 checksum;
7. create separate Bemis–Murcko scaffold train, calibration and test partitions;
8. train a class-balanced ECFP4 logistic-regression baseline;
9. fit Platt calibration only on the held-out calibration scaffolds;
10. report AUROC, average precision, balanced accuracy, sensitivity, specificity, Brier score and expected calibration error on the frozen test scaffolds;
11. retain a portable JSON model artifact by SHA-256;
12. calculate prediction uncertainty and nearest-training similarity; and
13. propose a diverse active-learning batch without ordering compounds or starting an experiment.

This is the correct first comparison model before a graph neural network. A complex model should not be accepted unless it beats the same frozen baseline and split.

## Enable locally

Keep the model laboratory disabled on unprotected shared deployments. In `.env`:

```dotenv
OSIEL_PUBLIC_CONNECTORS_ENABLED=true
OSIEL_PUBLIC_CONNECTOR_USER_AGENT="Oncogon-OSIEL/0.3 research-use (contact: your-real-university-email)"
OSIEL_MODEL_LAB_ENABLED=true
OSIEL_MODEL_LAB_MAX_RECORDS=2000
```

Then start the supplied Docker or local Python/Next.js stack. Open **Model laboratory** in the left navigation.

## Developer checks

Software-only reproducibility check:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_model_lab.py
```

Bounded live ChEMBL check:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_model_lab.py --live --max-records 1000
```

The default command uses explicitly non-experimental fixture labels to test the pipeline. The `--live` command retrieves public records. Neither command performs a wet-lab experiment.

## API sequence

| Step | Route | Output |
|---|---|---|
| Inspect | `GET /v1/model-lab/capabilities` | operator state, model and evaluation contract |
| Snapshot | `POST /v1/model-lab/chembl/snapshots` | immutable source and normalized dataset hashes |
| Train | `POST /v1/model-lab/models` | scaffold split, calibrated evaluation and artifact hash |
| Predict | `POST /v1/model-lab/predictions` | probability, uncertainty and applicability domain |
| Select | `POST /v1/model-lab/active-learning-batches` | human-gated next-test proposal |

No endpoint promotes a model automatically. The existing reviewer and champion/challenger controls remain a separate gate.

## Relationship to the 10.10B search map

The systems solve different problems:

- CartBlanche/SmallWorld searches the provider-hosted 10.10B-entry REALDB map for structurally related catalogue records.
- The model laboratory learns a bounded relationship between molecular fingerprints and one ChEMBL endpoint.
- Active learning ranks a bounded candidate pool for potential information gain.

A remote structure hit is not a model prediction. A model prediction is not a docking result. A docking result is not a measured biological response.

## Scientific limitations

The implemented reference gate is an engineering check only. Before a university treats a model as scientifically validated, it still needs:

- a faculty-approved task and assay inclusion protocol;
- a locked external dataset not used in model or threshold selection;
- assay and target curation beyond API-field filtering;
- temporal and chemical-series leakage review;
- subgroup and applicability-domain analysis;
- baseline comparison under the identical split;
- prospective wet-lab validation;
- independent reproduction and signed model-card approval.

The active-learning batch remains a proposal until a qualified scientist checks compound identity, purity, availability, synthesis, IP, safety, assay feasibility and controls.
