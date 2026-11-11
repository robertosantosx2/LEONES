#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${DSPINE_LLAMA_CPP_REPO:-https://github.com/Ajay9o9/llama.cpp.git}"
PINNED_COMMIT="${DSPINE_LLAMA_CPP_COMMIT:-d493f841b20241606c47a4e0537d3c786b5cf50b}"
WORK_DIR="${DSPINE_WORK_DIR:-${RUNNER_TEMP:-/tmp}/dspine-llama-cpp-audit}"
JOBS="${DSPINE_BUILD_JOBS:-2}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LEONES_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

log() { printf '\n[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null || die "git is required"
command -v cmake >/dev/null || die "cmake is required"
command -v c++ >/dev/null || die "a C++ compiler is required"
command -v python3 >/dev/null || die "python3 is required"

rm -rf "$WORK_DIR"
mkdir -p "$(dirname "$WORK_DIR")"

log "Fetch pinned DSpine implementation commit"
git init "$WORK_DIR"
git -C "$WORK_DIR" remote add origin "$REPO_URL"
git -C "$WORK_DIR" fetch --depth 1 origin "$PINNED_COMMIT"
git -C "$WORK_DIR" checkout --detach FETCH_HEAD
cd "$WORK_DIR"

log "Pin source identity"
printf 'Repository: %s\nPinned commit: %s\nResolved commit: %s\n' "$REPO_URL" "$PINNED_COMMIT" "$(git rev-parse HEAD)"
git show -s --format='Commit date: %cI%nSubject: %s%nAuthor: %an' HEAD

log "Run explicit DSpine capability audit"
python3 "$LEONES_ROOT/scripts/audit_dspine_llama_cpp.py" "$WORK_DIR" \
  --output "$WORK_DIR/dspine-audit.json"

log "Configure CPU-only llama.cpp build (not a DSpine runtime validation)"
cmake -S . -B build \
  -DGGML_CUDA=OFF \
  -DGGML_METAL=OFF \
  -DLLAMA_BUILD_TESTS=ON \
  -DLLAMA_BUILD_EXAMPLES=ON

log "Build llama-cli"
cmake --build build --target llama-cli --parallel "$JOBS"

log "Record build output"
find build -type f -name 'llama-cli' -perm -111 -print
log "CPU build completed. No model was downloaded or executed."
log "Read dspine-audit.json: a successful base build does not imply DSpine support."
