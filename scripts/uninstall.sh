#!/usr/bin/env bash
set -euo pipefail

# LEONES cleanup entry point. It can be called directly or from the RC2 flow.
# Nothing is removed unless the corresponding component is explicitly selected.
# Historical evidence is deliberately preserved by the LEONES cleanup option.

usage() {
  cat <<'EOF'
LEONES — uninstall / cleanup

Usage:
  bash scripts/uninstall.sh                         # interactive multi-selection
  bash scripts/uninstall.sh --leones --ods --llms  # combine selections
  bash scripts/uninstall.sh --all                  # all components
  bash scripts/uninstall.sh --dry-run ...          # show actions without changes
  bash scripts/uninstall.sh --yes ...              # skip confirmation

Components:
  --leones      LEONES generated local state (not the source checkout or evidence)
  --ods         ODS containers/images/volumes identifiable as ODS
  --magnitude   global @magnitudedev/cli
  --llms        all local Ollama models
EOF
}

DRY_RUN=0
ASSUME_YES=0
SELECTED=()
for arg in "$@"; do
  case "$arg" in
    --leones|--ods|--magnitude|--llms) SELECTED+=("${arg#--}") ;;
    --all) SELECTED=(leones ods magnitude llms) ;;
    --dry-run) DRY_RUN=1 ;;
    --yes) ASSUME_YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[ERROR] Unknown option: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

contains() { local x="$1"; shift; for y in "$@"; do [[ "$x" == "$y" ]] && return 0; done; return 1; }
run() { if (( DRY_RUN )); then printf '[DRY-RUN]'; printf ' %q' "$@"; printf '\n'; else "$@"; fi; }

if ((${#SELECTED[@]} == 0)); then
  echo
echo 'LEONES — LIMPIEZA / DESINSTALACIÓN'
  echo 'Selecciona uno o varios componentes: 1,2,3,4.'
  echo
  echo '  [1] LEONES       — estado local generado por LEONES'
  echo '  [2] ODS          — recursos ODS de contenedores'
  echo '  [3] Magnitude    — @magnitudedev/cli'
  echo '  [4] LLM cargados — todos los modelos locales de Ollama'
  echo '  [5] TODO         — 1 + 2 + 3 + 4'
  echo '  [6] Salir'
  read -r -p 'LEONES> ' choice
  case "$choice" in
    6) exit 0 ;;
    5) SELECTED=(leones ods magnitude llms) ;;
    *)
      IFS=',' read -r -a nums <<< "$choice"
      for n in "${nums[@]}"; do
        case "${n//[[:space:]]/}" in
          1) SELECTED+=(leones) ;; 2) SELECTED+=(ods) ;;
          3) SELECTED+=(magnitude) ;; 4) SELECTED+=(llms) ;;
          *) echo "[ERROR] Opción no válida: $n"; exit 2 ;;
        esac
      done
      ;;
  esac
fi

UNIQUE=()
for item in "${SELECTED[@]}"; do contains "$item" "${UNIQUE[@]}" || UNIQUE+=("$item"); done
SELECTED=("${UNIQUE[@]}")
printf '\nSeleccionado: %s\n' "${SELECTED[*]}"

if (( ! ASSUME_YES && ! DRY_RUN )); then
  echo '[WARN] Se eliminarán solo los componentes seleccionados.'
  read -r -p '¿Confirmar? [y/N] ' answer
  [[ "$answer" =~ ^[Yy]$ ]] || { echo 'Cancelado. No se ha eliminado nada.'; exit 0; }
fi

if contains leones "${SELECTED[@]}"; then
  echo '== LEONES =='
  if [[ -e .leones ]]; then run rm -rf -- .leones; else echo '[i] No existe: .leones'; fi
  echo '[✓] Estado local de LEONES limpiado; el checkout y las evidencias históricas permanecen.'
fi

if contains magnitude "${SELECTED[@]}"; then
  echo '== MAGNITUDE =='
  if command -v npm >/dev/null 2>&1; then
    if npm list -g --depth=0 @magnitudedev/cli >/dev/null 2>&1; then run npm uninstall -g @magnitudedev/cli; else echo '[i] Magnitude no aparece instalado globalmente.'; fi
    if command -v sudo >/dev/null 2>&1; then
      if (( DRY_RUN )); then
        echo '[DRY-RUN] sudo npm uninstall -g @magnitudedev/cli (si está instalado en el ámbito de sudo)'
      elif sudo npm list -g --depth=0 @magnitudedev/cli >/dev/null 2>&1; then
        sudo npm uninstall -g @magnitudedev/cli
      fi
    fi
  else echo '[i] npm no está disponible; Magnitude no se ha modificado.'; fi
fi

if contains llms "${SELECTED[@]}"; then
  echo '== LLM CARGADOS / OLLAMA =='
  if command -v ollama >/dev/null 2>&1; then
    mapfile -t models < <(ollama list 2>/dev/null | awk 'NR>1 && $1!="" {print $1}')
    for model in "${models[@]}"; do run ollama rm "$model"; done
    echo "[✓] ${#models[@]} modelo(s) Ollama tratado(s)."
  else echo '[i] Ollama no está disponible; no se ha modificado ningún LLM.'; fi
fi

if contains ods "${SELECTED[@]}"; then
  echo '== ODS =='
  echo '[INFO] Solo se eliminan recursos cuyo nombre permita identificarlos como ODS.'
  container_cmd=()
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then container_cmd=(docker)
  elif command -v sudo >/dev/null 2>&1 && command -v docker >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then container_cmd=(sudo docker)
  elif command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then container_cmd=(podman)
  elif command -v sudo >/dev/null 2>&1 && command -v podman >/dev/null 2>&1 && sudo podman info >/dev/null 2>&1; then container_cmd=(sudo podman)
  fi
  if ((${#container_cmd[@]})); then
    mapfile -t ids < <("${container_cmd[@]}" ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}' | awk 'BEGIN{IGNORECASE=1} $0 ~ /ods/ {print $1}')
    for id in "${ids[@]}"; do [[ -n "$id" ]] && run "${container_cmd[@]}" rm -f "$id"; done
    mapfile -t images < <("${container_cmd[@]}" images --format '{{.Repository}}:{{.Tag}}' | awk 'BEGIN{IGNORECASE=1} $0 ~ /ods/ {print $1}')
    for image in "${images[@]}"; do [[ -n "$image" ]] && run "${container_cmd[@]}" rmi "$image"; done
    mapfile -t volumes < <("${container_cmd[@]}" volume ls --format '{{.Name}}' | awk 'BEGIN{IGNORECASE=1} $0 ~ /ods/ {print $1}')
    for volume in "${volumes[@]}"; do [[ -n "$volume" ]] && run "${container_cmd[@]}" volume rm "$volume"; done
    echo '[✓] Recursos ODS identificables limpiados.'
  else echo '[i] No hay runtime Docker/Podman operativo; ODS no se ha modificado.'; fi
  echo '[i] Docker y Podman no se desinstalan.'
fi

echo '[✓] Limpieza finalizada. Los componentes no seleccionados no se han tocado.'
