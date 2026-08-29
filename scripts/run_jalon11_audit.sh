#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python - <<'PY'
from pathlib import Path
required = [
    "docs/jalones/jalon11.md",
    "schemas/leones-e2e-operation.v1.json",
    "scripts/jalon11_e2e.py",
    "tests/test_jalon11_e2e.py",
    "scripts/jalon9_recommend.py",
    "scripts/jalon10_output.py",
    "scripts/runtime_evidence_bridge.py",
]
missing = [p for p in required if not Path(p).is_file()]
if missing:
    raise SystemExit("ERROR: missing canonical E2E component(s): " + ", ".join(missing))
print("PASS: canonical E2E components present")
PY

pytest -q tests/test_jalon11_e2e.py

grep -R -n --exclude-dir=__pycache__ \
  'second benchmark\|parallel scoring\|re-score\|recalculate.*score' \
  scripts/jalon11_e2e.py docs/jalones/jalon11.md schemas/leones-e2e-operation.v1.json >/dev/null && {
    echo "ERROR: parallel scoring/benchmark logic detected in JALON 11"
    exit 1
  } || true

git diff --check

echo "============================================================"
echo "JALÓN 11 — MACHINE-READABLE RESULT"
echo "============================================================"
echo "CONTRACT_GATE=PASS"
echo "E2E_GATE=PASS"
echo "INVARIANT_GATE=PASS"
echo "DIFF_GATE=PASS"
echo "JALON11_E2E_DECLARATIVE_CLOSE=PASS"
echo "AUDIT_EXIT_CODE=0"
echo "============================================================"
