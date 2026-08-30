#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/jalon13_audit.py
pytest -q tests/test_jalon13_readiness.py
git diff --check

echo "JALON13_V1_READINESS_CLOSE=PASS"
