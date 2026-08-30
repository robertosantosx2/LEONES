#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python - <<'PY'
from pathlib import Path
required = [
    "docs/jalones/jalon11.md",
    "schemas/leones-e2e-operation.v1.json",
    "scripts/jalon11_e2e.py",
    "tests/test_jalon11_e2e.py",
    "scripts/jalon9_recommend.py",
    "scripts/jalon10_output.py",
    "scripts/runtime_evidence_bridge.py",
]
missing = [p for p in required if not Path(p).is_file()]
if missing:
    raise SystemExit("ERROR: missing canonical E2E component(s): " + ", ".join(missing))
print("PASS: canonical E2E components present")
PY

pytest -q tests/test_jalon11_e2e.py

python - <<'PY'
import importlib.util
from pathlib import Path

path = Path("scripts/jalon11_e2e.py")
spec = importlib.util.spec_from_file_location("jalon11_e2e", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

refs = {
    "selection_ref": "selection-1",
    "runtime_ref": "runtime-1",
    "execution_ref": "execution-1",
    "measurement_ref": "measurement-1",
    "evidence_refs": ["evidence-1"],
    "decision_ref": "decision-1",
    "recommendation_ref": "recommendation-1",
    "publication_ref": "publication-1",
    "output_ref": "output-1",
    "trace_ref": "trace-1",
}
result = module.build("audit-operation", refs, "planned")
forbidden = set(module.FORBIDDEN)
leaked = forbidden.intersection(result)
if leaked:
    raise SystemExit(f"ERROR: generated E2E operation contains forbidden scoring/measurement fields: {sorted(leaked)}")
print("PASS: generated E2E operation contains no parallel scoring/measurement fields")
print("PASS: E2E layer only transports canonical references")
PY

git diff --check

echo "============================================================"
echo "JALÓN 11 — MACHINE-READABLE RESULT"
echo "============================================================"
echo "CONTRACT_GATE=PASS"
echo "E2E_GATE=PASS"
echo "INVARIANT_GATE=PASS"
echo "DIFF_GATE=PASS"
echo "JALON11_E2E_DECLARATIVE_CLOSE=PASS"
echo "AUDIT_EXIT_CODE=0"
echo "============================================================"
