#!/usr/bin/env bash
set -euo pipefail

# LEONES wrapper: preflight first, then explicit consent, then invoke the
# upstream ODS installer. No telemetry or Atlas upload is performed here.

python3 scripts/integrations/ods_preflight.py
printf '\nThis will install ODS and may download Docker images/models. Continue? [y/N] '
read -r answer
[[ "$answer" =~ ^[Yy]$ ]] || { echo "Installation cancelled."; exit 0; }

: "${ODS_REF:=main}"
if [[ "$ODS_REF" == "main" ]]; then
  echo "WARNING: ODS_REF=main is not reproducible. Set ODS_REF to a release/tag/commit for a pinned install."
fi

if [[ "$ODS_REF" == "main" ]]; then
  curl -fsSL https://install.osmantic.com/ods.sh | bash
else
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT
  git clone --depth 1 --branch "$ODS_REF" https://github.com/Osmantic/ODS.git "$tmpdir/ODS"
  (cd "$tmpdir/ODS/ods" && ./install.sh)
fi
