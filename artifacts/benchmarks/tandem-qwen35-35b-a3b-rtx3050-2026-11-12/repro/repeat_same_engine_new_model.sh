#!/usr/bin/env bash
set -euo pipefail
# Keep the engine/server unchanged; point this client at the already-running API.
: "${MODEL_ID:?Set MODEL_ID to the API model name}"
BASE_URL="${BASE_URL:-http://127.0.0.1:18086}"
ENGINE_LABEL="${ENGINE_LABEL:-tandem.cpp}"
MODEL_PATH="${MODEL_PATH:-$MODEL_ID}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/run_battery.py" --mode same-engine-new-model --base-url "$BASE_URL" --engine "$ENGINE_LABEL" --model "$MODEL_ID" --model-path "$MODEL_PATH" --output "${OUTPUT_DIR:-tandem-same-engine-new-model-$(date +%Y%m%d-%H%M%S)}"
