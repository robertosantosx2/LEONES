#!/usr/bin/env python3
"""Optional RC2 end-of-flow cleanup, reusable independently of the wizard."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
UNINSTALL = REPO_ROOT / "scripts" / "uninstall.sh"

OPTIONS = {
    "1": "--leones",
    "2": "--ods",
    "3": "--magnitude",
    "4": "--llms",
}


def run_cleanup(input_fn=input, output_fn=print) -> int:
    output_fn("")
    output_fn("═" * 60)
    output_fn("LEONES — LIMPIEZA / DESINSTALACIÓN")
    output_fn("═" * 60)
    output_fn("Puedes conservar la instalación o seleccionar uno o varios componentes.")
    output_fn("Esta misma operación también puede ejecutarse fuera del wizard:")
    output_fn("  $ bash scripts/uninstall.sh")
    output_fn("")
    output_fn("  [1] LEONES       — estado local generado por LEONES")
    output_fn("  [2] ODS          — recursos ODS")
    output_fn("  [3] Magnitude    — @magnitudedev/cli")
    output_fn("  [4] LLM cargados — modelos locales de Ollama")
    output_fn("  [5] TODO         — 1 + 2 + 3 + 4")
    output_fn("  [6] Conservar y finalizar")
    output_fn("  [7] Salir")

    while True:
        choice = input_fn("LEONES> ").strip()
        if choice in {"6", "7"}:
            output_fn("[i] No se ha solicitado ninguna limpieza.")
            return 0
        if choice == "5":
            args = ["--all"]
            break
        parts = [p.strip() for p in choice.split(",") if p.strip()]
        if parts and all(p in OPTIONS for p in parts):
            args = []
            for p in parts:
                if OPTIONS[p] not in args:
                    args.append(OPTIONS[p])
            break
        output_fn("[!] Opción no válida. Usa 1,2,3,4,5,6 o 7.")

    output_fn("[i] Siguiente: se ejecutará la limpieza seleccionada y solo esos componentes.")
    return subprocess.run(["bash", str(UNINSTALL), *args], cwd=str(REPO_ROOT), check=False).returncode


def main() -> int:
    return run_cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
