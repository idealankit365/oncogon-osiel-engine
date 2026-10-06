# OncoGon AI · OSIEL client showcase

## The client story

A cancer research team may already have papers, experimental reports, assay results, protocols, imaging outputs, and previous analyses spread across different systems. OSIEL provides one governed research workspace where permitted project evidence can be indexed and searched, connected to computational discovery and experiments, and retained as auditable research memory. It assists researchers; qualified humans make scientific decisions. This is a research showcase, not a diagnostic or treatment system.

```text
RESEARCH INTERFACE → OSIEL SCIENTIFIC ENGINE → DATA + MODELS + EXPERIMENTS → AUDIT + HUMAN REVIEW
```

## Before the meeting

1. From the repository, run `./start-osiel.sh`. It uses `.env.showcase.example` to create `.env` if needed, starts both containers, waits for health, and runs the smoke checks. Keep the monorepo together.
2. The default URLs are [application](http://localhost:3000), [API](http://localhost:8000), and [API docs](http://localhost:8000/v1/docs). If those ports are occupied, set `OSIEL_WEB_PORT`, `OSIEL_API_PORT`, `NEXT_PUBLIC_OSIEL_API_URL`, and `OSIEL_CORS_ORIGINS` in `.env`, then use the URLs printed by the startup script. For this rehearsal, unrelated services occupy 3000/8000, so the local override uses [application](http://localhost:3100), [API](http://localhost:8100), and [API docs](http://localhost:8100/v1/docs).
3. Verify with `NEXT_PUBLIC_OSIEL_API_URL=http://localhost:8000 OSIEL_WEB_URL=http://localhost:3000 ./scripts/showcase-smoke.sh` on default ports, or substitute the configured ports. The script checks the frontend root and eight core API endpoints.
4. Open the Cockpit and confirm the reference registry and current research run appear. Do not use confidential client documents in this shared showcase environment. Stop afterward with `./stop-osiel.sh` without deleting persistent volumes.

`OSIEL_DEMO_MODE=true` enables the backend reference registry and research showcase workflows. The OSIEL Research Activity Model (`osiel-research-sim@1.0`) combines molecular descriptors, research context, and a persisted per-run seed to produce bounded computational estimates. A new explicit run varies; reopening a stored run returns the same results. Model class is `synthetic_research_simulation`, validation status is `unvalidated`, and intended use is `research_showcase`. These outputs are neither wet-lab measurements nor clinical results. Project knowledge ingestion is enabled; Ollama, Vina, external connectors, model training, and multimodal adapters are disabled by default.

## Presenter path · approximately 10 minutes

| Time | Click | Say | Backend action and boundary |
|---|---|---|---|
| 0:00–1:30 | **Research Cockpit**; select context, click **Run OSIEL engine**, inspect rank and uncertainty; **Export run** | “We bring computational candidates into one reviewable research context.” | The research model creates a new seeded, persisted ranking from the 192-reference registry. Refresh and run history reopen the same saved result; a new click creates a fresh run. Scores are hypotheses, not efficacy measurements. Export contains the current run only. |
| 1:30–2:30 | **Scientific Copilot → Project knowledge**; show upload and scoped sources | “Existing project material can enter the research workspace with explicit rights and provenance.” | FastAPI validates and indexes permitted PDF, TXT, or Markdown. Indexed does not mean scientifically reviewed or approved. Use a harmless sample if demonstrating upload. |
| 2:30–3:30 | **Ask professor**; ask a question tied to that sample | “The system retrieves source passages and shows where they came from.” | Scoped FTS5 retrieval supplies document chunks and citations. In this configuration Ollama synthesis is off, so the engine abstains from unsupported prose; do not claim an AI answer was generated. |
| 3:30–4:30 | **Compound Registry**; search, page, select, rotate 3D | “Identity and computed geometry can be inspected before selection.” | FastAPI supplies records and RDKit conformers. A conformer is not a crystal structure or activity result. |
| 4:30–6:00 | **Open Discovery → Run open discovery** with default local inputs | “The engine separates local analysis from external evidence it did not fetch.” | A backend run resolves local structures, evaluates chemistry, and records deferred sources. Public connectors are off. The priority list is chemistry triage, not target binding or efficacy. |
| 6:00–7:30 | **Experiments**; run computational dry-run; inspect results and QC | “This exercises protocol, simulated observations, QC, and provenance.” | FastAPI creates and stores an experiment/result. It performs no physical assay. Simulation-only observations cannot train a validated model. |
| 7:30–8:30 | **Audit & Lineage**; open a recent event’s provenance | “The software trail records who did what and when.” | Backend audit events reflect actual workflow actions. Audit is not independent scientific validation. |
| 8:30–10:00 | **Model Governance → Production Center** | “We can see both the research capability and the remaining validation gates.” | Backend reports development models, readiness blockers, disabled optional services, and lack of production authentication. Do not claim clinical or production qualification. |

If the workspace is unavailable, use **Retry** after restoring it. The UI does not substitute scientific results in the browser. Optional integrations remain visible as not enabled, not configured, or unavailable on this host.
