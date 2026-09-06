#!/usr/bin/env python3
"""RC4 physical preflight: canonical hardware probe + FitLLM preselection.

This is deliberately a preflight only. It does not install, execute a model,
or authorize measurement. Physical MEASURED remains outside this script.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rc4_fitllm_recommend import recommend  # noqa: E402


def run_hardware_probe() -> dict:
    cmd = [sys.executable, str(ROOT / "scripts/hardware_profile.py")]
    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "hardware_profile.py failed: "
            + (completed.stderr.strip() or completed.stdout.strip() or "unknown error")
        )
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "rc4-ubuntu-preflight.json",
    )
    parser.add_argument("--use-case", default=None)
    parser.add_argument("--max-context", type=int, default=None)
    args = parser.parse_args()

    if platform.system() != "Linux":
        print(
            "RC4 UBUNTU PREFLIGHT: BLOCKED — "
            f"host OS is {platform.system()}, expected Linux/Ubuntu",
            file=sys.stderr,
        )
        return 2

    observed_at = datetime.now(timezone.utc).isoformat()
    try:
        hardware = run_hardware_probe()
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"RC4 UBUNTU PREFLIGHT: BLOCKED — hardware probe: {exc}", file=sys.stderr)
        return 2

    recommendation = recommend(use_case=args.use_case, max_context=args.max_context)
    payload = {
        "schema": "leones.rc4.ubuntu_preflight.v1",
        "observed_at_utc": observed_at,
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "hardware_profile": hardware,
        "fitllm_preselection": recommendation,
        "execution_authorized": False,
        "measurement_authorized": False,
        "measured": False,
        "next_step": (
            "USER_SELECT_MODEL_AND_STACK" if recommendation["status"] == "ok"
            else "INSTALL_FITLLM_OR_SELECT_MODEL_MANUALLY"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("RC4 UBUNTU PREFLIGHT: PASS")
    print(f"  hardware: {hardware.get('schema_version', 'UNKNOWN')}")
    print(
        f"  FitLLM: {recommendation['status']} "
        f"({recommendation['candidate_count']}/3 candidates)"
    )
    print("  execution_authorized: False")
    print("  measurement_authorized: False")
    print("  measured: False")
    print(f"  artifact: {args.out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
