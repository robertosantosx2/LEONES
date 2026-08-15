#!/usr/bin/env python3
"""Offline tests for Atlas <- hardware-price integration."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.atlas_recommend_from_feed import hardware_price_evidence, norm


def main():
    assert norm('RTX 5070 Ti') == 'rtx 5070 ti'
    prices=[
        {'component_type':'cpu','vendor':'intel','category':'Core i5','model':'Intel Core i5-14400F','capacity_gb':'','vram_gb':'','price_eur':'190','source':'PcComponentes'},
        {'component_type':'ram','vendor':'memory','category':'DDR5','model':'DDR5 16GB','capacity_gb':'16','vram_gb':'','price_eur':'55','source':'Coolmod'},
        {'component_type':'gpu','vendor':'nvidia','category':'RTX 5070','model':'RTX 5070 12GB','capacity_gb':'','vram_gb':'12','price_eur':'649','source':'LDLC España'},
    ]
    cpu,cs,ram,rs,gpu,gs,total,cov=hardware_price_evidence('cpu-i5-ddr5-16gb-rtx5070',16,12,prices)
    assert cpu==190 and cs=='PcComponentes'
    assert ram==55 and rs=='Coolmod'
    assert gpu==649 and gs=='LDLC España'
    assert total==894 and cov=='3/3'
    cpu,cs,ram,rs,gpu,gs,total,cov=hardware_price_evidence('cpu-i5-16gb',16,0,prices)
    assert cpu==190 and ram is None and gpu is None and cov=='1/3'
    print('OK: Atlas hardware price integration tests passed')


if __name__=='__main__':
    main()
