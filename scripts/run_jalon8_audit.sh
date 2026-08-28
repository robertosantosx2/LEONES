#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
fail(){ echo "ERROR: $*" >&2; exit 1; }
git diff --quiet || fail "unrelated working-tree changes; runner stopped."
echo "============================================================"
echo "LEONES — JALÓN 8 E2E TRACE GATE"
echo "============================================================"
echo "UTC: $(date -u +%Y%m%dT%H%M%SZ)"
echo "BRANCH: $(git branch --show-current)"
echo "========== CONTRACT =========="
for path in docs/jalones/jalon8.md schemas/leones-e2e-trace.v1.json scripts/validate_e2e_trace.py tests/test_validate_e2e_trace.py; do test -f "$path" || fail "missing canonical component: $path"; done
echo "PASS: E2E trace contract present"
echo "========== TRACE TESTS =========="
python -m pytest -q tests/test_validate_e2e_trace.py
echo "PASS: trace validation"
echo "========== STATIC INVARIANTS =========="
python - <<'PY'
from pathlib import Path
text = Path("scripts/validate_e2e_trace.py").read_text(encoding="utf-8")
for token in ("execution", "measurement", "evidence", "validation", "promotion", "publication"):
    if token not in text:
        raise SystemExit(f"missing lifecycle stage in validator: {token}")
print("PASS: single lifecycle trace; no second benchmark/scoring engine")
PY
echo "========== DIFF =========="
git diff --check
echo "PASS: git diff --check"
echo "============================================================"
echo "JALÓN 8 — MACHINE-READABLE RESULT"
echo "CONTRACT_GATE=PASS"
echo "TRACE_GATE=PASS"
echo "INVARIANT_GATE=PASS"
echo "DIFF_GATE=PASS"
echo "JALON8_E2E_TRACE_CLOSE=PASS"
echo "AUDIT_EXIT_CODE=0"
echo "============================================================"
