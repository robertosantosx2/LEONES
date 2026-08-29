#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
BRANCH="$(git branch --show-current)"
[ -n "$BRANCH" ] || { echo "ERROR: detached HEAD"; exit 2; }

TRACKED_DIR="docs/audits/jalon5"
TRACKED_OUT="$TRACKED_DIR/latest.txt"
OUTDIR="artifacts/jalon5-audit"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUT="$OUTDIR/jalon5-audit-$STAMP.txt"
LOCKDIR=".git/jalon5-audit-runner.lock"
mkdir -p "$TRACKED_DIR" "$OUTDIR"

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "ERROR: another JALÓN 5 runner appears active"; exit 6
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

UNRELATED="$(git status --porcelain --untracked-files=all | awk '{p=substr($0,4); if (p != "docs/audits/jalon5/latest.txt" && p !~ /^artifacts\/jalon5-audit\//) print}')"
if [ -n "$UNRELATED" ]; then
  echo "ERROR: unrelated working-tree changes; runner stopped."
  echo "$UNRELATED"
  exit 3
fi

git fetch origin "$BRANCH" >/dev/null 2>&1 || { echo "ERROR: fetch failed"; exit 4; }
REMOTE="origin/$BRANCH"
if git merge-base --is-ancestor "$REMOTE" HEAD; then
  echo "SYNC: local branch is equal to or ahead of $REMOTE."
elif git merge-base --is-ancestor HEAD "$REMOTE"; then
  git pull --rebase --autostash origin "$BRANCH"
else
  git pull --rebase --autostash origin "$BRANCH"
fi

# Keep the terminal transcript in the immutable local audit file. The tracked
# mirror is copied only after the audit finishes, so Git never commits a file
# that is still being written by tee.
exec 3>&1 4>&2
exec > >(tee "$OUT") 2>&1
RC=0

echo "============================================================"
echo "LEONES — JALÓN 5 AUDIT RUNNER"
echo "============================================================"
echo "UTC: $STAMP"
echo "BRANCH: $BRANCH"
echo
echo "========== CONTRACT =========="
[ -f docs/jalones/jalon5.md ] && [ -f schemas/leones-ods-magnitude-decision.v1.json ] && echo "PASS: JALÓN 5 contract and schema present" || { echo "FAIL: JALÓN 5 contract/schema missing"; RC=1; }

echo
echo "========== DECISION CONTRACT TESTS =========="
pytest -q tests/test_jalon5_decision_contract.py || RC=1

echo
echo "========== EXISTING SELECTOR/INTEGRATION TESTS =========="
pytest -q tests/test_ods_magnitude_benchmark_bridge.py tests/test_promote_measured_benchmark.py tests/test_publish_measured_benchmark.py || RC=1

echo
echo "========== DIFF =========="
git diff --check || RC=1
echo
echo "============================================================"
echo "JALÓN 5 — MACHINE-READABLE RESULT"
echo "============================================================"
echo "CONTRACT_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "DECISION_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "INTEGRATION_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "DIFF_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "JALON5_CONTRACT_CLOSE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "AUDIT_EXIT_CODE=$RC"
echo "============================================================"

exec 1>&3 2>&4
cp "$OUT" "$TRACKED_OUT"

git add -f "$TRACKED_OUT"
if ! git diff --cached --quiet; then
  git commit -m "chore: capture JALON 5 audit"
fi

PUSH_RC=0
for attempt in 1 2 3; do
  if git push origin "$BRANCH"; then
    echo "PASS: push succeeded (attempt $attempt)"
    break
  fi
  if [ "$attempt" -eq 3 ]; then PUSH_RC=50; break; fi
  git fetch origin "$BRANCH"
  git pull --rebase --autostash origin "$BRANCH"
done

[ "$RC" -eq 0 ] && [ "$PUSH_RC" -eq 0 ] || RC=1
echo "JALON5_CONTRACT_CLOSE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "full_local_audit=$OUT"
echo "tracked_audit=$TRACKED_OUT"
git status --short
exit "$RC"
