#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_root}"

[[ -x .venv/bin/python ]] || { echo "Run npm run setup:local first." >&2; exit 69; }
[[ -d node_modules ]] || { echo "Run npm run setup:local first." >&2; exit 69; }

set -a
[[ ! -f .env ]] || source .env
set +a

cleanup() {
  [[ -z "${api_pid:-}" ]] || kill "${api_pid}" 2>/dev/null || true
  [[ -z "${web_pid:-}" ]] || kill "${web_pid}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
api_pid=$!
npm run dev &
web_pid=$!

echo "OSIEL web: http://localhost:3000"
echo "Python API documentation: http://localhost:8000/v1/docs"
wait -n "${api_pid}" "${web_pid}"

