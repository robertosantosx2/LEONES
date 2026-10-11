#!/usr/bin/env bash
# ODS Strata service entrypoint (skeleton for PR C in Osmantic/ODS)
# Copy to: extensions/services/strata/entrypoint.sh
# Prefer upstream image ENTRYPOINT when using a pinned Strata image.

set -euo pipefail

DATA_DIR="${STRATA_DATA_DIR:-/data}"
mkdir -p "${DATA_DIR}"

echo "[ods-strata] data dir: ${DATA_DIR}"
echo "[ods-strata] MODEL=${MODEL:-} FAMILY=${FAMILY:-} CONTEXT=${CONTEXT:-} VISION=${VISION:-}"

if [[ -x /opt/strata/docker-entrypoint.sh ]]; then
  exec /opt/strata/docker-entrypoint.sh "$@"
fi

if [[ -x ./docker-entrypoint.sh ]]; then
  exec ./docker-entrypoint.sh "$@"
fi

echo "[ods-strata] ERROR: upstream docker-entrypoint.sh not found" >&2
exit 1
