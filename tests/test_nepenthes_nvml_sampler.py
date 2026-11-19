from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.nepenthes_nvml_sampler import EnergyAccumulator, NVMLSampler, derive_energy_efficiency


class FakeNVML:
    NVML_TEMPERATURE_GPU = 0
    NVML_CLOCK_GRAPHICS = 0
    NVML_CLOCK_MEM = 1

    def __init__(self):
        self.energy_values = iter([1000, 3500])

    def nvmlSystemGetNVMLVersion(self):
        return b"NVML fake-1"

    def nvmlDeviceGetCount(self):
        return 1

    def nvmlDeviceGetHandleByIndex(self, index):
        return {"index": index}

    def nvmlDeviceGetUUID(self, handle):
        return b"GPU-test-uuid"

    def nvmlDeviceGetName(self, handle):
        return b"NVIDIA RTX 3050 Laptop GPU"

    def nvmlDeviceGetPciInfo(self, handle):
        return SimpleNamespace(busId=b"00000000:01:00.0")

    def nvmlDeviceGetPowerUsage(self, handle):
        return 45000

    def nvmlDeviceGetTemperature(self, handle, sensor):
        return 61

    def nvmlDeviceGetUtilizationRates(self, handle):
        return SimpleNamespace(gpu=55, memory=30)

    def nvmlDeviceGetMemoryInfo(self, handle):
        return SimpleNamespace(used=2_000_000_000, total=4_000_000_000)

    def nvmlDeviceGetClockInfo(self, handle, clock):
        return 1500 if clock == self.NVML_CLOCK_GRAPHICS else 6000

    def nvmlDeviceGetTotalEnergyConsumption(self, handle):
        return next(self.energy_values)


def test_nvml_sampler_records_device_metrics_and_stable_identity():
    monotonic = iter([1_000_000_000, 2_000_000_000])
    wall = iter([1_800_000_000_000_000_000, 1_800_000_001_000_000_000])
    sampler = NVMLSampler(FakeNVML(), "run-1",
                          monotonic_clock_ns=lambda: next(monotonic),
                          wall_clock_ns=lambda: next(wall))
    first = sampler.sample_all()[0]
    second = sampler.sample_all()[0]
    assert first["gpu_uuid"] == "GPU-test-uuid"
    assert first["pci_bus_id"] == "00000000:01:00.0"
    assert first["metrics"]["power_w"] == 45.0
    assert first["metrics"]["temperature_c"] == 61.0
    assert first["metrics"]["gpu_utilization_percent"] == 55.0
    assert first["metrics"]["memory_used_bytes"] == 2_000_000_000
    assert second["metrics"]["energy_counter_mj"] == 3500.0
    assert first["device_attribution"] == "device_level_not_process_level"
    assert "pid" not in first and "process" not in first


def test_energy_accumulator_prefers_nvml_cumulative_energy_counter():
    accumulator = EnergyAccumulator()
    accumulator.add({"monotonic_ns": 1_000_000_000, "metrics": {"energy_counter_mj": 1000}})
    accumulator.add({"monotonic_ns": 2_000_000_000, "metrics": {"energy_counter_mj": 3500}})
    result = accumulator.result()
    assert result["energy_j"] == 2.5
    assert result["method"] == "nvml_total_energy_counter"
    assert result["quality"] == "measured_counter"


def test_energy_accumulator_uses_trapezoidal_power_fallback():
    accumulator = EnergyAccumulator(max_gap_seconds=2.0)
    accumulator.add({"monotonic_ns": 0, "metrics": {"power_w": 30.0}})
    accumulator.add({"monotonic_ns": 2_000_000_000, "metrics": {"power_w": 50.0}})
    result = accumulator.result()
    assert result["energy_j"] == 80.0
    assert result["method"] == "trapezoidal_power_integration"
    assert result["quality"] == "estimated"


def test_energy_accumulator_marks_gaps_instead_of_fabricating_energy():
    accumulator = EnergyAccumulator(max_gap_seconds=2.0)
    accumulator.add({"monotonic_ns": 0, "metrics": {"power_w": 30.0}})
    accumulator.add({"monotonic_ns": 10_000_000_000, "metrics": {"power_w": 40.0}})
    accumulator.add({"monotonic_ns": 11_000_000_000, "metrics": {"power_w": 50.0}})
    result = accumulator.result()
    assert result["energy_j"] == 45.0
    assert result["gap_count"] == 1
    assert result["quality"] == "partial_estimate"


def test_counter_reset_falls_back_to_power_integration():
    accumulator = EnergyAccumulator(max_gap_seconds=2.0)
    accumulator.add({"monotonic_ns": 0, "metrics": {"energy_counter_mj": 5000, "power_w": 20.0}})
    accumulator.add({"monotonic_ns": 1_000_000_000, "metrics": {"energy_counter_mj": 100, "power_w": 40.0}})
    result = accumulator.result()
    assert result["method"] == "trapezoidal_power_integration"
    assert result["energy_j"] == 30.0
    assert result["counter_reset"] is True


def test_energy_efficiency_scales_idle_baseline_and_rejects_nonpositive_delta():
    result = derive_energy_efficiency(run_energy_j=100.0, run_duration_s=10.0,
                                      baseline_energy_j=20.0, baseline_duration_s=5.0,
                                      generated_output_tokens=1200)
    assert result["incremental_energy_j"] == 60.0
    assert result["tokens_per_joule"] == 20.0
    assert result["joules_per_token"] == 0.05
    invalid = derive_energy_efficiency(run_energy_j=10.0, run_duration_s=10.0,
                                       baseline_energy_j=10.0, baseline_duration_s=10.0,
                                       generated_output_tokens=100)
    assert invalid["status"] == "invalid_nonpositive_incremental_energy"
    assert invalid["tokens_per_joule"] is None


def test_energy_efficiency_rejects_missing_or_invalid_inputs():
    result = derive_energy_efficiency(run_energy_j=None, run_duration_s=10.0,
                                      baseline_energy_j=1.0, baseline_duration_s=10.0,
                                      generated_output_tokens=100)
    assert result["status"] == "invalid"
    assert result["incremental_energy_j"] is None

def test_nvml_sampler_marks_unsupported_energy_counter_without_fabricating_a_value():
    class NoEnergyNVML(FakeNVML):
        def nvmlDeviceGetTotalEnergyConsumption(self, handle):
            raise RuntimeError("unsupported")

    sampler = NVMLSampler(NoEnergyNVML(), "run-no-energy")
    sample = sampler.sample_all()[0]
    assert "energy_counter_mj" not in sample["metrics"]
    assert "nvmlDeviceGetTotalEnergyConsumption" in sample["unavailable_metric_functions"]
    assert sample["quality"] == "partial"


def test_energy_efficiency_rejects_nonfinite_durations_and_boolean_token_counts():
    nonfinite = derive_energy_efficiency(run_energy_j=10.0, run_duration_s=float("nan"),
                                         baseline_energy_j=1.0, baseline_duration_s=1.0,
                                         generated_output_tokens=100)
    boolean_tokens = derive_energy_efficiency(run_energy_j=10.0, run_duration_s=1.0,
                                              baseline_energy_j=1.0, baseline_duration_s=1.0,
                                              generated_output_tokens=True)
    assert nonfinite["status"] == "invalid"
    assert boolean_tokens["status"] == "invalid"
