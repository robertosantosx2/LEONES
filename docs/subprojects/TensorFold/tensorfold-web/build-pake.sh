#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
OUT_DIR="$ROOT/build/pake"

if ! command -v pake >/dev/null 2>&1; then
  echo "Pake CLI not found. Install it with: npm install -g pake-cli" >&2
  exit 127
fi

echo "========== PAKE ENVIRONMENT =========="
pake --version
if command -v node >/dev/null 2>&1; then node --version; else echo "Node.js: missing"; fi
if command -v rustc >/dev/null 2>&1; then rustc --version; else echo "Rust: missing"; fi
echo
echo "Pake config: $ROOT/pake.config.json"
echo "Output directory: $OUT_DIR"
echo "Target URL: http://127.0.0.1:8787/"
echo
echo "Note: this creates a desktop wrapper. It does not install/start the Python bridge or TensorFold Engine."

mkdir -p "$OUT_DIR"
cd "$OUT_DIR"
exec pake --config "$ROOT/pake.config.json" --json
