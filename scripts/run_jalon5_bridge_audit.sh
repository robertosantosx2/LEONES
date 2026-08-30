#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() { echo "FAIL: $*"; exit 1; }

echo "============================================================"
echo "LEONES — JALÓN 5 DECISION BRIDGE AUDIT RUNNER"
echo "============================================================"
echo "========== CONTRACT =========="
[[ -f docs/jalones/jalon5.md ]] || fail "missing JALON 5 contract"
[[ -f schemas/leones-ods-magnitude-decision.v1.json ]] || fail "missing decision schema"
[[ -f scripts/ods_magnitude_decision.py ]] || fail "missing decision bridge"
echo "PASS: contract, schema and bridge present"
echo "========== BRIDGE TESTS =========="
python -m pytest -q tests/test_jalon5_decision_contract.py tests/test_jalon5_decision_bridge.py
echo "========== STATIC INVARIANTS =========="
grep -Fq 'estimate_only: true' docs/jalones/jalon5.md || fail "LLMFit estimate-only rule missing"
grep -Fq 'BENCHMARK_REQUIRED' docs/jalones/jalon5.md || fail "benchmark escalation rule missing"
grep -Fq 'selector LEONES' docs/jalones/jalon5.md || fail "selector authority rule missing"
echo "PASS: external signals remain distinct from measured evidence"
echo "========== DIFF =========="
git diff --check
echo "PASS: git diff --check"
echo "============================================================"
echo "JALÓN 5 — MACHINE-READABLE RESULT"
echo "CONTRACT_GATE=PASS"
echo "BRIDGE_GATE=PASS"
echo "INVARIANT_GATE=PASS"
echo "DIFF_GATE=PASS"
echo "JALON5_DECISION_BRIDGE_CLOSE=PASS"
echo "AUDIT_EXIT_CODE=0"
echo "============================================================"
