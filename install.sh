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
      return 0
    fi
  else
    echo "[→] Instalando FitLLM / LLMFit..."
    curl -fsSL https://llmfit.axjns.dev/install.sh | sh -s -- --local
    export PATH="$HOME/.local/bin:$PATH"
  fi
  command -v llmfit >/dev/null 2>&1 || fail "LLMFit no está disponible en PATH."
  echo "[✓] FitLLM / LLMFit operativo: $(llmfit --version 2>&1 | head -1)"
}

install_ods() {
  local ods_cli="$HOME/ods/ods-cli"
  local ods_bin="$HOME/.local/bin/ods"

  if command -v ods >/dev/null 2>&1; then
    local current latest
    current="$(ods --version 2>&1 | extract_version)"
    latest="$(latest_github_tag Osmantic/ODS)" || fail "No se pudo consultar la última versión estable de ODS."
    if require_latest_version "Osmantic ODS" "$current" "$latest"; then
      echo "[→] Actualizando Osmantic ODS..."
      command -v docker >/dev/null 2>&1 || fail "ODS requiere Docker; Docker no está instalado."
      if ! docker info >/dev/null 2>&1 && ! (command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1); then
        fail "ODS requiere un Docker operativo. Inicia Docker y vuelve a intentarlo."
      fi
      curl -fsSL https://install.osmantic.com/ods.sh | ODS_REF="v$latest" bash
    else
      echo "[✓] Osmantic ODS ya está en la última versión."
      return 0
    fi
  else
    command -v docker >/dev/null 2>&1 || fail "ODS requiere Docker; Docker no está instalado."
    if ! docker info >/dev/null 2>&1 && ! (command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1); then
      fail "ODS requiere un Docker operativo. Inicia Docker y vuelve a intentarlo."
    fi
    if [[ -x "$ods_cli" ]]; then
      echo "[→] ODS ya está instalado en $HOME/ods; registrando su CLI..."
    else
      echo "[→] Instalando Osmantic ODS..."
      curl -fsSL https://install.osmantic.com/ods.sh | bash
    fi
  fi

  if [[ ! -x "$ods_cli" ]]; then
    fail "ODS no dejó disponible su CLI esperado en $ods_cli."
  fi
  mkdir -p "$HOME/.local/bin"
  ln -sfn "$ods_cli" "$ods_bin"
  export PATH="$HOME/.local/bin:$PATH"
  command -v ods >/dev/null 2>&1 || fail "ODS está instalado pero 'ods' no quedó disponible en PATH."
  "$ods_bin" --help >/dev/null 2>&1 || fail "El CLI de ODS está presente pero no es ejecutable."
  echo "[✓] Osmantic ODS operativo: $(ods --version 2>&1 | head -1)"
}

install_magnitude() {
  command -v npm >/dev/null 2>&1 || fail "Magnitude requiere Node.js/npm."
  if command -v magnitude >/dev/null 2>&1; then
    local current latest
    current="$(magnitude --version 2>&1 | extract_version)"
    latest="$(npm view @magnitudedev/cli version 2>/dev/null)" || fail "No se pudo consultar la última versión de Magnitude."
    if require_latest_version "Magnitude" "$current" "$latest"; then
      echo "[→] Actualizando Magnitude..."
      if npm install -g @magnitudedev/cli; then :; else
        command -v sudo >/dev/null 2>&1 || fail "No se pudo actualizar Magnitude y sudo no está disponible."
        sudo npm install -g @magnitudedev/cli
      fi
    else
      echo "[✓] Magnitude ya está en la última versión."
      return 0
    fi
  else
    echo "[→] Instalando Magnitude..."
    if npm install -g @magnitudedev/cli; then :; else
      command -v sudo >/dev/null 2>&1 || fail "No se pudo instalar Magnitude y sudo no está disponible."
      sudo npm install -g @magnitudedev/cli
    fi
  fi
  command -v magnitude >/dev/null 2>&1 || fail "Magnitude no está en PATH."
  echo "[✓] Magnitude operativo: $(magnitude --version 2>&1 | head -1)"
}

install_hermes() {
  local hermes_bin="$HOME/.local/bin/hermes"
  local hermes_ok=0

  if command -v hermes >/dev/null 2>&1 && hermes --version >/dev/null 2>&1; then
    hermes_ok=1
  fi

  if (( hermes_ok )); then
    local current latest
    current="$(hermes --version 2>&1 | extract_version)"
    latest="$(latest_hermes_version)" || fail "No se pudo consultar la última versión estable de Hermes."
    if require_latest_version "Hermes" "$current" "$latest"; then
      echo "[→] Actualizando Hermes..."
      hermes update
    else
      echo "[✓] Hermes ya está en la última versión."
      return 0
    fi
  else
    if [[ -x "$hermes_bin" ]]; then
      echo "[→] Hermes existe pero no está operativo; reparando instalación..."
    else
      echo "[→] Instalando Hermes..."
    fi
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
  fi

  command -v hermes >/dev/null 2>&1 || fail "Hermes no quedó disponible."
  hermes --version >/dev/null 2>&1 || fail "Hermes quedó instalado pero no es operativo."
  echo "[✓] Hermes operativo: $(hermes --version 2>&1 | head -1)"
}

install_omh() {
  local omh_skills="$HOME/.local/share/omh/generations/bootstrap-legacy/skills"

  if command -v omh >/dev/null 2>&1; then
    local current latest
    current="$(omh --version 2>&1 | extract_version)"
    latest="$(latest_github_tag rlaope/oh-my-hermes)" || fail "No se pudo consultar la última versión estable de OMH."
    if require_latest_version "Oh My Hermes" "$current" "$latest"; then
      echo "[→] Actualizando Oh My Hermes..."
      omh update
    else
      echo "[✓] Oh My Hermes ya está en la última versión."
      omh setup
    fi
  else
    curl -fsSL https://raw.githubusercontent.com/rlaope/oh-my-hermes/main/install.sh | OMH_CHANNEL=stable sh
    export PATH="$HOME/.local/bin:$PATH"
  fi
  command -v omh >/dev/null 2>&1 || fail "Oh My Hermes no quedó disponible."

  if [[ -L "$omh_skills" && ! -e "$omh_skills" ]]; then
    echo "[→] Reparando enlace residual roto de OMH: $omh_skills"
    rm -f -- "$omh_skills"
  fi

  omh --version >/dev/null 2>&1 || fail "Oh My Hermes está presente pero no es operativo."
  omh setup
  omh doctor >/dev/null 2>&1 || fail "Oh My Hermes quedó instalado pero la comprobación 'omh doctor' falló."
}

selected=()
if (($# == 0)); then usage; exit 2; fi
for arg in "$@"; do
  case "$arg" in
    --fitllm) selected+=(fitllm) ;;
    --ods) selected+=(ods) ;;
    --magnitude) selected+=(magnitude) ;;
    --hermes) selected+=(hermes) ;;
    --omh) selected+=(omh) ;;
    --all) selected+=(fitllm ods magnitude hermes omh) ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Opción desconocida: $arg" ;;
  esac
done

run_component() {
  local index="$1" total="$2" component="$3"; shift 3
  echo "[→] Instalación $index/$total — $component"
  "$@" &
  local pid=$! tick=0 status
  local frames=('|' '/' '-' '\\')
  while kill -0 "$pid" 2>/dev/null; do
    printf '\r[→] Instalando %-12s %s actividad... ' "$component" "${frames[$((tick % 4))]}"
    tick=$((tick + 1))
    sleep 1
  done
  if wait "$pid"; then
    printf '\r[✓] Instalación %d/%d — %-12s completada.\n' "$index" "$total" "$component"
  else
    status=$?
    printf '\r[✗] Instalación %d/%d — %-12s fallida (código %d).\n' "$index" "$total" "$component" "$status" >&2
    return "$status"
  fi
}

total=${#selected[@]}
index=0
for component in "${selected[@]}"; do
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
