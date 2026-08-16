"""Pruebas del contrato oficial CABE/RULA.

Las fronteras son especialmente importantes: un cambio accidental de < a <=
puede clasificar de forma distinta todos los modelos que estén justo en el
límite. Por eso probamos explícitamente 1, 10 y 100 tok/s.

También probamos valores imposibles. Una medición infinita no significa que el
modelo sea extraordinariamente rápido: significa que el dato está roto y debe
rechazarse antes de llegar al recomendador o al Atlas.
"""

import importlib.util
import math
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "classify_cabe_rula.py"
spec = importlib.util.spec_from_file_location("classify_cabe_rula", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


classify = module.classify_tokens_per_second


def test_below_cabe():
    assert classify(0.99) == "NO_CABE"


def test_lower_cabe_boundary():
    assert classify(1) == "CABE"


def test_inside_cabe():
    assert classify(9.99) == "CABE"


def test_rula_boundary():
    assert classify(10) == "RULA"


def test_inside_rula():
    assert classify(100) == "RULA"


def test_above_rula():
    assert classify(100.01) == "RULA+"


def test_negative_is_invalid():
    try:
        classify(-1)
    except ValueError:
        return
    raise AssertionError("Una velocidad negativa debe rechazarse")


def test_nan_is_invalid():
    try:
        classify(math.nan)
    except ValueError:
        return
    raise AssertionError("NaN debe rechazarse")


def test_infinity_is_invalid():
    try:
        classify(math.inf)
    except ValueError:
        return
    raise AssertionError("infinito debe rechazarse")
