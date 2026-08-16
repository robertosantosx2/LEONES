#!/usr/bin/env python3
"""Clasifica una velocidad de inferencia según el contrato CABE/RULA de LEONES.

Este pequeño script convierte un dato continuo (tokens por segundo) en una
etiqueta fácil de usar por el resto del proyecto. Conservamos siempre el
número original: la etiqueta es una ayuda para razonar, no sustituye a la
medición.

Reglas oficiales:
    < 1 tok/s       -> NO_CABE
    1 <= tok/s < 10 -> CABE
    10 <= tok/s <= 100 -> RULA
    > 100 tok/s     -> RULA+
"""

from __future__ import annotations


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
        Si la medición no es un número finito o es negativa.
    """
    if tokens_per_second != tokens_per_second:  # NaN
        raise ValueError("tokens_per_second no puede ser NaN")
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
    """Ejemplo sencillo para comprobar el contrato desde la terminal."""
    import argparse

    parser = argparse.ArgumentParser(description="Clasifica tok/s como CABE/RULA")
    parser.add_argument("tokens_per_second", type=float)
    args = parser.parse_args()
    print(classify_tokens_per_second(args.tokens_per_second))


if __name__ == "__main__":
    main()
