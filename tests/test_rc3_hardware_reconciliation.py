"""RC3 hardware probe/reconciliation contract tests."""
from __future__ import annotations

from scripts import hardware_profile
from scripts import rc3_hardware_discovery
from runtime_selection.hardware_profile import normalize_hardware, reconcile_hardware


def test_canonical_cpu_probe_is_locale_independent(monkeypatch):
    monkeypatch.setattr(
        hardware_profile,
        "_run",
        lambda *args, **kwargs: "0,0,0\n1,0,0\n2,1,0\n3,1,0\n4,2,0\n5,2,0\n6,3,0\n7,3,0\n" if args[:2] == ("lscpu", "-p=CPU,Core") else "",
    )
    monkeypatch.setattr(
        hardware_profile.Path,
        "read_text",
        lambda self, *args, **kwargs: "model name\t: Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz\nflags\t: avx avx2 avx512f avx512_vnni\n",
    )
    cpu = hardware_profile.cpu()
    assert cpu["model"] == "Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz"
    assert cpu["logical_cpus"] == 8
    assert cpu["physical_cores"] == 4
    assert cpu["sockets"] == 1
    assert cpu["threads_per_core"] == 2
    assert {"avx", "avx2", "avx512f", "avx512_vnni"} <= set(cpu["flags"])


def test_reconciliation_prefers_detected_hardware():
    declared = {"schema": "hardware-profile.v1", "cpu": {"model": "declared"}, "ram_gb": 16}
    detected = {"schema": "hardware-profile.v1", "cpu": {"model": "detected"}, "ram_gb": 8}
    result = reconcile_hardware(declared, detected)
    assert result["source"] == "reconciled"
    assert result["verification"] == "discrepancy"
    assert result["cpu"]["model"] == "detected"
    assert result["ram_gb"] == 8
    assert set(result["discrepancies"]) == {"cpu", "ram_gb"}


def test_rc3_adapter_uses_canonical_probe(monkeypatch):
    canonical = {
        "schema_version": "hardware-profile.v1",
        "probe": "LEONES-hardware-profile",
        "observed_at_utc": "2026-09-04T20:00:00+00:00",
        "platform": {"system": "Linux", "release": "7.0.0", "machine": "x86_64"},
        "cpu": {
            "model": "Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz",
            "architecture": "x86_64",
            "logical_cpus": 8,
            "physical_cores": 4,
            "threads_per_core": 2,
            "sockets": 1,
            "flags": ["avx", "avx2", "avx512f", "avx512_vnni"],
        },
        "memory": {"visible_to_os_bytes": 8 * 1024**3, "available_bytes": 2 * 1024**3},
        "gpu": [{
            "pci_address": "0000:00:02.0",
            "description": "Intel Iris Plus Graphics G1",
            "vendor_device_id": "8086:8a56",
            "driver": "i915",
        }],
        "accelerator_tools": {},
    }
    monkeypatch.setattr(rc3_hardware_discovery, "profile", lambda: canonical)
    result = rc3_hardware_discovery.discover()
    assert result["schema"] == "hardware-profile.v1"
    assert result["cpu"]["physical_cores"] == 4
    assert result["cpu"]["threads_per_core"] == 2
    assert result["gpu"][0]["vendor_device_id"] == "8086:8a56"
    assert result["gpu"][0]["driver"] == "i915"
    assert result["backend"] == ["i915"]
    assert result["accelerators"] == ["avx", "avx2", "avx512f", "avx512_vnni"]
    assert result["hermes"]["discovery_cli"] == "not-exposed"


def test_normalization_preserves_unknowns_without_fabrication():
    result = normalize_hardware({"schema": "hardware-profile.v1", "ram": {"total_gb": 8}, "vram_gb": None})
    assert result["ram_gb"] == 8
    assert result["vram_gb"] is None
    assert result["gpu"] is None
