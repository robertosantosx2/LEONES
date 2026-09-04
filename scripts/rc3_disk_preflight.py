#!/usr/bin/env python3
"""RC3 disk + installation preflight before model/stack selection.

The check is deliberately conservative and provenance-aware:
- Hermes: 2 GiB recommended persistent space (upstream guidance).
- LLM: 2 GiB local planning reserve for a small quantized model, temporary
  downloads and runtime artifacts. This is a LEONES safety reserve, not a
  vendor minimum; the exact model artifact is checked again before download.
- Magnitude: 5 GiB LEONES planning reserve because Magnitude has no fixed
  upstream disk minimum; the selected model artifact is included in the
  final download gate.
- ODS: 40 GiB upstream free-disk requirement for models/container images.

Installation detection is read-only: command/path presence only. No files are
installed, downloaded, started, stopped, or modified by this command.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

GIB = 1024**3
HERMES_RECOMMENDED_GIB = 2.0
LLM_RESERVE_GIB = 2.0
MAGNITUDE_RESERVE_GIB = 5.0
ODS_REQUIRED_GIB = 40.0
SCHEMA_VERSION = "disk-preflight.v2"


def _usage(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    usage = shutil.disk_usage(path)
    return {
        "path": str(path),
        "mount_free_bytes": usage.free,
        "mount_free_gib": round(usage.free / GIB, 3),
        "mount_total_gib": round(usage.total / GIB, 3),
    }


def _existing(path: Path) -> dict[str, Any]:
    path = path.expanduser()
    if not path.exists():
        return {"path": str(path), "exists": False, "size_bytes": 0}
    total = 0
    if path.is_file():
        total = path.stat().st_size
    else:
        for root, dirs, files in os.walk(path):
            for name in files:
                try:
                    total += (Path(root) / name).stat().st_size
                except OSError:
                    pass
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": total,
        "size_gib": round(total / GIB, 3),
    }


def _command(name: str) -> dict[str, Any]:
    resolved = shutil.which(name)
    return {
        "name": name,
        "found": resolved is not None,
        "path": resolved,
    }


def _installation_state() -> dict[str, Any]:
    """Detect already-installed tools without executing them."""
    home = Path.home()
    commands = {
        "hermes": _command("hermes"),
        "magnitude": _command("magnitude"),
        "ods": _command("ods"),
    }
    paths = {
        "hermes_state": _existing(home / ".hermes"),
        "hermes_bin": _existing(home / ".local" / "bin" / "hermes"),
        "magnitude_state": _existing(home / ".magnitude"),
        "ods_runtime": _existing(home / "ods"),
        "ods_cli": _existing(home / "ods" / "ods-cli"),
    }
    installed = {
        "hermes": commands["hermes"]["found"] or paths["hermes_state"]["exists"] or paths["hermes_bin"]["exists"],
        "magnitude": commands["magnitude"]["found"] or paths["magnitude_state"]["exists"],
        "ods": commands["ods"]["found"] or paths["ods_runtime"]["exists"] or paths["ods_cli"]["exists"],
    }
    return {
        "method": "read_only_command_and_path_detection",
        "commands": commands,
        "paths": paths,
        "installed": installed,
    }


def build_report(
    *,
    base: Path,
    llm_reserve_gib: float = LLM_RESERVE_GIB,
    magnitude_reserve_gib: float = MAGNITUDE_RESERVE_GIB,
) -> dict[str, Any]:
    disk = _usage(base)
    free = disk["mount_free_gib"]
    requirements = {
        "hermes": {
            "required_gib": HERMES_RECOMMENDED_GIB,
            "basis": "upstream_recommended",
            "scope": "persistent Hermes installation/data",
        },
        "llm": {
            "required_gib": llm_reserve_gib,
            "basis": "leones_safety_reserve",
            "scope": "model download + temporary files + runtime headroom",
        },
        "magnitude": {
            "required_gib": magnitude_reserve_gib,
            "basis": "leones_safety_reserve",
            "scope": "Magnitude installation/runtime; model checked separately",
        },
        "ods": {
            "required_gib": ODS_REQUIRED_GIB,
            "basis": "upstream_requirement",
            "scope": "models and container images",
        },
    }
    existing_paths = {
        "hermes": _existing(Path.home() / ".hermes"),
        "hermes_bin": _existing(Path.home() / ".local" / "bin" / "hermes"),
        "leones": _existing(base),
        "magnitude": _existing(Path.home() / ".magnitude"),
        "ods": _existing(Path.home() / "ods"),
    }

    combined = {
        "hermes_plus_llm_plus_magnitude": HERMES_RECOMMENDED_GIB
        + llm_reserve_gib
        + magnitude_reserve_gib,
        "hermes_plus_llm_plus_ods": HERMES_RECOMMENDED_GIB
        + llm_reserve_gib
        + ODS_REQUIRED_GIB,
    }
    status = {
        "hermes": free >= requirements["hermes"]["required_gib"],
        "llm": free >= requirements["llm"]["required_gib"],
        "magnitude": free >= requirements["magnitude"]["required_gib"],
        "ods": free >= requirements["ods"]["required_gib"],
        "hermes_plus_llm_plus_magnitude": free >= combined["hermes_plus_llm_plus_magnitude"],
        "hermes_plus_llm_plus_ods": free >= combined["hermes_plus_llm_plus_ods"],
    }
    stack_readiness = {
        "magnitude": {
            "ready": status["hermes_plus_llm_plus_magnitude"],
            "required_gib": combined["hermes_plus_llm_plus_magnitude"],
            "headroom_gib": round(free - combined["hermes_plus_llm_plus_magnitude"], 3),
        },
        "ods": {
            "ready": status["hermes_plus_llm_plus_ods"],
            "required_gib": combined["hermes_plus_llm_plus_ods"],
            "headroom_gib": round(free - combined["hermes_plus_llm_plus_ods"], 3),
        },
    }
    selection_ready = status["hermes"] and status["llm"] and any(
        option["ready"] for option in stack_readiness.values()
    )
    any_constraints = not all(option["ready"] for option in stack_readiness.values())

    return {
        "schema_version": SCHEMA_VERSION,
        "verification": "detected",
        "filesystem": disk,
        "requirements": requirements,
        "combined_reserves_gib": combined,
        "status": status,
        "existing_paths": existing_paths,
        "installation": _installation_state(),
        "download_installation": {"performed": False},
        "selection_gate": {
            "ready": selection_ready,
            "state": "READY_WITH_CONSTRAINTS" if selection_ready and any_constraints else ("READY" if selection_ready else "BLOCKED"),
            "stack_readiness": stack_readiness,
            "model_artifact_recheck_required": True,
            "stack_choice_required": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="LEONES RC3 disk + installation preflight")
    parser.add_argument("--base", default=".", help="filesystem location to inspect")
    parser.add_argument("--out", help="write JSON report")
    parser.add_argument("--llm-reserve-gib", type=float, default=LLM_RESERVE_GIB)
    parser.add_argument("--magnitude-reserve-gib", type=float, default=MAGNITUDE_RESERVE_GIB)
    args = parser.parse_args()

    report = build_report(
        base=Path(args.base),
        llm_reserve_gib=args.llm_reserve_gib,
        magnitude_reserve_gib=args.magnitude_reserve_gib,
    )
    fs = report["filesystem"]
    print("RC3 DISK + INSTALLATION PREFLIGHT")
    print(f"Filesystem: {fs['path']}")
    print(f"Free: {fs['mount_free_gib']:.2f} GiB / {fs['mount_total_gib']:.2f} GiB")
    for key in ("hermes", "llm", "magnitude", "ods"):
        req = report["requirements"][key]["required_gib"]
        ok = "PASS" if report["status"][key] else "BLOCK"
        print(f"  {key:10s}: {ok:5s} · reserve/requirement={req:.2f} GiB")
    print("INSTALLATION DETECTION (read-only)")
    for key in ("hermes", "magnitude", "ods"):
        state = "INSTALLED/PRESENT" if report["installation"]["installed"][key] else "NOT DETECTED"
        command = report["installation"]["commands"][key]
        print(f"  {key:10s}: {state} · command={command['path'] or 'not found'}")
    print(
        "  combined  : "
        f"Hermes+LLM+Magnitude={report['combined_reserves_gib']['hermes_plus_llm_plus_magnitude']:.2f} GiB · "
        f"Hermes+LLM+ODS={report['combined_reserves_gib']['hermes_plus_llm_plus_ods']:.2f} GiB"
    )
    print(f"SELECTION GATE: {report['selection_gate']['state']}")
    for stack, option in report["selection_gate"]["stack_readiness"].items():
        state = "READY" if option["ready"] else "BLOCKED"
        print(f"  {stack:10s}: {state} · headroom={option['headroom_gib']:.2f} GiB")
    print("MODEL ARTIFACT RECHECK: required before download")
    print("INSTALL/DOWNLOAD PERFORMED: false")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"REPORT: {args.out}")
    return 0 if report["selection_gate"]["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
