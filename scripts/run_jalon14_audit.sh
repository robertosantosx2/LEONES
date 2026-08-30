#!/usr/bin/env bash
set -euo pipefail

# JALÓN 14 sólo comprueba el puente hacia la ejecución física canónica.
# No ejecuta el benchmark: esa parte pertenece a la máquina física del usuario.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/jalon14_audit.py
pytest -q tests/test_jalon14_physical_handoff.py
python3 -m compileall -q scripts/jalon14_audit.py

git diff --check
