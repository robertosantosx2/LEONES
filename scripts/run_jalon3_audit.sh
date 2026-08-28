#!/usr/bin/env bash
set -u

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUTDIR="artifacts/jalon3-audit"
OUT="$OUTDIR/jalon3-audit-$STAMP.txt"

mkdir -p "$OUTDIR"

exec > >(tee "$OUT") 2>&1

echo "============================================================"
echo "LEONES — JALÓN 3 AUDIT RUNNER"
echo "============================================================"
echo "UTC: $STAMP"
echo "ROOT: $ROOT"
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
find docs scripts tests artifacts \
  -maxdepth 4 \
  -type f \
  \( -iname '*jalon3*' -o -iname '*measurement*' -o -iname '*benchmark*' \) \
  -print 2>/dev/null | sort
echo

echo "========== DOCUMENTACIÓN JALÓN 3 =========="
if [ -f docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md ]; then
    wc -l docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md
    echo "--- HEAD ---"
    head -40 docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md
    echo "--- TAIL ---"
    tail -40 docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md
else
    echo "NO EXISTE: docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md"
fi
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
echo

echo "========== FINAL STATUS =========="
git status --short
echo

echo "============================================================"
echo "AUDIT OUTPUT: $OUT"
echo "============================================================"

git add "$OUT"

if git diff --cached --quiet; then
    echo "No hay cambios nuevos que commitear."
else
    git commit -m "chore: capture JALON 3 audit"
    git push
fi

echo
echo "========== PUSH RESULT =========="
git status --short
echo "Archivo de auditoría: $OUT"
