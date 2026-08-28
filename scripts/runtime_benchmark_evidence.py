#!/usr/bin/env python3
"""Run a shell-free inference command and emit reusable LEONES evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from statistics import mean, median, stdev

TOKENS_PER_SECOND = re.compile(
    r"(?:Generation:\s*)?([0-9]+(?:[.,][0-9]+)?)\s*(?:tok(?:ens)?|t)/s",
    re.I,
)
LLAMA_CPP_GENERATION_TPS = re.compile(
    r"Generation:\s*([0-9]+(?:[.,][0-9]+)?)\s*t/s", re.I
)
LLAMA_CPP_REVISION = re.compile(r"commit\s+([0-9a-f]+)", re.I)


def now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def command_version(executable: str) -> str:
    try:
        proc = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    text = (proc.stdout + "\n" + proc.stderr).strip()
    return text.splitlines()[0] if text else "unknown"


def runtime_revision(version: str) -> str | None:
    match = LLAMA_CPP_REVISION.search(version)
    return match.group(1) if match else None


def command_output_token_limit(command: list[str]) -> int | None:
    for flag in ("-n", "--predict", "--n-predict"):
        if flag in command:
            i = command.index(flag)
            if i + 1 < len(command):
                try:
                    value = int(command[i + 1])
                except ValueError:
                    return None
                return value if value > 0 else None
    return None


def infer_backend(command: list[str], explicit: str | None) -> str | None:
    if explicit:
        return explicit
    for flag in ("-ngl", "--n-gpu-layers"):
        if flag in command:
            i = command.index(flag)
            if i + 1 < len(command):
                try:
                    return "gpu" if int(command[i + 1]) > 0 else "cpu"
                except ValueError:
                    return None
    return "cpu"


def hardware() -> dict:
    ram_total_mb = 0
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        ram_total_mb = int(pages * page_size / 1024 / 1024)
    except (AttributeError, OSError, ValueError):
        pass

    cpu = platform.processor() or ""
    if not cpu and Path("/proc/cpuinfo").exists():
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
                if line.lower().startswith("model name") and ":" in line:
                    cpu = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
    cpu = cpu or platform.machine() or "unknown"
    return {"os": platform.platform(), "cpu": cpu, "ram_total_mb": ram_total_mb}


def peak_memory_mb() -> float | None:
    try:
        import resource

        value = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        return round(value / 1024, 3) if value else None
    except (ImportError, AttributeError, OSError):
        return None


def gpu_snapshot() -> tuple[float | None, float | None]:
    if not shutil.which("nvidia-smi"):
        return None, None
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    line = next((x.strip() for x in proc.stdout.splitlines() if x.strip()), "")
    if not line:
        return None, None
    parts = [x.strip() for x in line.split(",")]
    try:
        return float(parts[0]), float(parts[1])
    except (IndexError, ValueError):
        return None, None


def run_once(command: list[str]) -> dict:
    started = time.perf_counter()
    first_output = None
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
    )
    import selectors

    sel = selectors.DefaultSelector()
    assert proc.stdout is not None and proc.stderr is not None
    sel.register(proc.stdout, selectors.EVENT_READ, "stdout")
    sel.register(proc.stderr, selectors.EVENT_READ, "stderr")
    while sel.get_map():
        for key, _ in sel.select(timeout=0.1):
            line = key.fileobj.readline()
            if line == "":
                sel.unregister(key.fileobj)
                continue
            if first_output is None and line.strip():
                first_output = (time.perf_counter() - started) * 1000
            (stdout_chunks if key.data == "stdout" else stderr_chunks).append(line)
    code = proc.wait()
    total = (time.perf_counter() - started) * 1000
    text = "".join(stdout_chunks) + "\n" + "".join(stderr_chunks)
    llama_matches = LLAMA_CPP_GENERATION_TPS.findall(text)
    if llama_matches:
        tps = float(llama_matches[-1].replace(",", "."))
    else:
        matches = TOKENS_PER_SECOND.findall(text)
        tps = float(matches[-1].replace(",", ".")) if matches else None

    output_tokens = command_output_token_limit(command)
    generation_ms = (
        output_tokens / tps * 1000
        if output_tokens is not None and tps and tps > 0
        else None
    )
    vram, power = gpu_snapshot()
    return {
        # First non-empty process output is intentionally NOT called TTFT:
        # llama-cli emits startup/prompt text before generated tokens.
        "ttft_ms": None,
        "first_output_ms": first_output,
        "generation_time_ms": generation_ms,
        "output_tokens": output_tokens,
        "tokens_per_second": tps,
        "total_time_ms": round(total, 3),
        "peak_memory_mb": peak_memory_mb(),
        "peak_vram_mb": vram,
        "power_w": power,
        "exit_code": code,
        "stdout": "".join(stdout_chunks),
        "stderr": "".join(stderr_chunks),
    }


def summary(measurements: list[dict]) -> dict:
    result: dict = {}
    for key in (
        "ttft_ms",
        "generation_time_ms",
        "tokens_per_second",
        "total_time_ms",
        "peak_memory_mb",
        "peak_vram_mb",
        "power_w",
    ):
        vals = [float(m[key]) for m in measurements if m.get(key) is not None]
        if not vals:
            continue
        result[key] = {
            "mean": mean(vals),
            "median": median(vals),
            "min": min(vals),
            "max": max(vals),
        }
        if len(vals) > 1:
            result[key]["stdev"] = stdev(vals)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--command-json", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--artifact", type=Path, required=True)
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--model-name", required=True)
    ap.add_argument("--model-revision", required=True)
    ap.add_argument("--quantization", required=True)
    ap.add_argument("--context", type=int, required=True)
    ap.add_argument("--prompt-protocol-id", required=True)
    ap.add_argument("--prompt", default="")
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--cooldown-seconds", type=float, default=5.0)
    ap.add_argument("--output-token-limit", type=int, default=128)
    ap.add_argument("--protocol-id", required=True)
    ap.add_argument("--protocol-sha256", required=True)
    ap.add_argument("--runtime", default="llama.cpp")
    ap.add_argument("--backend", default=None)
    args = ap.parse_args()

    if args.warmup < 0:
        raise SystemExit("warmup must be >= 0")
    if args.iterations < 5:
        raise SystemExit("iterations must be >= 5 for runtime-benchmark-evidence.v1.1")
    if args.cooldown_seconds < 0:
        raise SystemExit("cooldown-seconds must be >= 0")
    if args.output_token_limit < 1:
        raise SystemExit("output-token-limit must be >= 1")
    if not re.fullmatch(r"[a-f0-9]{64}", args.protocol_sha256):
        raise SystemExit("protocol-sha256 must be a lowercase 64-character SHA-256")

    command = json.loads(args.command_json.read_text(encoding="utf-8"))
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise SystemExit("command-json must contain a non-empty JSON string array")

    command_limit = command_output_token_limit(command)
    if command_limit != args.output_token_limit:
        raise SystemExit(
            f"command output-token limit {command_limit!r} does not match protocol "
            f"{args.output_token_limit}"
        )

    version = command_version(command[0])
    backend = infer_backend(command, args.backend)

    warmups = []
    for _ in range(args.warmup):
        warmups.append(run_once(command))
        if args.cooldown_seconds:
            time.sleep(args.cooldown_seconds)

    start = now()
    measurements = []
    for i in range(1, args.iterations + 1):
        m = run_once(command)
        m["iteration"] = i
        measurements.append(m)
        if i != args.iterations and args.cooldown_seconds:
            time.sleep(args.cooldown_seconds)
    end = now()

    artifact = args.artifact.resolve()
    if not artifact.exists() or not artifact.is_file():
        raise SystemExit(f"artifact does not exist: {artifact}")

    successful_runs = sum(m["exit_code"] == 0 for m in measurements)
    warmup_success = all(m["exit_code"] == 0 for m in warmups)
    complete_metrics = all(
        m["exit_code"] == 0
        and m["tokens_per_second"] is not None
        and m["output_tokens"] == args.output_token_limit
        and m["generation_time_ms"] is not None
        for m in measurements
    )
    valid = (
        successful_runs == args.iterations
        and warmup_success
        and complete_metrics
    )

    evidence = {
        "schema": "runtime-benchmark-evidence.v1.1",
        "status": "valid" if valid else "invalid",
        "execution_id": "rt-" + uuid.uuid4().hex,
        "timestamp_start": start,
        "timestamp_end": end,
        "model": {
            "id": args.model_id,
            "name": args.model_name,
            "revision": args.model_revision,
            "artifact": str(artifact),
            "quantization": args.quantization,
            "context_length": args.context,
        },
        "protocol": {
            "protocol_id": args.protocol_id,
            "protocol_sha256": args.protocol_sha256,
            "prompt_protocol_id": args.prompt_protocol_id,
            "prompt": args.prompt,
            "context": args.context,
            "output_token_limit": args.output_token_limit,
            "warmup_iterations": args.warmup,
            "measurement_iterations": args.iterations,
            "cooldown_seconds": args.cooldown_seconds,
            "ttft_method": "not_available_from_llama_cli_stdout",
        },
        "runtime": {
            "name": args.runtime,
            "version": version,
            "revision": runtime_revision(version),
            "backend": backend,
            "command": command,
        },
        "hardware": hardware(),
        "warmup": {
            "count": len(warmups),
            "exit_codes": [m["exit_code"] for m in warmups],
        },
        "measurements": measurements,
        "summary": summary(measurements),
        "acceptance": {
            "minimum_successful_runs": 5,
            "successful_runs": successful_runs,
            "warmup_success": warmup_success,
            "complete_metrics": complete_metrics,
            "require_exit_code_zero": True,
            "allow_partial_results": False,
            "require_output_token_limit_match": True,
        },
        "process": {
            "exit_code": max(m["exit_code"] for m in measurements),
            "stdout": "\n".join(m["stdout"] for m in measurements),
            "stderr": "\n".join(m["stderr"] for m in measurements),
        },
        "artifact": {
            "path": str(artifact),
            "sha256": sha256_file(artifact),
            "size": artifact.stat().st_size,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "execution_id": evidence["execution_id"],
                "status": evidence["status"],
                "output": str(args.output),
                "summary": evidence["summary"],
            },
            indent=2,
        )
    )
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
