#!/usr/bin/env bash
set -u

# JALÓN 3 — canonical audit runner.
# Contract: one command on Ubuntu -> complete audit -> tracked latest -> Git push.
# Runtime artifacts stay under artifacts/ and remain ignored; only latest.txt is
# the compact Git-tracked mirror consumed from GitHub.

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

BRANCH="$(git branch --show-current)"
TRACKED_DIR="docs/audits/jalon3"
TRACKED_OUT="$TRACKED_DIR/latest.txt"
OUTDIR="artifacts/jalon3-audit"
CONTRACT="docs/jalones/jalon3.md"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUT="$OUTDIR/jalon3-audit-$STAMP.txt"

mkdir -p "$OUTDIR" "$TRACKED_DIR"

# Refuse to run over unrelated user work. Generated audit artifacts are allowed.
UNRELATED="$(git status --porcelain --untracked-files=all | grep -vE '^.. (artifacts/jalon3-audit/|docs/audits/jalon3/latest\.txt$)' || true)"
if [ -n "$UNRELATED" ]; then
    echo "ERROR: working tree contains unrelated changes; runner stopped."
    echo "$UNRELATED"
    exit 2
fi

# Keep the branch aligned before creating a new audit commit. Never overwrite
# local work and never force-push.
git fetch origin "$BRANCH" >/dev/null 2>&1 || {
    echo "ERROR: unable to fetch origin/$BRANCH"
    exit 3
}
if ! git merge-base --is-ancestor HEAD "origin/$BRANCH"; then
    echo "ERROR: local branch is not an ancestor of origin/$BRANCH."
    echo "Synchronize the branch first (git pull --rebase --ff-only origin $BRANCH)."
    exit 4
fi

# Everything below is simultaneously written to the full local transcript and
# to the single tracked mirror. This avoids terminal-copy/paste entirely.
exec > >(tee "$OUT" | tee "$TRACKED_OUT") 2>&1

AUDIT_RC=0

run_audit() {
    echo "============================================================"
    echo "LEONES — JALÓN 3 AUDIT RUNNER"
    echo "============================================================"
    echo "UTC: $STAMP"
    echo "ROOT: $ROOT"
    echo "BRANCH: $BRANCH"
    echo

    echo "========== CONTRACT =========="
    if [ -f "$CONTRACT" ]; then
        echo "OK: $CONTRACT"
        grep -E '^(\*\*Estado:\*\*|\*\*Fecha:\*\*|\*\*Base:\*\*|\*\*Commit de implementación asociado:\*\*)' "$CONTRACT" || true
    else
        echo "ERROR: missing canonical contract: $CONTRACT"
        return 10
    fi
    echo

    echo "========== GIT BASELINE =========="
    git status --short
    git log -5 --oneline --decorate
    echo

    echo "========== JALÓN 3 FILES =========="
    find docs scripts tests artifacts -maxdepth 4 -type f \
        \( -iname '*jalon3*' -o -iname '*measurement*' -o -iname '*benchmark*' \) \
        -print 2>/dev/null | sort
    echo

    echo "========== CANONICAL DOCUMENTATION =========="
    wc -l "$CONTRACT"
    head -40 "$CONTRACT"
    echo "--- TAIL ---"
    tail -40 "$CONTRACT"
    echo

    echo "========== IMPLEMENTATION =========="
    for f in \
        schemas/runtime-benchmark-evidence.v1.1.json \
        scripts/runtime_benchmark_evidence.py \
        tests/test_runtime_benchmark_evidence.py \
        docs/runtime-benchmark-evidence-v1.1.md; do
        if [ -f "$f" ]; then echo "OK: $f"; else echo "MISSING: $f"; fi
    done
    echo

    echo "========== TESTS =========="
    if command -v pytest >/dev/null 2>&1; then
        pytest -q || return 20
    else
        echo "ERROR: pytest not available"
        return 21
    fi
    echo

    echo "========== DIFF CHECK =========="
    git diff --check || return 30
    echo "git diff --check exit code: 0"
    echo

    echo "========== REAL RUNTIME EVIDENCE DISCOVERY =========="
    for f in artifacts/runtime-executions/jalon3-run-001/runtime-benchmark-evidence.json \
             artifacts/a01-real-runtime-benchmark.v1.json \
             artifacts/llama-cpp-smollm2-135m-real-benchmark.json; do
        if [ -f "$f" ]; then
            echo "FOUND: $f"
        else
            echo "NOT PRESENT: $f"
        fi
    done
    echo

    return 0
}

run_audit || AUDIT_RC=$?

echo "========== AUDIT RESULT =========="
echo "audit_exit_code=$AUDIT_RC"
echo

echo "========== PUBLISH AUDIT =========="
# Only the compact mirror is committed. Full runtime artifacts remain local /
# ignored, preserving repository size and the evidence separation contract.
git add -f "$TRACKED_OUT"
if git diff --cached --quiet; then
    echo "No new tracked audit changes."
else
    git commit -m "chore: capture JALON 3 audit" || AUDIT_RC=40
fi

echo

echo "========== PUSH =========="
if [ "$AUDIT_RC" -eq 0 ]; then
    if ! git push origin "$BRANCH"; then
        echo "ERROR: push failed; no force-push attempted."
        AUDIT_RC=50
    fi
else
    echo "Audit failed; publishing the transcript for diagnosis."
    git push origin "$BRANCH" || AUDIT_RC=51
fi

echo

echo "========== FINAL =========="
echo "audit_exit_code=$AUDIT_RC"
echo "full_local_audit=$OUT"
echo "tracked_audit=$TRACKED_OUT"
git status --short

echo "============================================================"

exit "$AUDIT_RC"
