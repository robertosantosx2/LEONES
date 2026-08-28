#!/usr/bin/env python3
"""LEONES E2E orchestrator v0.1.

Runs the local evidence pipeline without inventing measurements:
hardware -> model -> task -> router -> runtime -> inference -> LOTB.
Each step is optional and consumes existing JSON artifacts when available.
"""

from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "e2e"
OUT.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], output: Path) -> dict:
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=120)
        result = {
            "command": cmd,
            "returncode": p.returncode,
            "stdout": p.stdout[-12000:],
            "stderr": p.stderr[-4000:],
        }
    except Exception as exc:
        result = {"command": cmd, "error": str(exc)}
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="chat")
    ap.add_argument("--skip-probes", action="store_true")
    args = ap.parse_args()

    manifest = {"version": "0.1", "task": args.task, "steps": []}
    scripts = ROOT / "scripts"
    if not args.skip_probes:
        for name in ("leones-hardware.py", "leones-model.py", "leones-runtime.py"):
            path = scripts / name
            if path.exists():
                r = run(["python3", str(path)], OUT / f"{path.stem}.json")
                manifest["steps"].append(
                    {"name": path.stem, "returncode": r.get("returncode")}
                )

    task = scripts / "leones-task.py"
    if task.exists():
        r = run(["python3", str(task), args.task], OUT / "leones-task.json")
        manifest["steps"].append({"name": "task", "returncode": r.get("returncode")})

    manifest["status"] = "prepared"
    manifest["note"] = (
        "No performance or capability claim is made until a real local runtime/model and LOTB execution produce evidence."
    )
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
