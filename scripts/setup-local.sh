#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_root}"

command -v node >/dev/null || { echo "Node.js 22.13+ is required." >&2; exit 69; }
command -v npm >/dev/null || { echo "npm is required." >&2; exit 69; }
command -v python3 >/dev/null || { echo "Python 3.12+ is required." >&2; exit 69; }

node_major="$(node -p 'process.versions.node.split(".")[0]')"
python_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if (( node_major < 22 )); then echo "Node.js 22.13+ is required; found $(node -v)." >&2; exit 69; fi
if [[ "${python_version}" != "3.12" && "${python_version}" != "3.13" ]]; then
  echo "Python 3.12 or 3.13 is required; found ${python_version}." >&2
  exit 69
fi

if [[ ! -f .env ]]; then cp .env.example .env; fi
npm ci --cache "${project_root}/.npm-cache"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements-test.txt

echo "OSIEL setup complete. Run: npm run run:local"
