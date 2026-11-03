#!/bin/bash
# Build tandem.cpp: clone llama.cpp at the base commit, apply tandem.patch, build llama-server with CUDA.
# usage: bash build.sh [dir] [extra cmake args, e.g. -DCMAKE_CUDA_ARCHITECTURES=89]
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
DIR=${1:-tandem}; shift || true
BASE=$(cat "$HERE/BASE_COMMIT")
[ -d "$DIR" ] || git clone https://github.com/ggml-org/llama.cpp "$DIR"
cd "$DIR"
git checkout -q "$BASE"
if git apply --check "$HERE/tandem.patch" 2>/dev/null; then
  git apply "$HERE/tandem.patch"
elif git apply --check --reverse "$HERE/tandem.patch" 2>/dev/null; then
  echo "tandem.patch is already applied"
else
  echo "tandem.patch does not apply to $(git rev-parse --short HEAD) (local changes?)"; exit 1
fi
cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release "$@"
cmake --build build -j --target llama-server
echo "built: $(pwd)/build/bin/llama-server"
