#!/usr/bin/env bash
# VirtualBox-Rober-postinstalacion.sh
# Actualiza Ubuntu y muestra datos de validación. No toca particiones.
set -Eeuo pipefail
echo "========== UBUNTU =========="
if ! command -v lsb_release >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y lsb-release
fi
lsb_release -a || true
echo "========== ACTUALIZACIÓN =========="
sudo apt-get update
sudo apt-get full-upgrade -y
echo "========== HERRAMIENTAS Y HEADERS =========="
sudo apt-get install -y build-essential dkms linux-headers-"$(uname -r)" curl wget git
echo "========== HARDWARE INVITADO =========="
printf 'Kernel: '; uname -r
printf 'CPU virtuales: '; nproc
free -h
df -h /
echo "========== RED =========="
ip -brief address || true
ip route || true
echo "========== GUEST ADDITIONS =========="
lsmod | grep -E 'vboxguest|vboxsf|vboxvideo' || echo "No se detectan módulos VBox cargados."
echo "========== GRUPOS =========="
id
echo "Terminado. Reinicia si se han instalado actualizaciones del kernel."
