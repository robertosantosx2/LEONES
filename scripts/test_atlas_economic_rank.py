#!/usr/bin/env python3
"""Offline tests for the Atlas economic ranking."""
from pathlib import Path
import sys
import tempfile, csv

# Make direct execution from the repository root work consistently in CI.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.atlas_economic_rank import economic_rank

def main():
    rows=[
      {'model_id':'a','model_name':'A','hardware_id':'cpu-i5-16gb','fit_score':'0.90','jgb_level':'5','tokens_per_second':'20'},
      {'model_id':'b','model_name':'B','hardware_id':'cpu-i5-16gb','fit_score':'0.80','jgb_level':'3','tokens_per_second':'10'},
    ]
    prices=[
      {'component_type':'cpu','category':'Core i5','capacity_gb':'','price_eur':'200'},
      {'component_type':'cpu','category':'Core i5','capacity_gb':'','price_eur':'220'},
      {'component_type':'ram','category':'DDR4','capacity_gb':'16','price_eur':'40'},
      {'component_type':'ram','category':'DDR4','capacity_gb':'16','price_eur':'50'},
    ]
    ranked=economic_rank(rows,prices,'cpu-i5-16gb',16)
    assert len(ranked)==2
    assert ranked[0][0] > 0
    assert ranked[0][5] == 255
    assert ranked[0][6] == 'complete'
    empty=economic_rank(rows,prices,'cpu-i9-16gb',32)
    assert all(x[0] == -1 for x in empty)
    assert all(x[6] == 'unknown' for x in empty)
    print('OK: Atlas economic ranking tests passed')

if __name__=='__main__': main()
