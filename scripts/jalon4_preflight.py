"""JALON 4 host preflight: inspect only, never install or download."""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "runtime_registry.v1.1.json"
OPERATIONAL = {
    "soho": ["llama.cpp", "FreeToken", "AirLLM", "ollama"],
    "cpd": ["vLLM", "SGLang"],
}


def command_version(command: str) -> str | None:
    exe = shutil.which(command)
    if not exe:
        return None
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (p.stdout or p.stderr).strip().splitlines()
    return text[0] if text else "present"


def python_module(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["soho", "cpd", "all"], default="all")
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    names = OPERATIONAL["soho"] + OPERATIONAL["cpd"] if args.profile == "all" else OPERATIONAL[args.profile]
    entries = {x["id"]: x for x in registry["runtimes"]}

    print("JALON4_PREFLIGHT_V1")
    print(f"platform={platform.system()} {platform.release()} {platform.machine()}")
    print(f"python={platform.python_version()}")
    print(f"profile={args.profile}")
    print(f"operational={','.join(names)}")
    print(f"model_artifacts={sum(1 for _ in (ROOT / 'artifacts/models').glob('*.gguf')) if (ROOT / 'artifacts/models').exists() else 0}")

    for name in names:
        entry = entries[name]
        argv = entry["entrypoint"]["argv"]
        checks: list[str] = []
        if entry["entrypoint"]["kind"] == "executable" and argv:
            checks.append(f"executable={command_version(argv[0]) or 'MISSING'}")
        elif entry["entrypoint"]["kind"] == "python-module" and argv:
            checks.append(f"module={argv[0]}:{'present' if python_module(argv[0]) else 'MISSING'}")
        elif entry["entrypoint"]["kind"] == "service" and argv:
            checks.append(f"service_cli={command_version(argv[0]) or 'MISSING'}")
        else:
            checks.append("entrypoint=adapter-controlled")
        print(f"{name}: " + "; ".join(checks))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
