#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(git rev-parse --show-toplevel)"
exec python3 "$ROOT/scripts/vendor_engines.py" --engine kinetic "$@"
