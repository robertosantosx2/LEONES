#!/usr/bin/env python3
"""Compare llama-debug dumps (last full pass) with ds_run STRATA_DS_TRACE lines.
usage: cmp_trace.py llama_dump.txt mine.err
llama prints 3 values at each end of every row; we compare the first row's first 3 values (token 0)
and the last row's last 3 values (last token) against our per-token traces."""
import re, sys
VAL = re.compile(r"^\s+\[\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+),\s+\.\.\.,\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\],?$")
ll, name = {}, None
for line in open(sys.argv[1], errors="replace"):
    m = re.match(r"common_debug_cb_eval:\s+(\S+) = ", line)
    if m:
        name = m.group(1)
        if name == "hc_init":
            ll = {}
        ll[name] = [None, None]
        continue
    m = VAL.match(line)
    if m and name:
        v = [float(x) for x in m.groups()]
        if ll[name][0] is None:
            ll[name][0] = v[:3]
        ll[name][1] = v[3:]
mine, order = {}, []
for line in open(sys.argv[2], errors="replace"):
    m = re.match(r"TRACE (\S+) \[\s*(\S+)\s+(\S+)\s+(\S+) \.\.\.\s+(\S+)\s+(\S+)\s+(\S+)\] sum", line)
    if m:
        n = m.group(1).replace("--1", "")
        v = [float(x) for x in m.groups()[1:]]
        if n not in mine:
            order.append(n)
            mine[n] = [v[:3], v[3:]]
        else:
            mine[n][1] = v[3:]
def err(a, b):
    return max(abs(x - y) / (abs(x) + 1e-3) for x, y in zip(a, b))
for n in order:
    a, b = ll.get(n), mine[n]
    if not a or a[0] is None:
        continue
    print(f"{n:22s} first3 relerr={err(a[0], b[0]):.1e}  last3 relerr={err(a[1], b[1]):.1e}")
