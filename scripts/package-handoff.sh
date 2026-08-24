#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_path="${1:-${project_root}/deliverables/Oncogon_OSIEL_Developer_Handoff.zip}"
if [[ "${output_path}" != /* ]]; then
  output_path="${project_root}/${output_path}"
fi
temporary_dir="$(mktemp -d)"
trap 'rm -rf "${temporary_dir}"' EXIT

mkdir -p "${temporary_dir}/oncogon-osiel-engine"
(
  cd "${project_root}"
  git ls-files --cached --others --exclude-standard -z \
    | tar --null -T - -cf - \
    | tar -xf - -C "${temporary_dir}/oncogon-osiel-engine"
)

(
  cd "${temporary_dir}/oncogon-osiel-engine"
  find . -type f -print0 | sort -z | xargs -0 sha256sum > SOURCE_MANIFEST.sha256
)

mkdir -p "$(dirname "${output_path}")"
(
  cd "${temporary_dir}"
  zip -qr "${output_path}" oncogon-osiel-engine
)
sha256sum "${output_path}" > "${output_path}.sha256"
echo "Created ${output_path}"
echo "Created ${output_path}.sha256"
