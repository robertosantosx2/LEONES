#!/usr/bin/env bash
set -euo pipefail

# LEONES cleanup entry point. Independent opt-in per component.
# LEONES state is offered last. Evidence and source checkout are preserved by default.

usage() {
  cat <<'USAGE'
LEONES — uninstall / cleanup (independent components)

Usage:
  bash scripts/uninstall.sh
  bash scripts/uninstall.sh --fitllm --magnitude
  bash scripts/uninstall.sh --all
  bash scripts/uninstall.sh --dry-run ...
  bash scripts/uninstall.sh --yes ...

Components:
  --fitllm      FitLLM / LLMFit CLI
  --magnitude   global @magnitudedev/cli
  --ods         ODS containers/images/volumes identifiable as ODS
  --hermes      Hermes local state when detectable
  --omh         Oh My Hermes local state when detectable
  --llms        all local Ollama models
  --leones      LEONES generated local state (.leones/) — offered last
USAGE
}

DRY_RUN=0
ASSUME_YES=0
SELECTED=()

finish_status() {
  local rc="${1:-0}"
  if (( rc == 0 )); then
    if (( DRY_RUN )); then
      echo '[✓] DRY-RUN finalizado correctamente. No se han realizado cambios.'
    else
      echo '[✓] DESINSTALACIÓN / LIMPIEZA FINALIZADA CORRECTAMENTE.'
      echo '[✓] Solo se tocaron componentes explícitamente seleccionados.'
    fi
  else
    echo "[✗] DESINSTALACIÓN / LIMPIEZA FALLIDA (código $rc)." >&2
  fi
}
trap 'rc=$?; finish_status "$rc"; exit "$rc"' EXIT

for arg in "$@"; do
  case "$arg" in
    --fitllm|--magnitude|--ods|--hermes|--omh|--llms|--leones) SELECTED+=("${arg#--}") ;;
    --all) SELECTED=(fitllm magnitude ods hermes omh llms leones) ;;
    --dry-run) DRY_RUN=1 ;;
    --yes) ASSUME_YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[ERROR] Unknown option: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

contains() {
  local x="$1"; shift
  for y in "$@"; do [[ "$x" == "$y" ]] && return 0; done
  return 1
}
run() {
  if (( DRY_RUN )); then
    printf '[DRY-RUN]'; printf ' %q' "$@"; printf '\n'
  else
    "$@"
  fi
}

if contains leones "${SELECTED[@]}"; then
  TMP=()
  for s in "${SELECTED[@]}"; do [[ "$s" != leones ]] && TMP+=("$s"); done
  TMP+=(leones)
  SELECTED=("${TMP[@]}")
fi

if ((${#SELECTED[@]} == 0)); then
  echo
  echo '╔══════════════════════════════════════════════════════════════╗'
  echo '║  LEONES — LIMPIEZA / DESINSTALACIÓN INDEPENDIENTE          ║'
  echo '╚══════════════════════════════════════════════════════════════╝'
  echo 'Selecciona uno o varios: 1,2,3…  (LEONES siempre al final si se elige)'
  echo
  echo '  [1] FitLLM / LLMFit'
  echo '  [2] Magnitude'
  echo '  [3] ODS'
  echo '  [4] Hermes'
  echo '  [5] Oh My Hermes (OMH)'
  echo '  [6] LLM cargados (Ollama models)'
  echo '  [7] LEONES estado local (.leones/)  ← último'
  echo '  [8] TODO'
  echo '  [9] Salir'
  echo
  read -r -p 'LEONES> ' choice || choice=9
  case "$choice" in
    8) SELECTED=(fitllm magnitude ods hermes omh llms leones) ;;
    9) echo '[i] Sin cambios.'; exit 0 ;;
    *)
      SELECTED=()
      IFS=',' read -r -a nums <<< "$choice"
      for n in "${nums[@]}"; do
        n="${n//[[:space:]]/}"
        case "$n" in
          1) SELECTED+=(fitllm) ;; 2) SELECTED+=(magnitude) ;; 3) SELECTED+=(ods) ;;
          4) SELECTED+=(hermes) ;; 5) SELECTED+=(omh) ;; 6) SELECTED+=(llms) ;; 7) SELECTED+=(leones) ;;
        esac
      done
      ;;
  esac
  if ((${#SELECTED[@]} == 0)); then echo '[i] Nada seleccionado.'; exit 0; fi
  if contains leones "${SELECTED[@]}"; then
    TMP=(); for s in "${SELECTED[@]}"; do [[ "$s" != leones ]] && TMP+=("$s"); done
    TMP+=(leones); SELECTED=("${TMP[@]}")
  fi
fi

if (( ! ASSUME_YES && ! DRY_RUN )); then
  echo; echo "Se van a limpiar: ${SELECTED[*]}"
  read -r -p '¿Confirmar? [s/N] ' ans || ans=''
  case "$ans" in s|S|y|Y) ;; *) echo '[i] Cancelado.'; exit 0 ;; esac
fi

if contains fitllm "${SELECTED[@]}"; then
  echo '== FitLLM / LLMFit =='
  if command -v pipx >/dev/null 2>&1 && pipx list 2>/dev/null | grep -qi llmfit; then run pipx uninstall llmfit || true; fi
  if command -v pip3 >/dev/null 2>&1; then run pip3 uninstall -y llmfit fitllm 2>/dev/null || true
  elif command -v pip >/dev/null 2>&1; then run pip uninstall -y llmfit fitllm 2>/dev/null || true; fi

  # LLMFit is a standalone ELF. The official installer can leave it in
  # /usr/local/bin, so LEONES owns both supported locations explicitly.
  # Unlink permission is determined by the parent directory, not file ownership.
  remove_llmfit() {
    local llmfit_path="$1"
    local llmfit_dir
    llmfit_dir="$(dirname "$llmfit_path")"
    if [[ ! -f "$llmfit_path" ]]; then
      return 0
    fi
    if [[ -w "$llmfit_dir" ]]; then
      run rm -f -- "$llmfit_path"
    elif command -v sudo >/dev/null 2>&1; then
      run sudo rm -f -- "$llmfit_path"
    else
      echo "[✗] No se puede eliminar $llmfit_path: requiere sudo." >&2
      return 1
    fi
  }

  remove_llmfit "$HOME/.local/bin/llmfit"
  remove_llmfit "/usr/local/bin/llmfit"

  hash -r 2>/dev/null || true
  if command -v llmfit >/dev/null 2>&1; then
    echo "[✗] llmfit sigue en PATH: $(command -v llmfit)" >&2
    exit 1
  else
    echo '[✓] FitLLM/LLMFit retirado correctamente.'
  fi
fi

if contains magnitude "${SELECTED[@]}"; then
  echo '== Magnitude =='
  if command -v npm >/dev/null 2>&1; then
    if npm list -g --depth=0 @magnitudedev/cli >/dev/null 2>&1; then run npm uninstall -g @magnitudedev/cli; else echo '[i] Magnitude no aparece instalado globalmente (user).'; fi
    if command -v sudo >/dev/null 2>&1; then
      if (( DRY_RUN )); then echo '[DRY-RUN] sudo npm uninstall -g @magnitudedev/cli (si aplica)'
      elif sudo npm list -g --depth=0 @magnitudedev/cli >/dev/null 2>&1; then sudo npm uninstall -g @magnitudedev/cli; fi
    fi
  else echo '[i] npm no disponible; Magnitude no modificado.'; fi
fi

if contains hermes "${SELECTED[@]}"; then
  echo '== Hermes =='
  if command -v hermes >/dev/null 2>&1; then echo "[i] hermes en PATH: $(command -v hermes) — binario de sistema no retirado automáticamente."; fi
  if [[ -d "$HOME/.hermes" ]]; then run rm -rf -- "$HOME/.hermes"; else echo '[i] No existe ~/.hermes'; fi
fi

if contains omh "${SELECTED[@]}"; then
  echo '== Oh My Hermes =='
  local_omh_bin="$HOME/.local/bin/omh"
  local_omh_state="$HOME/.local/share/omh"
  if command -v omh >/dev/null 2>&1; then echo "[i] omh en PATH: $(command -v omh)"; fi
  if [[ -e "$local_omh_bin" || -L "$local_omh_bin" ]]; then
    if [[ -L "$local_omh_bin" ]]; then
      target="$(readlink "$local_omh_bin")"
      if [[ "$target" == *"/.local/share/omh/"* || "$target" == "$HOME/.local/share/omh"* ]]; then
        run rm -f -- "$local_omh_bin"
      else
        echo "[i] No se elimina $local_omh_bin: enlace ajeno a OMH.";
      fi
    else
      echo "[i] No se elimina $local_omh_bin: no es un enlace simbólico gestionable por OMH.";
    fi
  fi
  if [[ -d "$local_omh_state" ]]; then run rm -rf -- "$local_omh_state"; else echo '[i] No existe ~/.local/share/omh'; fi
  if [[ -d "$HOME/.omh" ]]; then run rm -rf -- "$HOME/.omh"; else echo '[i] No existe ~/.omh'; fi
  hash -r 2>/dev/null || true
  if command -v omh >/dev/null 2>&1; then
    echo "[✗] omh sigue en PATH: $(command -v omh)" >&2
    exit 1
  else
    echo '[✓] Oh My Hermes retirado correctamente.'
  fi
fi

if contains llms "${SELECTED[@]}"; then
  echo '== LLM CARGADOS / OLLAMA =='
  if command -v ollama >/dev/null 2>&1; then
    mapfile -t models < <(ollama list 2>/dev/null | awk 'NR>1 && $1!="" {print $1}')
    for model in "${models[@]}"; do run ollama rm "$model"; done
    echo "[✓] ${#models[@]} modelo(s) Ollama tratado(s)."
  else echo '[i] Ollama no disponible; LLM no modificados.'; fi
fi

if contains ods "${SELECTED[@]}"; then
  echo '== ODS =='; echo '[INFO] Solo recursos identificables como ODS.'
  container_cmd=()
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then container_cmd=(docker)
  elif command -v sudo >/dev/null 2>&1 && command -v docker >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then container_cmd=(sudo docker)
  elif command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then container_cmd=(podman)
  elif command -v sudo >/dev/null 2>&1 && command -v podman >/dev/null 2>&1 && sudo podman info >/dev/null 2>&1; then container_cmd=(sudo podman); fi
  if ((${#container_cmd[@]})); then
    mapfile -t ids < <("${container_cmd[@]}" ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}' | awk 'BEGIN{IGNORECASE=1} $0 ~ /ods/ {print $1}')
    for id in "${ids[@]}"; do [[ -n "$id" ]] && run "${container_cmd[@]}" rm -f "$id"; done
    mapfile -t images < <("${container_cmd[@]}" images --format '{{.Repository}}:{{.Tag}}' | awk 'BEGIN{IGNORECASE=1} $0 ~ /ods/ {print $1}')
    for image in "${images[@]}"; do [[ -n "$image" ]] && run "${container_cmd[@]}" rmi "$image"; done
    mapfile -t volumes < <("${container_cmd[@]}" volume ls --format '{{.Name}}' | awk 'BEGIN{IGNORECASE=1} $0 ~ /ods/ {print $1}')
    for volume in "${volumes[@]}"; do [[ -n "$volume" ]] && run "${container_cmd[@]}" volume rm "$volume"; done
    echo '[✓] Recursos ODS identificables limpiados.'
  else echo '[i] No hay Docker/Podman operativo; ODS no modificado.'; fi
  echo '[i] Docker y Podman no se desinstalan.'
fi

if contains leones "${SELECTED[@]}"; then
  echo '== LEONES (estado local) =='
  if [[ -e .leones ]]; then run rm -rf -- .leones; else echo '[i] No existe: .leones'; fi
  echo '[i] Checkout fuente y evidencias históricas no se borran por defecto.'
fi

exit 0
