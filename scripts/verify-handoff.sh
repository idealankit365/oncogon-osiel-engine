#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_root}"

required=(
  .env.example .env.docker.example README.md package.json package-lock.json
  Dockerfile.web docker-compose.yml docker-compose.gpu.yml Makefile
  start-osiel.sh stop-osiel.sh start-osiel.ps1
  app/page.tsx app/lib/osiel-client.ts backend/Dockerfile backend/requirements.txt
  backend/app/main.py backend/app/data/compounds.json contracts/openapi.json
  docs/OSIEL_Developer_SRS.md docs/DEVELOPER_HANDOFF.md
  docs/OPEN_DISCOVERY_WORKFLOW.md backend/scripts/e2e_open_discovery.py
  docs/ZINC22_BILLION_SCALE_SEARCH.md backend/scripts/e2e_zinc22.py
  docs/VINA_DOCKING.md backend/scripts/fetch_vina_example.py backend/scripts/e2e_vina.py
  docs/LOCAL_SCIENTIFIC_COPILOT.md docs/RECURSION_FREE_ALTERNATIVES_ROADMAP.md
  backend/app/connectors/cartblanche.py backend/app/connectors/ollama.py
  backend/app/zinc22_search.py backend/app/vina_docking.py backend/app/vina_worker.py
  app/components/zinc22-search.tsx app/components/vina-runner.tsx
  app/components/recursion-roadmap.tsx
  docs/MODEL_LAB_AND_ACTIVE_LEARNING.md backend/scripts/e2e_model_lab.py
  backend/app/model_lab.py backend/app/docking_benchmark.py app/components/model-lab.tsx
  docs/AI_PROFESSOR_ENGINE.md backend/app/knowledge.py backend/scripts/e2e_professor.py
  docs/INTERACTIVE_3D_COMPOUNDS.md backend/app/conformer.py backend/scripts/e2e_conformer.py
  app/components/compound-3d-viewer.tsx public/demo-conformers.json
  docs/EXTENDED_DATA_CONNECTORS.md backend/app/data_connectors.py
  backend/app/connectors/bulk_sources.py backend/app/connectors/uniprot.py
  backend/app/connectors/tdc.py backend/app/connectors/chemspace.py
  backend/requirements-connectors.txt app/components/source-connectors.tsx
  backend/scripts/export_openapi.py
  docs/INDEX.md docs/ONE_CLICK_SETUP.md docs/API_GUIDE.md docs/SERVICE_CATALOG.md
  docs/ENVIRONMENT_REFERENCE.md docs/IMPLEMENTATION_GUIDE.md
  docs/THREAD_PROJECT_RECORD.md docs/MULTIMODAL_ENGINE_AND_ML_PLAN.md
  backend/app/model_gateway.py backend/app/multimodal_engine.py
  app/components/multimodal-workbench.tsx backend/tests/test_multimodal_engine.py
)
for path in "${required[@]}"; do
  [[ -f "${path}" ]] || { echo "Missing required handoff file: ${path}" >&2; exit 66; }
done

[[ -x .venv/bin/python ]] || { echo "Missing .venv; run npm run setup:local." >&2; exit 69; }
[[ -d node_modules ]] || { echo "Missing node_modules; run npm run setup:local." >&2; exit 69; }

npm run lint
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_demo.py
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_open_discovery.py >/dev/null
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_model_lab.py >/dev/null
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_professor.py >/dev/null
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_conformer.py >/dev/null

echo "Developer handoff verification passed."
