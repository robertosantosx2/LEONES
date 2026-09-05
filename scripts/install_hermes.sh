#!/usr/bin/env bash
set -euo pipefail

# Hermes is an external runtime/agent dependency. The installer is upstream's
# canonical Linux installer; LEONES does not vendor or fork Hermes.
if command -v hermes >/dev/null 2>&1; then
  echo "LEONES: Hermes already installed: $(hermes --version 2>/dev/null || true)"
  exit 0
fi

if [[ "${LEONES_ALLOW_NETWORK_INSTALL:-0}" != "1" ]]; then
  echo "LEONES: Hermes is not installed."
  echo "For a network install, re-run with LEONES_ALLOW_NETWORK_INSTALL=1."
  echo "This executes the upstream installer documented by Nous Research."
  echo "Command: curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
  exit 2
fi

curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

if ! command -v hermes >/dev/null 2>&1; then
  echo "LEONES: Hermes installation completed but 'hermes' is not on PATH. Reload your shell." >&2
  exit 3
fi

hermes --version || true
