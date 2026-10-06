#!/usr/bin/env bash
set -euo pipefail

api_url="${NEXT_PUBLIC_OSIEL_API_URL:-http://localhost:8000}"
web_url="${OSIEL_WEB_URL:-http://localhost:${OSIEL_WEB_PORT:-3000}}"
command -v curl >/dev/null || { echo 'curl is required for the showcase smoke test.' >&2; exit 69; }
for path in /health /v1/system/capabilities /v1/system/readiness /v1/compounds /v1/models /v1/audit /v1/experiments /v1/literature; do
  code="$(curl --noproxy '*' -sS -o /dev/null -w '%{http_code}' --max-time 15 "${api_url%/}${path}")"
  if [[ "$code" != 200 ]]; then echo "FAIL ${path}: HTTP ${code}" >&2; exit 1; fi
  echo "PASS ${path}"
done
code="$(curl --noproxy '*' -sS -o /dev/null -w '%{http_code}' --max-time 15 "${web_url%/}/")"
if [[ "$code" != 200 ]]; then echo "FAIL frontend /: HTTP ${code}" >&2; exit 1; fi
echo 'PASS frontend /'
