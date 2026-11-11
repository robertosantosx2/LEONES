#!/usr/bin/env python3
"""Aggregate `ncu --csv --page raw` DRAM metrics per kernel (M2-T5, issue #30).

Usage: python3 -I tools/ncu_summary.py <raw.csv> [--tokens N] [--peak 898.0]

Input: the CSV produced by `tools/ncu_gemv.sh` (one row per kernel launch and metric). Output: one line per
kernel family with launches, DRAM bytes read, summed kernel time, achieved GB/s and the mean
`dram__throughput.avg.pct_of_peak_sustained_elapsed`; then the total against the analytic per-token byte budget of
issue #30 (1.7313 GB, dense 81 % / routed experts 19 %).

Missing metrics are reported, never invented: on Volta/driver 580 a counter may not be collected, in which case the
summary falls back to whatever bytes/time columns are present (and says so).
"""

import argparse
import csv
import sys

PEAK_GBS = 898.0  # V100-SXM2-32GB: 2 x 877 MHz x 4096 bit / 8
BUDGET_GB = 1.7313  # per decode token, issue #30
BUDGET_DENSE = 0.81
BUDGET_MOE = 0.19

# ncu's metric units for time, scaled to seconds, and for bytes, scaled to bytes.
TIME_UNITS = {"ns": 1e-9, "nsecond": 1e-9, "us": 1e-6, "usec": 1e-6, "microsecond": 1e-6,
              "ms": 1e-3, "msecond": 1e-3, "millisecond": 1e-3, "s": 1.0, "second": 1.0}
BYTE_UNITS = {"byte": 1.0, "bytes": 1.0, "Kbyte": 1e3, "KB": 1e3, "Mbyte": 1e6, "MB": 1e6,
              "Gbyte": 1e9, "GB": 1e9}


def load(path):
    """The first CSV table with both a kernel and a metric column (ncu prints a preamble before it)."""
    with open(path, newline="") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if "Kernel Name" in line and "Metric Name" in line:
            return list(csv.DictReader(lines[i:]))
    raise SystemExit(f"{path}: no ncu CSV header with `Kernel Name` and `Metric Name` (is this --page raw?)")


def scale(value, unit, table):
    """`value` in the base unit (bytes or seconds) from ncu's unit string, or None when the unit is unknown."""
    return value * table[unit] if unit in table else None


def summarize(rows):
    """{(kernel, launch id): {read, bytes, secs, pct}} from the raw rows."""
    launches = {}
    for r in rows:
        name = (r.get("Kernel Name") or "").strip()
        metric = (r.get("Metric Name") or "").strip()
        if not name or not metric:
            continue
        try:
            value = float(r.get("Metric Value") or "nan")
        except ValueError:
            continue
        unit = (r.get("Metric Unit") or "").strip()
        rec = launches.setdefault((name, r.get("ID", "")), {"read": None, "bytes": None, "secs": None, "pct": None})
        if metric in ("dram__bytes_read.sum", "dram__bytes.sum"):
            b = scale(value, unit, BYTE_UNITS)
            if b is not None:
                key = "read" if metric == "dram__bytes_read.sum" else "bytes"
                rec[key] = (rec[key] or 0.0) + b
        elif metric == "gpu__time_duration.sum":
            t = scale(value, unit, TIME_UNITS)
            if t is not None:
                rec["secs"] = (rec["secs"] or 0.0) + t
        elif metric == "dram__throughput.avg.pct_of_peak_sustained_elapsed":
            rec["pct"] = value
    return launches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--tokens", type=int, default=1, help="decode tokens in the profiled run (bench --tg)")
    ap.add_argument("--peak", type=float, default=PEAK_GBS, help="roofline GB/s (default 898.0)")
    a = ap.parse_args()

    try:
        rows = load(a.csv)
    except FileNotFoundError:
        raise SystemExit(f"no such file: {a.csv}")
    if not rows:
        raise SystemExit("the CSV has no metric rows")
    have = {r.get("Metric Name", "") for r in rows}
    for m in ("dram__bytes_read.sum", "dram__bytes.sum", "gpu__time_duration.sum",
              "dram__throughput.avg.pct_of_peak_sustained_elapsed"):
        if m not in have:
            print(f"note: {m} was not collected (Volta/driver 580); its column stays empty", file=sys.stderr)

    per = {}  # kernel -> [launches, read bytes, dram bytes, seconds, pct * seconds, pct seconds]
    for (name, _), rec in summarize(rows).items():
        p = per.setdefault(name, [0, 0.0, 0.0, 0.0, 0.0, 0.0])
        p[0] += 1
        p[1] += rec["read"] or 0.0
        p[2] += rec["bytes"] or 0.0
        if rec["secs"]:
            p[3] += rec["secs"]
            if rec["pct"] is not None:
                p[4] += rec["pct"] * rec["secs"]
                p[5] += rec["secs"]

    print(f"{'kernel':38} {'launch':>7} {'read MiB':>10} {'time ms':>9} {'GB/s':>8} {'%peak':>6} {'%898':>6}")
    tot = [0, 0.0, 0.0, 0.0, 0.0, 0.0]
    for name, p in sorted(per.items(), key=lambda kv: -kv[1][1]):
        launches, read, _bytes, secs, pct_s, pct_t = p
        gbs = read / secs / 1e9 if secs else 0.0
        pct = pct_s / pct_t if pct_t else 0.0
        print(f"{name[:38]:38} {launches:>7} {read / 2**20:>10.1f} {secs * 1e3:>9.2f} {gbs:>8.1f} {pct:>6.1f} "
              f"{100.0 * gbs / a.peak:>6.1f}")
        for i, v in enumerate(p):
            tot[i] += v
    launches, read, _bytes, secs, pct_s, pct_t = tot
    gbs = read / secs / 1e9 if secs else 0.0
    print(f"{'TOTAL':38} {launches:>7} {read / 2**20:>10.1f} {secs * 1e3:>9.2f} {gbs:>8.1f} "
          f"{(pct_s / pct_t if pct_t else 0.0):>6.1f} {100.0 * gbs / a.peak:>6.1f}")

    # Cross-check against the analytic budget. The profiled run also executes prefill, so the comparison is only
    # exact for a decode-only profile; when it is not, the ratio is an upper bound and the note says so.
    per_tok = read / max(a.tokens, 1) / 1e9
    print(f"\ndram bytes read / token: {per_tok:.3} GB (ncu) vs {BUDGET_GB:.3} GB analytic "
          f"(dense {BUDGET_DENSE:.0%}, routed experts {BUDGET_MOE:.0%}); ratio {per_tok / BUDGET_GB:.2f}x")
    print(f"analytic roofline at {a.peak:.1f} GB/s: {a.peak / BUDGET_GB:.1f} tok/s; 85 % = "
          f"{0.85 * a.peak / BUDGET_GB:.1f} tok/s")
    if per_tok > 1.05 * BUDGET_GB:
        print("note: the profile includes prefill launches of the same kernels; divide by the decode-only launch "
              "count or bound the run with --launch-skip for a strict per-token check")


if __name__ == "__main__":
    main()
