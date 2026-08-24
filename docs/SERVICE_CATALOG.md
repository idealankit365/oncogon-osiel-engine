# OSIEL service catalog

| Service | Container/process | Port | Responsibility | Current state |
|---|---|---:|---|---|
| Research workbench | `web` | 3000 | Next.js/Vinext UI, loaders, experiment debugger, evidence, 3D and multimodal console | working |
| Scientific API | `api` | 8000 | FastAPI orchestration, RDKit, ranking, experiments, Professor, connectors, model lab and governance | working |
| Reference database | API volume | internal | SQLite system of record for the developer reference | working |
| Immutable objects | API volume | internal | SHA-256-addressed raw documents, connector files, conformers and model artifacts | working |
| Ollama | `ollama` profile `ai` | 11434 | optional local Qwen inference and embeddings | opt-in |
| Model downloader | `ollama-models` profile `ai` | none | one-shot pull of configured model tags | opt-in |
| PostgreSQL | profile `future-infra` | internal | production migration target; RDKit cartridge/RLS work remains | not connected |
| MinIO | profile `future-infra` | internal | production object-storage target | not connected |
| Chemistry adapter | external HTTPS/loopback | configured | versioned Chemprop/validated scientific model | contract ready |
| Protein adapter | external HTTPS/loopback | configured | versioned sequence/structure model | contract ready |
| Imaging adapter | external HTTPS/loopback | configured | validated microscopy feature model | contract ready |

## Data connectors

Built-in executable connector paths cover PubChem, ChEMBL, Open Targets,
RCSB/AlphaFold structure services, ZINC22/CartBlanche, NCI-60, TDC, COCONUT,
NPASS, ANPDB, LOTUS, Tox21, ToxCast, UniProt and Chemspace. Every connector is
bounded, server-side and fail-closed. Bulk/licensed sources require approved
release URLs, expected checksums or provider keys before use.

## Service boundaries

- The browser never receives provider/model secrets.
- LLM output never supplies quantitative activity labels.
- Model adapters must return structured findings, confidence, evidence and an
  exact model version.
- Simulation and user ratings never enter training.
- Laboratory authorization always requires a named scientist.
