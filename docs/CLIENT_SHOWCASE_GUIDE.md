# OncoGon AI OSIEL client showcase

## Start

From this repository, copy `.env.showcase.example` to `.env` if you want to review the settings, then run `./start-osiel.sh`. The script creates the safe showcase `.env` if none exists, starts the frontend and FastAPI together, and checks their core endpoints. Open **http://localhost:3000**. API documentation is at **http://localhost:8000/v1/docs**. Stop with `./stop-osiel.sh`.

The showcase uses `OSIEL_DEMO_MODE=true`: the backend supplies 192 reference structures and deterministic computational predictions. They are research hypotheses, not measured or clinically validated efficacy. Project document ingestion is enabled; Ollama, Vina, external connectors, model training, and multimodal adapters are disabled unless an operator intentionally configures them. Do not upload confidential client material to a shared showcase machine.

## Architecture

```text
RESEARCH INTERFACE
        ↓
OSIEL SCIENTIFIC ENGINE
        ↓
DATA + MODELS + EXPERIMENTS
        ↓
AUDIT + HUMAN REVIEW
```

OSIEL connects evidence, computational analysis, experiment records, project knowledge, and human review in one research workflow. It does not make clinical recommendations or authorize laboratory work. Frontend and backend remain in **this single repository**.

## Live walkthrough

| Step | Click and show | What actually happens | Scientific boundary |
|---|---|---|---|
| 1. Research Cockpit | Select context, inspect ranked compounds, export the run | FastAPI checks health, loads compounds and creates a computational ranking | Scores and uncertainty are hypotheses |
| 2. Compound Registry | Search, page, select a compound, inspect identity and 3D | FastAPI returns registry identity and generates an RDKit conformer | A structure does not establish activity |
| 3. Open Discovery | Enter disease and seed context, run discovery, inspect trace/evidence | Backend performs local RDKit triage; optional public sources report their actual status | Priority is chemistry triage, not efficacy |
| 4. Scientific Copilot | Open **Project knowledge**, add an approved PDF/TXT/Markdown document, ask a question | Backend validates and indexes the file, retrieves scoped evidence, returns cited guidance or abstains | AI synthesis may be disabled; citations require human review |
| 5. Experiments | Select candidates in Cockpit, run computational experiment, inspect history/QC | FastAPI creates protocol and simulation-only result with audit lineage | No wet-lab measurement; simulation cannot train a validated model |
| 6. Audit & Lineage | Inspect recorded events after ranking/experiment | FastAPI supplies actor, event, time, resource, and detail | Recorded software provenance supports review; it is not scientific validation |
| 7. Model Governance | Inspect reference model and readiness | FastAPI supplies model registry and readiness | No validated production oncology model is configured |
| 8. Production Center | Review service status and blockers | FastAPI reports environment, optional capabilities, and readiness | Institutional deployment needs further validation and approval |

## Recovery during a call

If the research engine is unavailable, the UI shows an unavailable state and no scientific results. Restart the stack or use **Retry connection**. Optional services remain visible with their disabled status; avoid enabling network or compute integrations during the call unless already configured and tested.
