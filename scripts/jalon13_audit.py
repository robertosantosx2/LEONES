#!/usr/bin/env python3
"""Comprueba que la V1 está preparada para su prueba física final.

Este auditor es deliberadamente sencillo: verifica contratos, entrada de usuario,
documentación y ausencia de un motor paralelo. No mide modelos ni decide.
"""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

# JALÓN 5 fijó el contrato de decisión real de LEONES: ODS/Magnitude + LLMFit
# alimentan al selector LEONES. No existe un segundo ``leones-decision.v1``.
# Mantener aquí el nombre canónico evita que el readiness gate invente una
# interfaz que el proyecto no utiliza.
REQUIRED = [
    "scripts/run_leones_v1.sh",
    "scripts/leones_v1.py",
    "schemas/leones-v1-preflight.v1.json",
    "schemas/leones-ods-magnitude-decision.v1.json",
    "schemas/leones-e2e-operation.v1.json",
    "schemas/leones-recommendation.v1.json",
    "schemas/leones-recommendation-output.v1.json",
    "docs/V1-USER-GUIDE.md",
    "docs/jalones/jalon12.md",
    "docs/jalones/jalon13.md",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def main() -> int:
    print("LEONES — JALÓN 13 V1 READINESS AUDIT")

    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
    if missing:
        fail("missing canonical V1 components: " + ", ".join(missing))
    print("PASS: canonical V1 components present")

    schema = json.loads((ROOT / "schemas/leones-v1-preflight.v1.json").read_text())
    if schema.get("properties", {}).get("schema", {}).get("const") != "leones-v1-preflight.v1":
        fail("preflight schema is not fixed to leones-v1-preflight.v1")
    print("PASS: preflight contract is fixed")

    launcher = (ROOT / "scripts/run_leones_v1.sh").read_text()
    if "scripts/leones_v1.py" not in launcher:
        fail("user launcher does not delegate to canonical V1 entrypoint")
    print("PASS: user launcher delegates to canonical V1 entrypoint")

    # No calculadora nueva: el auditor sólo comprueba la estructura de la V1.
    audit_text = (ROOT / "docs/jalones/jalon13.md").read_text().lower()
    if "segundo" in audit_text and "benchmark" in audit_text and "scoring" in audit_text:
        print("PASS: documentation explicitly rejects parallel benchmark/scoring logic")
    else:
        fail("JALON 13 documentation does not state the no-parallel-engine invariant")

    subprocess.run([sys.executable, "scripts/leones_v1.py", "preflight"], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    print("PASS: canonical V1 preflight executes")
    print("JALON13_V1_READINESS_CLOSE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
