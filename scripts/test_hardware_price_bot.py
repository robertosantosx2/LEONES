#!/usr/bin/env python3
"""Offline regression tests for the LEONES price collector."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.collect_hardware_prices import extract_products, classify, parse_price


def main():
    assert parse_price("372,77 €") == 372.77
    assert parse_price("372.77 €") == 372.77
    assert parse_price("372 ^{77} €") == 372.77

    # Product cards represented as separate title/specification and price lines.
    html = """<html><body>
    <article>
      Intel Core i5-14400F
      187,00 €
    </article>
    <article>
      AMD Ryzen 5 9600X
      184,90 €
    </article>
    <article>
      Corsair Vengeance DDR5 32 GB
      431,95 €
    </article>
    <article>
      ASUS GeForce RTX 5070 12GB
      689,95 €
    </article>
    </body></html>"""
    products = extract_products(html)
    names = [x[0] for x in products]
    print("EXTRACTION TEST PRODUCTS:", names)
    assert any("i5" in n.lower() for n in names)
    assert any("ryzen 5" in n.lower() for n in names)
    assert any("ddr5" in n.lower() for n in names)
    assert any("rtx 5070" in n.lower() for n in names)

    # Marketplace-style card: title, specs and price are separated by lines.
    mediamarkt = """
    Memoria RAM - CORSAIR Vengeance LPX CMK16GX4M2E3200C16 módulo de memoria
    Tipo de dispositivo
    Memoria RAM
    Tipo de RAM
    DDR4
    Tamaño de la memoria RAM
    16 GB
    Compatibilidad
    PC/servidor
    187,18 €
    """
    mm = extract_products(mediamarkt)
    assert mm, "MediaMarkt-style product card was not extracted"
    mm_context = " | ".join(x[3] for x in mm)
    assert classify(mm[0][0] + " | " + mm_context)[0] == "ram"
    assert classify(mm[0][0] + " | " + mm_context)[3] == "16"

    # DDR capacity may precede the DDR generation.
    assert classify("Kingston 32 GB DDR5 6000")[0] == "ram"
    assert classify("Corsair 16 GB DDR4 3200")[3] == "16"

    assert classify("Intel Core i5-14400F")[0] == "cpu"
    assert classify("AMD Ryzen 7 9800X3D")[1] == "amd"
    assert classify("Corsair DDR4 32 GB")[0] == "ram"
    assert classify("ASUS GeForce RTX 5090 32GB")[1] == "nvidia"
    print("OK: hardware price collector regression tests passed")


if __name__ == "__main__":
    main()
