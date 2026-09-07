#!/usr/bin/env python3
"""RC4 component inventory and independent uninstall offers.

Problem
    Before recommending installs, RC4 must show what is already on the host and
    offer independent uninstall of each optional component. LEONES uninstall is
    offered last and never implied by other removals.

Inputs
    Live host probes (CLI presence, common paths). Optional --json.

Outputs
    Schema leones.rc4.component_inventory.v1 with components[] and
    uninstall_offers[]. Human-readable ASCII panel by default.

What this script does NOT do
    Perform uninstalls by itself (unless --apply with explicit selection).
    Delete evidence or the source checkout.
    Treat Hermes/OMH as model selectors.

Canonical uninstall entry remains scripts/uninstall.sh for destructive actions.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "leones.rc4.component_inventory.v1"

CATALOG: list[dict[str, Any]] = [
    {
        "component_id": "fitllm",
        "display_name": "FitLLM / LLMFit",
        "commands": ["llmfit", "fitllm"],
        "paths": [],
        "uninstall_flag": "--fitllm",
        "group": "recommender",
        "notes": "Recomendador ESTIMATED opcional. No es autoridad LEONES.",
    },
    {
        "component_id": "magnitude",
        "display_name": "Magnitude",
        "commands": ["magnitude"],
        "paths": ["~/magnitude", "~/leones-work/Magnitude"],
        "uninstall_flag": "--magnitude",
        "group": "stack",
        "notes": "Stack de ejecución. Desinstalable de forma independiente.",
    },
    {
        "component_id": "ods",
        "display_name": "ODS",
        "commands": ["ods"],
        "paths": ["~/ods", "~/leones-work/ODS"],
        "uninstall_flag": "--ods",
        "group": "stack",
        "notes": "Stack Docker/compose. No desinstala Docker/Podman.",
    },
    {
        "component_id": "hermes",
        "display_name": "Hermes",
        "commands": ["hermes"],
        "paths": ["~/.hermes", "~/hermes"],
        "uninstall_flag": "--hermes",
        "group": "harness",
        "notes": "Harness opcional. No es selector de modelo RC4.",
    },
    {
        "component_id": "omh",
        "display_name": "Oh My Hermes (OMH)",
        "commands": ["omh"],
        "paths": ["~/.omh"],
        "uninstall_flag": "--omh",
        "group": "harness",
        "notes": "Ops sobre Hermes. Opcional. No selecciona modelos en RC4.",
    },
    {
        "component_id": "ollama",
        "display_name": "Ollama (runtime)",
        "commands": ["ollama"],
        "paths": ["~/.ollama"],
        "uninstall_flag": None,
        "group": "runtime",
        "notes": "Motor de inferencia. LEONES no desinstala el runtime por defecto.",
    },
    {
        "component_id": "llms",
        "display_name": "LLMs locales (Ollama models)",
        "commands": ["ollama"],
        "paths": [],
        "uninstall_flag": "--llms",
        "group": "models",
        "notes": "Modelos listados por ollama list. No toca otros runtimes.",
        "special": "ollama_models",
    },
    {
        "component_id": "leones",
        "display_name": "LEONES (estado local .leones/)",
        "commands": [],
        "paths": [".leones"],
        "uninstall_flag": "--leones",
        "group": "leones",
        "notes": "Último en la lista. No borra checkout ni evidencias históricas por defecto.",
        "offer_last": True,
    },
]


def _expand(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    return p


def _cmd_present(name: str) -> str | None:
    return shutil.which(name)


def _ollama_models() -> list[str]:
    if not shutil.which("ollama"):
        return []
    try:
        out = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if out.returncode != 0:
            return []
        models: list[str] = []
        for line in out.stdout.splitlines()[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except (OSError, subprocess.TimeoutExpired):
        return []


def probe_component(entry: dict[str, Any]) -> dict[str, Any]:
    installed = False
    path: str | None = None
    detected_via: str | None = None
    version: str | None = None
    extra: dict[str, Any] = {}

    for cmd in entry.get("commands") or []:
        found = _cmd_present(cmd)
        if found:
            installed = True
            path = found
            detected_via = "command"
            break

    if not installed:
        for raw in entry.get("paths") or []:
            p = _expand(raw)
            if p.exists():
                installed = True
                path = str(p)
                detected_via = "filesystem"
                break

    if entry.get("special") == "ollama_models":
        models = _ollama_models()
        extra["models"] = models
        installed = bool(models)
        detected_via = "ollama list" if models else detected_via
        if models and path is None:
            path = _cmd_present("ollama")

    if entry["component_id"] == "leones":
        p = ROOT / ".leones"
        if p.exists():
            installed = True
            path = str(p)
            detected_via = "filesystem"

    return {
        "component_id": entry["component_id"],
        "display_name": entry["display_name"],
        "group": entry["group"],
        "installed": installed,
        "path": path,
        "detected_via": detected_via,
        "version": version,
        "uninstall_flag": entry.get("uninstall_flag"),
        "uninstallable": entry.get("uninstall_flag") is not None,
        "notes": entry.get("notes", ""),
        "offer_last": bool(entry.get("offer_last")),
        **extra,
    }


def inventory() -> dict[str, Any]:
    components = [probe_component(e) for e in CATALOG]
    offers = [
        c
        for c in components
        if c["installed"] and c["uninstallable"] and not c["offer_last"]
    ]
    leones = [
        c
        for c in components
        if c["installed"] and c["uninstallable"] and c["offer_last"]
    ]
    uninstall_offers = offers + leones

    return {
        "schema": SCHEMA,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "host_root": str(ROOT),
        "components": components,
        "uninstall_offers": [
            {
                "component_id": c["component_id"],
                "display_name": c["display_name"],
                "uninstall_flag": c["uninstall_flag"],
                "command_hint": f"bash scripts/uninstall.sh {c['uninstall_flag']}",
                "opt_in_required": True,
                "independent": True,
            }
            for c in uninstall_offers
        ],
        "rules": {
            "independent_uninstall": True,
            "leones_offered_last": True,
            "no_implicit_all": True,
            "evidence_not_deleted_by_default": True,
            "checkout_not_deleted": True,
        },
    }


def render_ascii(inv: dict[str, Any]) -> str:
    lines = [
        "╔══════════════════════════════════════════════════════════════╗",
        "║  LEONES RC4 · INVENTARIO DE COMPONENTES                      ║",
        "╠══════════════════════════════════════════════════════════════╣",
    ]
    for c in inv["components"]:
        mark = "●" if c["installed"] else "○"
        status = "instalado" if c["installed"] else "ausente"
        name = c["display_name"][:28]
        row = f"║  {mark} {name:<28} {status:<10}"
        lines.append(row.ljust(63) + "║")
        if c.get("models"):
            m = ", ".join(c["models"][:4])
            if len(c["models"]) > 4:
                m += "…"
            sub = f"║      modelos: {m}"
            lines.append(sub[:62].ljust(63) + "║")
    lines.append("╠══════════════════════════════════════════════════════════════╣")
    lines.append("║  DESINSTALACIÓN INDEPENDIENTE (opt-in)                       ║")
    if not inv["uninstall_offers"]:
        lines.append("║  (nada instalado desinstalable en este host)                 ║")
    else:
        for i, o in enumerate(inv["uninstall_offers"], 1):
            last = " · último" if o["component_id"] == "leones" else ""
            row = f"║  [{i}] {o['display_name']}{last}"
            lines.append(row[:62].ljust(63) + "║")
            hint = f"║      {o['command_hint']}"
            lines.append(hint[:62].ljust(63) + "║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("Regla: cada componente se retira solo si el usuario lo elige.")
    lines.append("LEONES se ofrece al final. Evidencias y checkout no se borran por defecto.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true", help="emit inventory JSON")
    p.add_argument(
        "--apply",
        nargs="*",
        metavar="COMPONENT_ID",
        help="invoke scripts/uninstall.sh for these ids (opt-in destructive)",
    )
    p.add_argument("--dry-run", action="store_true", help="pass --dry-run to uninstall.sh")
    p.add_argument("--yes", action="store_true", help="pass --yes to uninstall.sh")
    args = p.parse_args(argv)

    inv = inventory()

    if args.apply is not None and len(args.apply) > 0:
        id_to_flag = {
            c["component_id"]: c["uninstall_flag"]
            for c in inv["components"]
            if c.get("uninstall_flag")
        }
        selected = list(dict.fromkeys(args.apply))
        if "leones" in selected:
            selected = [x for x in selected if x != "leones"] + ["leones"]
        cmd = ["bash", str(ROOT / "scripts" / "uninstall.sh")]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.yes:
            cmd.append("--yes")
        unknown = []
        for cid in selected:
            flag = id_to_flag.get(cid)
            if not flag:
                unknown.append(cid)
            else:
                cmd.append(flag)
        if unknown:
            print(f"RC4 INVENTORY: unknown or non-uninstallable: {unknown}", file=sys.stderr)
            return 2
        if len(cmd) <= 2:
            print("RC4 INVENTORY: nothing to uninstall", file=sys.stderr)
            return 2
        print("RC4 INVENTORY: invoking →", " ".join(cmd))
        return subprocess.run(cmd, cwd=ROOT, check=False).returncode

    if args.json:
        print(json.dumps(inv, ensure_ascii=False, indent=2))
    else:
        print(render_ascii(inv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
