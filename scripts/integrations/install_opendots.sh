#!/usr/bin/env bash
set -euo pipefail

# Optional OpenDots checkout for LEONES. The source remains an upstream clone;
# LEONES keeps its integration adapter, configuration helper and tests here.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${OPENDOTS_DIR:-$HOME/.local/share/leones/opendots}"
REF="${OPENDOTS_REF:-main}"

fail() { echo "[FAIL] $1" >&2; exit 1; }

command -v git >/dev/null 2>&1 || fail "git is required."
command -v node >/dev/null 2>&1 || fail "Node.js 24+ is required."
command -v npm >/dev/null 2>&1 || fail "npm is required."
command -v python3 >/dev/null 2>&1 || fail "Python 3 is required."

node - <<'NODE' || exit 1
const major = Number(process.versions.node.split('.')[0]);
if (major < 24) {
  console.error(`[FAIL] OpenDots requires Node.js >=24; found ${process.versions.node}.`);
  process.exit(1);
}
console.log(`[OK] Node.js ${process.versions.node}`);
NODE

if [[ -e "$TARGET" ]]; then
  [[ -f "$TARGET/package.json" ]] || fail "Target exists but is not an OpenDots checkout: $TARGET"
  python3 - "$TARGET/package.json" <<'PY'
import json, sys
try:
    package = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"[FAIL] Cannot read existing package.json: {exc}")
if package.get("name") != "opendots":
    raise SystemExit("[FAIL] Existing target is not the OpenDots package.")
PY
  echo "[i] Reusing existing OpenDots checkout; no git pull or overwrite performed."
else
  mkdir -p "$(dirname "$TARGET")"
  git clone --depth 1 --branch "$REF" https://github.com/CopilotKit/OpenDots.git "$TARGET"
fi

echo "[i] OpenDots revision: $(git -C "$TARGET" rev-parse --short HEAD)"
echo "[→] Installing locked npm dependencies..."
npm --prefix "$TARGET" ci

if [[ ! -f "$TARGET/.env" ]]; then
  cp "$TARGET/.env.example" "$TARGET/.env"
  echo "[i] Created .env from .env.example; no credentials were added."
else
  echo "[i] Existing .env preserved."
fi

echo "[PASS] OpenDots checkout and dependencies are ready at: $TARGET"
echo "[NEXT] Configure CopilotKit Intelligence using OpenDots docs/SETUP.md."
echo "[NEXT] Start the LEONES compatibility facade, then run:"
echo "       bash \"$ROOT/scripts/integrations/configure_opendots_magnitude.sh\" \"$TARGET\" local"
