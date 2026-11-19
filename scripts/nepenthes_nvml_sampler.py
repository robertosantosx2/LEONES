#!/usr/bin/env python3
"""Collect device-level NVIDIA NVML telemetry and account for GPU energy.

The module is hardware-independent until CLI execution. Tests inject a fake NVML
provider; actual collection imports pynvml lazily and never requires root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = "1.0"


def stable_id(*parts: Any) -> str:
    raw = "\0".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def text_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return None
    return float(value)


@dataclass(frozen=True)
class DeviceIdentity:
    index: int
    uuid: str
    name: str | None
    pci_bus_id: str | None


class NVMLSampler:
    def __init__(self, nvml: Any, run_id: str, *,
                 monotonic_clock_ns: Callable[[], int] = time.monotonic_ns,
                 wall_clock_ns: Callable[[], int] = time.time_ns):
        self.nvml = nvml
        self.run_id = run_id
        self.monotonic_clock_ns = monotonic_clock_ns
        self.wall_clock_ns = wall_clock_ns
        self.nvml_version = text_value(self._call("nvmlSystemGetNVMLVersion"))
        self.devices = self.discover_devices()

    def _call(self, function_name: str, *args: Any) -> Any:
        function = getattr(self.nvml, function_name, None)
        if not callable(function):
            raise AttributeError(function_name)
        return function(*args)

    def _optional(self, errors: list[str], function_name: str, *args: Any) -> Any:
        try:
            return self._call(function_name, *args)
        except Exception:
            errors.append(function_name)
            return None

    def discover_devices(self) -> list[tuple[DeviceIdentity, Any]]:
        count = int(self._call("nvmlDeviceGetCount"))
        devices = []
        for index in range(count):
            handle = self._call("nvmlDeviceGetHandleByIndex", index)
            errors: list[str] = []
            device_uuid = text_value(self._optional(errors, "nvmlDeviceGetUUID", handle)) or f"index:{index}"
            name = text_value(self._optional(errors, "nvmlDeviceGetName", handle))
            pci = self._optional(errors, "nvmlDeviceGetPciInfo", handle)
            pci_bus_id = text_value(getattr(pci, "busId", None) or getattr(pci, "busIdLegacy", None)) if pci else None
            devices.append((DeviceIdentity(index, device_uuid, name, pci_bus_id), handle))
        return devices

    def sample_device(self, identity: DeviceIdentity, handle: Any) -> dict[str, Any]:
        errors: list[str] = []
        metrics: dict[str, float | int] = {}
        power_mw = self._optional(errors, "nvmlDeviceGetPowerUsage", handle)
        power_w = finite_number(power_mw / 1000.0) if isinstance(power_mw, (int, float)) and not isinstance(power_mw, bool) else None
        if power_w is not None:
            metrics["power_w"] = power_w
        temperature = self._optional(errors, "nvmlDeviceGetTemperature", handle, getattr(self.nvml, "NVML_TEMPERATURE_GPU", 0))
        temperature_c = finite_number(temperature)
        if temperature_c is not None:
            metrics["temperature_c"] = temperature_c
        utilization = self._optional(errors, "nvmlDeviceGetUtilizationRates", handle)
        if utilization is not None:
            gpu = finite_number(getattr(utilization, "gpu", None))
            memory = finite_number(getattr(utilization, "memory", None))
            if gpu is not None:
                metrics["gpu_utilization_percent"] = gpu
            if memory is not None:
                metrics["memory_utilization_percent"] = memory
        memory_info = self._optional(errors, "nvmlDeviceGetMemoryInfo", handle)
        if memory_info is not None:
            used = finite_number(getattr(memory_info, "used", None))
            total = finite_number(getattr(memory_info, "total", None))
            if used is not None:
                metrics["memory_used_bytes"] = int(used)
            if total is not None:
                metrics["memory_total_bytes"] = int(total)
        for key, constant_name in (("graphics_clock_mhz", "NVML_CLOCK_GRAPHICS"), ("memory_clock_mhz", "NVML_CLOCK_MEM")):
            constant = getattr(self.nvml, constant_name, None)
            if constant is not None:
                clock = self._optional(errors, "nvmlDeviceGetClockInfo", handle, constant)
                clock_value = finite_number(clock)
                if clock_value is not None:
                    metrics[key] = clock_value
        energy_mj = self._optional(errors, "nvmlDeviceGetTotalEnergyConsumption", handle)
        energy_value = finite_number(energy_mj)
        if energy_value is not None:
            metrics["energy_counter_mj"] = energy_value

        monotonic_ns = self.monotonic_clock_ns()
        timestamp_ns = self.wall_clock_ns()
        return {
            "schema_version": SCHEMA_VERSION,
            "event_id": stable_id(self.run_id, identity.uuid, monotonic_ns),
            "run_id": self.run_id,
            "event_kind": "nvml_device_sample",
            "source_tool": "nvml",
            "source_version": self.nvml_version,
            "device_index": identity.index,
            "gpu_uuid": identity.uuid,
            "gpu_model_name": identity.name,
            "pci_bus_id": identity.pci_bus_id,
            "device_scope": "whole_device",
            "device_attribution": "device_level_not_process_level",
            "timestamp_unix_ns": timestamp_ns,
            "monotonic_ns": monotonic_ns,
            "metrics": metrics,
            "unavailable_metric_functions": sorted(set(errors)),
            "quality": "unavailable" if not metrics else ("partial" if errors else "available"),
        }

    def sample_all(self) -> list[dict[str, Any]]:
        return [self.sample_device(identity, handle) for identity, handle in self.devices]


class EnergyAccumulator:
    def __init__(self, max_gap_seconds: float = 2.0):
        if max_gap_seconds <= 0:
            raise ValueError("max_gap_seconds must be > 0")
        self.max_gap_ns = int(max_gap_seconds * 1_000_000_000)
        self.samples: list[dict[str, Any]] = []

    def add(self, sample: dict[str, Any]) -> None:
        self.samples.append(sample)

    def result(self) -> dict[str, Any]:
        if len(self.samples) < 2:
            return {"energy_j": None, "method": "unavailable", "quality": "insufficient_samples",
                    "sample_count": len(self.samples), "integrated_intervals": 0, "gap_count": 0}
        counter_samples = [sample for sample in self.samples
                           if finite_number(sample.get("metrics", {}).get("energy_counter_mj")) is not None]
        counter_reset = any(
            float(right["metrics"]["energy_counter_mj"]) < float(left["metrics"]["energy_counter_mj"])
            for left, right in zip(counter_samples, counter_samples[1:])
        )
        if len(counter_samples) >= 2 and not counter_reset:
            delta_mj = float(counter_samples[-1]["metrics"]["energy_counter_mj"]) - float(counter_samples[0]["metrics"]["energy_counter_mj"])
            return {"energy_j": delta_mj / 1000.0, "method": "nvml_total_energy_counter",
                    "quality": "measured_counter", "sample_count": len(self.samples),
                    "counter_sample_count": len(counter_samples), "integrated_intervals": 0, "gap_count": 0}

        energy_j = 0.0
        integrated = 0
        gaps = 0
        for left, right in zip(self.samples, self.samples[1:]):
            t0 = left.get("monotonic_ns")
            t1 = right.get("monotonic_ns")
            p0 = finite_number(left.get("metrics", {}).get("power_w"))
            p1 = finite_number(right.get("metrics", {}).get("power_w"))
            if not isinstance(t0, int) or not isinstance(t1, int) or t1 <= t0 or p0 is None or p1 is None:
                gaps += 1
                continue
            delta_ns = t1 - t0
            if delta_ns > self.max_gap_ns:
                gaps += 1
                continue
            energy_j += ((p0 + p1) / 2.0) * (delta_ns / 1_000_000_000.0)
            integrated += 1
        if integrated == 0:
            return {"energy_j": None, "method": "trapezoidal_power_integration",
                    "quality": "unavailable", "sample_count": len(self.samples),
                    "integrated_intervals": 0, "gap_count": gaps, "counter_reset": counter_reset}
        return {"energy_j": energy_j, "method": "trapezoidal_power_integration",
                "quality": "estimated" if gaps == 0 else "partial_estimate",
                "sample_count": len(self.samples), "integrated_intervals": integrated,
                "gap_count": gaps, "counter_reset": counter_reset}


def derive_energy_efficiency(*, run_energy_j: float | None, run_duration_s: float,
                             baseline_energy_j: float | None, baseline_duration_s: float,
                             generated_output_tokens: int | None) -> dict[str, Any]:
    invalid = {"status": "invalid", "incremental_energy_j": None,
               "tokens_per_joule": None, "joules_per_token": None}
    if (run_energy_j is None or baseline_energy_j is None or run_duration_s <= 0
            or baseline_duration_s <= 0 or generated_output_tokens is None
            or generated_output_tokens <= 0 or not math.isfinite(run_energy_j)
            or not math.isfinite(baseline_energy_j)):
        return invalid
    baseline_for_run = baseline_energy_j * (run_duration_s / baseline_duration_s)
    incremental = run_energy_j - baseline_for_run
    if incremental <= 0:
        return {**invalid, "status": "invalid_nonpositive_incremental_energy"}
    return {"status": "available", "baseline_energy_scaled_j": baseline_for_run,
            "incremental_energy_j": incremental,
            "tokens_per_joule": generated_output_tokens / incremental,
            "joules_per_token": incremental / generated_output_tokens}


def positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be numeric") from exc
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and > 0")
    return number


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run_sampler(args: argparse.Namespace, nvml: Any) -> dict[str, Any]:
    output = args.output.expanduser().resolve()
    summary_path = output.with_name("nvml_energy_summary.json")
    if output.exists() or summary_path.exists():
        raise ValueError("NVML output or summary already exists; choose a new campaign path")
    output.parent.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or str(uuid.uuid4())
    nvml.nvmlInit()
    try:
        sampler = NVMLSampler(nvml, run_id)
        if not sampler.devices:
            raise RuntimeError("NVML reports zero GPU devices")
        accumulators = {identity.uuid: EnergyAccumulator(args.max_gap_seconds) for identity, _ in sampler.devices}
        started_wall = time.time_ns()
        started_mono = time.monotonic_ns()
        sample_count = 0
        with output.open("x", encoding="utf-8") as stream:
            while True:
                samples = sampler.sample_all()
                for sample in samples:
                    stream.write(json.dumps(sample, separators=(",", ":"), allow_nan=False) + "\n")
                    accumulators[sample["gpu_uuid"]].add(sample)
                    sample_count += 1
                stream.flush()
                elapsed = (time.monotonic_ns() - started_mono) / 1_000_000_000.0
                if elapsed >= args.duration_seconds:
                    break
                time.sleep(min(args.interval_ms / 1000.0, max(0.0, args.duration_seconds - elapsed)))
        finished_wall = time.time_ns()
        finished_mono = time.monotonic_ns()
        devices = []
        for identity, _ in sampler.devices:
            devices.append({
                "device_index": identity.index, "gpu_uuid": identity.uuid,
                "gpu_model_name": identity.name, "pci_bus_id": identity.pci_bus_id,
                "device_scope": "whole_device",
                "device_attribution": "device_level_not_process_level",
                "energy": accumulators[identity.uuid].result(),
            })
        report = {
            "schema_version": SCHEMA_VERSION, "run_id": run_id,
            "source_tool": "nvml", "source_version": sampler.nvml_version,
            "started_at_unix_ns": started_wall, "finished_at_unix_ns": finished_wall,
            "started_monotonic_ns": started_mono, "finished_monotonic_ns": finished_mono,
            "duration_seconds": (finished_mono - started_mono) / 1_000_000_000.0,
            "interval_ms_requested": args.interval_ms, "sample_count": sample_count,
            "samples_file": output.name, "devices": devices,
            "energy_policy": "prefer NVML cumulative energy counter; otherwise trapezoidal integration of sampled power; GPU values are device-wide and not process-attributed.",
        }
        write_json_atomic(summary_path, report)
        return report
    finally:
        nvml.nvmlShutdown()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=positive_float, default=30.0)
    parser.add_argument("--interval-ms", type=int, default=500)
    parser.add_argument("--max-gap-seconds", type=positive_float, default=2.0)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    if args.interval_ms < 50:
        parser.error("--interval-ms must be >= 50")
    try:
        import pynvml as nvml
        report = run_sampler(args, nvml)
    except ImportError:
        print("ERROR: pynvml is unavailable; install nvidia-ml-py in this environment", file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError, AttributeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"run_id": report["run_id"], "sample_count": report["sample_count"],
                      "devices": len(report["devices"]), "summary": "nvml_energy_summary.json"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())