#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel)"
DEST="$ROOT/third_party/kinetic"
URL="https://github.com/Veloresearch/kinetic.git"
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

if [[ -e "$DEST/.git" ]]; then
  echo "ERROR: destination contains a Git repository; refusing to overwrite: $DEST" >&2
  exit 2
fi
if [[ -d "$DEST" ]] && find "$DEST" -mindepth 1 -maxdepth 1 ! -name UPSTREAM.md -print -quit | grep -q .; then
  echo "ERROR: destination is not empty; inspect it before importing: $DEST" >&2
  exit 2
fi

git clone --filter=blob:none "$URL" "$TMP/kinetic"
COMMIT="$(git -C "$TMP/kinetic" rev-parse HEAD)"
mkdir -p "$DEST"
rsync -a --delete --exclude='.git' --exclude='UPSTREAM.md' "$TMP/kinetic/" "$DEST/"
printf '%s\n' "$COMMIT" > "$DEST/UPSTREAM_COMMIT"
cat > "$DEST/LEONES_IMPORT.md" <<EOF
# LEONES vendored source notice

Copied from $URL
Upstream commit: $COMMIT
Imported at (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)

The upstream source and notices are retained. See LICENSE, NOTICE (if present),
TRADEMARKS.md and the upstream documentation for applicable terms.
LEONES benchmark adapters and reports are maintained outside this directory.
EOF

echo "Imported Kinetic at $COMMIT into $DEST"
echo "Review the diff and commit the vendored source separately."
