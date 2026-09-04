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
# LEONES deliberately delegates installation to the upstream installer.
# -----------------------------------------------------------------------------
install_hermes() {
    if command -v hermes >/dev/null 2>&1; then
        echo "[✓] Hermes ya está instalado: $(hermes --version 2>/dev/null | head -1 || true)"
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
# It is installed after Hermes and remains optional to the physical benchmark,
# but is part of the canonical RC3 installation path.
# -----------------------------------------------------------------------------
install_omh() {
    if command -v omh >/dev/null 2>&1; then
        echo "[✓] Oh My Hermes ya está instalado: $(omh --version 2>/dev/null | head -1 || true)"
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

install_hermes
install_omh

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
