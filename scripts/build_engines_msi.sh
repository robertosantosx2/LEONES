#!/usr/bin/env bash
# Sequential, resumable source builds for the LEONES MSI benchmark host.
# Builds binaries only: no model weights, no server startup, no inference.
set -Eeuo pipefail
umask 022

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK_ROOT="$(printenv LEONES_BUILD_ROOT || printf '%s' "$HOME/build/leones-engine-builds")"
LOG_ROOT="$ROOT/artifacts/engine-builds"
REPORT="$WORK_ROOT/build-batch-$STAMP.tsv"
mkdir -p "$WORK_ROOT" "$LOG_ROOT"
cd "$ROOT"

# Keep the 14 GiB laptop responsive and avoid unbounded parallelism.
export CARGO_BUILD_JOBS="$(printenv CARGO_BUILD_JOBS || printf 2)"
export CMAKE_BUILD_PARALLEL_LEVEL="$(printenv CMAKE_BUILD_PARALLEL_LEVEL || printf 2)"
export MAKEFLAGS="$(printenv MAKEFLAGS || printf '%s' '-j2')"
export CUDA_HOME="$(printenv CUDA_HOME || printf '%s' /usr/local/cuda-13.4)"
export CUDACXX="$(printenv CUDACXX || printf '%s' "$CUDA_HOME/bin/nvcc")"
export CMAKE_CUDA_COMPILER="$CUDACXX"

declare -A STATUS
FAILURES=0
SKIPS=0
SUCCESSES=0

say() { printf '\n[%s] %s\n' "$(date -Is)" "$*"; }
source_dir() {
  local id="$1" meta="third_party/engines/$1/SOURCE.json"
  [[ -f "$meta" ]] || { echo "Missing source metadata: $meta" >&2; return 1; }
  python3 - "$meta" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text())
tree = d.get("source_tree", "")
if not tree.startswith("source/") or ".." in pathlib.PurePosixPath(tree).parts:
    raise SystemExit(f"unsafe source_tree in {p}")
out = p.parent / tree
if not out.is_dir():
    raise SystemExit(f"vendored source tree missing: {out}")
print(out.resolve())
PY
}
record() {
  local id="$1" status="$2" detail="$3"
  STATUS["$id"]="$status"
  printf '%s\t%s\t%s\n' "$id" "$status" "$detail" | tee -a "$REPORT"
  case "$status" in
    OK) SUCCESSES=$((SUCCESSES+1));;
    FAILED) FAILURES=$((FAILURES+1));;
    SKIPPED) SKIPS=$((SKIPS+1));;
  esac
}
need() {
  local cmd="$1" id="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    say "$id: missing required command: $cmd"
    return 1
  fi
}
run_logged() {
  local id="$1" log="$2"; shift 2
  say "$id: $*"
  nice -n 5 "$@" 2>&1 | tee "$log"
}
capture() {
  local id="$1" binary="$2" command_text="$3" log="$4"; shift 4
  python3 scripts/capture_engine_build.py \
    --engine "$id" --binary "$binary" --build-command "$command_text" \
    --build-log "$log" "$@" \
    --output "$LOG_ROOT/$id/build.json"
}
failed() {
  local id="$1" log="$2" why="$3"
  record "$id" FAILED "$why (log: $log)"
}

build_kinetic() {
  local id=kinetic src log install bin cmd
  log="$LOG_ROOT/$id/build.log"; install="$WORK_ROOT/$id/install"
  mkdir -p "$LOG_ROOT/$id" "$install"
  if ! need cargo "$id" || ! need rustc "$id"; then record "$id" SKIPPED "Rust toolchain missing"; return; fi
  src="$(source_dir "$id")" || { failed "$id" "$log" "source unavailable"; return; }
  bin="$install/bin/kinetic"
  cmd="cargo install --locked --path $src/crates/kinetic-cli --root $install --force"
  if ! run_logged "$id" "$log" cargo install --locked --path "$src/crates/kinetic-cli" --root "$install" --force; then
    failed "$id" "$log" "cargo install failed"; return
  fi
  if ! capture "$id" "$bin" "$cmd" "$log" \
      --compiler 'rustc --version' --compiler 'cargo --version' \
      --backend cuda --feature default-features --feature sm_86; then
    failed "$id" "$log" "build evidence capture failed"; return
  fi
  record "$id" OK "binary=$bin"
}

build_tensorfold() {
  local id=tensorfold src work log bin required_zig cmd
  log="$LOG_ROOT/$id/build.log"; work="$WORK_ROOT/$id/source"
  mkdir -p "$LOG_ROOT/$id" "$WORK_ROOT/$id"
  if ! need zig "$id" || ! need python3 "$id"; then record "$id" SKIPPED "Zig/Python toolchain missing"; return; fi
  src="$(source_dir "$id")" || { failed "$id" "$log" "source unavailable"; return; }
  required_zig="$(cat "$src/.zig-version" 2>/dev/null || true)"
  if [[ -n "$required_zig" && "$(zig version)" != "$required_zig" ]]; then
    record "$id" SKIPPED "requires Zig $required_zig; found $(zig version)"
    return
  fi
  if [[ ! -x "$CUDACXX" ]]; then record "$id" SKIPPED "CUDA compiler missing at $CUDACXX"; return; fi
  rm -rf "$work"; mkdir -p "$work"; cp -a "$src/." "$work/"
  bin="$work/zig-out/native/bin/tensorfold-native"
  cmd="zig build -j2 -Dgpu=sm_86 -Dnvcc=$CUDACXX (isolated working copy)"
  if ! (cd "$work" && run_logged "$id" "$log" zig build -j2 -Dgpu=sm_86 "-Dnvcc=$CUDACXX"); then
    failed "$id" "$log" "Zig/CUDA build failed"; return
  fi
  if ! capture "$id" "$bin" "$cmd" "$log" \
      --compiler 'zig version' --compiler "$CUDACXX --version" \
      --backend cuda --feature sm_86 --feature nvcc; then
    failed "$id" "$log" "build evidence capture failed"; return
  fi
  record "$id" OK "binary=$bin"
}

build_llama() {
  local id="$1" src log build bin cmd
  log="$LOG_ROOT/$id/build.log"; build="$WORK_ROOT/$id/build"
  mkdir -p "$LOG_ROOT/$id" "$WORK_ROOT/$id"
  if ! need cmake "$id" || ! need c++ "$id" || ! need nvcc "$id"; then
    record "$id" SKIPPED "CMake/C++/CUDA toolchain missing"; return
  fi
  src="$(source_dir "$id")" || { failed "$id" "$log" "source unavailable"; return; }
  bin="$build/bin/llama-server"
  cmd="cmake -S $src -B $build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=86 && cmake --build $build --config Release -j2 --target llama-server"
  if ! run_logged "$id" "$log" cmake -S "$src" -B "$build" \
      -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=86; then
    failed "$id" "$log" "CMake configure failed"; return
  fi
  if ! run_logged "$id" "$log" cmake --build "$build" --config Release -j2 --target llama-server; then
    failed "$id" "$log" "llama-server compile failed"; return
  fi
  if ! capture "$id" "$bin" "$cmd" "$log" \
      --compiler 'cmake --version' --compiler 'c++ --version' --compiler 'nvcc --version' \
      --backend cuda --feature GGML_CUDA --feature sm_86; then
    failed "$id" "$log" "build evidence capture failed"; return
  fi
  record "$id" OK "binary=$bin"
}

build_tandem() {
  local id=tandem-cpp tandem_src base_src work log build bin patch cmd
  log="$LOG_ROOT/$id/build.log"; work="$WORK_ROOT/$id/source"; build="$WORK_ROOT/$id/build"
  mkdir -p "$LOG_ROOT/$id" "$WORK_ROOT/$id"
  if ! need cmake "$id" || ! need c++ "$id" || ! need nvcc "$id" || ! need git "$id"; then
    record "$id" SKIPPED "CMake/C++/CUDA/Git toolchain missing"; return
  fi
  tandem_src="$(source_dir "$id")" || { failed "$id" "$log" "Tandem source unavailable"; return; }
  base_src="$(source_dir llama-cpp-tandem-base)" || { failed "$id" "$log" "exact base source unavailable"; return; }
  patch="$tandem_src/tandem.patch"
  [[ -f "$patch" ]] || { failed "$id" "$log" "tandem.patch missing"; return; }
  rm -rf "$work" "$build"; mkdir -p "$work" "$build"
  {
    echo "Using vendored llama.cpp Tandem base: $base_src"
    echo "Applying patch: $patch"
    cp -a "$base_src/." "$work/"
    cd "$work"
    git init -q
    git apply --check "$patch"
    git apply "$patch"
  } 2>&1 | tee "$log" || { failed "$id" "$log" "Tandem patch did not apply"; return; }
  bin="$build/bin/llama-server"
  cmd="copy exact vendored base; git apply $patch; cmake -S $work -B $build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=86; cmake --build $build -j2 --target llama-server"
  if ! run_logged "$id" "$log" cmake -S "$work" -B "$build" \
      -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=86; then
    failed "$id" "$log" "Tandem CMake configure failed"; return
  fi
  if ! run_logged "$id" "$log" cmake --build "$build" -j2 --target llama-server; then
    failed "$id" "$log" "Tandem llama-server compile failed"; return
  fi
  if ! capture "$id" "$bin" "$cmd" "$log" \
      --compiler 'cmake --version' --compiler 'c++ --version' --compiler 'nvcc --version' \
      --backend cuda --feature GGML_CUDA --feature sm_86 \
      --patch "$patch" \
      --base-source-meta third_party/engines/llama-cpp-tandem-base/SOURCE.json; then
    failed "$id" "$log" "build evidence capture failed"; return
  fi
  record "$id" OK "binary=$bin"
}

build_rusting() {
  local id=rusting-strata src log target bin cmd
  log="$LOG_ROOT/$id/build.log"; target="$WORK_ROOT/$id/target"
  mkdir -p "$LOG_ROOT/$id" "$WORK_ROOT/$id"
  if ! need cargo "$id" || ! need rustc "$id"; then record "$id" SKIPPED "Rust toolchain missing"; return; fi
  src="$(source_dir "$id")" || { failed "$id" "$log" "source unavailable"; return; }
  bin="$target/release/rustingstrata"
  cmd="cargo build --release --locked --manifest-path $src/Cargo.toml --target-dir $target"
  if ! run_logged "$id" "$log" cargo build --release --locked \
      --manifest-path "$src/Cargo.toml" --target-dir "$target"; then
    failed "$id" "$log" "RustingStrata cargo build failed"; return
  fi
  if ! capture "$id" "$bin" "$cmd" "$log" \
      --compiler 'rustc --version' --compiler 'cargo --version' \
      --backend cuda --feature NVRTC --feature sm_86; then
    failed "$id" "$log" "build evidence capture failed"; return
  fi
  record "$id" OK "binary=$bin"
}

printf 'engine\tstatus\tdetail\n' > "$REPORT"
say "LEONES sequential MSI build batch"
say "Repository: $ROOT"
say "Build workspace: $WORK_ROOT"
say "Logs/evidence: $LOG_ROOT"
say "Limits: Cargo jobs=$CARGO_BUILD_JOBS; CMake jobs=$CMAKE_BUILD_PARALLEL_LEVEL; MAKEFLAGS=$MAKEFLAGS"
say "No models will be downloaded; no server or benchmark will be launched."

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv 2>&1 | tee "$WORK_ROOT/gpu-preflight-$STAMP.txt" || true
else
  say "WARNING: nvidia-smi is unavailable; CUDA builds may fail."
fi
if command -v df >/dev/null 2>&1; then
  df -h "$ROOT" | tee "$WORK_ROOT/disk-preflight-$STAMP.txt"
  free -h 2>/dev/null | tee "$WORK_ROOT/memory-preflight-$STAMP.txt" || true
fi
for ac in /sys/class/power_supply/AC*/online; do
  if [[ -r "$ac" && "$(cat "$ac")" != "1" ]]; then
    say "WARNING: AC power is not detected. Connect the charger for this long build batch."
    break
  fi
done

build_kinetic
build_tensorfold
build_llama llama-cpp
build_llama llama-cpp-tandem-base
build_tandem
build_rusting

# Maya is source-vendored, but setup selects/downloads model packs and requires >=32 GiB RAM.
record project-maya SKIPPED "not built: setup downloads weights; minimum host RAM is 32 GiB"

say "BATCH FINISHED: OK=$SUCCESSES FAILED=$FAILURES SKIPPED=$SKIPS"
say "Batch report: $REPORT"
say "Per-engine build evidence: $LOG_ROOT/<engine>/build.json"
say "Per-engine build logs: $LOG_ROOT/<engine>/build.log"
if (( FAILURES > 0 )); then
  say "Some builds failed. Inspect their logs and rerun after fixing prerequisites; CMake/Cargo caches are retained."
  exit 1
fi
