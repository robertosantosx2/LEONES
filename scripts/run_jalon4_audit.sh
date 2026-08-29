#!/usr/bin/env bash
set -euo pipefail

# JALÓN 4 — canonical runtime taxonomy audit.
# Validates the declarative deployment/serving gate before host execution.
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
BRANCH="$(git branch --show-current)"
[ -n "$BRANCH" ] || { echo "ERROR: detached HEAD"; exit 2; }

TRACKED_DIR="docs/audits/jalon4"
TRACKED_OUT="$TRACKED_DIR/latest.txt"
OUTDIR="artifacts/jalon4-audit"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUT="$OUTDIR/jalon4-audit-$STAMP.txt"
LOCKDIR=".git/jalon4-audit-runner.lock"
mkdir -p "$TRACKED_DIR" "$OUTDIR"

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "ERROR: another JALÓN 4 runner appears active"; exit 6
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

UNRELATED="$(git status --porcelain --untracked-files=all | awk '{p=substr($0,4); if (p != "docs/audits/jalon4/latest.txt" && p !~ /^artifacts\/jalon4-audit\//) print}')"
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

# Save the real terminal streams so the tracked audit is copied only after
# the audit itself is finished. This prevents tee/process-substitution from
# modifying latest.txt while Git is committing it.
exec 3>&1 4>&2
exec > >(tee "$OUT") 2>&1

RC=0

echo "============================================================"
echo "LEONES — JALÓN 4 AUDIT RUNNER"
echo "============================================================"
echo "UTC: $STAMP"
echo "BRANCH: $BRANCH"
echo
echo "========== CONTRACT =========="
if [ -f docs/jalones/jalon4.md ] && [ -f runtime_registry.v1.1.json ]; then
  echo "PASS: JALÓN 4 contract and runtime registry present"
else
  echo "FAIL: JALÓN 4 contract or registry missing"; RC=1
fi

echo
echo "========== TAXONOMY TESTS =========="
pytest -q tests/test_jalon4_runtime_taxonomy.py || RC=1

echo
echo "========== ADAPTER/STACK CONTRACT TESTS =========="
pytest -q tests/test_external_stack_contract.py tests/test_ods_magnitude_adapters.py tests/test_ods_magnitude_benchmark_bridge.py tests/test_ods_magnitude_evidence.py || RC=1

echo
echo "========== DIFF =========="
git diff --check || RC=1
echo
echo "============================================================"
echo "JALÓN 4 — MACHINE-READABLE RESULT"
echo "============================================================"
echo "CONTRACT_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "TAXONOMY_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "ADAPTER_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "DIFF_GATE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "JALON4_DECLARATIVE_CLOSE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "AUDIT_EXIT_CODE=$RC"
echo "============================================================"

# Stop recording before touching Git. latest.txt is therefore a stable
# snapshot of the audit, not a file that changes during its own commit.
exec 1>&3 2>&4
cp "$OUT" "$TRACKED_OUT"

git add -f "$TRACKED_OUT"
if ! git diff --cached --quiet; then
  git commit -m "chore: capture JALON 4 audit"
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
echo "JALON4_DECLARATIVE_CLOSE=$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "full_local_audit=$OUT"
echo "tracked_audit=$TRACKED_OUT"
git status --short
exit "$RC"
