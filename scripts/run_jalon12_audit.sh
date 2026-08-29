#!/usr/bin/env bash
set -euo pipefail

# JALÓN 12 audit: prove that the user-facing V1 entrypoint is real,
# documented and still delegates to the canonical contracts.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/jalon12_audit.py
pytest -q tests/test_jalon12_v1_entrypoint.py tests/test_leones_v1_launcher.py

git diff --check

echo "JALON12_V1_ENTRYPOINT_CLOSE=PASS"
