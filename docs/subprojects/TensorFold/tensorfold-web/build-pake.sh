#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
OUT_DIR="$ROOT/build/pake"
PAKE_URL="${TENSORFOLD_WEB_URL:-http://127.0.0.1:8787/}"

if ! command -v pake >/dev/null 2>&1; then
  echo "Pake CLI not found. Install it with: npm install -g pake-cli" >&2
  exit 127
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required to prepare the Pake config." >&2
  exit 127
fi

echo "========== PAKE ENVIRONMENT =========="
pake --version
if command -v node >/dev/null 2>&1; then node --version; else echo "Node.js: missing"; fi
if command -v rustc >/dev/null 2>&1; then rustc --version; else echo "Rust: missing"; fi
echo
echo "Pake config: $ROOT/pake.config.json"
echo "Target URL: $PAKE_URL"
echo "Output directory: $OUT_DIR"
echo "Note: this creates a desktop wrapper. It does not install/start the Python bridge or TensorFold Engine."

mkdir -p "$OUT_DIR"
python3 - "$ROOT/pake.config.json" "$OUT_DIR/pake.config.json" "$PAKE_URL" <<'PY'
import json
import sys
from urllib.parse import urlsplit

source, destination, target = sys.argv[1:]
parsed = urlsplit(target)
if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
    raise SystemExit("TENSORFOLD_WEB_URL must be an http://127.0.0.1 or http://localhost URL")
if parsed.username or parsed.password or parsed.query or parsed.fragment:
    raise SystemExit("TENSORFOLD_WEB_URL must not contain credentials, query or fragment")
with open(source, encoding="utf-8") as stream:
    config = json.load(stream)
config["url"] = target
with open(destination, "w", encoding="utf-8") as stream:
    json.dump(config, stream, indent=2)
    stream.write("\n")
PY

cd "$OUT_DIR"
exec pake --config "$OUT_DIR/pake.config.json" --json
