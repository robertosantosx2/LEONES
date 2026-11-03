#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
exec python3 "$ROOT/tensorfold-web-bridge.py" --web-root "$ROOT" --engine-url "${TENSORFOLD_ENGINE_URL:-http://127.0.0.1:8080}" --host "${TENSORFOLD_WEB_HOST:-127.0.0.1}" --port "${TENSORFOLD_WEB_PORT:-8787}"
