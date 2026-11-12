#!/usr/bin/env bash
set -euo pipefail
# Collect logs and host measurements without stopping/restarting any service.
ROOT="${ROOT:-$HOME/Descargas/tandem-research}"
REPO="${REPO:-$ROOT/engines/tandem.cpp}"
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
MODEL="${MODEL:-$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${OUT:-$HOME/Descargas/tandem-qwen35-evidence-$STAMP}"
mkdir -p "$OUT/logs" "$OUT/system" "$OUT/model" "$OUT/repo"
printf 'captured_at=%s\nhostname=%s\nroot=%s\nrepo=%s\nmodel=%s\n' "$(date --iso-8601=seconds)" "$(hostname)" "$ROOT" "$REPO" "$MODEL" > "$OUT/collection-manifest.txt"
for pattern in 'qwen35-*' 'tandem-cuda-build.log'; do
  find "$LOG_DIR" -maxdepth 1 -type f -name "$pattern" -print0 |
    while IFS= read -r -d '' f; do cp -a "$f" "$OUT/logs/"; done
done
uname -a > "$OUT/system/uname.txt"
cat /etc/os-release > "$OUT/system/os-release.txt" 2>&1 || true
lscpu > "$OUT/system/lscpu.txt" 2>&1 || true
free -h > "$OUT/system/free.txt" 2>&1 || true
swapon --show --bytes > "$OUT/system/swapon.txt" 2>&1 || true
df -hT "$HOME" > "$OUT/system/disk.txt" 2>&1 || true
nvidia-smi > "$OUT/system/nvidia-smi.txt" 2>&1 || true
nvidia-smi -q > "$OUT/system/nvidia-smi-full.txt" 2>&1 || true
nvcc --version > "$OUT/system/nvcc-version.txt" 2>&1 || true
{
  echo '=== health ==='; curl -sS --max-time 5 http://127.0.0.1:18086/health || true
  echo; echo '=== props ==='; curl -sS --max-time 10 http://127.0.0.1:18086/props || true
  echo; echo '=== sockets ==='; ss -ltnp 2>&1 | grep -E '18086|State' || true
  echo; echo '=== process ==='; ps -eo pid,ppid,etimes,%cpu,%mem,rss,args --sort=-rss | grep -E 'llama-server|PID' | grep -v grep || true
} > "$OUT/system/server-state.txt"
if [ -d "$REPO/.git" ]; then
  git -C "$REPO" rev-parse HEAD > "$OUT/repo/tandem-commit.txt" 2>&1 || true
  git -C "$REPO" status --short --branch > "$OUT/repo/tandem-status.txt" 2>&1 || true
  git -C "$REPO/tandem" rev-parse HEAD > "$OUT/repo/llama-submodule-commit.txt" 2>&1 || true
  "$REPO/tandem/build/bin/llama-server" --version > "$OUT/repo/server-version.txt" 2>&1 || true
  ldd "$REPO/tandem/build/bin/llama-server" > "$OUT/repo/server-ldd.txt" 2>&1 || true
fi
if [ -f "$MODEL" ]; then
  stat "$MODEL" > "$OUT/model/model-stat.txt"
  du -h "$MODEL" > "$OUT/model/model-size.txt"
  if [ "${HASH_MODEL:-0}" = "1" ]; then sha256sum "$MODEL" > "$OUT/model/model-sha256.txt"
  else echo 'Not hashed; set HASH_MODEL=1 to hash the full GGUF.' > "$OUT/model/model-sha256.txt"; fi
fi
(cd "$OUT"; find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 -r sha256sum > SHA256SUMS)
tar -C "$(dirname "$OUT")" -czf "$OUT.tar.gz" "$(basename "$OUT")"
sha256sum "$OUT.tar.gz" > "$OUT.tar.gz.sha256"
echo "Evidence directory: $OUT"
echo "Archive: $OUT.tar.gz"
echo "No model weights copied; no service stopped or restarted."
