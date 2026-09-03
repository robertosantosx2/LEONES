#!/usr/bin/env bash
set -u

# Canonical RC2 interactive entrypoint.
# The wizard completes its normal lifecycle first; cleanup is then offered as
# an optional, independent lifecycle action. Cleanup can always be invoked
# directly with: bash scripts/uninstall.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/rc2_wizard.py "$@"
RC=$?

# Do not clean up after a blocked/failed wizard state. The user can invoke the
# standalone cleanup explicitly when desired.
if [ "$RC" -eq 0 ]; then
  printf '\n'
  printf '%s\n' '============================================================'
  printf '%s\n' 'LEONES RC2 — FIN DEL FLUJO / LIMPIEZA OPCIONAL'
  printf '%s\n' '============================================================'
  python3 scripts/rc2_cleanup.py
  CLEANUP_RC=$?
  if [ "$CLEANUP_RC" -ne 0 ]; then
    printf '[!] La limpieza terminó con código %s. La ejecución RC2 sigue siendo válida.\n' "$CLEANUP_RC"
  fi
fi

exit "$RC"
