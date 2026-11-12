#!/usr/bin/env bash
set -euo pipefail
# Start the alternative engine manually and expose its OpenAI-compatible API.
# This script only sends requests; it does not launch or stop a server.
: "\${BASE_URL:?Set BASE_URL to the alternative engine API root}"
: "\${MODEL_ID:?Set MODEL_ID to the API model name}"
ENGINE_LABEL="\${ENGINE_LABEL:-alternative-engine}"
MODEL_PATH="\${MODEL_PATH:-$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf}"
SCRIPT_DIR="$(cd -- "$(dirname -- "\${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/run_battery.py" --mode same-model-new-engine --base-url "$BASE_URL" --engine "$ENGINE_LABEL" --model "$MODEL_ID" --model-path "$MODEL_PATH" --output "\${OUTPUT_DIR:-tandem-same-model-new-engine-$(date +%Y%m%d-%H%M%S)}"
