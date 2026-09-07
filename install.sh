#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

echo "============================================================"
echo "LEONES — RC4 INSTALL"
echo "============================================================"
echo "[i] RC4 bootstrap: FitLLM/LLMFit → ODS (Osmantic) → Magnitude"
echo "[i] Hermes / Oh My Hermes se conservan como capas opcionales."
echo

fail() { echo "[✗] $1" >&2; exit 1; }
warn() { echo "[!] $1" >&2; }

command -v python3 >/dev/null 2>&1 || fail "Python 3 no está instalado."
command -v git >/dev/null 2>&1 || fail "Git no está instalado."
command -v curl >/dev/null 2>&1 || fail "curl no está instalado; es necesario para los instaladores oficiales."

python3 - <<'PY' || exit 1
import sys
if sys.version_info < (3, 10):
    print("[✗] LEONES RC4 requiere Python 3.10 o superior.")
    raise SystemExit(1)
print(f"[✓] Python {sys.version.split()[0]}")
PY

echo "[✓] Git $(git --version | awk '{print $3}')"

# -----------------------------------------------------------------------------
# RC4 required component 1: FitLLM / LLMFit.
# Use the upstream binary installer so RC4 does not depend on distro Python
# packaging or write into system directories. The installer supports --local.
# -----------------------------------------------------------------------------
install_fitllm() {
    if command -v llmfit >/dev/null 2>&1; then
        echo "[✓] FitLLM / LLMFit ya está instalado: $(llmfit --version 2>/dev/null | head -1 || true)"
        return 0
    fi

    echo "[→] FitLLM / LLMFit no está instalado. Instalando versión oficial..."
    curl -fsSL https://llmfit.axjns.dev/install.sh | sh -s -- --local
    export PATH="$HOME/.local/bin:$PATH"
    command -v llmfit >/dev/null 2>&1 || fail "LLMFit se instaló pero 'llmfit' no está en PATH."
    echo "[✓] FitLLM / LLMFit instalado: $(llmfit --version 2>/dev/null | head -1 || true)"
}

# -----------------------------------------------------------------------------
# RC4 required component 2: Osmantic ODS.
# ODS is the execution/application stack. Its official installer handles the
# current stack and model bootstrap. Docker must already be operational.
# -----------------------------------------------------------------------------
install_ods() {
    if command -v ods >/dev/null 2>&1; then
        echo "[✓] Osmantic ODS ya está instalado: $(ods --version 2>/dev/null | head -1 || true)"
        return 0
    fi

    command -v docker >/dev/null 2>&1 || fail "ODS requiere Docker; Docker no está instalado."
    if ! docker info >/dev/null 2>&1; then
        if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
            echo "[i] Docker responde mediante sudo; ODS se instalará usando el instalador oficial."
        else
            fail "ODS requiere un Docker operativo. Inicia Docker y vuelve a ejecutar ./install.sh."
        fi
    fi

    echo "[→] Osmantic ODS no está instalado. Ejecutando instalador oficial..."
    curl -fsSL https://install.osmantic.com/ods.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
    command -v ods >/dev/null 2>&1 || warn "ODS terminó su instalador, pero el comando 'ods' aún no aparece en PATH."
    if command -v ods >/dev/null 2>&1; then
        echo "[✓] Osmantic ODS instalado: $(ods --version 2>/dev/null | head -1 || true)"
    else
        echo "[i] ODS puede gestionarse desde su directorio de instalación; inventario RC4 lo volverá a detectar."
    fi
}

# -----------------------------------------------------------------------------
# RC4 required component 3: Magnitude.
# Magnitude publishes the supported CLI through npm. Keep installation global
# to match the canonical command and the independent uninstall contract.
# -----------------------------------------------------------------------------
install_magnitude() {
    if command -v magnitude >/dev/null 2>&1; then
        echo "[✓] Magnitude ya está instalado: $(magnitude --version 2>/dev/null | head -1 || true)"
        return 0
    fi

    command -v npm >/dev/null 2>&1 || fail "Magnitude requiere npm/Node.js; npm no está instalado."
    echo "[→] Magnitude no está instalado. Instalando @magnitudedev/cli..."
    if npm install -g @magnitudedev/cli; then
        :
    else
        warn "npm global sin permisos; reintentando con sudo."
        command -v sudo >/dev/null 2>&1 || fail "No se pudo instalar Magnitude globalmente y sudo no está disponible."
        sudo npm install -g @magnitudedev/cli
    fi
    command -v magnitude >/dev/null 2>&1 || fail "Magnitude se instaló pero el comando 'magnitude' no está en PATH."
    echo "[✓] Magnitude instalado: $(magnitude --version 2>/dev/null | head -1 || true)"
}

# -----------------------------------------------------------------------------
# Existing optional layers from the RC3 bootstrap. They are retained because
# RC4 inventory/uninstall already models them independently.
# -----------------------------------------------------------------------------
install_hermes() {
    if command -v hermes >/dev/null 2>&1; then
        echo "[✓] Hermes ya está instalado: $(hermes --version 2>/dev/null | head -1 || true)"
        echo "[→] Hermes instalado: intentando actualizar..."
        if hermes update --yes; then
            echo "[✓] Hermes actualizado/verificado."
        else
            echo "[!] Hermes: la actualización falló; se conserva la instalación existente."
        fi
        return 0
    fi

    echo "[→] Hermes no está instalado. Instalando desde el instalador oficial..."
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
    command -v hermes >/dev/null 2>&1 || fail "Hermes se instaló pero el comando 'hermes' no está en PATH."
    echo "[✓] Hermes instalado: $(hermes --version 2>/dev/null | head -1 || true)"
}

install_omh() {
    if command -v omh >/dev/null 2>&1; then
        echo "[✓] Oh My Hermes ya está instalado: $(omh --version 2>/dev/null | head -1 || true)"
        if omh update; then
            echo "[✓] Oh My Hermes actualizado/verificado."
        else
            echo "[!] Oh My Hermes: la actualización falló; se conserva la instalación existente."
        fi
    else
        echo "[→] Oh My Hermes no está instalado. Instalando desde el repositorio oficial..."
        curl -fsSL https://raw.githubusercontent.com/rlaope/oh-my-hermes/main/install.sh | OMH_CHANNEL=stable sh
        export PATH="$HOME/.local/bin:$PATH"
        command -v omh >/dev/null 2>&1 || fail "Oh My Hermes se instaló pero el comando 'omh' no está en PATH."
        echo "[✓] Oh My Hermes instalado: $(omh --version 2>/dev/null | head -1 || true)"
    fi

    echo "[→] Configurando Oh My Hermes sobre Hermes..."
    omh setup
    echo "[✓] Oh My Hermes configurado."
}

# RC4 canonical bootstrap: required components first.
install_fitllm
install_ods
install_magnitude

# Preserve the existing optional agent/harness layers.
install_hermes
install_omh

chmod +x "$ROOT/leones" "$ROOT/scripts/rc2_wizard.py" 2>/dev/null || true

echo
echo "============================================================"
echo "LEONES — RC4 INSTALL COMPLETADO"
echo "============================================================"
echo "[✓] FitLLM / LLMFit"
echo "[✓] Osmantic ODS"
echo "[✓] Magnitude"
echo "[i] Hermes / Oh My Hermes: capas opcionales conservadas"
echo
echo "[i] Inventario: ./leones --inventory"
echo "[i] Recomendador RC4: python3 scripts/rc4_fitllm_recommend.py --purpose programming --json"
echo "[i] ODS: requiere Docker operativo"
echo "[i] Desinstalación independiente: bash scripts/uninstall.sh --fitllm --ods --magnitude"
echo "[i] Ejecuta: ./leones"
