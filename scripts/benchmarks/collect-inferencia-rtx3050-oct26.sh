#!/usr/bin/env bash
# Collect reproducibility artifacts for "Inferencia en RTX 3050 4Gb oct26".
# Does not copy model weights, credentials, shell history, or unrelated home files.
set -Eeuo pipefail
umask 077

ROOT="${HOME}/benchmarks"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${ROOT}/inferencia-rtx3050-4gb-oct26-collection-${STAMP}"
mkdir -p "${DEST}"/{environment,scripts,results,logs,hashes}
: > "${DEST}/environment/missing-artifacts.txt"
: > "${DEST}/environment/copied-files.txt"
: > "${DEST}/environment/copied-directories.txt"
printf 'Collection created: %s\n' "$DEST"

capture() {
  local name="$1"; shift
  { "$@"; } > "${DEST}/environment/${name}.txt" 2>&1 || true
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
copy_if_file "${ROOT}/qwen3-30b-a3b-iq3-xxs/report-inferencia-denso-octubre-2026.md" "${DEST}/results/report-inferencia-denso-octubre-2026.md"
copy_if_dir "${ROOT}/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737" "${DEST}/results/layer-sweep-20261022-115737"
copy_if_dir "${ROOT}/qwen3-30b-a3b-iq3-xxs/tensorfold-qwen35-2b-4bit-20261022-121705" "${DEST}/results/tensorfold-qwen35-2b-4bit-20261022-121705"

# Collect benchmark evidence from known experiment roots, but never model weights
# or runtime caches. Preserve relative paths so logs remain traceable to experiments.
collect_evidence_tree() {
  local src="$1" label="$2" file rel
  if [[ ! -d "$src" ]]; then
    printf 'MISSING evidence directory: %s\n' "$src" >> "${DEST}/environment/missing-artifacts.txt"
    return
  fi
  while IFS= read -r -d '' file; do
    case "$file" in
      *.gguf|*.safetensors|*.bin|*/cache/*|*/strata-bench-cache/*|*/.cache/*) continue ;;
    esac
    case "$file" in
      *.log|*.csv|*.json|*.jsonl|*.txt|*.time|*.md|*.tsv|*.sh|*.py)
        rel="${file#"$src"/}"
        mkdir -p "${DEST}/results/${label}/$(dirname "$rel")"
        cp -p "$file" "${DEST}/results/${label}/$rel"
        printf '%s\n' "$file" >> "${DEST}/environment/copied-files.txt"
        ;;
    esac
  done < <(find "$src" -type f -print0)
}
collect_evidence_tree "${ROOT}/qwen3-30b-a3b-iq3-xxs" "qwen3-30b-a3b-iq3-xxs"
collect_evidence_tree "${ROOT}/qwen3.5-35b-a3b-iq2-xxs" "qwen3.5-35b-a3b-iq2-xxs"
collect_evidence_tree "${ROOT}/head-to-head-20261021" "head-to-head-20261021"

# Collect root-level benchmark scripts and backups for the earlier 4B comparison.
while IFS= read -r -d '' file; do
  case "$file" in
    *.sh|*.sh.bak*|*.report-fix.bak)
      cp -p "$file" "${DEST}/scripts/$(basename "$file")"
      printf '%s\n' "$file" >> "${DEST}/environment/copied-files.txt"
      ;;
  esac
done < <(find "$ROOT" -maxdepth 1 -type f \( -name '*qwen35*4b*.sh' -o -name 'benchmark-strata-vs-llamacpp.sh' \) -print0)

# Deduplicate inventory entries; preserve a readable empty-state file.
sort -u "${DEST}/environment/copied-files.txt" -o "${DEST}/environment/copied-files.txt"
sort -u "${DEST}/environment/copied-directories.txt" -o "${DEST}/environment/copied-directories.txt"
if [[ ! -s "${DEST}/environment/missing-artifacts.txt" ]]; then
  printf 'None of the explicitly requested paths were missing. This does not prove the collection is exhaustive.\n' > "${DEST}/environment/missing-artifacts.txt"
fi

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

ARCHIVE="${DEST}.tar.gz"
tar -C "$(dirname "$DEST")" -czf "$ARCHIVE" "$(basename "$DEST")"
sha256sum "$ARCHIVE" > "${ARCHIVE}.sha256"
printf '\nCollection complete.\nDirectory: %s\nArchive: %s\nArchive hash: %s.sha256\n' "$DEST" "$ARCHIVE" "$ARCHIVE"
printf 'Review %s/environment/missing-artifacts.txt and redact sensitive local paths before sharing. Model weights were not copied.\n' "$DEST"
