#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
BRANCH="$(git branch --show-current)"
[ -n "$BRANCH" ] || { echo "ERROR: detached HEAD"; exit 2; }

TRACKED_DIR="docs/audits/jalon6"
TRACKED_OUT="$TRACKED_DIR/latest.txt"
OUTDIR="artifacts/jalon6-audit"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUT="$OUTDIR/jalon6-audit-$STAMP.txt"
LOCKDIR=".git/jalon6-audit-runner.lock"
mkdir -p "$TRACKED_DIR" "$OUTDIR"

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "ERROR: another JALÓN 6 runner appears active"
  exit 6
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

UNRELATED="$(git status --porcelain --untracked-files=all | awk '{p=substr($0,4); if (p != "docs/audits/jalon6/latest.txt" && p !~ /^artifacts\/jalon6-audit\//) print}')"
if [ -n "$UNRELATED" ]; then
  echo "ERROR: unrelated working-tree changes; runner stopped."
  echo "$UNRELATED"
  exit 3
fi

# The audit transcript is written to a timestamped artifact first. We restore
# the normal terminal before copying/committing latest.txt, which makes the
# runner idempotent and guarantees a clean working tree after a successful run.
exec 3>&1 4>&2
exec > >(tee "$OUT") 2>&1
RC=0

echo "============================================================"
echo "LEONES — JALÓN 6 RECOMMENDATION EVIDENCE GATE"
echo "============================================================"
echo "UTC: $STAMP"
echo "BRANCH: $BRANCH"

echo
echo "========== CONTRACT =========="
[ -f docs/jalones/jalon6.md ] || { echo "FAIL: missing JALÓN 6 contract"; RC=1; }
[ -f scripts/validate_recommendation_gate.py ] || { echo "FAIL: missing recommendation gate"; RC=1; }
[ -f scripts/validate_measured_benchmark.py ] || { echo "FAIL: missing measurement boundary"; RC=1; }
[ -f scripts/runtime_feedback_atlas.py ] || { echo "FAIL: missing Atlas feedback bridge"; RC=1; }
[ "$RC" -eq 0 ] && echo "PASS: canonical recommendation/evidence components present"

echo
echo "========== GATE TESTS =========="
python -m pytest -q tests/test_jalon6_recommendation_gate.py || RC=1

echo
echo "========== EXISTING EVIDENCE BOUNDARY TESTS =========="
python -m pytest -q tests/test_validate_measured_benchmark.py tests/test_promote_measured_benchmark.py scripts/test_runtime_feedback_atlas.py || RC=1

echo
echo "========== STATIC INVARIANTS =========="
grep -Fq 'No crea nuevos benchmarks' docs/jalones/jalon6.md || RC=1
grep -Fq 'No inventa ponderaciones' docs/jalones/jalon6.md || RC=1
grep -Fq 'next_action' scripts/validate_recommendation_gate.py || RC=1
[ "$RC" -eq 0 ] && echo "PASS: no parallel benchmark/scoring system introduced"
echo
echo "========== DIFF =========="
git diff --check || RC=1
echo
echo "============================================================"
echo "JALÓN 6 — MACHINE-READABLE RESULT"
echo "============================================================"
echo "CONTRACT_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "GATE_TESTS=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "EVIDENCE_BOUNDARY_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "INVARIANT_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "DIFF_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "JALON6_DECLARATIVE_CLOSE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "AUDIT_EXIT_CODE=$RC"
echo "============================================================"

exec 1>&3 2>&4
cp "$OUT" "$TRACKED_OUT"

git add -f "$TRACKED_OUT"
if ! git diff --cached --quiet; then
  git commit -m "chore: capture JALON 6 audit"
fi

git push origin "$BRANCH"

echo "full_local_audit=$OUT"
echo "tracked_audit=$TRACKED_OUT"
git status --short
exit "$RC"
