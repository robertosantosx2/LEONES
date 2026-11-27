#!/usr/bin/env bash
# Reproducible request runner for the openset-llm MSI campaign.
# Start the server separately and wait for "model loaded" before invoking this script.
set -euo pipefail
MODE="${1:-128}"
OUT="${2:-run-${MODE}.json}"
URL="${OPENSET_URL:-http://127.0.0.1:8080/v1/chat/completions}"
case "$MODE" in
  128)
    read -r -d '' BODY <<'JSON' || true
{
  "messages": [{"role":"user","content":"Explain why AVX-VNNI can accelerate integer inference on a CPU. Answer in 5 concise bullet points."}],
  "temperature": 0,
  "max_tokens": 128
}
JSON
    ;;
  512)
    read -r -d '' BODY <<'JSON' || true
{
  "messages": [{"role":"user","content":"Explain in detail how AVX2 and AVX-VNNI accelerate quantized neural network inference on modern Intel CPUs. Cover vector dot products, integer accumulation, instruction throughput, memory bandwidth, quantization, and practical limitations. Use a structured technical explanation."}],
  "temperature": 0,
  "max_tokens": 512
}
JSON
    ;;
  *)
    echo "Usage: $0 {128|512} [output.json]" >&2
    exit 2
    ;;
esac
curl -fsS "$URL" -H 'Content-Type: application/json' -d "$BODY" | tee "$OUT" | python3 -m json.tool
echo "Saved: $OUT" >&2
