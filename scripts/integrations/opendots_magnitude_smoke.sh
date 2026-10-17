#!/usr/bin/env bash
set -euo pipefail

# Smoke test for Magnitude's documented OpenAI-compatible API.
# Does not start/stop services, download models, change configuration, or use remote fallback.

BASE_URL="${MAGNITUDE_BASE_URL:-http://127.0.0.1:10100/inference/v1}"
MODEL="${OPENAI_MODEL:-}"
API_KEY="${MAGNITUDE_API_KEY:-}"

if [[ -z "$MODEL" ]]; then
  echo "[FAIL] Set OPENAI_MODEL to the exact model id returned by /models." >&2
  exit 2
fi
command -v curl >/dev/null 2>&1 || { echo "[FAIL] curl is required." >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "[FAIL] python3 is required." >&2; exit 2; }

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
auth=()
if [[ -n "$API_KEY" ]]; then auth=(-H "Authorization: Bearer $API_KEY"); fi

echo "[1/3] Checking model list: $BASE_URL/models"
if ! curl -fsS --connect-timeout 3 --max-time 15 "${auth[@]}" "$BASE_URL/models" -o "$tmpdir/models.json"; then
  echo "[FAIL] Magnitude /models is not reachable. Check service, URL, network access and key." >&2
  exit 1
fi
python3 - "$tmpdir/models.json" "$MODEL" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"[FAIL] /models returned invalid JSON: {exc}")
ids = [x.get("id") for x in data.get("data", []) if isinstance(x, dict)]
if sys.argv[2] not in ids:
    print("[FAIL] OPENAI_MODEL is not an exact model id returned by Magnitude.", file=sys.stderr)
    print("Available IDs: " + (", ".join(x for x in ids if x) or "(none)"), file=sys.stderr)
    raise SystemExit(1)
print(f"[OK] Model id is available: {sys.argv[2]}")
PY

python3 - "$tmpdir/request.json" "$MODEL" <<'PY'
import json, sys
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump({"model": sys.argv[2], "messages": [{"role": "user", "content": "Reply with exactly: MAGNITUDE_LOCAL_OK"}], "max_tokens": 48, "temperature": 0, "stream": False}, f)
PY
echo "[2/3] Checking non-streaming chat completion"
if ! curl -fsS --connect-timeout 3 --max-time 180 -H 'Content-Type: application/json' "${auth[@]}" --data-binary "@$tmpdir/request.json" "$BASE_URL/chat/completions" -o "$tmpdir/chat.json"; then
  echo "[FAIL] /chat/completions request failed." >&2
  exit 1
fi
python3 - "$tmpdir/chat.json" <<'PY'
import json, sys
try:
    text = json.load(open(sys.argv[1], encoding="utf-8"))["choices"][0]["message"]["content"]
except Exception as exc:
    raise SystemExit(f"[FAIL] Invalid chat completion response: {exc}")
if not isinstance(text, str) or not text.strip():
    raise SystemExit("[FAIL] Chat completion returned empty content.")
print("[OK] Non-streaming completion returned non-empty text.")
PY

python3 - "$tmpdir/stream-request.json" "$MODEL" <<'PY'
import json, sys
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump({"model": sys.argv[2], "messages": [{"role": "user", "content": "Reply with exactly: STREAM_OK"}], "max_tokens": 48, "temperature": 0, "stream": True}, f)
PY
echo "[3/3] Checking SSE streaming"
if ! curl -fsSN --connect-timeout 3 --max-time 180 -H 'Content-Type: application/json' "${auth[@]}" --data-binary "@$tmpdir/stream-request.json" "$BASE_URL/chat/completions" -o "$tmpdir/stream.txt"; then
  echo "[FAIL] Streaming request failed." >&2
  exit 1
fi
python3 - "$tmpdir/stream.txt" <<'PY'
import json, sys
lines = [line[6:].strip() for line in open(sys.argv[1], encoding="utf-8") if line.startswith("data:")]
if not lines:
    raise SystemExit("[FAIL] No SSE data events were returned.")
if "[DONE]" not in lines:
    raise SystemExit("[FAIL] SSE stream did not include [DONE].")
chunks = []
for line in lines:
    if line == "[DONE]":
        continue
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        continue
    for choice in obj.get("choices", []):
        content = choice.get("delta", {}).get("content")
        if isinstance(content, str):
            chunks.append(content)
if not "".join(chunks).strip():
    raise SystemExit("[FAIL] SSE events contained no streamed text.")
print("[OK] SSE stream delivered text and [DONE].")
PY

echo "[PASS] Magnitude OpenAI-compatible API smoke test passed."
echo "[INFO] This does not prove OpenDots tool-calling or full end-to-end behavior."
