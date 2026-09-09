#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

fail() { echo "[✗] $1" >&2; exit 1; }
warn() { echo "[!] $1" >&2; }

usage() {
  cat <<'EOF'
LEONES RC4 component installer

Usage:
  ./install.sh --fitllm
  ./install.sh --ods
  ./install.sh --magnitude
  ./install.sh --hermes
  ./install.sh --omh
  ./install.sh --all

With no component flag, --all is NOT assumed.

If a supported AI component is already installed, LEONES checks its
current version against the latest stable upstream release and updates
it when a newer version exists.

Permanent AI software contract: when an installed component is older,
LEONES updates it when a newer version exists, then verifies that it is
operational. Future AI components must follow the same contract.
EOF
}

command -v python3 >/dev/null 2>&1 || fail "Python 3 no está instalado."
command -v curl >/dev/null 2>&1 || fail "curl no está instalado."
python3 - <<'PY' || exit 1
import sys
if sys.version_info < (3, 10):
    print("[✗] LEONES RC4 requiere Python 3.10 o superior.")
    raise SystemExit(1)
PY

extract_version() {
  grep -Eo '[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?' | head -1
}

version_lt() {
  local current="$1" latest="$2"
  [[ "$current" != "$latest" ]] && [[ "$(printf '%s\n%s\n' "$current" "$latest" | sort -V | head -1)" == "$current" ]]
}

latest_github_tag() {
  local repo="$1"
  curl -fsSL --retry 2 "https://api.github.com/repos/$repo/releases/latest" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))'
}

latest_hermes_version() {
  curl -fsSL --retry 2 https://raw.githubusercontent.com/NousResearch/hermes-agent/main/pyproject.toml \
    | python3 -c 'import re,sys; text=sys.stdin.read(); m=re.search(r"^version\s*=\s*\"([^\"]+)\"", text, re.M); print(m.group(1) if m else "")'
}

require_latest_version() {
  local component="$1" current="$2" latest="$3"
  if [[ -z "$current" ]]; then
    fail "No se pudo determinar la versión instalada de $component."
  fi
  if [[ -z "$latest" ]]; then
    fail "No se pudo consultar la última versión estable de $component."
  fi
  echo "[i] $component: instalada=$current · última=$latest"
  version_lt "$current" "$latest"
}

install_fitllm() {
  if command -v llmfit >/dev/null 2>&1; then
    local current latest
    current="$(llmfit --version 2>&1 | extract_version)"
    latest="$(latest_github_tag AlexsJones/llmfit)" || fail "No se pudo consultar la última versión de FitLLM/LLMFit."
    if require_latest_version "FitLLM / LLMFit" "$current" "$latest"; then
      echo "[→] Actualizando FitLLM / LLMFit..."
      curl -fsSL https://llmfit.axjns.dev/install.sh | sh -s -- --local
      export PATH="$HOME/.local/bin:$PATH"
    else
      echo "[✓] FitLLM / LLMFit ya está en la última versión."
    fi
  else
    echo "[→] Instalando FitLLM / LLMFit..."
    curl -fsSL https://llmfit.axjns.dev/install.sh | sh -s -- --local
    export PATH="$HOME/.local/bin:$PATH"
  fi
  command -v llmfit >/dev/null 2>&1 || fail "FitLLM / LLMFit no quedó operativo."
  llmfit --version >/dev/null 2>&1 || fail "FitLLM / LLMFit quedó instalado pero no operativo."
}

install_ods() {
  local ods_bin="${ODS_BIN:-$HOME/.local/bin/ods}"
  if command -v ods >/dev/null 2>&1; then
    local current latest
    current="$(ods --version 2>&1 | extract_version)"
    latest="$(latest_github_tag osmantic/ods)" || fail "No se pudo consultar la última versión de ODS."
    if require_latest_version "ODS" "$current" "$latest"; then
      echo "[→] Actualizando ODS..."
      curl -fsSL https://install.osmantic.com/ods.sh | bash
      export PATH="$HOME/.local/bin:$PATH"
    else
      echo "[✓] ODS ya está en la última versión."
    fi
  elif [[ -x "$HOME/ods/ods-cli" ]]; then
    mkdir -p "$(dirname "$ods_bin")"
    ln -sf "$HOME/ods/ods-cli" "$ods_bin"
    export PATH="$HOME/.local/bin:$PATH"
  else
    echo "[→] Instalando ODS..."
    curl -fsSL https://install.osmantic.com/ods.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
  fi
  command -v ods >/dev/null 2>&1 || fail "ODS no quedó operativo en PATH."
  ods --version >/dev/null 2>&1 || fail "ODS quedó instalado pero no operativo."
}

install_magnitude() {
  if command -v magnitude >/dev/null 2>&1; then
    local current latest
    current="$(magnitude --version 2>&1 | extract_version)"
    latest="$(npm view @magnitudedev/cli version 2>/dev/null)" || fail "No se pudo consultar la última versión de Magnitude."
    if require_latest_version "Magnitude" "$current" "$latest"; then
      echo "[→] Actualizando Magnitude..."
      npm install -g @magnitudedev/cli@latest
    else
      echo "[✓] Magnitude ya está en la última versión."
    fi
  else
    echo "[→] Instalando Magnitude..."
    npm install -g @magnitudedev/cli@latest
  fi
  command -v magnitude >/dev/null 2>&1 || fail "Magnitude no quedó operativo."
  magnitude --version >/dev/null 2>&1 || fail "Magnitude quedó instalado pero no operativo."
}

install_hermes() {
  if command -v hermes >/dev/null 2>&1; then
    local current latest
    current="$(hermes --version 2>&1 | extract_version)"
    latest="$(latest_hermes_version)" || fail "No se pudo consultar la última versión de Hermes."
    if require_latest_version "Hermes" "$current" "$latest"; then
      echo "[→] Actualizando Hermes..."
      hermes update
    else
      echo "[✓] Hermes ya está en la última versión."
    fi
  else
    echo "[→] Instalando Hermes..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
  fi
  command -v hermes >/dev/null 2>&1 || fail "Hermes no quedó operativo."
  hermes --version >/dev/null 2>&1 || fail "Hermes quedó instalado pero no operativo."
  echo "[✓] Hermes operativo: $(hermes --version 2>&1 | head -1)"
}

install_omh() {
  if command -v omh >/dev/null 2>&1; then
    local current latest
    current="$(omh --version 2>&1 | extract_version)"
    latest="$(latest_github_tag NousResearch/openhands-manager)" || fail "No se pudo consultar la última versión de OMH."
    if require_latest_version "OMH" "$current" "$latest"; then
      echo "[→] Actualizando OMH..."
      omh update
    else
      echo "[✓] OMH ya está en la última versión."
    fi
  else
    echo "[→] Instalando OMH..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/openhands-manager/main/install.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
  fi
  command -v omh >/dev/null 2>&1 || fail "OMH no quedó operativo."
  omh --version >/dev/null 2>&1 || fail "OMH quedó instalado pero no operativo."
}

run_component() {
  local index="$1" total="$2" name="$3" fn="$4"
  printf '[→] Instalación %d/%d — %-10s | actividad... ' "$index" "$total" "$name"
  "$fn"
  echo "[✓] Instalación $index/$total — $name       completada."
}

components=()
for arg in "$@"; do
  case "$arg" in
    --fitllm) components+=(fitllm) ;;
    --ods) components+=(ods) ;;
    --magnitude) components+=(magnitude) ;;
    --hermes) components+=(hermes) ;;
    --omh) components+=(omh) ;;
    --all) components=(fitllm ods magnitude hermes omh) ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Argumento desconocido: $arg" ;;
  esac
done

((${#components[@]} > 0)) || fail "Debe indicar un componente (--fitllm, --ods, --magnitude, --hermes, --omh o --all)."

total=${#components[@]}
index=0
for component in "${components[@]}"; do
  index=$((index + 1))
  case "$component" in
    fitllm) run_component "$index" "$total" fitllm install_fitllm ;;
    ods) run_component "$index" "$total" ods install_ods ;;
    magnitude) run_component "$index" "$total" magnitude install_magnitude ;;
    hermes) run_component "$index" "$total" hermes install_hermes ;;
    omh) run_component "$index" "$total" omh install_omh ;;
  esac
done

echo "[✓] Instalación solicitada completada."
