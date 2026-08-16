#!/usr/bin/env python3
"""Ejecuta un comando de inferencia y registra sus tokens por segundo.

El runner es deliberadamente genérico: LEONES no debe imponer un runtime
concreto a todos los modelos. Recibe un comando ya preparado por el adaptador
del runtime, ejecuta el proceso, recoge su salida y extrae una métrica explícita
mediante una expresión regular.

Para lectores con conocimientos básicos: el script hace tres cosas. Primero
lanza el programa que realmente ejecuta el modelo. Después busca en su salida
una cifra de tokens por segundo. Finalmente pasa esa cifra al contrato común
de ``record_measurement`` para evitar registros incompletos o mal etiquetados.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from typing import Any

from record_benchmark import record_measurement


def run_and_record(command: list[str], metadata: dict[str, Any], pattern: str) -> dict[str, Any]:
    """Ejecuta ``command`` y registra la primera métrica que coincida con ``pattern``.

    El comando debe ser proporcionado por un adaptador de runtime y no se
    ejecuta mediante un shell. Esto evita que una cadena recibida como dato
    pueda convertirse accidentalmente en varios comandos del sistema.
    """
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(pattern, output)
    if completed.returncode != 0:
        raise RuntimeError(f"benchmark command failed with exit code {completed.returncode}")
    if not match:
        raise ValueError("benchmark output does not contain a tokens-per-second measurement")

    data = dict(metadata)
    data["tokens_per_second"] = float(match.group(1))
    return record_measurement(data)


def main() -> None:
    """Expone el runner como una herramienta de línea de comandos."""
    parser = argparse.ArgumentParser(description="Ejecuta una inferencia y registra tok/s medidos")
    parser.add_argument("--pattern", required=True, help="Regex cuyo primer grupo contiene tok/s")
    parser.add_argument("--model", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--quantization", required=True)
    parser.add_argument("--context-tokens", required=True, type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Comando del adaptador de runtime")
    args = parser.parse_args()

    if not args.command:
        parser.error("a runtime command is required")

    metadata = {
        "model": args.model,
        "variant": args.variant,
        "runtime": args.runtime,
        "hardware": args.hardware,
        "workload": args.workload,
        "quantization": args.quantization,
        "context_tokens": args.context_tokens,
    }
    result = run_and_record(args.command, metadata, args.pattern)
    print(result)


if __name__ == "__main__":
    main()
