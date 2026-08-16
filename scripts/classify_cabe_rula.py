#!/usr/bin/env python3
"""Clasifica una velocidad de inferencia según el contrato CABE/RULA de LEONES.

Este pequeño módulo convierte un dato continuo (tokens por segundo) en una
etiqueta que el resto del proyecto puede entender fácilmente. Conservamos
siempre el número original: la etiqueta ayuda a razonar, pero nunca sustituye
la medición.

Reglas oficiales:
    < 1 tok/s          -> NO_CABE
    1 <= tok/s < 10    -> CABE
    10 <= tok/s <= 100  -> RULA
    > 100 tok/s        -> RULA+

El clasificador es deliberadamente pequeño. La normalización de entradas
externas se realiza antes, en ``normalize_cabe_rula_measurement.py``; aun así,
este punto de entrada también protege el contrato frente a NaN e infinito.
"""

from __future__ import annotations

import math


def classify_tokens_per_second(tokens_per_second: float) -> str:
    """Devuelve la clase CABE/RULA correspondiente a una medición.

    Parameters
    ----------
    tokens_per_second:
        Velocidad observada de generación de tokens por segundo.

    Returns
    -------
    str
        Una de: ``NO_CABE``, ``CABE``, ``RULA`` o ``RULA+``.

    Raises
    ------
    ValueError
        Si la medición no es un número finito o es negativa. Una velocidad
        infinita no representa una observación física válida y no debe acabar
        convertida accidentalmente en ``RULA+``.
    """
    if not math.isfinite(tokens_per_second):
        raise ValueError("tokens_per_second debe ser finito")
    if tokens_per_second < 0:
        raise ValueError("tokens_per_second no puede ser negativo")

    if tokens_per_second < 1:
        return "NO_CABE"
    if tokens_per_second < 10:
        return "CABE"
    if tokens_per_second <= 100:
        return "RULA"
    return "RULA+"


def main() -> None:
    """Permite probar el contrato desde la terminal.

    Ejemplo: ``python scripts/classify_cabe_rula.py 7.5`` imprime ``CABE``.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Clasifica tok/s como CABE/RULA")
    parser.add_argument("tokens_per_second", type=float)
    args = parser.parse_args()
    print(classify_tokens_per_second(args.tokens_per_second))


if __name__ == "__main__":
    main()
