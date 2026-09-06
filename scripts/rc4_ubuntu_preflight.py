#!/usr/bin/env python3
"""RC4 physical preflight: hardware probe + evidence-bounded FitLLM preselection.

Problem
    Before any install or measurement, RC4 needs a reproducible snapshot of the
    host (hardware-profile.v1) and a proposal that respects USER_INTENT[] and the
    evidence-backed intersection with LLMFit.

Inputs
    --purpose  (repeatable, required)  e.g. programming, reasoning
    --max-context  optional token cap for estimation
    --out  JSON artifact path (relative paths resolve under the repo root)

Outputs
    JSON schema leones.rc4.ubuntu_preflight.v1 with:
      hardware_profile, fitllm_preselection, execution_authorized=false,
      measurement_authorized=false, measured=false, next_step

What this script does NOT do
    Install models, start runtimes, authorize execution, or claim MEASURED.
    Invent candidates when the intersection has fewer than three matches
    (status becomes insufficient).

Why this boundary exists
    RC4 separates discovery/preselection from physical measurement. Mixing them
    would present external estimates as local evidence.

Contract failure examples
    Non-Linux host -> exit 2
    hardware_profile.py failure -> exit 2
    Missing --purpose -> argparse error
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
    """Run the canonical LEONES hardware probe; return hardware-profile.v1."""
    cmd = [sys.executable, str(ROOT / "scripts/hardware_profile.py")]
    completed = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, check=False
    )
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
    parser.add_argument(
        "--purpose",
        dest="purposes",
        action="append",
        required=True,
        help=(
            "User intent purpose (repeatable). "
            "Example: --purpose programming --purpose reasoning"
        ),
    )
    parser.add_argument("--max-context", type=int, default=None)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else (ROOT / args.out)
    out = out.resolve()

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
        print(
            f"RC4 UBUNTU PREFLIGHT: BLOCKED — hardware probe: {exc}",
            file=sys.stderr,
        )
        return 2

    # user_intent is mandatory and multiple; recommend() never pads to 3.
    recommendation = recommend(
        user_intent=args.purposes,
        max_context=args.max_context,
    )
    status = recommendation.get("status") or "ok"
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
            "USER_SELECT_MODEL_AND_STACK"
            if status == "ok"
            else "REVIEW_INSUFFICIENT_OR_INSTALL_FITLLM"
        ),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("RC4 UBUNTU PREFLIGHT: PASS")
    print(f"  hardware: {hardware.get('schema_version', 'UNKNOWN')}")
    print(
        f"  FitLLM: {status} "
        f"({recommendation.get('candidate_count', 0)}/3 candidates)"
    )
    print("  execution_authorized: False")
    print("  measurement_authorized: False")
    print("  measured: False")
    try:
        artifact = out.relative_to(ROOT)
    except ValueError:
        artifact = out
    print(f"  artifact: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
