#!/usr/bin/env bash
set -Eeuo pipefail

LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-}"
TARGET_DIR="${QWEN3_8B_TARGET_DIR:-}"
DRAFT_DIR="${QWEN3_8B_DSPINE_DIR:-}"
OUTPUT="${QWEN3_8B_DSPINE_GGUF:-$PWD/Qwen3-8B-DSpine-b16-BF16.gguf}"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
info() { printf '[DSpine GGUF] %s\n' "$*"; }

[[ -n "$LLAMA_CPP_DIR" && -d "$LLAMA_CPP_DIR" ]] || die "Set LLAMA_CPP_DIR to the Ajay9o9/llama.cpp dspine checkout"
[[ -f "$LLAMA_CPP_DIR/convert_hf_to_gguf.py" ]] || die "convert_hf_to_gguf.py not found"
[[ -d "$TARGET_DIR" ]] || die "Set QWEN3_8B_TARGET_DIR to a local Qwen3-8B HF snapshot"
[[ -d "$DRAFT_DIR" ]] || die "Set QWEN3_8B_DSPINE_DIR to a local tencent/Qwen3-8B-DSpine-b16 HF snapshot"
[[ -f "$TARGET_DIR/config.json" && -f "$DRAFT_DIR/config.json" ]] || die "Both local snapshots need config.json"
[[ -f "$DRAFT_DIR/model.safetensors.index.json" || -n "$(find "$DRAFT_DIR" -maxdepth 1 -name '*.safetensors' -print -quit)" ]] || die "DSpine safetensors weights not found"

command -v python3 >/dev/null || die "python3 is required"
python3 - <<'PY' || die "Install the converter dependencies (at least torch, numpy and safetensors) in this Python environment"
import torch, numpy, safetensors
print("torch", torch.__version__)
print("numpy", numpy.__version__)
print("safetensors", safetensors.__version__)
PY

info "Converting the official Qwen3-8B DSpine draft using the target's tokenizer/metadata"
info "Output is BF16; do not quantize code-bridge tensors blindly."
python3 "$LLAMA_CPP_DIR/convert_hf_to_gguf.py" "$DRAFT_DIR" \
  --target-model-dir "$TARGET_DIR" \
  --outtype bf16 \
  --outfile "$OUTPUT"

[[ -s "$OUTPUT" ]] || die "Converter did not create $OUTPUT"

info "Verify GGUF contains the DSpine bridge tensors"
PYTHONPATH="$LLAMA_CPP_DIR/gguf-py" python3 - "$OUTPUT" <<'PY'
import sys
from gguf import GGUFReader

path = sys.argv[1]
reader = GGUFReader(path, "r")
names = {tensor.name for tensor in reader.tensors}
required = {
    "dspine_codebook.weight",
    "dspine_gate.weight",
    "dspine_gate.bias",
    "dspine_pred_gate.weight",
    "dspine_prev.weight",
}
missing = sorted(required - names)
read_layers = sorted(name for name in names if name.startswith("blk.") and ".dspine_read.weight" in name)
write_layers = sorted(name for name in names if name.startswith("blk.") and ".dspine_write.weight" in name)
print("GGUF:", path)
print("Tensor count:", len(names))
print("DSpine read tensors:", len(read_layers))
print("DSpine write tensors:", len(write_layers))
if missing or not read_layers or len(read_layers) != len(write_layers):
    print("Missing global tensors:", missing)
    print("Read tensors:", read_layers)
    print("Write tensors:", write_layers)
    raise SystemExit("DSpine GGUF validation failed")
print("DSpine tensor inventory: PASS")
PY

info "Conversion and static GGUF tensor check completed."
info "This does not load the target/drafter or prove generation correctness."
