#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${SCRIPT_DIR}/nepenthes.py"
BIN_DIR="${NEPENTHES_BIN_DIR:-${HOME}/.local/bin}"
DATA_DIR="${NEPENTHES_DATA_DIR:-${HOME}/.local/share/nepenthes}"
IMPORTER_SOURCE="${SCRIPT_DIR}/nepenthes_nsys_import.py"
MIGRATION_SOURCE="${SCRIPT_DIR}/../db/migrations/002_nepenthes_observability.sql"
MIGRATION_003_SOURCE="${SCRIPT_DIR}/../db/migrations/003_nepenthes_nsys_only.sql"
MIGRATION_006_SOURCE="${SCRIPT_DIR}/../db/migrations/006_nepenthes_typed_event_metadata.sql"
usage(){ echo "Usage: $0 [--uninstall] [--bin-dir PATH]"; }
while (($#)); do
  case "$1" in
    --uninstall) rm -f -- "${BIN_DIR}/nepenthes" "${DATA_DIR}/scripts/nepenthes_nsys_import.py" "${DATA_DIR}/db/migrations/002_nepenthes_observability.sql" "${DATA_DIR}/db/migrations/003_nepenthes_nsys_only.sql" "${DATA_DIR}/db/migrations/006_nepenthes_typed_event_metadata.sql"; echo "Removed NEPENTHES CLI and importer components"; exit 0 ;;
    --bin-dir) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; BIN_DIR="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ -f "$SOURCE" ]] || { echo "Missing CLI source: $SOURCE" >&2; exit 1; }
command -v python3 >/dev/null || { echo "Python 3 is required" >&2; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3,10)' || { echo "Python 3.10+ required" >&2; exit 1; }
mkdir -p "$BIN_DIR" "$DATA_DIR"
install -m 0755 "$SOURCE" "${BIN_DIR}/nepenthes"
if [[ -f "$IMPORTER_SOURCE" && -f "$MIGRATION_SOURCE" && -f "$MIGRATION_003_SOURCE" ]]; then
  mkdir -p "${DATA_DIR}/scripts" "${DATA_DIR}/db/migrations"
  install -m 0644 "$IMPORTER_SOURCE" "${DATA_DIR}/scripts/nepenthes_nsys_import.py"
  install -m 0644 "$MIGRATION_SOURCE" "${DATA_DIR}/db/migrations/002_nepenthes_observability.sql"
  install -m 0644 "$MIGRATION_003_SOURCE" "${DATA_DIR}/db/migrations/003_nepenthes_nsys_only.sql"
  install -m 0644 "$MIGRATION_006_SOURCE" "${DATA_DIR}/db/migrations/006_nepenthes_typed_event_metadata.sql"
else
  echo "Warning: Nsight importer/migration not found; baseline capture remains available." >&2
fi
"${BIN_DIR}/nepenthes" --version
echo "Installed: ${BIN_DIR}/nepenthes"
case ":${PATH}:" in *":${BIN_DIR}:"*) ;; *) echo "Add to PATH: export PATH=\"${BIN_DIR}:\$PATH\"" ;; esac
echo "Run: nepenthes doctor"
