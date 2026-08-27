#!/usr/bin/env python3
"""Shell-free runtime benchmark harness producing LEONES evidence v1.1."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import selectors
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from statistics import mean, median, stdev

TPS_RE = re.compile(r"(?:Generation:\s*)?([0-9]+(?:[.,][0-9]+)?)\s*(?:tok(?:ens)?|t)/s", re.I)
TOKENS_RE = re.compile(r"([0-9]+)\s+tokens?", re.I)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def version(exe: str) -> str:
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10, check=False)
        text = (p.stdout or p.stderr).strip()
        return text.splitlines()[0] if text else "unknown"
    except Exception as exc:
        return f"unavailable: {exc}"


def hardware() -> dict:
    try:
        ram = round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024 / 1024, 2)
    except Exception:
        ram = None
    physical = None
    try:
        rows = subprocess.run(["lscpu", "-p=CPU,Core"], capture_output=True, text=True, timeout=5, check=False).stdout.splitlines()
        rows = {line for line in rows if line and not line.startswith("#")}
        physical = len({line.split(",", 1)[1] for line in rows if "," in line}) or None
    except Exception:
        pass
    gpu = vram = None
    if shutil.which("nvidia-smi"):
        try:
            line = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, check=False,
            ).stdout.strip().splitlines()[0]
            name, memory = line.split(",", 1)
            gpu, vram = name.strip(), float(memory.strip())
        except Exception:
            pass
    return {
        "host": platform.node(), "os": platform.platform(), "kernel": platform.release(),
        "architecture": platform.machine(), "cpu": platform.processor() or platform.uname().processor,
        "cpu_threads": os.cpu_count(), "physical_cores": physical, "ram_total_mb": ram,
        "gpu": gpu, "vram_total_mb": vram,
    }


def child_rss() -> float | None:
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 2)
    except Exception:
        return None


def gpu_snapshot() -> tuple[float | None, float | None]:
    if not shutil.which("nvidia-smi"):
        return None, None
    try:
        line = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,power.draw", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip().splitlines()[0]
        memory, power = line.split(",", 1)
        return float(memory.strip()), float(power.strip())
    except Exception:
        return None, None


def run_once(command: list[str]) -> dict:
    """Run one process and preserve stdout/stderr separately.

    First-output latency is a local observable: time until the first non-empty
    stdout line. It must not be presented as hosted/API TTFT unless stdout is
    known to correspond to the first generated token.
    """
    started = time.perf_counter()
    first_stdout = None
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    while selector.get_map():
        for key, _ in selector.select(0.1):
            line = key.fileobj.readline()
            if line == "":
                selector.unregister(key.fileobj)
                continue
            if key.data == "stdout":
                if first_stdout is None and line.strip():
                    first_stdout = (time.perf_counter() - started) * 1000
                stdout_lines.append(line)
            else:
                stderr_lines.append(line)
    exit_code = process.wait()
    total_ms = (time.perf_counter() - started) * 1000
    stdout, stderr = "".join(stdout_lines), "".join(stderr_lines)
    combined = stdout + "\n" + stderr
    tps = TPS_RE.findall(combined)
    tokens = TOKENS_RE.findall(stdout)
    peak_vram, power = gpu_snapshot()
    return {
        "ttft_ms": first_stdout,
        "first_output_ms": first_stdout,
        "generation_time_ms": max(0, total_ms - first_stdout) if first_stdout is not None else None,
        "output_tokens": int(tokens[-1]) if tokens else None,
        "tokens_per_second": float(tps[-1].replace(",", ".")) if tps else None,
        "total_time_ms": round(total_ms, 3),
        "peak_memory_mb": child_rss(), "peak_vram_mb": peak_vram, "power_w": power,
        "exit_code": exit_code, "stdout": stdout, "stderr": stderr,
    }


def summarize(measurements: list[dict]) -> dict:
    metrics = {}
    for key in ("ttft_ms", "generation_time_ms", "output_tokens", "tokens_per_second", "total_time_ms", "peak_memory_mb", "peak_vram_mb", "power_w"):
        values = [float(item[key]) for item in measurements if item.get(key) is not None]
        if not values:
            continue
        result = {"mean": mean(values), "median": median(values), "min": min(values), "max": max(values)}
        if len(values) > 1:
            result["stdev"] = stdev(values)
        metrics[key] = result
    return {"measurement_count": len(measurements), "metrics": metrics}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--command-json", type=Path, required=True); p.add_argument("--output", type=Path, required=True); p.add_argument("--artifact", type=Path, required=True)
    p.add_argument("--model-id", required=True); p.add_argument("--model-name", required=True); p.add_argument("--model-revision", required=True); p.add_argument("--model-source", default=None); p.add_argument("--quantization", required=True); p.add_argument("--context", type=int, required=True)
    p.add_argument("--prompt-protocol-id", required=True); p.add_argument("--prompt", default=""); p.add_argument("--input-tokens", type=int, default=None); p.add_argument("--output-token-limit", type=int, default=128); p.add_argument("--temperature", type=float, default=0.0); p.add_argument("--top-p", type=float, default=None); p.add_argument("--seed", type=int, default=None); p.add_argument("--warmup", type=int, default=1); p.add_argument("--iterations", type=int, default=5); p.add_argument("--runtime", default="llama.cpp"); p.add_argument("--backend", default=None)
    a = p.parse_args()
    command = json.loads(a.command_json.read_text())
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise SystemExit("command-json must be a non-empty JSON string array")
    artifact = a.artifact.resolve()
    if not artifact.is_file():
        raise SystemExit(f"artifact does not exist: {artifact}")
    binary = Path(command[0]).resolve()
    for _ in range(a.warmup):
        run_once(command)
    start, measurements = now(), []
    for iteration in range(1, a.iterations + 1):
        item = run_once(command); item["iteration"] = iteration; measurements.append(item)
    evidence = {
        "schema": "runtime-benchmark-evidence.v1.1", "execution_id": "rt-" + uuid.uuid4().hex,
        "timestamp_start": start, "timestamp_end": now(),
        "model": {"id": a.model_id, "name": a.model_name, "revision": a.model_revision, "source": a.model_source, "artifact": str(artifact), "quantization": a.quantization, "context_length": a.context},
        "protocol": {"prompt_protocol_id": a.prompt_protocol_id, "prompt_sha256": sha256_text(a.prompt) if a.prompt else None, "input_tokens": a.input_tokens, "output_token_limit": a.output_token_limit, "temperature": a.temperature, "top_p": a.top_p, "seed": a.seed, "context": a.context, "warmup_iterations": a.warmup, "measurement_iterations": a.iterations},
        "runtime": {"name": a.runtime, "version": version(command[0]), "revision": None, "backend": a.backend, "binary": str(binary), "binary_sha256": sha256_file(binary) if binary.is_file() else None, "command": command},
        "hardware": hardware(), "measurements": measurements, "summary": summarize(measurements),
        "process": {"exit_code": max(x["exit_code"] for x in measurements), "stdout": "\n".join(x["stdout"] for x in measurements), "stderr": "\n".join(x["stderr"] for x in measurements)},
        "artifact": {"path": str(artifact), "sha256": sha256_file(artifact), "size": artifact.stat().st_size},
    }
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"execution_id": evidence["execution_id"], "output": str(a.output), "summary": evidence["summary"]}, indent=2))
    return 0 if all(x["exit_code"] == 0 for x in measurements) else 1


if __name__ == "__main__":
    raise SystemExit(main())
