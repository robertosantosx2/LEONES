#!/usr/bin/env bash
set -uo pipefail

BASE="$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs"
M="$BASE/Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf"
LLAMA="$HOME/llama.cpp-cuda/build-cuda/bin/llama-cli"
STRATA="$HOME/rusting-strata-test/target/release/strata"
NVRTC="$HOME/rusting-strata-test/vendor/nvrtc13/root/usr/local/cuda-13.0/targets/x86_64-linux/lib"
OUT="$BASE/head-to-head-20261021"
PROMPT="Responde brevemente en español: ¿qué es la inferencia local?"

mkdir -p "$OUT/llama" "$OUT/strata"
export LD_LIBRARY_PATH="$NVRTC${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=8

echo "===== VALIDACIÓN ====="
test -r "$M" || { echo "No se encuentra el modelo: $M"; exit 1; }
test -x "$LLAMA" || { echo "No se encuentra llama-cli: $LLAMA"; exit 1; }
test -x "$STRATA" || { echo "No se encuentra strata: $STRATA"; exit 1; }
sha256sum "$M"
"$LLAMA" --version
"$STRATA" --version
nvidia-smi
free -h

run_llama() {
  local i="$1"
  local d="$OUT/llama"
  echo "llama.cpp ejecución $i/6"

  /usr/bin/time -v -o "$d/time-$i.txt" \
    "$LLAMA" \
      --model "$M" \
      --n-gpu-layers 14 \
      --fit off \
      --ctx-size 1024 \
      --batch-size 64 \
      --ubatch-size 32 \
      --threads 8 \
      --predict 128 \
      --temp 0 \
      --seed 42 \
      --prompt "$PROMPT" \
      --single-turn \
      --simple-io \
      --verbose \
      > "$d/rep-$i.log" 2>&1

  local rc=$?
  echo "$rc" > "$d/rc-$i.txt"
  echo "llama.cpp ejecución $i: RC=$rc"
  if [ "$rc" -ne 0 ]; then
    tail -50 "$d/rep-$i.log"
    return "$rc"
  fi
}

run_strata() {
  local i="$1"
  local d="$OUT/strata"
  echo "RustingStrata ejecución $i/6"

  XDG_CACHE_HOME="$OUT/strata/cache" \
  /usr/bin/time -v -o "$d/time-$i.txt" \
    "$STRATA" generate \
      --model "$M" \
      --gpu \
      --ctx 1024 \
      --threads 8 \
      --prompt "$PROMPT" \
      -n 128 \
      --temp 0 \
      > "$d/rep-$i.log" 2>&1

  local rc=$?
  echo "$rc" > "$d/rc-$i.txt"
  echo "RustingStrata ejecución $i: RC=$rc"
  if [ "$rc" -ne 0 ]; then
    tail -50 "$d/rep-$i.log"
    return "$rc"
  fi
}

echo
echo "===== LLAMA.CPP: 1 inicial + 5 repeticiones ====="
for i in 1 2 3 4 5 6; do
  run_llama "$i" || {
    echo "Serie llama.cpp detenida en ejecución $i"
    break
  }
done

echo
echo "===== RUSTINGSTRATA: 1 inicial + 5 repeticiones ====="
for i in 1 2 3 4 5 6; do
  run_strata "$i" || {
    echo "Serie RustingStrata detenida en ejecución $i"
    break
  }
done

echo
echo "===== RESUMEN LLAMA.CPP ====="
for i in 1 2 3 4 5 6; do
  [ -f "$OUT/llama/time-$i.txt" ] || continue
  echo "--- ejecución $i; RC=$(cat "$OUT/llama/rc-$i.txt") ---"
  grep -E 'Elapsed \(wall clock\) time|Maximum resident set size|Exit status' \
    "$OUT/llama/time-$i.txt"
  grep -E 'prompt eval time|^[[:space:]]*\| eval time =' \
    "$OUT/llama/rep-$i.log" | tail -4
done

echo
echo "===== RESUMEN RUSTINGSTRATA ====="
for i in 1 2 3 4 5 6; do
  [ -f "$OUT/strata/time-$i.txt" ] || continue
  echo "--- ejecución $i; RC=$(cat "$OUT/strata/rc-$i.txt") ---"
  grep -E 'Elapsed \(wall clock\) time|Maximum resident set size|Exit status' \
    "$OUT/strata/time-$i.txt"
  grep -Ei 'prompt.*tok|gen .*tok|expert hit|cache swaps|CPU expert compute' \
    "$OUT/strata/rep-$i.log" | tail -10
done

echo
echo "Resultados: $OUT"
