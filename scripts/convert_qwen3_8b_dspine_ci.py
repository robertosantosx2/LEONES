#!/usr/bin/env python3
"""Prepare the minimum target HF files and convert the official Qwen3-8B DSpine draft."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

TARGET_REPO = os.environ.get("DSPINE_TARGET_REPO", "Qwen/Qwen3-8B")
DRAFT_REPO = os.environ.get("DSPINE_DRAFT_REPO", "tencent/Qwen3-8B-DSpine-b16")
ROOT = Path(os.environ.get("RUNNER_TEMP", "/tmp"))
TARGET_DIR = ROOT / "qwen3-8b-target-hf"
DRAFT_DIR = ROOT / "qwen3-8b-dspine-hf"
LLAMA_DIR = ROOT / "llama.cpp-dspine"
OUTPUT = ROOT / "Qwen3-8B-DSpine-b16-BF16.gguf"


def main() -> None:
    print(f"Download target metadata/tokenizer: {TARGET_REPO}", flush=True)
    snapshot_download(
        repo_id=TARGET_REPO,
        local_dir=TARGET_DIR,
        allow_patterns=["*.json", "*.txt", "*.model", "*.jinja"],
    )

    index_path = TARGET_DIR / "model.safetensors.index.json"
    if not index_path.is_file():
        raise FileNotFoundError(f"Target safetensors index missing: {index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    weight_map = index.get("weight_map", {})
    config = json.loads((TARGET_DIR / "config.json").read_text(encoding="utf-8"))
    tie_embeddings = bool(config.get("tie_word_embeddings", False))
    needed = ["model.embed_tokens.weight"]
    if not tie_embeddings:
        needed.append("lm_head.weight")

    for tensor_name in needed:
        shard = weight_map.get(tensor_name)
        if not shard:
            raise KeyError(f"Target index has no shard for {tensor_name}")
        print(f"Download target tensor shard: {tensor_name} -> {shard}", flush=True)
        hf_hub_download(repo_id=TARGET_REPO, filename=shard, local_dir=TARGET_DIR)

    print(f"Download DSpine draft checkpoint: {DRAFT_REPO}", flush=True)
    snapshot_download(
        repo_id=DRAFT_REPO,
        local_dir=DRAFT_DIR,
        allow_patterns=["*.json", "*.txt", "*.model", "*.jinja", "*.safetensors", "*.pt"],
    )

    print("Clone llama.cpp DSpine branch", flush=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", "--branch", "dspine",
         "https://github.com/Ajay9o9/llama.cpp.git", str(LLAMA_DIR)],
        check=True,
    )
    print("Pinned llama.cpp commit:", subprocess.check_output(
        ["git", "-C", str(LLAMA_DIR), "rev-parse", "HEAD"], text=True
    ).strip(), flush=True)

    env = os.environ.copy()
    env.update({
        "LLAMA_CPP_DIR": str(LLAMA_DIR),
        "QWEN3_8B_TARGET_DIR": str(TARGET_DIR),
        "QWEN3_8B_DSPINE_DIR": str(DRAFT_DIR),
        "QWEN3_8B_DSPINE_GGUF": str(OUTPUT),
    })
    script = Path(__file__).resolve().parent / "prepare_qwen3_8b_dspine_gguf.sh"
    subprocess.run(["bash", str(script)], check=True, env=env)
    print(f"CONVERSION_OK={OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
