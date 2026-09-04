#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "============================================================"
echo "LEONES — RC3 INSTALL"
echo "============================================================"
echo "[i] RC3 bootstrap: Hermes → Oh My Hermes → LEONES"
echo

fail() { echo "[✗] $1"; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "Python 3 no está instalado."
command -v git >/dev/null 2>&1 || fail "Git no está instalado."

python3 - <<'PY' || exit 1
import sys
if sys.version_info < (3, 10):
    print("[✗] LEONES RC3 requiere Python 3.10 o superior.")
    raise SystemExit(1)
print(f"[✓] Python {sys.version.split()[0]}")
PY

echo "[✓] Git $(git --version | awk '{print $3}')"

# -----------------------------------------------------------------------------
# Hermes: canonical bootstrap/discovery layer.
# If already installed, update it in place using the upstream updater.
# -----------------------------------------------------------------------------
install_hermes() {
    if command -v hermes >/dev/null 2>&1; then
        echo "[✓] Hermes ya está instalado: $(hermes --version 2>/dev/null | head -1 || true)"
        echo "[→] Hermes instalado: intentando actualizar..."
        if hermes update --yes; then
            echo "[✓] Hermes actualizado/verificado: $(hermes --version 2>/dev/null | head -1 || true)"
        else
            echo "[!] Hermes: la actualización falló; se conserva la instalación existente."
        fi
        return 0
    fi

    echo "[→] Hermes no está instalado. Instalando desde el instalador oficial..."
    command -v curl >/dev/null 2>&1 || fail "curl no está instalado; es necesario para instalar Hermes."
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

    # The upstream installer may place the command in ~/.local/bin.
    export PATH="$HOME/.local/bin:$PATH"
    command -v hermes >/dev/null 2>&1 || fail "Hermes se instaló pero el comando 'hermes' no está en PATH."
    echo "[✓] Hermes instalado: $(hermes --version 2>/dev/null | head -1 || true)"
}

# -----------------------------------------------------------------------------
# Oh My Hermes: operating layer above Hermes.
# Existing installs are updated before setup so managed skills/plugins are fresh.
# -----------------------------------------------------------------------------
install_omh() {
    if command -v omh >/dev/null 2>&1; then
        echo "[✓] Oh My Hermes ya está instalado: $(omh --version 2>/dev/null | head -1 || true)"
        echo "[→] Oh My Hermes instalado: intentando actualizar..."
        if omh update; then
            echo "[✓] Oh My Hermes actualizado/verificado: $(omh --version 2>/dev/null | head -1 || true)"
        else
            echo "[!] Oh My Hermes: la actualización falló; se conserva la instalación existente."
        fi
    else
        echo "[→] Oh My Hermes no está instalado. Instalando desde el repositorio oficial..."
        command -v curl >/dev/null 2>&1 || fail "curl no está instalado; es necesario para instalar Oh My Hermes."
        curl -fsSL https://raw.githubusercontent.com/rlaope/oh-my-hermes/main/install.sh | OMH_CHANNEL=stable sh
        export PATH="$HOME/.local/bin:$PATH"
        command -v omh >/dev/null 2>&1 || fail "Oh My Hermes se instaló pero el comando 'omh' no está en PATH."
        echo "[✓] Oh My Hermes instalado: $(omh --version 2>/dev/null | head -1 || true)"
    fi

    echo "[→] Configurando Oh My Hermes sobre Hermes..."
    omh setup
    echo "[✓] Oh My Hermes configurado."
}

# -----------------------------------------------------------------------------
# Optional execution stacks: never install them implicitly in RC3, but if the
# user already has one, keep it current. Failures are warnings, not blockers.
# -----------------------------------------------------------------------------
update_magnitude_if_installed() {
    if command -v magnitude >/dev/null 2>&1; then
        echo "[✓] Magnitude ya está instalado: $(magnitude --version 2>/dev/null | head -1 || true)"
        if command -v npm >/dev/null 2>&1; then
            echo "[→] Magnitude instalado: intentando actualizar @magnitudedev/cli..."
            if npm install -g @magnitudedev/cli; then
                echo "[✓] Magnitude actualizado/verificado: $(magnitude --version 2>/dev/null | head -1 || true)"
            else
                echo "[!] Magnitude: la actualización falló; se conserva la instalación existente."
            fi
        else
            echo "[!] Magnitude detectado, pero npm no está disponible; no se puede intentar la actualización."
        fi
    else
        echo "[i] Magnitude no detectado; no se instala automáticamente en RC3."
    fi
}

update_ods_if_installed() {
    if command -v ods >/dev/null 2>&1; then
        echo "[✓] ODS ya está instalado: $(ods --version 2>/dev/null | head -1 || true)"
        echo "[→] ODS instalado: intentando actualizar..."
        if ods update; then
            echo "[✓] ODS actualizado/verificado: $(ods --version 2>/dev/null | head -1 || true)"
        else
            echo "[!] ODS: la actualización falló; se conserva la instalación existente."
        fi
    else
        echo "[i] ODS no detectado; no se instala automáticamente en RC3."
    fi
}

install_hermes
install_omh
update_magnitude_if_installed
update_ods_if_installed

# -----------------------------------------------------------------------------
# RC3 deliberately has no LLMFit/FitLLM dependency.
# -----------------------------------------------------------------------------
echo
echo "[✓] LLMFit/FitLLM: fuera de RC3 (no se instala ni bloquea el arranque)."

echo
chmod +x "$ROOT/leones" "$ROOT/scripts/rc2_wizard.py" 2>/dev/null || true
echo "[✓] Instalación RC3 preparada."
echo "[i] Flujo: Hermes discovery → hardware-profile.v1 → LEONES → elección → Magnitude/ODS → medición → evidencia."
echo "[i] Verificación Hermes: hermes doctor"
echo "[i] Verificación OMH: omh doctor"
echo "[i] Ejecuta: ./leones"
