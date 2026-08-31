#!/usr/bin/env bash
set -euo pipefail

python3 scripts/integrations/magnitude_preflight.py

printf '\nThis will install @magnitudedev/cli globally with npm. Continue? [y/N] '
read -r answer
[[ "$answer" =~ ^[Yy]$ ]] || { echo "Installation cancelled."; exit 0; }

echo
echo "============================================================"
echo "LEONES — MAGNITUDE INSTALL"
echo "============================================================"
echo "[1/3] Installing @magnitudedev/cli..."
echo "[i] Activity is monitored; installation may take some time."

tmp_log="$(mktemp)"
cleanup() { rm -f "$tmp_log"; }
trap cleanup EXIT

set +e
npm install -g @magnitudedev/cli >"$tmp_log" 2>&1 &
pid=$!
last_size=0
elapsed=0

while kill -0 "$pid" 2>/dev/null; do
    size=$(wc -c <"$tmp_log")
    if [[ "$size" -ne "$last_size" ]]; then
        echo "[i] npm is active — output updated (${size} bytes)"
        last_size="$size"
    else
        echo "[i] npm is still running — ${elapsed}s elapsed"
    fi
    sleep 5
    elapsed=$((elapsed + 5))
done

wait "$pid"
rc=$?
set -e

cat "$tmp_log"

if [[ "$rc" -ne 0 ]]; then
    if grep -qE 'EACCES|permission denied' "$tmp_log"; then
        echo
        echo "[!] Global npm directory requires elevated privileges."
        echo "[i] Retrying with sudo..."
        sudo npm install -g @magnitudedev/cli
    else
        echo
        echo "[!] Magnitude installation failed."
        exit "$rc"
    fi
fi

echo
echo "[2/3] Verifying Magnitude..."
command -v magnitude
magnitude --version

echo
echo "[3/3] Installation complete."
echo "[✓] @magnitudedev/cli installed and executable."
