#!/usr/bin/env bash
set -Eeuo pipefail

# Reproducible Linux/Ubuntu CPU build for the ThumbLLM Ornith 1.5 9B recipe.
# This clones upstream source and a separate pinned llama.cpp checkout. It does
# not modify ~/llama.cpp-cuda, ODS, or any existing model installation.

ROOT="${THUMBLLM_LINUX_ROOT:-$HOME/leones-work/thumbllm-ornith-linux}"
UPSTREAM="$ROOT/ThumbLLM"
LLAMA="$ROOT/llama.cpp"
MODEL_DIR="$ROOT/models"
MODEL="$MODEL_DIR/Ornith-1.5-9B-OBLITERATED-Q4_K_M.gguf"
TAG="Release-1-Ornith-1.5-9B-CPU"
LLAMA_COMMIT="c060ca974"
MODEL_SHA256="88ce99bb696fbc921edc4f995c4beb12a66bf94319d00bfd5f44265d02fa6dfb"
MODEL_URL="https://huggingface.co/OBLITERATUS/Ornith-1.5-9B-OBLITERATED/resolve/main/Ornith-1.5-9B-OBLITERATED-Q4_K_M.gguf"

for cmd in git cmake c++ curl sha256sum; do
  command -v "$cmd" >/dev/null || {
    echo "Missing command: $cmd. Install build-essential, cmake, git and curl." >&2
    exit 2
  }
done

mkdir -p "$ROOT" "$MODEL_DIR"

if [[ ! -d "$UPSTREAM/.git" ]]; then
  git clone --branch "$TAG" --single-branch https://github.com/TeksEdge/ThumbLLM.git "$UPSTREAM"
else
  git -C "$UPSTREAM" fetch origin --tags
  git -C "$UPSTREAM" checkout "$TAG"
fi

if [[ ! -d "$LLAMA/.git" ]]; then
  git clone https://github.com/ggml-org/llama.cpp.git "$LLAMA"
fi
git -C "$LLAMA" fetch origin
git -C "$LLAMA" checkout --detach "$LLAMA_COMMIT"

if [[ ! -f "$MODEL" ]]; then
  echo "Downloading model (several GB)..."
  curl -fL --retry 5 --retry-delay 3 --retry-all-errors "$MODEL_URL" -o "$MODEL.part"
  mv "$MODEL.part" "$MODEL"
fi

actual="$(sha256sum "$MODEL" | awk '{print $1}')"
if [[ "$actual" != "$MODEL_SHA256" ]]; then
  echo "ERROR: model SHA-256 mismatch." >&2
  echo "Expected: $MODEL_SHA256" >&2
  echo "Actual:   $actual" >&2
  rm -f "$MODEL"
  exit 3
fi

cmake -S "$LLAMA" -B "$LLAMA/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=OFF \
  -DGGML_NATIVE=ON
cmake --build "$LLAMA/build" --config Release -j "${BUILD_JOBS:-8}"

echo
echo "Setup completed."
echo "ThumbLLM tag: $(git -C "$UPSTREAM" describe --tags --exact-match)"
echo "llama.cpp commit: $(git -C "$LLAMA" rev-parse HEAD)"
echo "Model SHA-256: $actual"
echo "Server: $LLAMA/build/bin/llama-server"
echo "Model:  $MODEL"
echo "Next: run scripts/ubuntu-ornith-cpu-serve.sh (or see docs/ubuntu-reproduction.md)."
