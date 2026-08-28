#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail() { echo "ERROR: $*" >&2; exit 1; }

git diff --quiet || fail "unrelated working-tree changes; runner stopped."

echo "============================================================"
echo "LEONES — JALÓN 7 EVIDENCE PUBLICATION GATE"
echo "============================================================"
echo "UTC: $(date -u +%Y%m%dT%H%M%SZ)"
echo "BRANCH: $(git branch --show-current)"

echo "========== CONTRACT =========="
for path in \
  docs/jalones/jalon7.md \
  scripts/validate_measured_benchmark.py \
  scripts/promote_measured_benchmark.py \
  scripts/publish_measured_benchmark.py \
  tests/test_validate_measured_benchmark.py \
  tests/test_promote_measured_benchmark.py \
  tests/test_publish_measured_benchmark.py; do
  test -f "$path" || fail "missing canonical component: $path"
done
echo "PASS: canonical publication components present"

echo "========== PUBLICATION TESTS =========="
python -m pytest -q \
  tests/test_validate_measured_benchmark.py \
  tests/test_promote_measured_benchmark.py \
  tests/test_publish_measured_benchmark.py

echo "PASS: validation → promotion → publication"

echo "========== STATIC INVARIANTS =========="
python - <<'PY'
from pathlib import Path

checks = {
    "validator": (Path("scripts/validate_measured_benchmark.py"), "measurement_type"),
    "promoter": (Path("scripts/promote_measured_benchmark.py"), "validate_measured_benchmark"),
    "publisher": (Path("scripts/publish_measured_benchmark.py"), "promote"),
}
for name, (path, token) in checks.items():
    text = path.read_text(encoding="utf-8")
    if token not in text:
        raise SystemExit(f"missing {token} in {name}")
print("PASS: explicit validation/promotion/publication chain")
PY

echo "========== DIFF =========="
git diff --check

echo "PASS: git diff --check"

echo "============================================================"
echo "JALÓN 7 — MACHINE-READABLE RESULT"
echo "CONTRACT_GATE=PASS"
echo "PUBLICATION_GATE=PASS"
echo "INVARIANT_GATE=PASS"
echo "DIFF_GATE=PASS"
echo "JALON7_PUBLICATION_CLOSE=PASS"
echo "AUDIT_EXIT_CODE=0"
echo "============================================================"
