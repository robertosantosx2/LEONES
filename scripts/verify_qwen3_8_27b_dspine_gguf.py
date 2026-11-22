#!/usr/bin/env python3
"""Download and validate the fork-compatible Qwen3.8-27B DSpine GGUF drafter."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from huggingface_hub import hf_hub_download

LLAMA_DIR = Path(os.environ["LLAMA_CPP_DIR"])
OUT_DIR = Path(os.environ.get("RUNNER_TEMP", "/tmp"))
REPO_ID = "aj9o9/Qwen3.8-27B-DSpine-b16-GGUF"
FILENAME = "Qwen3.8-27B-DSpine-b16-Q4_K_M.gguf"


def main() -> None:
    import sys
    sys.path.insert(0, str(LLAMA_DIR / "gguf-py"))
    from gguf import GGUFReader

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model_path = Path(hf_hub_download(repo_id=REPO_ID, filename=FILENAME, local_dir=OUT_DIR))
    reader = GGUFReader(model_path, "r")
    names = {tensor.name for tensor in reader.tensors}

    required = {
        "dspine_codebook.weight",
        "dspine_gate.weight",
        "dspine_gate.bias",
        "dspine_pred_gate.weight",
        "dspine_prev.weight",
    }
    missing = sorted(required - names)
    read_layers = sorted(
        name for name in names
        if name.startswith("blk.") and ".dspine_read.weight" in name
    )
    write_layers = sorted(
        name for name in names
        if name.startswith("blk.") and ".dspine_write.weight" in name
    )
    if missing or len(read_layers) != 5 or len(write_layers) != 5:
        raise RuntimeError(
            f"Unexpected DSpine GGUF tensor inventory: missing={missing}, "
            f"read_layers={read_layers}, write_layers={write_layers}"
        )

    def scalar(name: str):
        field = reader.fields.get(name)
        return None if field is None else field.contents()

    block_size = scalar("dflash.block_size")
    selector_top_k = scalar("dflash.selector_top_k")
    if block_size != 16 or selector_top_k != 16:
        raise RuntimeError(
            f"Unexpected DSpine metadata: block_size={block_size}, selector_top_k={selector_top_k}"
        )

    digest = hashlib.sha256()
    with model_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)

    report = {
        "repo_id": REPO_ID,
        "filename": FILENAME,
        "path": str(model_path),
        "size_bytes": model_path.stat().st_size,
        "sha256": digest.hexdigest(),
        "status": "GGUF_DSPINE_TENSORS_AND_METADATA_VALID",
        "block_size": block_size,
        "selector_top_k": selector_top_k,
        "read_tensor_count": len(read_layers),
        "write_tensor_count": len(write_layers),
        "read_tensors": read_layers,
        "write_tensors": write_layers,
    }
    report_path = OUT_DIR / "qwen3.8-27b-dspine-gguf-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
