#!/usr/bin/env bash
set -euo pipefail

# Configure only OpenDots' model-provider variables. Other service settings are preserved.
# This script is opt-in and does not start services or change Magnitude's network exposure.

usage() {
  echo "Usage: MAGNITUDE_BASE_URL=http://127.0.0.1:10101/v1 bash $0 /path/to/OpenDots EXACT_MODEL_ID" >&2
}

[[ $# -eq 2 ]] || { usage; exit 2; }
OPENDOTS_DIR="$(cd "$1" && pwd)"
MODEL="$2"
BASE_URL="${MAGNITUDE_BASE_URL:-http://127.0.0.1:10101/v1}"

[[ -f "$OPENDOTS_DIR/package.json" && -f "$OPENDOTS_DIR/.env.example" ]] || {
  echo "[FAIL] Directory is not an OpenDots checkout (package.json/.env.example missing)." >&2
  exit 2
}
python3 - "$OPENDOTS_DIR/package.json" <<'PY'
import json, sys
try:
    package = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"[FAIL] Cannot read package.json: {exc}")
if package.get("name") != "opendots":
    raise SystemExit("[FAIL] package.json name is not 'opendots'.")
print(f"[OK] OpenDots package version: {package.get('version', 'unknown')}")
PY
command -v curl >/dev/null 2>&1 || { echo "[FAIL] curl is required." >&2; exit 2; }

models_file="$(mktemp)"
trap 'rm -f "$models_file"' EXIT
echo "[1/2] Verifying selected model against $BASE_URL/models"
curl -fsS --connect-timeout 3 --max-time 15 "$BASE_URL/models" -o "$models_file"
python3 - "$MODEL" "$models_file" <<'PY'
import json, sys
model, path = sys.argv[1:3]
try:
    data = json.load(open(path, encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"[FAIL] Invalid /models JSON: {exc}")
ids = [item.get("id") for item in data.get("data", []) if isinstance(item, dict)]
if model not in ids:
    print("[FAIL] Model id does not exactly match Magnitude /models.", file=sys.stderr)
    print("Available IDs: " + (", ".join(x for x in ids if x) or "(none)"), file=sys.stderr)
    raise SystemExit(1)
print(f"[OK] Model id verified: {model}")
PY
if [[ ! -f "$OPENDOTS_DIR/.env" ]]; then
  cp "$OPENDOTS_DIR/.env.example" "$OPENDOTS_DIR/.env"
  echo "[i] Created .env from .env.example."
fi

echo "[2/2] Updating only OPENAI_API_KEY, OPENAI_BASE_URL and OPENAI_MODEL"
python3 - "$OPENDOTS_DIR/.env" "$BASE_URL" "$MODEL" <<'PY'
import os, sys
path, base_url, model = sys.argv[1:4]
values = {
    "OPENAI_API_KEY": "local",
    "OPENAI_BASE_URL": base_url,
    "OPENAI_MODEL": model,
}
with open(path, encoding="utf-8") as f:
    lines = f.read().splitlines()
out = []
seen = set()
for line in lines:
    stripped = line.lstrip()
    key = stripped.split("=", 1)[0].strip() if "=" in stripped and not stripped.startswith("#") else None
    if key not in values:
        out.append(line)
    elif key not in seen:
        out.append(f"{key}={values[key]}")
        seen.add(key)
    # Remove duplicate active definitions so dotenv precedence is unambiguous.
for key, value in values.items():
    if key not in seen:
        out.append(f"{key}={value}")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
PY
echo "[PASS] OpenDots model-provider settings now target Magnitude."
echo "[INFO] Other .env values were preserved; secrets were not printed."
echo "[NEXT] Configure CopilotKit Intelligence separately, then start OpenDots and run the end-to-end checks."
