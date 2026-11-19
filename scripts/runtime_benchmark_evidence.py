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
import threading
import uuid
from pathlib import Path
from statistics import mean, median, stdev

TOKENS_PER_SECOND = re.compile(
    r"(?:Generation:\s*)?([0-9]+(?:[.,][0-9]+)?)\s*(?:tok(?:ens)?|t)/s",
    re.I,
)

LLAMA_CPP_GENERATION_TPS = re.compile(
    r"Generation:\s*([0-9]+(?:[.,][0-9]+)?)\s*t/s",
    re.I,
)


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
        p = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return (
            (p.stdout or p.stderr).strip().splitlines()[0]
            if (p.stdout or p.stderr).strip()
            else "unknown"
        )
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
            p = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            gpu = p.stdout.strip() or None
        except Exception:
            pass
    return {
        "os": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or platform.uname().processor,
        "ram_total_mb": ram_mb,
        "gpu": gpu,
    }


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
        p = subprocess.run(
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
        line = p.stdout.strip().splitlines()[0]
        mem, power = [x.strip() for x in line.split(",", 1)]
        return float(mem), float(power)
    except Exception:
        return None, None



def process_rss_mb(pid: int) -> float | None:
    status = Path(f"/proc/{pid}/status")
    try:
        for line in status.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 2)
    except (OSError, ValueError, IndexError):
        return None
    return None


def system_ram_used_mb() -> float | None:
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, value = line.split(":", 1)
            if key in ("MemTotal", "MemAvailable"):
                values[key] = int(value.strip().split()[0])
        if "MemTotal" in values and "MemAvailable" in values:
            return round((values["MemTotal"] - values["MemAvailable"]) / 1024, 2)
    except (OSError, ValueError, IndexError):
        return None
    return None


class TelemetrySampler:
    """Low-frequency host and device-wide sampling during one child execution."""

    def __init__(self, pid: int, host_interval_ms: int = 100, gpu_interval_ms: int = 500):
        self.pid = pid
        self.host_interval = max(20, host_interval_ms) / 1000
        self.gpu_interval_ms = max(100, gpu_interval_ms)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.values = {
            "peak_process_rss_mb": None,
            "peak_system_ram_used_mb": None,
            "peak_vram_mb_device_wide": None,
            "peak_power_w": None,
            "power_sum_w": 0.0,
            "power_samples": 0,
            "gpu_sample_count": 0,
        }
        self.host_thread = threading.Thread(target=self._sample_host, daemon=True)
        self.gpu_process = None
        self.gpu_thread = None
        if shutil.which("nvidia-smi"):
            try:
                self.gpu_process = subprocess.Popen(
                    [
                        "nvidia-smi", "--id=0",
                        "--query-gpu=memory.used,power.draw",
                        "--format=csv,noheader,nounits",
                        f"--loop-ms={self.gpu_interval_ms}",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                )
                self.gpu_thread = threading.Thread(target=self._sample_gpu, daemon=True)
                self.gpu_thread.start()
            except OSError:
                self.gpu_process = None
        self.host_thread.start()

    def _sample_host(self) -> None:
        while not self.stop_event.is_set():
            rss = process_rss_mb(self.pid)
            ram = system_ram_used_mb()
            with self.lock:
                if rss is not None:
                    current = self.values["peak_process_rss_mb"]
                    self.values["peak_process_rss_mb"] = rss if current is None else max(current, rss)
                if ram is not None:
                    current = self.values["peak_system_ram_used_mb"]
                    self.values["peak_system_ram_used_mb"] = ram if current is None else max(current, ram)
            self.stop_event.wait(self.host_interval)

    def _sample_gpu(self) -> None:
        if self.gpu_process is None or self.gpu_process.stdout is None:
            return
        for line in self.gpu_process.stdout:
            if self.stop_event.is_set():
                break
            try:
                parts = [item.strip() for item in line.strip().split(",")]
                memory = float(parts[0]) if parts and parts[0] not in ("N/A", "") else None
                power = float(parts[1]) if len(parts) > 1 and parts[1] not in ("N/A", "") else None
            except (ValueError, IndexError):
                continue
            with self.lock:
                if memory is not None:
                    current = self.values["peak_vram_mb_device_wide"]
                    self.values["peak_vram_mb_device_wide"] = memory if current is None else max(current, memory)
                if power is not None:
                    current = self.values["peak_power_w"]
                    self.values["peak_power_w"] = power if current is None else max(current, power)
                    self.values["power_sum_w"] += power
                    self.values["power_samples"] += 1
                self.values["gpu_sample_count"] += 1

    def close(self) -> dict:
        self.stop_event.set()
        if self.gpu_process is not None:
            try:
                self.gpu_process.terminate()
                self.gpu_process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self.gpu_process.kill()
                except OSError:
                    pass
        self.host_thread.join(timeout=1)
        if self.gpu_thread is not None:
            self.gpu_thread.join(timeout=1)
        with self.lock:
            result = dict(self.values)
        samples = result.pop("power_samples")
        power_sum = result.pop("power_sum_w")
        result["mean_power_w"] = round(power_sum / samples, 3) if samples else None
        result["peak_vram_mb"] = result["peak_vram_mb_device_wide"]
        return result


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires at least one value")
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def run_once(command: list[str], host_sample_ms: int = 100, gpu_sample_ms: int = 500) -> dict:
    started = time.perf_counter()
    first_output = None
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
    )
    telemetry = TelemetrySampler(proc.pid, host_sample_ms, gpu_sample_ms)
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
    telemetry_values = telemetry.close()
    total = (time.perf_counter() - started) * 1000
    text = "".join(stdout_chunks) + "\n" + "".join(stderr_chunks)
    llama_matches = LLAMA_CPP_GENERATION_TPS.findall(text)
    if llama_matches:
        tps = float(llama_matches[-1].replace(",", "."))
    else:
        matches = TOKENS_PER_SECOND.findall(text)
        tps = float(matches[-1].replace(",", ".")) if matches else None
    gen_ms = None if first_output is None else max(0.0, total - first_output)
    out_tokens = (
        round(tps * gen_ms / 1000) if tps is not None and gen_ms is not None else None
    )
    vram, power = gpu_snapshot()
    return {
        "ttft_ms": first_output,
        "first_output_ms": first_output,
        "generation_time_ms": gen_ms,
        "output_tokens": out_tokens,
        "tokens_per_second": tps,
        "total_time_ms": round(total, 3),
        "peak_memory_mb": peak_memory_mb(),
        "peak_process_rss_mb": telemetry_values["peak_process_rss_mb"],
        "peak_system_ram_used_mb": telemetry_values["peak_system_ram_used_mb"],
        "peak_vram_mb": telemetry_values["peak_vram_mb"],
        "peak_vram_mb_device_wide": telemetry_values["peak_vram_mb_device_wide"],
        "power_w": power,
        "mean_power_w": telemetry_values["mean_power_w"],
        "peak_power_w": telemetry_values["peak_power_w"],
        "gpu_sample_count": telemetry_values["gpu_sample_count"],
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
        "peak_process_rss_mb",
        "peak_system_ram_used_mb",
        "peak_vram_mb_device_wide",
        "power_w",
        "mean_power_w",
        "peak_power_w",
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
        result[key]["p25"] = percentile(vals, 0.25)
        result[key]["p75"] = percentile(vals, 0.75)
        result[key]["iqr"] = result[key]["p75"] - result[key]["p25"]
        result[key]["mad"] = median([abs(value - result[key]["median"]) for value in vals])
        if len(vals) > 1:
            result[key]["stdev"] = stdev(vals)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--command-json",
        type=Path,
        required=True,
        help="JSON array containing the shell-free command",
    )
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--artifact", type=Path, required=True)
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--model-name", required=True)
    ap.add_argument("--model-revision", required=True)
    ap.add_argument("--quantization", required=True)
    ap.add_argument("--context", type=int, required=True)
    ap.add_argument("--input-tokens", type=int, default=None)
    ap.add_argument("--output-token-limit", type=int, default=None)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--top-p", type=float, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--prompt-protocol-id", required=True)
    ap.add_argument("--prompt", default="")
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--runtime", default="llama.cpp")
    ap.add_argument("--backend", default=None)
    ap.add_argument("--condition", choices=("off", "jsonl", "nsys", "combined"), default="off")
    ap.add_argument("--pair-id", default=None)
    ap.add_argument("--profile", choices=("smoke", "standard", "full", "moe-deep", "latency-critical"), default="standard")
    ap.add_argument("--dataset-sha256", default=None)
    ap.add_argument("--engine-revision", default=None)
    ap.add_argument("--hardware-id", default=None)
    ap.add_argument("--sampling-config-json", type=Path, default=None)
    ap.add_argument("--host-sample-ms", type=int, default=100)
    ap.add_argument("--gpu-sample-ms", type=int, default=500)
    args = ap.parse_args()
    if args.host_sample_ms < 20 or args.gpu_sample_ms < 100:
        raise SystemExit("sampling intervals are too aggressive; host>=20ms and GPU>=100ms are required")
    sampling_config = json.loads(args.sampling_config_json.read_text(encoding="utf-8")) if args.sampling_config_json else {}
    if not isinstance(sampling_config, dict):
        raise SystemExit("sampling-config-json must contain a JSON object")
    command = json.loads(args.command_json.read_text(encoding="utf-8"))
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(x, str) for x in command)
    ):
        raise SystemExit("command-json must contain a non-empty JSON string array")
    for _ in range(args.warmup):
        run_once(command, args.host_sample_ms, args.gpu_sample_ms)
    start = now()
    measurements = []
    for i in range(1, args.iterations + 1):
        m = run_once(command, args.host_sample_ms, args.gpu_sample_ms)
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
        "model": {
            "id": args.model_id,
            "name": args.model_name,
            "revision": args.model_revision,
            "artifact": str(artifact),
            "quantization": args.quantization,
            "context_length": args.context,
        },
        "protocol": {
            "prompt_protocol_id": args.prompt_protocol_id,
            "prompt": args.prompt,
            "prompt_sha256": hashlib.sha256(args.prompt.encode("utf-8")).hexdigest(),
            "context": args.context,
            "input_tokens": args.input_tokens,
            "output_token_limit": args.output_token_limit,
            "temperature": args.temperature,
            "top_p": args.top_p,
            "seed": args.seed,
            "warmup_iterations": args.warmup,
            "measurement_iterations": args.iterations,
        },
        "runtime": {
            "name": args.runtime,
            "version": command_version(command[0]),
            "revision": args.engine_revision,
            "backend": args.backend,
            "command": command,
        },
        "hardware": hardware(),
        "instrumentation": {
            "condition": args.condition,
            "pair_id": args.pair_id,
            "profile": args.profile,
            "dataset_sha256": args.dataset_sha256,
            "hardware_id": args.hardware_id,
            "sampling_config": sampling_config,
            "host_sample_ms": args.host_sample_ms,
            "gpu_sample_ms": args.gpu_sample_ms,
        },
        "measurements": measurements,
        "summary": summary(measurements),
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
    args.output.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "execution_id": evidence["execution_id"],
                "output": str(args.output),
                "summary": evidence["summary"],
            },
            indent=2,
        )
    )
    return 0 if all(m["exit_code"] == 0 for m in measurements) else 1


if __name__ == "__main__":
    raise SystemExit(main())
