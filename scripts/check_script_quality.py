#!/usr/bin/env python3
"""Comprueba reglas sencillas de legibilidad para los scripts de LEONES.

No modifica archivos. Solo detecta problemas fáciles de corregir antes de aceptar
un script nuevo o modificado.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "scripts"
MAX_LINE_LENGTH = 100


def python_files(directory: Path) -> list[Path]:
    """Devuelve los scripts Python, sin revisar cachés ni submódulos vendorizados."""
    return sorted(
        path
        for path in directory.rglob("*.py")
        if "__pycache__" not in path.parts
        and ".git" not in path.parts
        and "upstream" not in path.parts
    )


def check_file(path: Path) -> list[str]:
    """Devuelve avisos comprensibles para un único script."""
    lines = path.read_text(encoding="utf-8").splitlines()
    problems: list[str] = []

    if not lines or not lines[0].startswith("#!"):
        problems.append("falta el encabezado ejecutable (shebang)")

    if not any(line.strip().startswith('"""') for line in lines[:12]):
        problems.append("falta un docstring inicial que explique el propósito")

    for number, line in enumerate(lines, start=1):
        if len(line) > MAX_LINE_LENGTH:
            problems.append(f"línea {number}: supera {MAX_LINE_LENGTH} caracteres")
        if ";" in line and not line.lstrip().startswith("#"):
            problems.append(f"línea {number}: varias instrucciones en una línea")

    return problems


def main() -> int:
    """Revisa los scripts y devuelve 1 si encuentra incumplimientos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    failures = 0
    for path in python_files(args.directory):
        problems = check_file(path)
        if not problems:
            continue
        print(path.relative_to(ROOT))
        for problem in problems:
            print(f"  - {problem}")
        failures += len(problems)

    if failures:
        print(f"\n{failures} avisos de calidad de scripts.")
        return 1

    print("OK: todos los scripts cumplen las comprobaciones básicas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
