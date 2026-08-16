#!/usr/bin/env python3
"""Adaptador mínimo para llama.cpp.

El adaptador no instala ni descarga nada y tampoco inventa una medición. Su
responsabilidad es construir el comando de inferencia que después ejecutará
``run_and_record_benchmark.py``. La expresión regular acepta las formas más
habituales de salida que contienen una cifra seguida de ``tok/s``.

Así cada runtime puede tener su propio adaptador, mientras que la validación y
el almacenamiento de la medición siguen siendo comunes para todo LEONES.
"""
from __future__ import annotations

import re

TOKENS_PER_SECOND_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*tok/s", re.IGNORECASE)


def build_command(executable: str, model_path: str, prompt: str) -> list[str]:
    """Construye un comando seguro para una ejecución de llama.cpp.

    Se devuelven argumentos separados en una lista; el runner los ejecuta sin
    shell. El adaptador no afirma que el comando se haya ejecutado con éxito.
    """
    return [executable, "-m", model_path, "-p", prompt]


def tokens_per_second_pattern() -> str:
    """Devuelve el patrón que el runner usará para extraer tok/s."""
    return TOKENS_PER_SECOND_PATTERN.pattern
