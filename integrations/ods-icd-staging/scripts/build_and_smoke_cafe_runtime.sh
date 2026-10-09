#!/usr/bin/env bash
# Build the pinned candidate in a disposable checkout, then run the isolated
# NVIDIA smoke test. Never modifies the user's ODS checkout or .env.
set -Eeuo pipefail

MODEL_PATH="${1:-}"
[[ -n "$MODEL_PATH" ]] || { echo "Usage: $0 /absolute/path/to/model.gguf" >&2; exit 2; }
[[ "$MODEL_PATH" = /* && -f "$MODEL_PATH" ]] || { echo "Model path must be an existing absolute file path" >&2; exit 2; }
command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v docker >/dev/null || { echo "docker is required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }

LEONES_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
PATCHER="$LEONES_ROOT/integrations/ods-icd-staging/scripts/harden_cafe_artifact.py"
SMOKE="$LEONES_ROOT/integrations/ods-icd-staging/scripts/smoke_test_cafe_runtime.sh"
TMP_DIR="$(mktemp -d)"
IMAGE="ods-cafe-llama:smoke-$$"
cleanup() {
  docker image rm -f "$IMAGE" >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

git clone --depth 1 --branch feat/cafe-llama-runtime-improvements \
  https://github.com/robertosantosx2/ODS.git "$TMP_DIR/ods-src"
(
  cd "$TMP_DIR"
  python3 "$PATCHER"
)
docker build --pull \
  --file "$TMP_DIR/ods-src/ods/extensions/library/services/cafe-llama/Dockerfile" \
  --tag "$IMAGE" \
  "$TMP_DIR/ods-src/ods/extensions/library/services/cafe-llama"

CAFE_SMOKE_IMAGE="$IMAGE" bash "$SMOKE" "$MODEL_PATH"
