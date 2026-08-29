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
# The producer intentionally mentions forbidden field names in its guard set.
# Inspect the actual generated output instead of grepping the implementation,
# which would create a false positive against that guard itself.
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
cat > "$TMP_DIR/recommendation.json" <<'JSON'
{
  "recommendation_id": "audit-jalon10",
  "entity": "audit-model",
  "decision_ref": "audit-decision",
  "evidence_refs": ["audit-evidence"],
  "status": "recommend",
  "rationale": "audit fixture",
  "unknowns": [],
  "next_action": "continue"
}
JSON
"$PYTHON" scripts/jalon10_output.py "$TMP_DIR/recommendation.json" "$TMP_DIR/output.json" >/dev/null
"$PYTHON" - "$TMP_DIR/output.json" <<'PY'
import json, sys
forbidden = {"score", "ranking_score", "estimated_tps", "tokens_per_second_estimate"}
out = json.load(open(sys.argv[1], encoding="utf-8"))
leaked = forbidden.intersection(out)
if leaked:
    print(f"ERROR: parallel scoring/measurement field found in generated JALÓN 10 output: {sorted(leaked)}", file=sys.stderr)
    raise SystemExit(1)
print("PASS: generated output contains no parallel scoring/measurement fields")
PY
if grep -n -E 'recalcul|reinterpre|tokens_per_second' docs/jalones/jalon10.md | grep -v -E 'no puede|no crea|no puede contener|sin reinterpretar|sin crear' >/dev/null; then
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
