#!/usr/bin/env bash
set -euo pipefail

# Default to the newest published stable CLI. Set MAGNITUDE_CLI_VERSION to
# install a reproducible version explicitly, e.g. 0.2.9.
MAGNITUDE_CLI_VERSION="${MAGNITUDE_CLI_VERSION:-latest}"

python3 scripts/integrations/magnitude_preflight.py
printf '\nThis will install @magnitudedev/cli@%s globally with npm. Continue? [y/N] ' "$MAGNITUDE_CLI_VERSION"
read -r answer
[[ "$answer" =~ ^[Yy]$ ]] || { echo "Installation cancelled."; exit 0; }

npm install -g "@magnitudedev/cli@${MAGNITUDE_CLI_VERSION}"
printf '\nInstalled Magnitude CLI version: '
magnitude --version
