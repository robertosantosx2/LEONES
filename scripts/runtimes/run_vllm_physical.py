#!/usr/bin/env python3
"""Prepare/execute the vLLM CPD physical execution boundary."""
from __future__ import annotations

import argparse
import json
import shlex


def build_command(model: str, host: str, port: int, *, tensor_parallel_size: int = 1) -> list[str]:
    return [
        "vllm", "serve", model,
        "--host", host,
        "--port", str(port),
        "--tensor-parallel-size", str(tensor_parallel_size),
    ]


def build_request(model: str, prompt: str, max_tokens: int, temperature: float, top_p: float) -> dict:
    return {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--tensor-parallel-size", type=int, default=1)
    p.add_argument("--max-tokens", type=int, default=128)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--top-p", type=float, default=1.0)
    p.add_argument("--execute", action="store_true", help="Reserved for the physical-host execution stage")
    args = p.parse_args()

    command = build_command(args.model, args.host, args.port, tensor_parallel_size=args.tensor_parallel_size)
    request = build_request(args.model, args.prompt, args.max_tokens, args.temperature, args.top_p)
    plan = {
        "runtime": "vLLM",
        "profile": "cpd",
        "requires_physical_host": True,
        "execution_authorized": bool(args.execute),
        "server_command": command,
        "server_command_shell": shlex.join(command),
        "api": f"http://{args.host}:{args.port}/v1/completions",
        "request": request,
        "measurement_contract": "runtime-benchmark-evidence.v1.1",
    }
    print(json.dumps(plan, indent=2))
    if not args.execute:
        return 0
    raise SystemExit("Physical vLLM execution is intentionally gated for the CPD host stage.")


if __name__ == "__main__":
    raise SystemExit(main())
