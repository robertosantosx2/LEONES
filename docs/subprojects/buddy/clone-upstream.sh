#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${ROOT}/upstream"
REPO="https://github.com/juanje/buddy.git"

if [[ -e "${DEST}/.git" ]]; then
  git -C "${DEST}" fetch --depth=1 origin main
  git -C "${DEST}" reset --hard origin/main
else
  git clone --depth=1 --branch main "${REPO}" "${DEST}"
fi

echo "Buddy upstream available at ${DEST}"
git -C "${DEST}" log -1 --oneline
