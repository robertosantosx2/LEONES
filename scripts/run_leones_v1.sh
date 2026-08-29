#!/usr/bin/env bash
set -euo pipefail

# LEONES V1 — simple front door for a person who is not a programmer.
#
# This launcher deliberately does not implement recommendation or benchmarking.
# It calls the canonical Python entry point so that there is only one source of
# truth. The first useful operation is a host preflight.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: Python 3 is required."
  exit 2
fi

cd "$ROOT"
exec "$PYTHON" scripts/leones_v1.py preflight --pretty
