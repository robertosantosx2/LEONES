#!/usr/bin/env bash
set -Eeuo pipefail

SRC_DIR="\${DSPINE_SRC_DIR:-$HOME/src/llama.cpp-dspine}"
BUILD_DIR="\${DSPINE_BUILD_DIR:-$SRC_DIR/build-cuda}"
JOBS="\${DSPINE_BUILD_JOBS:-2}"
LOG="\${DSPINE_BUILD_LOG:-$HOME/dspine-llama-cpp-cuda-build-$(date -u +%Y%m%dT%H%M%SZ).log}"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
for cmd in git cmake nvcc nvidia-smi c++; do
    command -v "$cmd" >/dev/null 2>&1 || die "Required command missing: $cmd"
done
[[ ! -e "$SRC_DIR" ]] || die "Refusing to overwrite existing path: $SRC_DIR"

mkdir -p "$(dirname "$SRC_DIR")"
exec > >(tee "$LOG") 2>&1

echo "========== MSI DSpine CUDA BUILD =========="
date -Is
nvidia-smi
nvcc --version
cmake --version | head -1
c++ --version | head -1

echo "========== FETCH PINNED DSpine FORK =========="
git init "$SRC_DIR"
git -C "$SRC_DIR" remote add origin https://github.com/Ajay9o9/llama.cpp.git
git -C "$SRC_DIR" fetch --depth 1 origin d493f841b20241606c47a4e0537d3c786b5cf50b
git -C "$SRC_DIR" checkout --detach FETCH_HEAD
echo "Pinned source commit: d493f841b20241606c47a4e0537d3c786b5cf50b"
git -C "$SRC_DIR" rev-parse HEAD
git -C "$SRC_DIR" status --short

echo "========== CONFIGURE CUDA SM86 =========="
cmake -S "$SRC_DIR" -B "$BUILD_DIR" \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=86 \
  -DCMAKE_BUILD_TYPE=Release

echo "========== BUILD TARGETS =========="
cmake --build "$BUILD_DIR" \
  --target llama-server llama-cli llama-quantize \
  --parallel "$JOBS"

echo "========== BINARIES =========="
for bin in llama-server llama-cli llama-quantize; do
    path="$BUILD_DIR/bin/$bin"
    [[ -x "$path" ]] || die "Expected binary missing: $path"
    echo "--- $path"
    "$path" --version 2>&1 | head -8 || true
done

echo "========== BUILD RESULT =========="
echo "BUILD_STATUS=SUCCESS"
echo "SOURCE_DIR=$SRC_DIR"
echo "BUILD_DIR=$BUILD_DIR"
echo "LOG=$LOG"
echo "No system installation or existing llama.cpp binary was modified."
