#!/usr/bin/env bash
set -u

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUTDIR="artifacts/jalon3-audit"
OUT="$OUTDIR/jalon3-audit-$STAMP.txt"
TRACKED_DIR="docs/audits/jalon3"
TRACKED_OUT="$TRACKED_DIR/latest.txt"
CONTRACT="docs/jalones/jalon3.md"

mkdir -p "$OUTDIR" "$TRACKED_DIR"
exec > >(tee "$OUT" | tee "$TRACKED_OUT") 2>&1

echo "============================================================"
echo "LEONES — JALÓN 3 AUDIT RUNNER"
echo "============================================================"
echo "UTC: $STAMP"
echo "ROOT: $ROOT"
echo

echo "========== CONTRACT =========="
if [ -f "$CONTRACT" ]; then
    echo "OK: $CONTRACT"
    grep -E '^(\*\*Estado:\*\*|\*\*Fecha:\*\*|\*\*Base:\*\*|\*\*Commit de implementación asociado:\*\*)' "$CONTRACT" || true
else
    echo "ERROR: falta contrato canónico: $CONTRACT"
fi
echo

echo "========== GIT STATUS =========="
git status --short
echo

echo "========== GIT BRANCH =========="
git branch --show-current
echo

echo "========== GIT LOG =========="
git log -5 --oneline --decorate
echo

echo "========== JALÓN 3 FILES =========="
find docs scripts tests artifacts -maxdepth 4 -type f \( -iname '*jalon3*' -o -iname '*measurement*' -o -iname '*benchmark*' \) -print 2>/dev/null | sort
echo

echo "========== DOCUMENTACIÓN CANÓNICA JALÓN 3 =========="
if [ -f "$CONTRACT" ]; then
    wc -l "$CONTRACT"
    echo "--- HEAD ---"
    head -40 "$CONTRACT"
    echo "--- TAIL ---"
    tail -40 "$CONTRACT"
else
    echo "NO EXISTE: $CONTRACT"
fi
echo

echo "========== IMPLEMENTACIÓN =========="
for f in schemas/runtime-benchmark-evidence.v1.1.json scripts/runtime_benchmark_evidence.py tests/test_runtime_benchmark_evidence.py docs/runtime-benchmark-evidence-v1.1.md; do
    if [ -f "$f" ]; then echo "OK: $f"; else echo "MISSING: $f"; fi
done
echo

echo "========== SCRIPTS =========="
find scripts -maxdepth 2 -type f -print 2>/dev/null | sort
echo

echo "========== TESTS =========="
if command -v pytest >/dev/null 2>&1; then
    pytest -q
else
    echo "pytest no disponible"
fi
echo

echo "========== DIFF CHECK =========="
git diff --check
DIFF_CHECK_RC=$?
echo "git diff --check exit code: $DIFF_CHECK_RC"
echo

echo "========== FINAL STATUS =========="
git status --short
echo

echo "============================================================"
echo "AUDIT OUTPUT: $OUT"
echo "TRACKED AUDIT: $TRACKED_OUT"
echo "============================================================"
echo

echo "========== PUBLISH AUDIT =========="
# Runtime artifacts remain ignored. The compact audit mirror is deliberately
# tracked so the complete runner output can be read from Git without copying
# terminal output into chat.
git add "$TRACKED_OUT"

if git diff --cached --quiet; then
    echo "No hay cambios nuevos que commitear."
else
    git commit -m "chore: capture JALON 3 audit"
    git push
fi

echo
echo "========== PUSH RESULT =========="
git status --short
echo "Archivo de auditoría local: $OUT"
echo "Auditoría rastreada: $TRACKED_OUT"

exit "$DIFF_CHECK_RC"
