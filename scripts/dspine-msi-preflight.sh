#!/usr/bin/env bash
set -u

OUT="${DSPINE_PREFLIGHT_OUT:-dspine-msi-preflight-$(date -u +%Y%m%dT%H%M%SZ).txt}"
exec > >(tee "$OUT") 2>&1

section() { printf '\n========== %s ==========\n' "$1"; }
run() {
    printf '\n$'
    printf ' %q' "$@"
    printf '\n'
    "$@" 2>&1 || printf '[WARN] command failed or is unavailable (exit=%s)\n' "$?"
}

section "IDENTITY"
date -Is
uname -a
lsb_release -a 2>/dev/null || cat /etc/os-release

section "CPU AND RAM"
lscpu
free -h
grep -E 'MemTotal|MemAvailable|SwapTotal|SwapFree' /proc/meminfo

section "GPU AND DRIVER"
if command -v nvidia-smi >/dev/null 2>&1; then
    run nvidia-smi
    run nvidia-smi --query-gpu=name,memory.total,compute_cap,driver_version --format=csv
else
    echo "nvidia-smi unavailable"
fi

section "CUDA TOOLCHAIN"
if command -v nvcc >/dev/null 2>&1; then run nvcc --version; else echo "nvcc unavailable"; fi
if [[ -d /usr/local/cuda ]]; then ls -ld /usr/local/cuda; fi

section "BUILD TOOLS"
for cmd in git cmake ninja c++ python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        printf '%s: %s\n' "$cmd" "$(command -v "$cmd")"
    else
        printf '%s: MISSING\n' "$cmd"
    fi
done
cmake --version 2>/dev/null | head -1
c++ --version 2>/dev/null | head -1
python3 --version 2>/dev/null

section "PYTHON CONVERTER DEPENDENCIES"
python3 - <<'PY'
for name in ("torch", "numpy", "safetensors", "transformers", "huggingface_hub"):
    try:
        module = __import__(name)
        print(f"{name}: {getattr(module, '__version__', 'installed')}")
    except Exception as exc:
        print(f"{name}: MISSING ({type(exc).__name__}: {exc})")
PY

section "DISK"
df -h "$HOME"
du -sh "$HOME/models" "$HOME/llama-cpp-cuda" 2>/dev/null || true

section "EXISTING LLAMA.CPP"
for bin in "$HOME/llama-cpp-cuda/build/bin/llama-cli" "$HOME/llama-cpp-cuda/build/bin/llama-server" /usr/local/bin/llama-cli /usr/local/bin/llama-server; do
    if [[ -x "$bin" ]]; then
        echo "$bin"
        "$bin" --version 2>&1 | head -8
    fi
done

section "RESULT"
echo "Preflight only: no downloads, builds, model loads, or generation were started."
echo "Report: $OUT"
