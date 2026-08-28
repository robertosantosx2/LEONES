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
EVIDENCE="artifacts/runtime-executions/jalon3-run-001/runtime-benchmark-evidence.json"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUT="$OUTDIR/jalon3-audit-$STAMP.txt"

mkdir -p "$OUTDIR" "$TRACKED_DIR"

# Refuse to run over unrelated user work. Generated audit artifacts are allowed.
UNRELATED="$(git status --porcelain --untracked-files=all | grep -vE '^.. (artifacts/jalon3-audit/|docs/audits/jalon3/latest\\.txt$)' || true)"
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
        grep -E '^(\\*\\*Estado:\\*\\*|\\*\\*Fecha:\\*\\*|\\*\\*Base:\\*\\*|\\*\\*Commit de implementación asociado:\\*\\*)' "$CONTRACT" || true
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

    echo "========== REAL RUNTIME EVIDENCE AUDIT =========="
    if [ -f "$EVIDENCE" ]; then
        echo "FOUND: $EVIDENCE"
        python - "$EVIDENCE" <<'PY'
import hashlib, json, pathlib, sys

p = pathlib.Path(sys.argv[1])
data = json.loads(p.read_text(encoding="utf-8"))
errors = []

required = ["schema", "execution_id", "timestamp_start", "timestamp_end", "model", "protocol", "runtime", "hardware", "measurements", "process", "artifact"]
for k in required:
    if k not in data:
        errors.append(f"missing:{k}")

if data.get("schema") != "runtime-benchmark-evidence.v1.1":
    errors.append("schema_mismatch")

for obj, keys in {
    "model": ["id", "name", "revision", "quantization", "context_length"],
    "protocol": ["prompt_protocol_id", "warmup_iterations", "measurement_iterations"],
    "runtime": ["name", "version", "command"],
    "hardware": ["os", "cpu", "ram_total_mb"],
    "artifact": ["path", "sha256", "size"],
}.items():
    section = data.get(obj, {})
    if isinstance(section, dict):
        for k in keys:
            if k not in section:
                errors.append(f"missing:{obj}.{k}")
    else:
        errors.append(f"invalid:{obj}")

measurements = data.get("measurements", [])
if not isinstance(measurements, list) or not measurements:
    errors.append("measurements_empty")
else:
    for i, m in enumerate(measurements, 1):
        for k in ["iteration", "exit_code", "total_time_ms", "stdout", "stderr"]:
            if k not in m:
                errors.append(f"measurement_{i}_missing:{k}")
        if m.get("exit_code") != 0:
            errors.append(f"measurement_{i}_exit_code:{m.get('exit_code')}")

artifact = data.get("artifact", {})
artifact_path = pathlib.Path(artifact.get("path", ""))
if artifact_path.exists() and artifact_path.is_file():
    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if artifact.get("sha256") != digest:
        errors.append("artifact_sha256_mismatch")
    if artifact.get("size") != artifact_path.stat().st_size:
        errors.append("artifact_size_mismatch")
else:
    print(f"artifact_local_check=NOT_AVAILABLE path={artifact_path}")

print(f"schema={data.get('schema')}")
print(f"execution_id={data.get('execution_id')}")
print(f"model_id={data.get('model',{}).get('id')}")
print(f"model_name={data.get('model',{}).get('name')}")
print(f"quantization={data.get('model',{}).get('quantization')}")
print(f"runtime={data.get('runtime',{}).get('name')} version={data.get('runtime',{}).get('version')}")
print(f"hardware_cpu={data.get('hardware',{}).get('cpu')}")
print(f"hardware_ram_mb={data.get('hardware',{}).get('ram_total_mb')}")
print(f"warmup_iterations={data.get('protocol',{}).get('warmup_iterations')}")
print(f"measurement_iterations_declared={data.get('protocol',{}).get('measurement_iterations')}")
print(f"measurement_iterations_found={len(measurements) if isinstance(measurements,list) else 0}")

tps = [m.get("tokens_per_second") for m in measurements if isinstance(m, dict) and m.get("tokens_per_second") is not None]
print(f"tokens_per_second_samples={len(tps)}")
if tps:
    print(f"tokens_per_second_mean={sum(tps)/len(tps):.4f}")
    print(f"tokens_per_second_min={min(tps):.4f}")
    print(f"tokens_per_second_max={max(tps):.4f}")

print(f"evidence_local_validation={'PASS' if not errors else 'FAIL'}")
if errors:
    for e in errors:
        print(f"ERROR:{e}")
    raise SystemExit(60)
PY
    else
        echo "NOT PRESENT: $EVIDENCE"
        return 61
    fi
    echo

    echo "========== REAL RUNTIME EVIDENCE DISCOVERY =========="
    for f in \
        "$EVIDENCE" \
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
