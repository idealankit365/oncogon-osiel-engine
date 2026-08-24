#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${project_root}"

if [[ "${1:-}" == "--purge" ]]; then
  echo "Refusing unattended data deletion. Run 'docker compose down' normally, or manually run"
  echo "'docker compose down --volumes' only after backing up the OSIEL volumes."
  exit 64
fi

docker compose --profile ai --profile future-infra down
echo "OSIEL stopped. Persistent database, objects and model cache were retained."
