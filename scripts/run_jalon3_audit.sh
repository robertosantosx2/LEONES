#!/usr/bin/env bash
set -euo pipefail

# JALÓN 3 — canonical audit runner.
# One command on Ubuntu -> audit -> tracked latest.txt -> Git push.
# The runner never declares operational closure unless a real llama.cpp
# evidence artifact satisfies the canonical v1.1 contract.

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

BRANCH="$(git branch --show-current)"
if [ -z "$BRANCH" ]; then
    echo "ERROR: detached HEAD; runner stopped."
    exit 2
fi

TRACKED_DIR="docs/audits/jalon3"
TRACKED_OUT="$TRACKED_DIR/latest.txt"
OUTDIR="artifacts/jalon3-audit"
CONTRACT="docs/jalones/jalon3.md"
SCHEMA="schemas/runtime-benchmark-evidence.v1.1.json"
EVIDENCE="artifacts/runtime-executions/jalon3-run-001/runtime-benchmark-evidence.json"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUT="$OUTDIR/jalon3-audit-$STAMP.txt"

mkdir -p "$OUTDIR" "$TRACKED_DIR"

# Only runner-owned generated paths may already be dirty.
UNRELATED="$(git status --porcelain --untracked-files=all | grep -vE '^.. (artifacts/jalon3-audit/|docs/audits/jalon3/latest\\.txt$)' || true)"
if [ -n "$UNRELATED" ]; then
    echo "ERROR: unrelated working-tree changes; runner stopped."
    echo "$UNRELATED"
    exit 3
fi

# Never force-push and never silently overwrite a divergent local branch.
git fetch origin "$BRANCH" >/dev/null 2>&1 || {
    echo "ERROR: unable to fetch origin/$BRANCH"
    exit 4
}
if ! git merge-base --is-ancestor HEAD "origin/$BRANCH"; then
    echo "ERROR: local branch is not an ancestor of origin/$BRANCH."
    echo "Synchronize first with: git pull --rebase origin $BRANCH"
    exit 5
fi

# Full transcript -> local artifact + one compact Git-tracked mirror.
exec > >(tee "$OUT" | tee "$TRACKED_OUT") 2>&1

AUDIT_RC=0
CONTRACT_RC=0
TESTS_RC=0
DIFF_RC=0
EVIDENCE_RC=0
REPRO_RC=0

run_contract_gate() {
    echo "========== GATE: CONTRACT =========="
    if [ ! -f "$CONTRACT" ]; then
        echo "FAIL: missing $CONTRACT"
        return 10
    fi
    if [ ! -f "$SCHEMA" ]; then
        echo "FAIL: missing $SCHEMA"
        return 11
    fi
    echo "PASS: canonical contract present"
    grep -E '^(\*\*Estado:\*\*|\*\*Fecha:\*\*|\*\*Base:\*\*|\*\*Commit de implementación asociado:\*\*)' "$CONTRACT" || true
    echo "PASS: v1.1 schema present"
    return 0
}

run_tests_gate() {
    echo "========== GATE: TESTS =========="
    if ! command -v pytest >/dev/null 2>&1; then
        echo "FAIL: pytest unavailable"
        return 20
    fi
    pytest -q
    rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "PASS: pytest"
    else
        echo "FAIL: pytest exit=$rc"
    fi
    return "$rc"
}

run_diff_gate() {
    echo "========== GATE: DIFF =========="
    git diff --check
    rc=$?
    if [ "$rc" -eq 0 ]; then echo "PASS: git diff --check"; else echo "FAIL: git diff --check"; fi
    return "$rc"
}

run_evidence_gate() {
    echo "========== GATE: REAL RUNTIME EVIDENCE =========="
    if [ ! -f "$EVIDENCE" ]; then
        echo "FAIL: missing $EVIDENCE"
        return 60
    fi

    python - "$EVIDENCE" "$SCHEMA" <<'PY'
import hashlib
import json
import pathlib
import sys

p = pathlib.Path(sys.argv[1])
schema_path = pathlib.Path(sys.argv[2])
data = json.loads(p.read_text(encoding="utf-8"))
schema = json.loads(schema_path.read_text(encoding="utf-8"))
errors = []

for key in schema["required"]:
    if key not in data:
        errors.append(f"missing:{key}")

if data.get("schema") != "runtime-benchmark-evidence.v1.1":
    errors.append("schema_mismatch")

checks = {
    "model": ["id", "name", "revision", "quantization", "context_length"],
    "protocol": ["prompt_protocol_id", "warmup_iterations", "measurement_iterations"],
    "runtime": ["name", "version", "command"],
    "hardware": ["os", "cpu", "ram_total_mb"],
    "artifact": ["path", "sha256", "size"],
    "process": ["exit_code"],
}
for section, keys in checks.items():
    obj = data.get(section)
    if not isinstance(obj, dict):
        errors.append(f"invalid:{section}")
        continue
    for key in keys:
        if key not in obj:
            errors.append(f"missing:{section}.{key}")

model = data.get("model", {})
runtime = data.get("runtime", {})
protocol = data.get("protocol", {})
process = data.get("process", {})
measurements = data.get("measurements")
artifact = data.get("artifact", {})

if runtime.get("name") != "llama.cpp":
    errors.append(f"runtime_not_llama_cpp:{runtime.get('name')}")
if not str(runtime.get("version", "")).strip():
    errors.append("runtime_version_empty")
if not isinstance(runtime.get("command"), list) or not runtime.get("command"):
    errors.append("runtime_command_empty")
if not str(data.get("execution_id", "")).strip():
    errors.append("execution_id_empty")
if not str(model.get("revision", "")).strip():
    errors.append("model_revision_empty")
if not str(model.get("quantization", "")).strip():
    errors.append("quantization_empty")

if not isinstance(measurements, list) or not measurements:
    errors.append("measurements_empty")
else:
    declared = protocol.get("measurement_iterations")
    if declared != len(measurements):
        errors.append(f"measurement_count_mismatch:{declared}!={len(measurements)}")
    for i, m in enumerate(measurements, 1):
        for key in ["iteration", "exit_code", "total_time_ms", "stdout", "stderr"]:
            if key not in m:
                errors.append(f"measurement_{i}_missing:{key}")
        if m.get("exit_code") != 0:
            errors.append(f"measurement_{i}_exit_code:{m.get('exit_code')}")
        if not isinstance(m.get("stdout"), str):
            errors.append(f"measurement_{i}_stdout_not_string")
        if not isinstance(m.get("stderr"), str):
            errors.append(f"measurement_{i}_stderr_not_string")

if process.get("exit_code") != 0:
    errors.append(f"process_exit_code:{process.get('exit_code')}")

artifact_path = pathlib.Path(str(artifact.get("path", "")))
if artifact_path.is_file():
    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if artifact.get("sha256") != digest:
        errors.append("artifact_sha256_mismatch")
    if artifact.get("size") != artifact_path.stat().st_size:
        errors.append("artifact_size_mismatch")
else:
    errors.append(f"artifact_missing_local:{artifact_path}")

print(f"execution_id={data.get('execution_id')}")
print(f"model={model.get('id')} name={model.get('name')}")
print(f"quantization={model.get('quantization')}")
print(f"runtime={runtime.get('name')} version={runtime.get('version')}")
print(f"warmup_iterations={protocol.get('warmup_iterations')}")
print(f"measurement_iterations_declared={protocol.get('measurement_iterations')}")
print(f"measurement_iterations_found={len(measurements) if isinstance(measurements,list) else 0}")
print(f"process_exit_code={process.get('exit_code')}")
print(f"artifact={artifact.get('path')}")
print(f"artifact_sha256={artifact.get('sha256')}")

if errors:
    print("FAIL: evidence contract / physical execution gate")
    for error in errors:
        print(f"ERROR:{error}")
    raise SystemExit(60)

print("PASS: runtime-benchmark-evidence.v1.1")
print("PASS: real runtime = llama.cpp")
print("PASS: measurements and stdout/stderr preserved")
print("PASS: artifact hash/size verified")
PY
    return $?
}

run_repro_gate() {
    echo "========== GATE: REPRODUCIBILITY =========="
    if [ ! -f "$EVIDENCE" ]; then
        echo "FAIL: no evidence to inspect"
        return 70
    fi
    python - "$EVIDENCE" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
errors=[]
for key in ("execution_id", "timestamp_start", "timestamp_end"):
    if not str(d.get(key, "")).strip(): errors.append(f"missing:{key}")
for section, keys in {
    "model": ("id", "revision", "quantization", "context_length"),
    "protocol": ("prompt_protocol_id", "warmup_iterations", "measurement_iterations"),
    "runtime": ("name", "version", "command"),
    "hardware": ("os", "cpu", "ram_total_mb"),
}.items():
    obj=d.get(section,{})
    for key in keys:
        if key not in obj or obj[key] in (None, "", []): errors.append(f"missing_or_empty:{section}.{key}")
if errors:
    print("FAIL: reproducibility identity incomplete")
    for e in errors: print(f"ERROR:{e}")
    raise SystemExit(70)
print("PASS: execution identity, timestamps, model, protocol, runtime and hardware present")
PY
    return $?
}

run_contract_gate || CONTRACT_RC=$?
run_tests_gate || TESTS_RC=$?
run_diff_gate || DIFF_RC=$?
run_evidence_gate || EVIDENCE_RC=$?
run_repro_gate || REPRO_RC=$?

if [ "$CONTRACT_RC" -eq 0 ] && [ "$TESTS_RC" -eq 0 ] && [ "$DIFF_RC" -eq 0 ] && [ "$EVIDENCE_RC" -eq 0 ] && [ "$REPRO_RC" -eq 0 ]; then
    AUDIT_RC=0
else
    AUDIT_RC=1
fi

echo
echo "============================================================"
echo "JALÓN 3 — MACHINE-READABLE RESULT"
echo "============================================================"
printf 'CONTRACT_GATE=%s\n' "$( [ "$CONTRACT_RC" -eq 0 ] && echo PASS || echo FAIL )"
printf 'TESTS_GATE=%s\n' "$( [ "$TESTS_RC" -eq 0 ] && echo PASS || echo FAIL )"
printf 'DIFF_GATE=%s\n' "$( [ "$DIFF_RC" -eq 0 ] && echo PASS || echo FAIL )"
printf 'REAL_RUNTIME_EVIDENCE_GATE=%s\n' "$( [ "$EVIDENCE_RC" -eq 0 ] && echo PASS || echo FAIL )"
printf 'REPRODUCIBILITY_GATE=%s\n' "$( [ "$REPRO_RC" -eq 0 ] && echo PASS || echo FAIL )"
printf 'JALON3_OPERATIONAL_CLOSE=%s\n' "$( [ "$AUDIT_RC" -eq 0 ] && echo PASS || echo FAIL )"
printf 'AUDIT_EXIT_CODE=%s\n' "$AUDIT_RC"
echo "============================================================"

# Publish the tracked mirror even on FAIL, so a failed audit is remotely
# inspectable without copying terminal output into chat.
git add -f "$TRACKED_OUT"
if git diff --cached --quiet; then
    echo "No new tracked audit changes."
else
    git commit -m "chore: capture JALON 3 audit"
fi

echo "========== PUSH =========="
if ! git push origin "$BRANCH"; then
    echo "ERROR: push failed; no force-push attempted."
    [ "$AUDIT_RC" -eq 0 ] && AUDIT_RC=50
fi

echo "========== FINAL =========="
echo "JALON3_OPERATIONAL_CLOSE=$([ "$AUDIT_RC" -eq 0 ] && echo PASS || echo FAIL)"
echo "full_local_audit=$OUT"
echo "tracked_audit=$TRACKED_OUT"
git status --short
exit "$AUDIT_RC"
