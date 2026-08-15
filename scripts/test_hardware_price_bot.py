#!/usr/bin/env python3
"""Offline regression tests for the LEONES price collector."""
import sys
from pathlib import Path

# Allow execution both as `python scripts/test_hardware_price_bot.py`
# and as an imported module from the repository root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.collect_hardware_prices import extract_products, classify, parse_price


def main():
    assert parse_price('372,77 €') == 372.77
    assert parse_price('372.77 €') == 372.77
    assert parse_price('372 ^{77} €') == 372.77
    html='''<html><body>
    <article>Intel Core i5-14400F 187,00 €</article>
    <article>AMD Ryzen 5 9600X 184,90 €</article>
    <article>Corsair Vengeance DDR5 32 GB 431,95 €</article>
    <article>ASUS GeForce RTX 5070 12GB 689,95 €</article>
    </body></html>'''
    products=extract_products(html)
    names=[x[0] for x in products]
    assert any('i5' in n.lower() for n in names)
    assert any('ryzen 5' in n.lower() for n in names)
    assert any('ddr5' in n.lower() for n in names)
    assert any('rtx 5070' in n.lower() for n in names)
    assert classify('Intel Core i5-14400F')[0]=='cpu'
    assert classify('AMD Ryzen 7 9800X3D')[1]=='amd'
    assert classify('Corsair DDR4 32 GB')[0]=='ram'
    assert classify('ASUS GeForce RTX 5090 32GB')[1]=='nvidia'
    print('OK: hardware price collector regression tests passed')


if __name__=='__main__': main()
