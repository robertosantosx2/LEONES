#!/bin/sh
# Weekly discovery hook for external, unvalidated estimates.
# Deliberately does not write Atlas or Router data.
# A human/research agent supplies reviewed source rows to estimate_sources.py.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

python -m leones.estimate_sources --help
printf '%s\n' "Weekly feed ready: add sourced rows to web/data/external_estimates.csv"
printf '%s\n' "STATUS MUST remain: external-unvalidated"
