#!/usr/bin/env python3
"""Classify an observed tokens/second value using the canonical H09 rules."""

from __future__ import annotations

from typing import Optional


def classify_tokens_per_second(tokens_per_second: Optional[float]) -> Optional[str]:
    """Return the H09 class, preserving missing measurements as unknown."""
    if tokens_per_second is None:
        return None
    value = float(tokens_per_second)
    if value < 1:
        return "No CABE"
    if value < 10:
        return "CABE"
    if value <= 100:
        return "RULA"
    return "RULA+"


def normalize_tokens_per_second(value: object) -> Optional[float]:
    """Normalize a numeric tok/s value without inventing missing measurements."""
    if value is None or value == "":
        return None
    result = float(value)
    if result < 0:
        raise ValueError("tokens_per_second cannot be negative")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Classify LEONES tok/s")
    parser.add_argument("tokens_per_second", type=float)
    args = parser.parse_args()
    value = normalize_tokens_per_second(args.tokens_per_second)
    print(classify_tokens_per_second(value))
