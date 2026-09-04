#!/usr/bin/env python3
"""RC3 disk-capacity gate before model/stack selection.

The check is deliberately conservative and provenance-aware:
- Hermes: 2 GiB recommended persistent space (upstream guidance).
- LLM: 2 GiB local planning reserve for a small quantized model, temporary
  downloads and runtime artifacts. This is a LEONES safety reserve, not a
  vendor minimum; the exact model artifact is checked again before download.
- Magnitude: 5 GiB LEONES planning reserve because Magnitude has no fixed
  upstream disk minimum; the selected model artifact is included in the
  final download gate.
- ODS: 40 GiB upstream free-disk requirement for models/container images.

No files are downloaded or installed by this command.
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
SCHEMA_VERSION = "disk-preflight.v1"


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
    paths = {
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
    return {
        "schema_version": SCHEMA_VERSION,
        "verification": "detected",
        "filesystem": disk,
        "requirements": requirements,
        "combined_reserves_gib": combined,
        "status": status,
        "existing_paths": paths,
        "download_installation": {"performed": False},
        "selection_gate": {
            "ready": status["hermes"] and status["llm"] and (
                status["magnitude"] or status["ods"]
            ),
            "model_artifact_recheck_required": True,
            "stack_choice_required": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="LEONES RC3 disk-capacity preflight")
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
    print("RC3 DISK PREFLIGHT")
    print(f"Filesystem: {fs['path']}")
    print(f"Free: {fs['mount_free_gib']:.2f} GiB / {fs['mount_total_gib']:.2f} GiB")
    for key in ("hermes", "llm", "magnitude", "ods"):
        req = report["requirements"][key]["required_gib"]
        ok = "PASS" if report["status"][key] else "BLOCK"
        print(f"  {key:10s}: {ok:5s} · reserve/requirement={req:.2f} GiB")
    print(
        "  combined  : "
        f"Hermes+LLM+Magnitude={report['combined_reserves_gib']['hermes_plus_llm_plus_magnitude']:.2f} GiB · "
        f"Hermes+LLM+ODS={report['combined_reserves_gib']['hermes_plus_llm_plus_ods']:.2f} GiB"
    )
    print(f"SELECTION GATE: {'READY' if report['selection_gate']['ready'] else 'BLOCKED'}")
    print("MODEL ARTIFACT RECHECK: required before download")
    print("INSTALL/DOWNLOAD PERFORMED: false")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"REPORT: {args.out}")
    return 0 if report["selection_gate"]["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
