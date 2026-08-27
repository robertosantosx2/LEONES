#!/usr/bin/env python3
"""Revisa la legibilidad básica de los scripts propios de LEONES.

Solo analiza Python que se comporta como script ejecutable. No modifica
archivos ni toca código de terceros.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "scripts"
MAX_LINE_LENGTH = 100


def python_files(directory: Path) -> list[Path]:
    """Devuelve scripts propios y omite cachés y código importado."""
    return sorted(
        path
        for path in directory.rglob("*.py")
        if "__pycache__" not in path.parts
        and ".git" not in path.parts
        and "upstream" not in path.parts
    )


def is_executable_script(lines: list[str]) -> bool:
    """Indica si el archivo contiene el punto de entrada de un script."""
    return any("if __name__ ==" in line and "__main__" in line for line in lines)


def has_initial_docstring(lines: list[str]) -> bool:
    """Comprueba el docstring del módulo sin confundir comentarios con código."""
    try:
        tree = ast.parse("\n".join(lines))
    except SyntaxError:
        return False
    return bool(ast.get_docstring(tree))


def check_file(path: Path) -> list[str]:
    """Devuelve avisos sencillos para un script ejecutable."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not is_executable_script(lines):
        return []

    problems: list[str] = []
    if not lines or not lines[0].startswith("#!"):
        problems.append("falta el encabezado ejecutable (shebang)")

    if not has_initial_docstring(lines):
        problems.append("falta un docstring inicial que explique el propósito")

    for number, line in enumerate(lines, start=1):
        if len(line) > MAX_LINE_LENGTH:
            problems.append(f"línea {number}: supera {MAX_LINE_LENGTH} caracteres")
        if ";" in line and not line.lstrip().startswith("#"):
            problems.append(f"línea {number}: varias instrucciones en una línea")

    return problems


def main() -> int:
    """Audita scripts y devuelve error solo con ``--strict`` si hay avisos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=DEFAULT_DIR)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="termina con error si encuentra incumplimientos",
    )
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
        return 1 if args.strict else 0

    print("OK: todos los scripts cumplen las comprobaciones básicas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
