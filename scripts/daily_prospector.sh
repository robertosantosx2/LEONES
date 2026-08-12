#!/bin/sh
# LEONES Prospector — daily discovery entry point.
# One job only: discover configured external sources.
# It never validates findings or updates Leones Atlas.
set -eu
python -m leones.prospector --sources config/prospector_sources.txt --output data/prospector/discoveries.jsonl
