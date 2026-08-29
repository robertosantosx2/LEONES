#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() { echo "ERROR: $*" >&2; exit 1; }

echo "============================================================"
echo "LEONES — JALÓN 10 RECOMMENDATION OUTPUT GATE"
echo "============================================================"

git diff --quiet || fail "unrelated working-tree changes; runner stopped."

PYTHON="${PYTHON:-python}"

 echo "========== CONTRACT =========="
[[ -f docs/jalones/jalon10.md ]] || fail "missing JALÓN 10 contract"
[[ -f schemas/leones-recommendation-output.v1.json ]] || fail "missing output schema"
[[ -f scripts/jalon10_output.py ]] || fail "missing output producer"
echo "PASS: canonical output components present"

echo "========== OUTPUT TESTS =========="
"$PYTHON" -m pytest -q tests/test_jalon10_output.py
 echo "PASS: faithful recommendation output"

echo "========== STATIC INVARIANTS =========="
if grep -R -n -E 'score|ranking_score|estimated_tps|tokens_per_second_estimate' scripts/jalon10_output.py schemas/leones-recommendation-output.v1.json; then
  fail "parallel scoring/measurement field found in JALÓN 10 output layer"
fi
if grep -n -E 'recalcul|reinterpre|score|tokens_per_second' docs/jalones/jalon10.md | grep -v -E 'no puede|no crea|no puede contener|sin reinterpretar|sin crear' >/dev/null; then
  fail "unexpected scoring/measurement logic in JALÓN 10 contract"
fi
echo "PASS: output layer only transports canonical recommendation"

echo "========== DIFF =========="
git diff --check
 echo "PASS: git diff --check"

echo "============================================================"
echo "JALÓN 10 — MACHINE-READABLE RESULT"
echo "CONTRACT_GATE=PASS"
echo "OUTPUT_GATE=PASS"
echo "INVARIANT_GATE=PASS"
echo "DIFF_GATE=PASS"
echo "JALON10_OUTPUT_CLOSE=PASS"
echo "AUDIT_EXIT_CODE=0"
echo "============================================================"
