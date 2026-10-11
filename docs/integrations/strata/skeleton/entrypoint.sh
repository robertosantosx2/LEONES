#!/usr/bin/env bash
# ODS Strata service entrypoint (skeleton for PR C)
# Copy to: extensions/services/strata/entrypoint.sh
#
# Prefer upstream image ENTRYPOINT (docker-entrypoint.sh) when using the
# official/pinned Strata image. Use this wrapper only if ODS needs pre-flight
# checks (envelope, data dir) before exec'ing upstream.

set -euo pipefail

DATA_DIR="${STRATA_DATA_DIR:-/data}"
mkdir -p "${DATA_DIR}"

# Optional: log envelope hints (enforcement belongs in ods enable / host agent)
echo "[ods-strata] data dir: ${DATA_DIR}"
echo "[ods-strata] MODEL=${MODEL:-} FAMILY=${FAMILY:-} CONTEXT=${CONTEXT:-} VISION=${VISION:-}"

# Hand off to upstream entrypoint if present in the image
if [[ -x /opt/strata/docker-entrypoint.sh ]]; then
  exec /opt/strata/docker-entrypoint.sh "$@"
fi

if [[ -x ./docker-entrypoint.sh ]]; then
  exec ./docker-entrypoint.sh "$@"
fi

echo "[ods-strata] ERROR: upstream docker-entrypoint.sh not found" >&2
exit 1
