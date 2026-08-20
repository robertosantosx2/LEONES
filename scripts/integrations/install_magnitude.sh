#!/usr/bin/env bash
set -euo pipefail

python3 scripts/integrations/magnitude_preflight.py
printf '\nThis will install @magnitudedev/cli globally with npm. Continue? [y/N] '
read -r answer
[[ "$answer" =~ ^[Yy]$ ]] || { echo "Installation cancelled."; exit 0; }

npm install -g @magnitudedev/cli
magnitude --version || true
