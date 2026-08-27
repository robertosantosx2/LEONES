#!/usr/bin/env python3
"""Comprueba la regla obligatoria de concurrencia de LEONES.

Un workflow que escribe en el repositorio no puede competir con otro workflow
escritor. Este comprobador es deliberadamente sencillo: busca todos los YAML
de ``.github/workflows`` y exige el grupo común en los workflows que declaran
permisos de escritura del contenido.

La intención es que una futura incorporación no pueda olvidar la regla por
simple descuido.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
REQUIRED_GROUP = "leones-main-writers"


def main() -> int:
    """Devuelve código 1 si algún workflow escritor incumple la norma."""
    errors: list[str] = []
    files = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))

    for path in files:
        text = path.read_text(encoding="utf-8")
        writes = "contents: write" in text or "git push" in text
        if not writes:
            continue
        if "concurrency:" not in text:
            errors.append(f"{path}: falta concurrency")
            continue
        if f"group: {REQUIRED_GROUP}" not in text:
            errors.append(f"{path}: grupo de concurrencia incorrecto")
        if "cancel-in-progress: false" not in text:
            errors.append(f"{path}: cancel-in-progress debe ser false")

    if errors:
        print("WORKFLOW CONCURRENCY CHECK: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"WORKFLOW CONCURRENCY CHECK: OK ({len(files)} workflows revisados)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
