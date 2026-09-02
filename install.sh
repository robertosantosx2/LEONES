#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "============================================================"
echo "LEONES — MINIMAL INSTALL"
echo "============================================================"

fail() { echo "[✗] $1"; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "Python 3 no está instalado."
command -v git >/dev/null 2>&1 || fail "Git no está instalado."

python3 - <<'PY' || exit 1
import sys
if sys.version_info < (3, 10):
    print("[✗] LEONES RC2 requiere Python 3.10 o superior.")
    raise SystemExit(1)
print(f"[✓] Python {sys.version.split()[0]}")
PY

echo "[✓] Git $(git --version | awk '{print $3}')"

if command -v llmfit >/dev/null 2>&1; then
    echo "[✓] LLMFit $(llmfit --version 2>/dev/null | head -1 || true)"
else
    echo "[!] LLMFit no está instalado."
    echo "    LEONES no instala ni sustituye LLMFit: es una dependencia externa canónica."
    echo
    echo "    Instálalo primero (Linux, sin sudo):"
    echo "      curl -fsSL https://llmfit.axjns.dev/install.sh | sh -s -- --local"
    echo
    echo "    Luego asegúrate de que esté en el PATH:"
    echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "      command -v llmfit"
    echo
    echo "    Docs: https://www.llmfit.org/"
    echo "    Repo: https://github.com/AlexsJones/llmfit"
    echo "    Guía LEONES: INSTALL.md · web/inicio-rapido.html"
    echo
    echo "    Cuando llmfit esté disponible, vuelve a ejecutar ./install.sh."
    exit 2
fi

chmod +x "$ROOT/leones" "$ROOT/scripts/rc2_wizard.py" 2>/dev/null || true

echo
echo "[✓] Instalación mínima preparada."
echo "[i] No se crea un entorno virtual ni se instalan stacks/modelos automáticamente."
echo "[i] Ejecuta: ./leones"
