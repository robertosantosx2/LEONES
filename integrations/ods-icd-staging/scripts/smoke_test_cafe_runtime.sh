#!/usr/bin/env bash
# Isolated NVIDIA runtime smoke test for the pinned cafe-llama image.
# Does not modify ODS .env, Compose services, or the active llama-server.
set -Eeuo pipefail

IMAGE="${CAFE_SMOKE_IMAGE:-ods-cafe-llama:local}"
MODEL_PATH="${1:-}"
PORT="${CAFE_SMOKE_PORT:-18081}"
TIMEOUT="${CAFE_SMOKE_TIMEOUT_SECONDS:-240}"
EXTRA_ARGS="${CAFE_SMOKE_EXTRA_ARGS:--ngl 999}"
NAME="ods-cafe-smoke-$$"
CID=""

fail() { echo "FAIL: $*" >&2; exit 1; }
cleanup() {
  if [[ -n "${CID}" ]]; then
    docker rm -f "${NAME}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

[[ -n "$MODEL_PATH" ]] || fail "Usage: $0 /absolute/path/to/model.gguf"
[[ "$MODEL_PATH" = /* && -f "$MODEL_PATH" ]] || fail "Model path must be an existing absolute file path"
[[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1024 && PORT <= 65535 )) || fail "CAFE_SMOKE_PORT must be 1024..65535"
command -v docker >/dev/null || fail "docker is required"
command -v curl >/dev/null || fail "curl is required"
command -v nvidia-smi >/dev/null || fail "nvidia-smi is required for this CUDA smoke test"
nvidia-smi >/dev/null || fail "NVIDIA driver is not healthy"
docker image inspect "$IMAGE" >/dev/null 2>&1 || fail "Image $IMAGE is not built locally"

labels="$(docker image inspect "$IMAGE" --format '{{json .Config.Labels}}')"
read_label() { LABELS="$labels" KEY="$1" python3 -c 'import json,os; print((json.loads(os.environ["LABELS"]) or {}).get(os.environ["KEY"], ""))'; }
BUILD_ID="$(read_label org.osmantic.cafe.build-id)"
DIGEST="$(read_label org.osmantic.cafe.artifact-sha256)"
ARCH="$(read_label org.osmantic.cafe.architecture)"
BACKEND="$(read_label org.osmantic.cafe.backend)"
[[ "$BUILD_ID" = "cafe-llama-0.75-linux-x64-cuda12.4" ]] || fail "Unexpected image build ID: $BUILD_ID"
[[ "$DIGEST" = "536ec49ec1de5277578be976a5c161bb985857d5f8066e74889afff6c3f5920c" ]] || fail "Unexpected image artifact digest"
[[ "$ARCH" = "linux-x64" && "$BACKEND" = "cuda-12.4" ]] || fail "Unexpected image architecture/backend: $ARCH / $BACKEND"

MODEL_DIR="$(dirname "$MODEL_PATH")"
MODEL_NAME="$(basename "$MODEL_PATH")"
echo "Starting isolated container; active ODS services and .env are not modified."
echo "Image: $IMAGE ($BUILD_ID, $BACKEND); model: $MODEL_NAME; port: $PORT"
CID="$(docker run -d --name "$NAME" --gpus all \
  -p "127.0.0.1:${PORT}:8081" \
  -v "$MODEL_DIR:/models:ro" \
  -e "CAFE_LLAMA_MODEL=/models/$MODEL_NAME" \
  "$IMAGE")" || fail "Docker could not start the CUDA container"

deadline=$((SECONDS + TIMEOUT))
ready=0
while (( SECONDS < deadline )); do
  if ! docker inspect "$NAME" >/dev/null 2>&1; then
    docker logs "$NAME" 2>&1 || true
    fail "Container exited before becoming ready"
  fi
  if curl --silent --show-error --fail "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if (( ready == 0 )); then
  docker logs "$NAME" 2>&1 || true
  fail "Health endpoint did not become ready within ${TIMEOUT}s"
fi

models="$(curl --silent --show-error --fail "http://127.0.0.1:$PORT/v1/models")" || fail "GET /v1/models failed"
MODEL_ID="$(printf '%s' "$models" | python3 -c 'import json,sys; x=json.load(sys.stdin); d=x.get("data"); assert isinstance(d,list) and d and isinstance(d[0].get("id"),str) and d[0]["id"], "empty or invalid model list"; print(d[0]["id"])')" || fail "Model list response was empty or invalid"

payload="$(MODEL_ID="$MODEL_ID" python3 -c 'import json,os; print(json.dumps({"model":os.environ["MODEL_ID"],"messages":[{"role":"user","content":"Reply with exactly: ODS CAFE SMOKE OK"}],"max_tokens":16,"temperature":0}))')"
response="$(curl --silent --show-error --fail --max-time 90 \
  -H 'Content-Type: application/json' \
  -d "$payload" "http://127.0.0.1:$PORT/v1/chat/completions")" || {
    docker logs "$NAME" 2>&1 || true
    fail "Bounded chat completion failed"
  }
printf '%s' "$response" | python3 -c 'import json,sys; x=json.load(sys.stdin); c=x.get("choices") or []; assert c and isinstance(c[0].get("message",{}).get("content"),str) and c[0]["message"]["content"].strip(), "no completion text"' || fail "Completion response had no text"

echo "PASS: image provenance, NVIDIA container startup, /health, /v1/models, and bounded chat completion."
echo "NOTE: this does not test ODS host-agent activation or rollback; it is an isolated runtime smoke test."
