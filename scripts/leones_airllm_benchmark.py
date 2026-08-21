#!/usr/bin/env python3
"""Run a small physical LEONES benchmark through AirLLM.

This runner is deliberately local: AirLLM is an optional dependency and the
result is a measurement only when the model was actually loaded and generated
new tokens. It uses the official AirLLM AutoModel API and records timing and
basic environment information without pretending to be a universal score.
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone

PROMPT = "Write one concise sentence explaining what a language model does."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("--prompt", default=PROMPT)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--compression", choices=["4bit", "8bit"])
    args = parser.parse_args()

    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        import torch
        from airllm import AutoModel
    except ImportError as exc:
        raise SystemExit(f"AirLLM benchmark dependencies unavailable: {exc}")

    kwargs = {}
    if args.compression:
        kwargs["compression"] = args.compression
    load_t0 = time.perf_counter()
    model = AutoModel.from_pretrained(args.model, **kwargs)
    load_seconds = time.perf_counter() - load_t0

    tokens = model.tokenizer(
        [args.prompt], return_tensors="pt", return_attention_mask=False,
        truncation=True, max_length=args.max_length, padding=False,
    )
    input_ids = tokens["input_ids"]
    if torch.cuda.is_available():
        input_ids = input_ids.cuda()
    gen_t0 = time.perf_counter()
    output = model.generate(
        input_ids, max_new_tokens=args.max_new_tokens,
        use_cache=True, return_dict_in_generate=True,
    )
    generation_seconds = time.perf_counter() - gen_t0
    sequence = output.sequences[0]
    generated_tokens = max(0, int(sequence.shape[-1] - input_ids.shape[-1]))
    tps = generated_tokens / generation_seconds if generation_seconds > 0 else None
    decoded = model.tokenizer.decode(sequence, skip_special_tokens=True)

    result = {
        "schema_version": "leones.runtime-benchmark.v1",
        "status": "measured",
        "evidence_status": "measured",
        "runtime": "airllm",
        "model": args.model,
        "observed_at": started,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cuda_available": bool(torch.cuda.is_available()),
        "prompt_tokens": int(input_ids.shape[-1]),
        "generated_tokens": generated_tokens,
        "generation_seconds": generation_seconds,
        "tokens_per_second": tps,
        "load_seconds": load_seconds,
        "output_preview": decoded[-1000:],
        "measurement_scope": "single local generation; not a quality benchmark",
        "elapsed_seconds": time.perf_counter() - t0,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
