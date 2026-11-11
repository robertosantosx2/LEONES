#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${DSPINE_LLAMA_CPP_REPO:-https://github.com/Ajay9o9/llama.cpp.git}"
REF="${DSPINE_LLAMA_CPP_REF:-dspine}"
WORK_DIR="${DSPINE_WORK_DIR:-${RUNNER_TEMP:-/tmp}/dspine-llama-cpp-audit}"
JOBS="${DSPINE_BUILD_JOBS:-2}"

log() { printf '\n[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null || die "git is required"
command -v cmake >/dev/null || die "cmake is required"
command -v c++ >/dev/null || die "a C++ compiler is required"

rm -rf "$WORK_DIR"
mkdir -p "$(dirname "$WORK_DIR")"

log "Clone only the DSpine reference branch"
git clone --depth 1 --single-branch --branch "$REF" "$REPO_URL" "$WORK_DIR"
cd "$WORK_DIR"

SHA="$(git rev-parse HEAD)"
log "Source: $REPO_URL"
log "Ref: $REF"
log "Commit: $SHA"
git show -s --format='Commit date: %cI%nSubject: %s%nAuthor: %an' HEAD

log "Inventory DSpine-related source references"
if ! git grep -niE 'dspine|d.flash|speculative' -- ':!*.md' ':!*.yml' ':!*.yaml' > "$WORK_DIR/dspine-source-inventory.txt"; then
  log "No matching source references found; investigate before claiming support"
fi
sed -n '1,240p' "$WORK_DIR/dspine-source-inventory.txt" || true

log "Configure CPU-only build (this does not validate CUDA)"
cmake -S . -B build \
  -DGGML_CUDA=OFF \
  -DGGML_METAL=OFF \
  -DLLAMA_BUILD_TESTS=ON \
  -DLLAMA_BUILD_EXAMPLES=ON

log "Build llama-cli"
cmake --build build --target llama-cli --parallel "$JOBS"

log "Record resulting executable and build metadata"
find build -type f -name 'llama-cli' -perm -111 -print
git status --short
log "CPU configure/build completed. No model was downloaded or executed."
