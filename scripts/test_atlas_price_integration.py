#!/usr/bin/env python3
"""Offline tests for Atlas <- hardware-price integration."""
import csv
import tempfile
from pathlib import Path

from scripts.atlas_recommend_from_feed import match_price, norm, price_key


def main():
    assert norm('RTX 5070 Ti') == 'rtx 5070 ti'
    assert price_key('NVIDIA GeForce RTX 5070 12GB') == 'rtx 5070 12gb'
    prices=[
        {'model':'ASUS GeForce RTX 5070 12GB','price_eur':'649','source':'Coolmod','observed_at':'2026-08-15'},
        {'model':'AMD Ryzen 5 9600X','price_eur':'189','source':'LDLC España','observed_at':'2026-08-15'},
    ]
    p=match_price('RTX 5070 12GB', prices)
    assert p and p['source']=='Coolmod' and p['price_eur']=='649'
    p=match_price('Ryzen 5 9600X', prices)
    assert p and p['source']=='LDLC España'
    assert match_price('modelo inexistente', prices) is None
    print('OK: Atlas hardware price integration tests passed')


if __name__ == '__main__':
    main()
