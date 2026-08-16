"""Pruebas del paso de normalización CABE/RULA."""

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "normalize_cabe_rula_measurement.py"
spec = importlib.util.spec_from_file_location("normalize_cabe_rula_measurement", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


normalize = module.normalize_measurement


def test_numeric_string_is_normalized():
    assert normalize("7.5") == 7.5


def test_integer_is_normalized():
    assert normalize(10) == 10.0


def test_negative_is_rejected():
    try:
        normalize(-0.1)
    except ValueError:
        return
    raise AssertionError("Los valores negativos deben rechazarse")


def test_nan_is_rejected():
    try:
        normalize("nan")
    except ValueError:
        return
    raise AssertionError("NaN debe rechazarse")


def test_infinity_is_rejected():
    try:
        normalize("inf")
    except ValueError:
        return
    raise AssertionError("Infinito debe rechazarse")
