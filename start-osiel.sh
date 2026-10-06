#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${project_root}"

command -v docker >/dev/null || { echo "Docker Desktop or Docker Engine is required." >&2; exit 69; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required." >&2; exit 69; }
docker info >/dev/null 2>&1 || { echo "Docker Engine is not running. Start Docker Desktop and retry." >&2; exit 69; }
command -v curl >/dev/null || { echo "curl is required for startup verification." >&2; exit 69; }

if [[ ! -f .env ]]; then
  cp .env.showcase.example .env
  echo "Created .env from the safe client showcase template."
fi

with_ai=false
with_gpu=false
for argument in "$@"; do
  case "${argument}" in
    --with-ai) with_ai=true ;;
    --with-ai-gpu) with_ai=true; with_gpu=true ;;
    --help|-h)
      echo "Usage: ./start-osiel.sh [--with-ai|--with-ai-gpu]"
      echo "  default    Web + complete Python API + SQLite/object volumes + connector code"
      echo "  --with-ai  Also starts Ollama and downloads the configured Qwen models"
      echo "  --with-ai-gpu  Same, with NVIDIA GPU access through Docker"
      exit 0
      ;;
    *) echo "Unknown option: ${argument}" >&2; exit 64 ;;
  esac
done

compose=(docker compose)
if [[ "${with_gpu}" == "true" ]]; then
  compose+=( -f docker-compose.yml -f docker-compose.gpu.yml )
fi

if [[ "${with_ai}" == "true" ]]; then
  export OSIEL_OLLAMA_ENABLED=true
  export OSIEL_OLLAMA_DOCKER_BASE_URL=http://ollama:11434
  "${compose[@]}" up --build -d --wait api web
  "${compose[@]}" --profile ai up -d --wait ollama
  "${compose[@]}" --profile ai run --rm ollama-models
  "${compose[@]}" restart api >/dev/null
  "${compose[@]}" up -d --wait api web
else
  "${compose[@]}" up --build -d --wait api web
fi

web_port="$("${compose[@]}" port web 3000 | awk -F: '{print $NF}')"
api_port="$("${compose[@]}" port api 8000 | awk -F: '{print $NF}')"
OSIEL_WEB_URL="http://localhost:${web_port}" NEXT_PUBLIC_OSIEL_API_URL="http://localhost:${api_port}" ./scripts/showcase-smoke.sh

echo
echo "OSIEL is ready."
echo "Application:      http://localhost:${web_port}"
echo "Scientific API:   http://localhost:${api_port}"
echo "API docs:         http://localhost:${api_port}/v1/docs"
echo "OpenAPI contract: http://localhost:${api_port}/v1/openapi.json"
echo "Health:           http://localhost:${api_port}/health"
echo
echo "Use ./stop-osiel.sh to stop services without deleting data."
