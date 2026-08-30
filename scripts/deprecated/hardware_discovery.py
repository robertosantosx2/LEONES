#!/usr/bin/env python3
"""Historical hardware discovery and microbenchmark helper.

RC1 separates hardware observation from measurement. The active
``hardware_profile.py`` owns the hardware observation boundary; runtime
measurement is handled by the authorized execution/evidence path. This older
script mixed inventory with optional NumPy/fio-style measurements and is kept
only for provenance.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path


def cmd(args):
    try:
        return subprocess.check_output(
            args, text=True, stderr=subprocess.DEVNULL, timeout=20
        ).strip()
    except Exception:
        return ""


def first_line(s):
    return s.splitlines()[0].strip() if s else ""


def lscpu():
    raw = cmd(["lscpu"])
    out = {}
    for line in raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return {
        "model": out.get("Model name", ""),
        "architecture": out.get("Architecture", ""),
        "cores": out.get("CPU(s)", ""),
        "threads_per_core": out.get("Thread(s) per core", ""),
        "frequency_mhz": out.get("CPU max MHz", out.get("CPU MHz", "")),
        "simd": out.get("Flags", ""),
    }


def memory():
    raw = cmd(["free", "-b"])
    total = ""
    for line in raw.splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            total = parts[1] if len(parts) > 1 else ""
    return {"capacity_bytes": int(total) if total.isdigit() else None}


def storage():
    raw = cmd(["lsblk", "-J", "-o", "NAME,TYPE,SIZE,MODEL,TRAN"])
    try:
        data = json.loads(raw)
    except Exception:
        return []
    return [
        {
            "name": d.get("name"),
            "type": d.get("type"),
            "size": d.get("size"),
            "model": d.get("model"),
            "transport": d.get("tran"),
        }
        for d in data.get("blockdevices", [])
        if d.get("type") == "disk"
    ]


def gpu():
    text = cmd(["lspci", "-mm"])
    return [
        line
        for line in text.splitlines()
        if any(
            label in line
            for label in (
                "VGA compatible controller",
                "3D controller",
                "Display controller",
            )
        )
    ]


def numpy_measure():
    try:
        import numpy as np
    except Exception:
        return {"status": "numpy_not_installed"}
    n = 2048
    a = np.random.random((n, n)).astype(np.float32)
    b = np.random.random((n, n)).astype(np.float32)
    t0 = time.perf_counter()
    a @ b
    dt = time.perf_counter() - t0
    flops = (2.0 * n**3) / max(dt, 1e-9)
    x = np.empty(256 * 1024 * 1024 // 4, dtype=np.float32)
    t0 = time.perf_counter()
    x.copy()
    dt2 = time.perf_counter() - t0
    bw = x.nbytes / max(dt2, 1e-9) / 1e9
    return {
        "cpu_matrix_gflops": flops / 1e9,
        "cpu_matrix_mflops": flops / 1e6,
        "memory_copy_gb_s": bw,
        "method": "numpy_float32_matmul_and_copy",
    }


def main():
    result = {
        "schema": "leones-hardware-discovery-0.1",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "cpu": lscpu(),
        "memory": memory(),
        "storage": storage(),
        "gpu_pci": gpu(),
        "measurements": numpy_measure(),
        "privacy": {
            "identity": "excluded",
            "hostname": "excluded",
            "serials": "excluded",
            "uuid": "excluded",
            "mac_ip": "excluded",
            "exact_location": "excluded",
            "private_paths": "excluded",
        },
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
