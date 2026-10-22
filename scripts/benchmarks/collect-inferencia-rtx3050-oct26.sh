#!/usr/bin/env bash
# Collect reproducibility artifacts for "Inferencia en RTX 3050 4Gb oct26".
# Does not copy model weights, credentials, shell history, or unrelated home files.
set -Eeuo pipefail
umask 077

ROOT="${HOME}/benchmarks"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${ROOT}/inferencia-rtx3050-4gb-oct26-collection-${STAMP}"
mkdir -p "${DEST}"/{environment,scripts,results,logs,hashes}
printf 'Collection created: %s\n' "$DEST"

capture() {
  local name="$1"; shift
  { "$@" ; } > "${DEST}/environment/${name}.txt" 2>&1 || true
}
capture system-date date --iso-8601=seconds
capture uname uname -a
capture os-release cat /etc/os-release
capture lscpu lscpu
capture memory free -h
capture swap swapon --show
capture nvidia-smi nvidia-smi
capture nvidia-smi-query nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu,utilization.memory,temperature.gpu,power.draw --format=csv
capture nvidia-smi-full nvidia-smi -q
capture nvcc nvcc --version
capture tensorfold-version "${HOME}/.local/opt/tensorfold-1.1.1-linux-x86_64/bin/tensorfold-native" --version
capture strata-version "${HOME}/rusting-strata-test/target/release/strata" --version
capture llama-bench-version "${HOME}/llama.cpp-cuda/build-cuda/bin/llama-bench" --version
capture llama-git git -C "${HOME}/llama.cpp-cuda" rev-parse HEAD
capture strata-git git -C "${HOME}/rusting-strata-test" rev-parse HEAD

copy_if_file() {
  local src="$1" dst="$2"
  if [[ -f "$src" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp -p "$src" "$dst"
    printf '%s\n' "$src" >> "${DEST}/environment/copied-files.txt"
  else
    printf 'MISSING file: %s\n' "$src" >> "${DEST}/environment/missing-artifacts.txt"
  fi
}
copy_if_dir() {
  local src="$1" dst="$2"
  if [[ -d "$src" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
    printf '%s\n' "$src" >> "${DEST}/environment/copied-directories.txt"
  else
    printf 'MISSING directory: %s\n' "$src" >> "${DEST}/environment/missing-artifacts.txt"
  fi
}

copy_if_file "${ROOT}/qwen3-30b-a3b-iq3-xxs/benchmark-layer-sweep.sh" "${DEST}/scripts/benchmark-layer-sweep.sh"
copy_if_file "${ROOT}/qwen3-30b-a3b-iq3-xxs/benchmark-tensorfold.sh" "${DEST}/scripts/benchmark-tensorfold.sh"
copy_if_file "${ROOT}/benchmark_qwen35_4b_three_engines_fixed_v2.sh" "${DEST}/scripts/benchmark_qwen35_4b_three_engines_fixed_v2.sh"
copy_if_dir "${ROOT}/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737" "${DEST}/results/layer-sweep-20261022-115737"
copy_if_dir "${ROOT}/qwen3-30b-a3b-iq3-xxs/tensorfold-qwen35-2b-4bit-20261022-121705" "${DEST}/results/tensorfold-qwen35-2b-4bit-20261022-121705"
copy_if_file "${ROOT}/qwen3-30b-a3b-iq3-xxs/report-inferencia-denso-octubre-2026.md" "${DEST}/results/report-inferencia-denso-octubre-2026.md"
copy_if_file "${ROOT}/qwen3-30b-a3b-iq3-xxs/benchmark-layer-sweep.sh" "${DEST}/scripts/benchmark-layer-sweep.sh"

# Include previous 4B experiment outputs if their directory is present.
for d in "${ROOT}"/*qwen35*4b* "${ROOT}"/qwen35-4b*; do
  [[ -d "$d" ]] || continue
  copy_if_dir "$d" "${DEST}/results/$(basename "$d")"
done

# Hash all collected text/data artifacts. Do not hash the archive into itself.
find "${DEST}/scripts" "${DEST}/results" "${DEST}/environment" -type f -print0 \
  | sort -z | xargs -0 -r sha256sum > "${DEST}/hashes/artifacts.sha256"

# Record model hashes without copying large model weights.
{
  for f in \
    "${HOME}/benchmarks/qwen3-30b-a3b-iq3-xxs/Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf" \
    "${HOME}/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf" \
    "${HOME}/benchmarks/qwen3-30b-a3b-iq3-xxs/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf"; do
    if [[ -f "$f" ]]; then sha256sum "$f"; else printf 'MISSING model: %s\n' "$f"; fi
  done
} > "${DEST}/hashes/model-sha256.txt" 2>&1

# Package output beside the collection directory so it is not included recursively.
ARCHIVE="${DEST}.tar.gz"
tar -C "$(dirname "$DEST")" -czf "$ARCHIVE" "$(basename "$DEST")"
sha256sum "$ARCHIVE" > "${ARCHIVE}.sha256"
printf '\nCollection complete.\nDirectory: %s\nArchive: %s\nArchive hash: %s.sha256\n' "$DEST" "$ARCHIVE" "$ARCHIVE"
printf 'Review missing-artifacts.txt and redact any sensitive local paths before sharing. Model weights were not copied.\n'
