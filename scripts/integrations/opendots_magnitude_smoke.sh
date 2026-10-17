#!/usr/bin/env bash
set -euo pipefail

# Smoke test for the LEONES OpenAI-compatible facade over the pinned Magnitude ICN.
# Does not start/stop services, download/load models, change configuration, or use remote fallback.

BASE_URL="${MAGNITUDE_BASE_URL:-http://127.0.0.1:10101/v1}"
MODEL="${OPENAI_MODEL:-local}"

command -v curl >/dev/null 2>&1 || { echo "[FAIL] curl is required." >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "[FAIL] python3 is required." >&2; exit 2; }

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

echo "[1/3] Checking facade health"
if ! curl -fsS --connect-timeout 3 --max-time 10 "${BASE_URL%/v1}/health" -o "$tmpdir/health.json"; then
  echo "[FAIL] Compatibility facade is not healthy. Check the proxy and the configured Ready model instance." >&2
  exit 1
fi
python3 - "$tmpdir/health.json" <<'PY'
import json, sys
try:
    obj = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"[FAIL] Invalid facade health response: {exc}")
if obj.get("status") != "ok":
    raise SystemExit("[FAIL] Facade health did not report status=ok.")
print("[OK] Facade and selected Magnitude instance are ready.")
PY

echo "[2/3] Checking OpenAI-compatible model list"
if ! curl -fsS --connect-timeout 3 --max-time 10 "$BASE_URL/models" -o "$tmpdir/models.json"; then
  echo "[FAIL] Facade /models request failed." >&2
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
    print("[FAIL] OPENAI_MODEL is not advertised by the facade.", file=sys.stderr)
    print("Available IDs: " + (", ".join(x for x in ids if x) or "(none)"), file=sys.stderr)
    raise SystemExit(1)
print(f"[OK] Model alias is available: {sys.argv[2]}")
PY

python3 - "$tmpdir/request.json" "$MODEL" <<'PY'
import json, sys
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump({
        "model": sys.argv[2],
        "messages": [{"role": "user", "content": "Reply with exactly: MAGNITUDE_LOCAL_OK"}],
        "max_completion_tokens": 48,
        "temperature": 0,
        "stream": True,
    }, f)
PY
echo "[3/3] Checking streaming chat completion"
if ! curl -fsSN --connect-timeout 3 --max-time 180 -H 'Content-Type: application/json' \
  --data-binary "@$tmpdir/request.json" "$BASE_URL/chat/completions" -o "$tmpdir/stream.txt"; then
  echo "[FAIL] /chat/completions request failed." >&2
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

echo "[PASS] LEONES OpenDots/Magnitude facade smoke test passed."
echo "[INFO] This does not prove OpenDots tool-calling or full end-to-end behavior."
