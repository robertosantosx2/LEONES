#!/usr/bin/env python3
"""Engine-agnostic NEPENTHES host/GPU collector. Never starts or stops the workload."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone


SCHEMA_VERSION = "1.0"
EVENT_KINDS = {
    "request_start", "request_end", "model_load", "model_unload",
    "allocation", "free", "transfer", "kernel", "sync", "cache_hit",
    "cache_miss", "eviction", "prefetch", "routing", "kv_cache",
    "fallback", "oom", "stall", "error", "checkpoint", "custom",
}


def wall_time() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def run_json(command: list[str], timeout: float = 2.0) -> dict:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            return {"available": False, "error": result.stderr.strip() or f"exit {result.returncode}"}
        return {"available": True, "stdout": result.stdout.strip()}
    except FileNotFoundError:
        return {"available": False, "error": f"{command[0]} not found"}
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def read_cpu_stat() -> dict:
    try:
        line = pathlib.Path("/proc/stat").read_text().splitlines()[0]
        values = list(map(int, line.split()[1:]))
        return {"available": True, "cpu_ticks": values}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def read_meminfo() -> dict:
    result = {}
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            key, raw = line.split(":", 1)
            match = re.search(r"\d+", raw)
            if match:
                result[key] = int(match.group()) * 1024
        total, available = result.get("MemTotal"), result.get("MemAvailable")
        result["used_bytes"] = max(0, total - available) if total is not None and available is not None else None
        swap_total, swap_free = result.get("SwapTotal"), result.get("SwapFree")
        result["swap_used_bytes"] = max(0, swap_total - swap_free) if swap_total is not None and swap_free is not None else None
    except Exception as exc:
        return {"available": False, "error": str(exc)}
    return {"available": True, "values_bytes": result}


def read_pressure() -> dict:
    result = {}
    for resource in ("cpu", "memory", "io"):
        path = pathlib.Path("/proc/pressure") / resource
        try:
            rows = {}
            for line in path.read_text().splitlines():
                parts = line.split()
                values = {}
                for item in parts[1:]:
                    key, _, value = item.partition("=")
                    try:
                        values[key] = float(value)
                    except ValueError:
                        pass
                if parts:
                    rows[parts[0]] = values
            result[resource] = {"available": True, "values": rows}
        except Exception as exc:
            result[resource] = {"available": False, "error": str(exc)}
    return result


def read_process_threads(pid: int | None, limit: int = 512) -> dict:
    if not pid:
        return {"available": False, "error": "target PID unavailable"}
    task_root = pathlib.Path("/proc") / str(pid) / "task"
    try:
        tids = sorted((int(item.name) for item in task_root.iterdir() if item.name.isdigit()))
    except Exception as exc:
        return {"available": False, "error": str(exc)}
    rows = []
    errors = []
    for tid in tids[:limit]:
        root = task_root / str(tid)
        row = {"tid": tid}
        try:
            row["name"] = (root / "comm").read_text().strip()
        except Exception:
            row["name"] = None
        try:
            fields = (root / "stat").read_text()
            tail = fields[fields.rfind(")") + 2:].split()
            row["state"] = tail[0]
            row["utime_ticks"] = int(tail[11])
            row["stime_ticks"] = int(tail[12])
            row["cpu_ticks"] = row["utime_ticks"] + row["stime_ticks"]
        except Exception as exc:
            row["stat_error"] = str(exc)
        try:
            sched = (root / "schedstat").read_text().split()
            if len(sched) >= 3:
                row["sched_runtime_ns"] = int(sched[0])
                row["sched_wait_ns"] = int(sched[1])
                row["sched_timeslices"] = int(sched[2])
        except Exception as exc:
            row["schedstat_error"] = str(exc)
        try:
            status = (root / "status").read_text().splitlines()
            for line in status:
                if line.startswith(("voluntary_ctxt_switches:", "nonvoluntary_ctxt_switches:", "Cpus_allowed_list:")):
                    key, value = line.split(":", 1)
                    row[key] = value.strip()
        except Exception:
            pass
        rows.append(row)
    return {"available": True, "threads": rows, "thread_count": len(tids),
            "truncated": len(tids) > limit, "limit": limit, "errors": errors}


def read_proc(pid: int | None) -> dict:
    if not pid:
        return {"available": False, "error": "target PID not supplied or discovered"}
    root = pathlib.Path("/proc") / str(pid)
    if not root.exists():
        return {"available": False, "error": f"PID {pid} is not present"}
    out = {"available": True, "pid": pid, "threads_detail": read_process_threads(pid)}
    try:
        raw = (root / "stat").read_text()
        tail = raw[raw.rfind(")") + 2:].split()
        out["stat"] = {
            "state": tail[0], "starttime_ticks": int(tail[19]),
            "utime_ticks": int(tail[11]),
            "stime_ticks": int(tail[12]),
            "threads": int(tail[17]),
            "rss_bytes": int(tail[21]) * os.sysconf("SC_PAGE_SIZE"),
        }
    except Exception as exc:
        out["stat_error"] = str(exc)
    for name in ("status", "io", "schedstat", "cgroup"):
        try:
            text = (root / name).read_text()
            if name == "status":
                fields = {}
                for line in text.splitlines():
                    if line.startswith(("Name:", "State:", "Threads:", "VmRSS:", "VmHWM:", "VmSwap:", "voluntary_ctxt_switches:", "nonvoluntary_ctxt_switches:")):
                        key, value = line.split(":", 1)
                        fields[key] = value.strip()
                out[name] = fields
            elif name == "io":
                fields = {}
                for line in text.splitlines():
                    key, value = line.split(":", 1)
                    try:
                        fields[key.strip()] = int(value.strip())
                    except ValueError:
                        pass
                out[name] = fields
            elif name == "schedstat":
                values = text.split()
                out[name] = {"runtime_ns": int(values[0]), "runqueue_wait_ns": int(values[1]), "timeslices": int(values[2])} if len(values) >= 3 else {"raw": text}
            else:
                out[name] = text.splitlines()
        except Exception as exc:
            out[name + "_error"] = str(exc)
    try:
        out["fd_count"] = len(list((root / "fd").iterdir()))
    except Exception as exc:
        out["fd_count_error"] = str(exc)
    return out


def read_cgroup(pid: int | None) -> dict:
    if not pid:
        return {"available": False, "error": "target PID unavailable"}
    try:
        lines = (pathlib.Path("/proc") / str(pid) / "cgroup").read_text().splitlines()
        unified = next((line.split(":", 2)[2] for line in lines if line.startswith("0::")), None)
        if unified is None:
            return {"available": False, "error": "cgroup v2 unified hierarchy not detected"}
        root = pathlib.Path("/sys/fs/cgroup") / unified.lstrip("/")
        names = ("memory.current", "memory.peak", "memory.max", "memory.events",
                 "cpu.stat", "cpu.max", "io.stat", "memory.pressure", "cpu.pressure", "io.pressure")
        data = {}
        for name in names:
            try:
                data[name] = (root / name).read_text().strip()
            except Exception as exc:
                data[name] = {"unavailable": str(exc)}
        return {"available": True, "path": str(root), "values": data}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def read_diskstats() -> dict:
    result = {}
    try:
        for line in pathlib.Path("/proc/diskstats").read_text().splitlines():
            fields = line.split()
            if len(fields) < 14:
                continue
            name = fields[2]
            if (pathlib.Path("/sys/class/block") / name / "partition").exists():
                continue
            result[name] = {
                "reads_completed": int(fields[3]), "sectors_read_512b": int(fields[5]),
                "writes_completed": int(fields[7]), "sectors_written_512b": int(fields[9]),
                "io_ms": int(fields[12]),
            }
        return {"available": True, "devices": result}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def read_vmstat() -> dict:
    keys = {"pswpin", "pswpout", "pgmajfault", "pgfault"}
    try:
        values = {}
        for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
            key, value = line.split()
            if key in keys:
                values[key] = int(value)
        return {"available": True, "values": values}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def read_cpu_frequency() -> dict:
    values = []
    for path in pathlib.Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_cur_freq"):
        try:
            values.append(int(path.read_text()) / 1000.0)
        except Exception:
            pass
    return {"available": bool(values), "mhz": values if values else None,
            "mean_mhz": sum(values) / len(values) if values else None}


def read_gpu() -> dict:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False, "error": "nvidia-smi not found"}
    query = "timestamp,index,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw,clocks.gr,clocks.sm"
    result = run_json([exe, f"--query-gpu={query}", "--format=csv,noheader,nounits"])
    if not result["available"]:
        return result
    rows = []
    for row in csv.reader(result["stdout"].splitlines()):
        values = [item.strip() for item in row]
        if len(values) != 11:
            continue
        def number(value):
            try:
                return float(value)
            except ValueError:
                return None
        rows.append({
            "timestamp": values[0], "index": values[1], "name": values[2],
            "gpu_util_pct": number(values[3]), "memory_util_pct": number(values[4]),
            "vram_used_mib": number(values[5]), "vram_total_mib": number(values[6]),
            "temperature_c": number(values[7]), "power_w": number(values[8]),
            "graphics_clock_mhz": number(values[9]), "sm_clock_mhz": number(values[10]),
        })
    compute = run_json([exe, "--query-compute-apps=pid,process_name,used_memory",
                         "--format=csv,noheader,nounits"])
    apps = []
    if compute["available"]:
        for row in csv.reader(compute["stdout"].splitlines()):
            values = [item.strip() for item in row]
            if len(values) != 3:
                continue
            try:
                apps.append({"pid": int(values[0]), "process_name": values[1],
                             "used_memory_mib": float(values[2])})
            except ValueError:
                continue
    return {"available": True, "gpus": rows, "compute_processes": apps,
            "compute_processes_available": compute["available"],
            "compute_processes_error": compute.get("error"),
            "source": "nvidia-smi --query-gpu / --query-compute-apps"}


def discover_pid(name: str | None, explicit: int | None) -> int | None:
    if explicit:
        return explicit
    if not name:
        return None
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            if name in cmd:
                return int(entry.name)
        except Exception:
            continue
    return None


class Dmon:
    def __init__(self):
        self.process = None
        self.thread = None
        self.stop_event = threading.Event()
        self.rows = []
        self.error = None
        self.lock = threading.Lock()

    def start(self):
        exe = shutil.which("nvidia-smi")
        if not exe:
            self.error = "nvidia-smi not found"
            return
        try:
            self.process = subprocess.Popen([exe, "dmon", "-s", "t", "-d", "1"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
            self.thread = threading.Thread(target=self._read, daemon=True)
            self.thread.start()
        except Exception as exc:
            self.error = str(exc)

    def _read(self):
        try:
            for line in self.process.stdout:
                match = re.match(r"^\s*(\d+)\s+([0-9.]+|-)\s+([0-9.]+|-)\s*$", line)
                if match:
                    def val(raw):
                        try: return float(raw)
                        except ValueError: return None
                    row = {"time": wall_time(), "monotonic_ns": time.monotonic_ns(),
                           "gpu_index": int(match.group(1)), "rx_mbps": val(match.group(2)),
                           "tx_mbps": val(match.group(3)), "source": "nvidia-smi-dmon"}
                    with self.lock:
                        self.rows.append(row)
                if self.stop_event.is_set() and self.process.poll() is not None:
                    break
        except Exception as exc:
            self.error = str(exc)

    def finish(self):
        self.stop_event.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        if self.thread:
            self.thread.join(timeout=2)
        with self.lock:
            return list(self.rows)


class UniversalCollector:
    def __init__(self, output_root: str, engine: str, model: str, pid: int | None = None,
                 process_name: str | None = None, interval: float = 1.0, metadata: dict | None = None):
        self.run_id = str(uuid.uuid4())
        self.pid = discover_pid(process_name, pid)
        self.interval = max(0.2, float(interval))
        self.root_parent = pathlib.Path(output_root).expanduser()
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f%z")
        self.run_dir = self.root_parent / f"nepenthes-{stamp}-{self.run_id[:8]}"
        self.engine, self.model = engine, model
        self.metadata = metadata or {}
        self.stop_event = threading.Event()
        self.thread = None
        self.errors = []
        self.dmon = Dmon()
        self.started_wall = None
        self.started_mono = None
        self.sample_count = 0

    def _mkdir(self):
        self.run_dir.mkdir(parents=True, exist_ok=False)
        for name in ("samples", "events", "requests", "profiles", "logs"):
            (self.run_dir / name).mkdir()

    def _write_json(self, path: pathlib.Path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _append(self, path: pathlib.Path, value):
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")

    def event(self, kind: str, payload: dict, request_id: str | None = None, source: str = "external"):
        if kind not in EVENT_KINDS:
            raise ValueError(f"Unsupported event kind: {kind}")
        row = {"schema_version": SCHEMA_VERSION, "run_id": self.run_id,
               "request_id": request_id, "event_id": str(uuid.uuid4()), "kind": kind,
               "time": wall_time(), "monotonic_ns": time.monotonic_ns(),
               "source": source, "payload": payload}
        self._append(self.run_dir / "events" / "engine_events.jsonl", row)
        return row

    def request_record(self, request_id: str, record: dict):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", request_id) or request_id in {".", ".."}:
            raise ValueError("request_id must be 1-128 safe filename characters")
        row = {"schema_version": SCHEMA_VERSION, "run_id": self.run_id,
               "request_id": request_id, "recorded_at": wall_time(),
               "monotonic_ns": time.monotonic_ns(), **record}
        self._write_json(self.run_dir / "requests" / f"{request_id}.json", row)

    def _sample(self):
        mono = time.monotonic_ns()
        return {
            "schema_version": SCHEMA_VERSION, "run_id": self.run_id,
            "time": wall_time(), "monotonic_ns": mono, "pid": self.pid,
            "host": {"cpu": read_cpu_stat(),
                     "memory": read_meminfo(), "vmstat": read_vmstat(),
                     "pressure": read_pressure(), "cpu_frequency": read_cpu_frequency(),
                     "disk": read_diskstats()},
            "process": read_proc(self.pid), "cgroup": read_cgroup(self.pid),
            "gpu": read_gpu(), "gpu_pcie_latest": self.dmon.rows[-1] if self.dmon.rows else None,
        }

    def _loop(self):
        path = self.run_dir / "samples" / "telemetry.jsonl"
        while not self.stop_event.is_set():
            row = self._sample()
            self._append(path, row)
            self.sample_count += 1
            self.stop_event.wait(self.interval)
        row = self._sample()
        self._append(path, row)
        self.sample_count += 1

    def start(self):
        self._mkdir()
        self.started_wall, self.started_mono = wall_time(), time.monotonic_ns()
        manifest = {
            "schema_version": SCHEMA_VERSION, "run_id": self.run_id,
            "started_at": self.started_wall, "started_monotonic_ns": self.started_mono,
            "hostname": socket.gethostname(), "platform": platform.platform(),
            "python": sys.version, "engine": self.engine, "model": self.model,
            "target_pid": self.pid, "sampling_interval_seconds": self.interval,
            "metadata": self.metadata,
            "probe_capabilities": {
                "host_procfs": pathlib.Path("/proc/stat").exists(),
                "pressure_stall_information": pathlib.Path("/proc/pressure").exists(),
                "cgroup_v2": pathlib.Path("/sys/fs/cgroup/cgroup.controllers").exists(),
                "nvidia_smi": shutil.which("nvidia-smi") is not None,
                "nsight_systems": shutil.which("nsys") is not None,
                "perf": shutil.which("perf") is not None,
            },
            "semantics": {
                "host_pressure_and_disk": "host-wide, not request-exclusive",
                "gpu_and_pcie": "device-wide; unrelated GPU clients may contribute",
                "missing_values": "unavailable/null, never coerced to zero",
                "target_process": "single PID snapshot; process tree aggregation is not implied",
                "engine_events": "require engine adapter or explicit event() calls; not inferred by host polling",
            },
        }
        self._write_json(self.run_dir / "run_manifest.json", manifest)
        self.dmon.start()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self.event("custom", {"message": "collector_started", "sampling_interval_seconds": self.interval}, source="collector")
        return self.run_dir

    def finish(self):
        if not self.thread:
            raise RuntimeError("collector was not started")
        self.stop_event.set()
        self.thread.join()
        pcie_rows = self.dmon.finish()
        pcie_path = self.run_dir / "samples" / "pcie.jsonl"
        for row in pcie_rows:
            self._append(pcie_path, {"run_id": self.run_id, **row})
        if self.dmon.error:
            self.errors.append({"probe": "nvidia-smi-dmon", "error": self.dmon.error})
        finished_wall, finished_mono = wall_time(), time.monotonic_ns()
        self.event("custom", {"message": "collector_finished", "sample_count": self.sample_count}, source="collector")
        manifest_path = self.run_dir / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest.update({"finished_at": finished_wall, "finished_monotonic_ns": finished_mono,
                         "duration_seconds": (finished_mono - self.started_mono) / 1e9})
        self._write_json(manifest_path, manifest)
        telemetry_path = self.run_dir / "samples" / "telemetry.jsonl"
        telemetry_rows = [json.loads(line) for line in telemetry_path.read_text().splitlines() if line.strip()]
        process_samples = sum(1 for row in telemetry_rows if row.get("process", {}).get("available"))
        gpu_samples = sum(1 for row in telemetry_rows if row.get("gpu", {}).get("available") and row.get("gpu", {}).get("gpus"))
        host_memory_samples = sum(1 for row in telemetry_rows if row.get("host", {}).get("memory", {}).get("available"))
        event_path = self.run_dir / "events" / "engine_events.jsonl"
        event_rows = [json.loads(line) for line in event_path.read_text().splitlines() if line.strip()]
        engine_event_count = sum(1 for row in event_rows if row.get("source") != "collector")
        report = {
            "schema_version": SCHEMA_VERSION, "run_id": self.run_id,
            "sample_count": self.sample_count, "pcie_sample_count": len(pcie_rows),
            "process_sample_count": process_samples, "gpu_sample_count": gpu_samples,
            "host_memory_sample_count": host_memory_samples, "engine_event_count": engine_event_count,
            "errors": self.errors,
            "coverage": {
                "host_samples": host_memory_samples > 0,
                "process_samples": process_samples > 0,
                "gpu_samples": gpu_samples > 0,
                "pcie_samples": len(pcie_rows) > 0,
                "engine_events": engine_event_count > 0,
                "collector_events": len(event_rows) - engine_event_count,
                "request_records": any((self.run_dir / "requests").glob("*.json")),
                "nsight_profiles": any((self.run_dir / "profiles").iterdir()),
            },
            "limitations": [
                "Host PSI, disk, swap and GPU PCIe counters are not exclusive to the inference process.",
                "This collector does not infer per-layer routing, expert-cache hits, KV-cache occupancy, CUDA kernel timings or allocation lifetimes.",
                "Those engine/CUDA details must be emitted by an engine adapter or imported as external profiler artifacts.",
                "A missing probe result means unavailable, not zero activity.",
            ],
        }
        self._write_json(self.run_dir / "collection_report.json", report)
        sums = []
        for path in sorted(self.run_dir.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                sums.append(f"{digest}  {path.relative_to(self.run_dir)}")
        (self.run_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        return self.run_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="./nepenthes-runs")
    parser.add_argument("--engine", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--process-name")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--duration", type=float, default=0, help="optional capture duration; 0 means until Ctrl-C")
    parser.add_argument("--metadata-json", default="{}")
    args = parser.parse_args()
    try:
        metadata = json.loads(args.metadata_json)
        if not isinstance(metadata, dict):
            raise ValueError("metadata-json must be a JSON object")
    except Exception as exc:
        parser.error(f"invalid --metadata-json: {exc}")
    collector = UniversalCollector(args.output_root, args.engine, args.model, args.pid,
                                   args.process_name, args.interval, metadata)
    run_dir = collector.start()
    print(f"NEPENTHES capture started: {run_dir}", flush=True)
    try:
        if args.duration > 0:
            collector.stop_event.wait(args.duration)
        else:
            while True:
                time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"NEPENTHES capture saved: {collector.finish()}", flush=True)


if __name__ == "__main__":
    main()
