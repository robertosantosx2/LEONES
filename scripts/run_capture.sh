#!/usr/bin/env bash
set -euo pipefail

# LEONES — canonical terminal-output capture runner.
# Usage: ./scripts/run_capture.sh -- <command> [args...]

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

TRACKED_OUT="docs/audits/terminal/latest.txt"
OUTDIR="artifacts/terminal-capture"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUT="$OUTDIR/capture-$STAMP.txt"
LOCKDIR=".git/terminal-capture-runner.lock"

if [ "${1:-}" != "--" ] || [ "$#" -lt 2 ]; then
    echo "Usage: $0 -- <command> [args...]"
    exit 2
fi
shift

BRANCH="$(git branch --show-current)"
[ -n "$BRANCH" ] || { echo "ERROR: detached HEAD"; exit 2; }

mkdir -p "$(dirname "$TRACKED_OUT")" "$OUTDIR"

if ! mkdir "$LOCKDIR" 2>/dev/null; then
    echo "ERROR: another terminal capture runner is active."
    exit 6
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

UNRELATED="$(git status --porcelain --untracked-files=all | awk '
{
    p=substr($0,4)
    if (p != "docs/audits/terminal/latest.txt" &&
        p !~ /^artifacts\/terminal-capture\// &&
        p != "scripts/run_capture.sh") print
}')"

if [ -n "$UNRELATED" ]; then
    echo "ERROR: unrelated working-tree changes; runner stopped."
    echo "$UNRELATED"
    exit 3
fi

git fetch origin "$BRANCH" >/dev/null 2>&1 || {
    echo "ERROR: unable to fetch origin/$BRANCH"
    exit 4
}

REMOTE="origin/$BRANCH"
if ! git merge-base --is-ancestor "$REMOTE" HEAD; then
    git pull --rebase --autostash origin "$BRANCH"
fi

COMMAND_DISPLAY="$*"

{
    echo "============================================================"
    echo "LEONES — TERMINAL CAPTURE"
    echo "============================================================"
    echo "timestamp_utc=$STAMP"
    echo "branch=$BRANCH"
    echo "commit=$(git rev-parse HEAD)"
    echo "command=$COMMAND_DISPLAY"
    echo "============================================================"
    echo
} > "$OUT"

exec 3>&1 4>&2

set +e
"$@" 2>&1 | tee -a "$OUT"
COMMAND_RC="${PIPESTATUS[0]}"
set -e

# CRITICAL: output capture is stopped before Git touches the snapshot.
exec 1>&3 2>&4

{
    echo
    echo "============================================================"
    echo "LEONES — CAPTURE RESULT"
    echo "============================================================"
    echo "command_exit_code=$COMMAND_RC"
    echo "full_local_capture=$OUT"
    echo "tracked_snapshot=$TRACKED_OUT"
    echo "============================================================"
} >> "$OUT"

cp "$OUT" "$TRACKED_OUT"

git add -f "$TRACKED_OUT"

if ! git diff --cached --quiet; then
    git commit -m "chore: capture terminal output"
fi

PUSH_RC=0
for attempt in 1 2 3; do
    if git push origin "$BRANCH"; then
        echo "PASS: push succeeded (attempt $attempt)"
        break
    fi

    if [ "$attempt" -eq 3 ]; then
        echo "ERROR: push failed after 3 attempts; no force-push."
        PUSH_RC=50
        break
    fi

    git fetch origin "$BRANCH"
    git pull --rebase --autostash origin "$BRANCH"
done

echo "============================================================"
echo "LEONES — TERMINAL CAPTURE FINAL"
echo "============================================================"
echo "COMMAND_EXIT_CODE=$COMMAND_RC"
echo "PUSH_EXIT_CODE=$PUSH_RC"
echo "tracked_snapshot=$TRACKED_OUT"
git status --short

[ "$PUSH_RC" -eq 0 ] || exit "$PUSH_RC"
exit "$COMMAND_RC"
