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

TOKENS_PER_SECOND = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*tok(?:ens)?/s", re.I)


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
        return (p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr).strip() else "unknown"
    except Exception as exc:
        return f"unavailable: {exc}"


def hardware() -> dict:
    ram_mb = None
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        size = os.sysconf("SC_PAGE_SIZE")
        ram_mb = round(pages * size / 1024 / 1024, 2)
    except (ValueError, OSError, AttributeError):
        pass
    gpu = None
    if shutil.which("nvidia-smi"):
        try:
            p = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=False)
            gpu = p.stdout.strip() or None
        except Exception:
            pass
    return {"os": platform.platform(), "kernel": platform.release(), "architecture": platform.machine(), "cpu": platform.processor() or platform.uname().processor, "ram_total_mb": ram_mb, "gpu": gpu}


def peak_memory_mb() -> float | None:
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
        line = p.stdout.strip().splitlines()[0]
        mem, power = [x.strip() for x in line.split(",", 1)]
        return float(mem), float(power)
    except Exception:
        return None, None


def run_once(command: list[str]) -> dict:
    started = time.perf_counter()
    first_output = None
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
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
    matches = [float(x) for x in TOKENS_PER_SECOND.findall(text)]
    tps = matches[-1] if matches else None
    gen_ms = None if first_output is None else max(0.0, total - first_output)
    out_tokens = round(tps * gen_ms / 1000) if tps is not None and gen_ms is not None else None
    vram, power = gpu_snapshot()
    return {"ttft_ms": first_output, "first_output_ms": first_output, "generation_time_ms": gen_ms, "output_tokens": out_tokens, "tokens_per_second": tps, "total_time_ms": round(total, 3), "peak_memory_mb": peak_memory_mb(), "peak_vram_mb": vram, "power_w": power, "exit_code": code, "stdout": "".join(stdout_chunks), "stderr": "".join(stderr_chunks)}


def summary(measurements: list[dict]) -> dict:
    result: dict = {}
    for key in ("ttft_ms", "generation_time_ms", "tokens_per_second", "total_time_ms", "peak_memory_mb", "peak_vram_mb", "power_w"):
        vals = [float(m[key]) for m in measurements if m.get(key) is not None]
        if not vals:
            continue
        result[key] = {"mean": mean(vals), "median": median(vals), "min": min(vals), "max": max(vals)}
        if len(vals) > 1:
            result[key]["stdev"] = stdev(vals)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--command-json", type=Path, required=True, help="JSON array containing the shell-free command")
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
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise SystemExit("command-json must contain a non-empty JSON string array")
    for _ in range(args.warmup):
        run_once(command)
    start = now()
    measurements = []
    for i in range(1, args.iterations + 1):
        m = run_once(command)
        m["iteration"] = i
        measurements.append(m)
    end = now()
    artifact = args.artifact.resolve()
    if not artifact.exists() or not artifact.is_file():
        raise SystemExit(f"artifact does not exist: {artifact}")
    evidence = {
        "schema": "runtime-benchmark-evidence.v1.1",
        "execution_id": "rt-" + uuid.uuid4().hex,
        "timestamp_start": start,
        "timestamp_end": end,
        "model": {"id": args.model_id, "name": args.model_name, "revision": args.model_revision, "artifact": str(artifact), "quantization": args.quantization, "context_length": args.context},
        "protocol": {"prompt_protocol_id": args.prompt_protocol_id, "prompt": args.prompt, "context": args.context, "warmup_iterations": args.warmup, "measurement_iterations": args.iterations},
        "runtime": {"name": args.runtime, "version": command_version(command[0]), "revision": None, "backend": args.backend, "command": command},
        "hardware": hardware(),
        "measurements": measurements,
        "summary": summary(measurements),
        "process": {"exit_code": max(m["exit_code"] for m in measurements), "stdout": "\n".join(m["stdout"] for m in measurements), "stderr": "\n".join(m["stderr"] for m in measurements)},
        "artifact": {"path": str(artifact), "sha256": sha256_file(artifact), "size": artifact.stat().st_size}
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"execution_id": evidence["execution_id"], "output": str(args.output), "summary": evidence["summary"]}, indent=2))
    return 0 if all(m["exit_code"] == 0 for m in measurements) else 1


if __name__ == "__main__":
    raise SystemExit(main())
