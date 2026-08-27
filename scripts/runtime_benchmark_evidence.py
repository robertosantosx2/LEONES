#!/usr/bin/env python3
"""Run a shell-free inference command and emit reproducible LEONES evidence."""
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
from typing import Any

TPS_RE = re.compile(r"(?:Generation|eval)[^\n]*?[:=]\s*([0-9]+(?:[.,][0-9]+)?)\s*t(?:okens)?/s", re.I)
LLAMA_SUMMARY_RE = re.compile(r"\[\s*Prompt:\s*([0-9]+(?:[.,][0-9]+)?)\s*t/s\s*\|\s*Generation:\s*([0-9]+(?:[.,][0-9]+)?)\s*t/s\s*\]", re.I)
LLAMA_GEN_RE = re.compile(r"Generation:\s*[^\n]*?([0-9]+(?:[.,][0-9]+)?)\s*ms", re.I)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def command_version(executable: str) -> str:
    try:
        p = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=10, check=False)
        text = (p.stdout or p.stderr).strip()
        return text.splitlines()[0] if text else "unknown"
    except Exception as exc:
        return f"unavailable: {exc}"


def cpu_model() -> str:
    try:
        out = subprocess.check_output(["lscpu"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if line.startswith("Model name:"):
                return line.split(":", 1)[1].strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    return platform.processor() or platform.uname().processor or "unknown"


def ram_total_mb() -> float | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / 1024, 2)
    except (OSError, ValueError):
        pass
    return None


def cores() -> tuple[int | None, int | None]:
    threads = os.cpu_count()
    try:
        out = subprocess.check_output(["lscpu", "-p=CPU,Core"], text=True, stderr=subprocess.DEVNULL)
        physical = len({line.split(",")[1] for line in out.splitlines() if line and not line.startswith("#") and "," in line}) or None
    except (OSError, subprocess.CalledProcessError, IndexError):
        physical = None
    return threads, physical


def gpu_info() -> tuple[str | None, float | None]:
    if not shutil.which("nvidia-smi"):
        return None, None
    try:
        p = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=False)
        line = p.stdout.strip().splitlines()[0]
        name, memory = [x.strip() for x in line.split(",", 1)]
        return name, float(memory)
    except (ValueError, IndexError, OSError):
        return None, None


def peak_child_rss_mb() -> float | None:
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 2)
    except Exception:
        return None


def gpu_snapshot() -> tuple[float | None, float | None]:
    if not shutil.which("nvidia-smi"):
        return None, None
    try:
        p = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,power.draw", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=False)
        mem, power = [x.strip() for x in p.stdout.strip().splitlines()[0].split(",", 1)]
        return float(mem), float(power)
    except (ValueError, IndexError, OSError):
        return None, None


def run_once(command: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    first_output = None
    stdout: list[str] = []
    stderr: list[str] = []
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    import selectors
    selector = selectors.DefaultSelector()
    assert proc.stdout is not None and proc.stderr is not None
    selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
    selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
    while selector.get_map():
        for key, _ in selector.select(timeout=0.1):
            line = key.fileobj.readline()
            if line == "":
                selector.unregister(key.fileobj)
                continue
            if first_output is None and line.strip():
                first_output = (time.perf_counter() - started) * 1000
            (stdout if key.data == "stdout" else stderr).append(line)
    code = proc.wait()
    total_ms = (time.perf_counter() - started) * 1000
    out, err = "".join(stdout), "".join(stderr)
    combined = out + "\n" + err

    tps = None
    generation_ms = None
    output_tokens = None
    summary_match = LLAMA_SUMMARY_RE.search(combined)
    if summary_match:
        tps = float(summary_match.group(2).replace(",", "."))
    else:
        matches = TPS_RE.findall(combined)
        if matches:
            tps = float(matches[-1].replace(",", "."))
    gen_match = LLAMA_GEN_RE.search(combined)
    if gen_match:
        generation_ms = float(gen_match.group(1).replace(",", "."))
        if tps is not None:
            output_tokens = max(0, round(tps * generation_ms / 1000))

    vram, power = gpu_snapshot()
    return {
        "ttft_ms": first_output,
        "first_output_ms": first_output,
        "generation_time_ms": generation_ms,
        "output_tokens": output_tokens,
        "tokens_per_second": tps,
        "total_time_ms": round(total_ms, 3),
        "peak_memory_mb": peak_child_rss_mb(),
        "peak_vram_mb": vram,
        "power_w": power,
        "exit_code": code,
        "stdout": out,
        "stderr": err,
    }


def summary(measurements: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("ttft_ms", "first_output_ms", "generation_time_ms", "output_tokens", "tokens_per_second", "total_time_ms", "peak_memory_mb", "peak_vram_mb", "power_w"):
        vals = [float(m[key]) for m in measurements if m.get(key) is not None]
        if not vals:
            continue
        item: dict[str, float] = {"mean": mean(vals), "median": median(vals), "min": min(vals), "max": max(vals)}
        if len(vals) > 1:
            item["stdev"] = stdev(vals)
        result[key] = item
    return result


def validate(evidence: dict[str, Any]) -> None:
    required = {"schema", "execution_id", "timestamp_start", "timestamp_end", "model", "protocol", "runtime", "hardware", "measurements", "summary", "process", "artifact"}
    missing = required - evidence.keys()
    if missing:
        raise ValueError(f"evidence missing required fields: {sorted(missing)}")
    if evidence["schema"] != "runtime-benchmark-evidence.v1.1":
        raise ValueError("invalid evidence schema")
    if not evidence["measurements"]:
        raise ValueError("at least one measurement is required")
    if any(m["exit_code"] != 0 for m in evidence["measurements"]):
        raise ValueError("failed measurement cannot be published as valid evidence")


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
    ap.add_argument("--runtime", default="llama.cpp")
    ap.add_argument("--backend", default=None)
    args = ap.parse_args()

    command = json.loads(args.command_json.read_text(encoding="utf-8"))
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        raise SystemExit("command-json must contain a non-empty JSON string array")
    if args.warmup < 0 or args.iterations < 1 or args.context < 1:
        raise SystemExit("warmup >= 0, iterations >= 1 and context >= 1 are required")
    artifact = args.artifact.resolve()
    if not artifact.is_file():
        raise SystemExit(f"artifact does not exist: {artifact}")

    for _ in range(args.warmup):
        run_once(command)
    timestamp_start = now()
    measurements = []
    for i in range(1, args.iterations + 1):
        measurement = run_once(command)
        measurement["iteration"] = i
        measurements.append(measurement)
    timestamp_end = now()

    binary = shutil.which(command[0]) or command[0]
    threads, physical = cores()
    gpu, vram_total = gpu_info()
    prompt_sha = hashlib.sha256(args.prompt.encode("utf-8")).hexdigest() if args.prompt else None
    artifact_sha = sha256_file(artifact)
    binary_path = Path(binary)
    evidence = {
        "schema": "runtime-benchmark-evidence.v1.1",
        "execution_id": "rt-" + uuid.uuid4().hex,
        "timestamp_start": timestamp_start,
        "timestamp_end": timestamp_end,
        "model": {
            "id": args.model_id,
            "name": args.model_name,
            "revision": args.model_revision,
            "source": None,
            "artifact": str(artifact),
            "artifact_sha256": artifact_sha,
            "artifact_size_bytes": artifact.stat().st_size,
            "quantization": args.quantization,
            "context_length": args.context,
        },
        "protocol": {
            "prompt_protocol_id": args.prompt_protocol_id,
            "measurement_scope": "local_process_first_output",
            "prompt": args.prompt,
            "prompt_sha256": prompt_sha,
            "input_tokens": None,
            "output_token_limit": None,
            "temperature": None,
            "top_p": None,
            "seed": None,
            "context": args.context,
            "warmup_iterations": args.warmup,
            "measurement_iterations": args.iterations,
        },
        "runtime": {
            "name": args.runtime,
            "version": command_version(command[0]),
            "revision": None,
            "backend": args.backend,
            "binary": binary,
            "binary_sha256": sha256_file(binary_path) if binary_path.is_file() else None,
            "command": command,
        },
        "hardware": {
            "host": platform.node(),
            "os": platform.platform(),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "cpu": cpu_model(),
            "cpu_threads": threads,
            "physical_cores": physical,
            "ram_total_mb": ram_total_mb(),
            "gpu": gpu,
            "vram_total_mb": vram_total,
            "storage": None,
            "driver": None,
        },
        "measurements": measurements,
        "summary": summary(measurements),
        "process": {
            "exit_code": max(m["exit_code"] for m in measurements),
            "stdout": "\n".join(m["stdout"] for m in measurements),
            "stderr": "\n".join(m["stderr"] for m in measurements),
        },
        "artifact": {"path": str(artifact), "sha256": artifact_sha, "size": artifact.stat().st_size},
    }
    validate(evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"execution_id": evidence["execution_id"], "output": str(args.output), "summary": evidence["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
