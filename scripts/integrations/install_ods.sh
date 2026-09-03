#!/usr/bin/env bash
set -euo pipefail

# LEONES wrapper: preflight first, then explicit consent, then invoke the
# upstream ODS installer. No telemetry or Atlas upload is performed here.
#
# Container policy:
#   * Docker rootful is valid; it must not be misclassified as rootless.
#   * Docker via sudo is valid for the current installer session.
#   * Podman is detected by preflight. ODS itself currently requires a
#     Docker-compatible CLI/Compose contract, so Podman-only hosts are stopped
#     with an actionable message instead of silently installing Docker.

PREFLIGHT_JSON="$(python3 scripts/integrations/ods_preflight.py)"
printf '%s\n' "$PREFLIGHT_JSON"

if ! python3 -c 'import json,sys; p=json.load(sys.stdin); raise SystemExit(0 if p["ready"] else 1)' <<<"$PREFLIGHT_JSON"; then
  echo ""
  echo "[ERROR] ODS requires a working Docker + Compose interface."
  echo "[INFO] Podman is supported as a detected host runtime, but ODS's current Linux installer is Docker/Compose based."
  echo "[INFO] On Fedora/RHEL-family systems, install/configure a Docker-compatible interface before retrying; LEONES will not silently replace Podman."
  exit 2
fi

printf '\nThis will install ODS and may download Docker images/models. Continue? [y/N] '
read -r answer
[[ "$answer" =~ ^[Yy]$ ]] || { echo "Installation cancelled."; exit 3; }

# ODS's rootless-ownership helper historically failed when its internal bare
# `docker info` could not reach a rootful daemon that LEONES had correctly
# discovered through `sudo docker`. Explicitly tell ODS the already-observed
# state so it does not guess. This is safe because it is only set for a known
# rootful Docker daemon; rootless Docker remains auto-detected by ODS.
RUNTIME_JSON="$PREFLIGHT_JSON" python3 - <<'PY' > /tmp/leones-ods-runtime.env
import json, os
p = json.loads(os.environ["RUNTIME_JSON"])["container_runtime"]
if p.get("runtime") == "docker" and p.get("rootless") is False:
    print("export ODS_ASSUME_ROOTLESS=0")
if p.get("runtime") == "docker" and p.get("access") == "sudo":
    print('export DOCKER_CMD="sudo docker"')
    print('export DOCKER_COMPOSE_CMD="sudo docker compose"')
PY
# shellcheck disable=SC1091
source /tmp/leones-ods-runtime.env
rm -f /tmp/leones-ods-runtime.env

: "${ODS_REF:=main}"
if [[ "$ODS_REF" == "main" ]]; then
  echo "WARNING: ODS_REF=main is not reproducible. Set ODS_REF to a release/tag/commit for a pinned install."
fi

if [[ "$ODS_REF" == "main" ]]; then
  curl -fsSL https://install.osmantic.com/ods.sh | bash
else
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT
  git clone --depth 1 --branch "$ODS_REF" https://github.com/Osmantic/ODS.git "$tmpdir/ODS"
  (cd "$tmpdir/ODS/ods" && ./install.sh)
fi
