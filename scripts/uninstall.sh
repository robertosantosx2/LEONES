#!/usr/bin/env bash
set -euo pipefail

# LEONES cleanup entry point. It can be called directly or from rc2_wizard.py.
# Nothing is removed unless the corresponding component is explicitly selected.

usage() {
  cat <<'EOF'
LEONES — uninstall / cleanup

Usage:
  bash scripts/uninstall.sh                  # interactive component selection
  bash scripts/uninstall.sh --leones         # remove LEONES local state
  bash scripts/uninstall.sh --ods            # remove ODS containers/images/volumes owned by ODS
  bash scripts/uninstall.sh --magnitude      # npm uninstall @magnitudedev/cli
  bash scripts/uninstall.sh --llms            # remove all Ollama models
  bash scripts/uninstall.sh --all             # all of the above
  bash scripts/uninstall.sh --dry-run ...     # show actions without changing anything
  bash scripts/uninstall.sh --yes ...         # do not ask for confirmation

LEONES source checkout is NOT deleted by --leones. Delete the repository separately
only when you are outside it. This prevents the cleanup command from destroying the
currently running program unexpectedly.
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
run() {
  if (( DRY_RUN )); then printf '[DRY-RUN]'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

if ((${#SELECTED[@]} == 0)); then
  echo
  echo 'LEONES — LIMPIEZA / DESINSTALACIÓN'
  echo 'Selecciona componentes; cada opción es independiente.'
  echo
  echo '  [1] LEONES (estado local; no borra este checkout)'
  echo '  [2] ODS'
  echo '  [3] Magnitude (@magnitudedev/cli)'
  echo '  [4] LLM cargados en Ollama (todos los modelos locales)'
  echo '  [5] TODO lo anterior'
  echo '  [6] Salir'
  read -r -p 'LEONES> ' choice
  case "$choice" in
    1) SELECTED=(leones) ;;
    2) SELECTED=(ods) ;;
    3) SELECTED=(magnitude) ;;
    4) SELECTED=(llms) ;;
    5) SELECTED=(leones ods magnitude llms) ;;
    6) exit 0 ;;
    *) echo '[ERROR] Opción no válida.'; exit 2 ;;
  esac
fi

printf '\nSeleccionado: %s\n' "${SELECTED[*]}"
(( DRY_RUN )) && echo '[INFO] Modo dry-run: no se modificará el equipo.'
if (( ! ASSUME_YES && ! DRY_RUN )); then
  echo '[WARN] Esta operación puede detener servicios y borrar modelos/datos locales de los componentes elegidos.'
  read -r -p '¿Confirmar? [y/N] ' answer
  [[ "$answer" =~ ^[Yy]$ ]] || { echo 'Cancelado. No se ha eliminado nada.'; exit 0; }
fi

if contains leones "${SELECTED[@]}"; then
  echo
  echo '== LEONES =='
  # Only LEONES-generated local state is removed. Source checkout remains intact.
  for path in .leones artifacts/runtime-executions artifacts/runtime-benchmark-evidence; do
    if [[ -e "$path" ]]; then run rm -rf -- "$path"; else echo "[i] No existe: $path"; fi
  done
  echo '[✓] Estado local de LEONES limpiado.'
fi

if contains magnitude "${SELECTED[@]}"; then
  echo
  echo '== MAGNITUDE =='
  if command -v npm >/dev/null 2>&1; then
    if npm list -g --depth=0 @magnitudedev/cli >/dev/null 2>&1; then
      run npm uninstall -g @magnitudedev/cli
    else
      echo '[i] @magnitudedev/cli no aparece instalado globalmente.'
    fi
  else
    echo '[i] npm no está disponible; Magnitude no se ha modificado.'
  fi
  if command -v sudo >/dev/null 2>&1 && (( ! DRY_RUN )); then
    if sudo npm list -g --depth=0 @magnitudedev/cli >/dev/null 2>&1; then
      run sudo npm uninstall -g @magnitudedev/cli
    fi
  fi
fi

if contains llms "${SELECTED[@]}"; then
  echo
  echo '== LLM CARGADOS / OLLAMA =='
  if command -v ollama >/dev/null 2>&1; then
    mapfile -t models < <(ollama list 2>/dev/null | awk 'NR>1 && $1!="" {print $1}')
    if ((${#models[@]} == 0)); then
      echo '[i] No hay modelos Ollama locales detectados.'
    else
      printf '[i] Modelos que se eliminarán: '; printf '%s ' "${models[@]}"; echo
      for model in "${models[@]}"; do run ollama rm "$model"; done
      echo '[✓] Modelos Ollama eliminados.'
    fi
  else
    echo '[i] Ollama no está disponible; no se ha modificado ningún LLM.'
  fi
fi

if contains ods "${SELECTED[@]}"; then
  echo
  echo '== ODS =='
  echo '[INFO] LEONES solo elimina recursos Docker/Podman identificables como ODS; no borra contenedores ajenos.'
  container_cmd=()
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    container_cmd=(docker)
  elif command -v sudo >/dev/null 2>&1 && command -v docker >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    container_cmd=(sudo docker)
  elif command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then
    container_cmd=(podman)
  elif command -v sudo >/dev/null 2>&1 && command -v podman >/dev/null 2>&1 && sudo podman info >/dev/null 2>&1; then
    container_cmd=(sudo podman)
  else
    echo '[i] No se encontró un runtime de contenedores operativo; ODS no se ha modificado.'
    container_cmd=()
  fi

  if ((${#container_cmd[@]})); then
    mapfile -t ids < <("${container_cmd[@]}" ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}' | awk 'BEGIN{IGNORECASE=1} $0 ~ /ods/ {print $1}')
    for id in "${ids[@]}"; do
      [[ -n "$id" ]] || continue
      run "${container_cmd[@]}" rm -f "$id"
    done
    mapfile -t images < <("${container_cmd[@]}" images --format '{{.Repository}}:{{.Tag}}' | awk 'BEGIN{IGNORECASE=1} $0 ~ /ods/ {print $1}')
    for image in "${images[@]}"; do
      [[ -n "$image" ]] || continue
      run "${container_cmd[@]}" rmi "$image"
    done
    mapfile -t volumes < <("${container_cmd[@]}" volume ls --format '{{.Name}}' | awk 'BEGIN{IGNORECASE=1} $0 ~ /ods/ {print $1}')
    for volume in "${volumes[@]}"; do
      [[ -n "$volume" ]] || continue
      run "${container_cmd[@]}" volume rm "$volume"
    done
    echo '[✓] Recursos ODS identificables han sido limpiados.'
  fi
  echo '[i] La eliminación de ODS no desinstala Docker ni Podman del sistema.'
fi

echo
echo '[✓] Limpieza finalizada. Los componentes no seleccionados no se han tocado.'
