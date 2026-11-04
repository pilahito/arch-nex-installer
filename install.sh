#!/usr/bin/env bash
# Instala Delta Setup en un Arch Linux ya instalado.
# Copia el script a /usr/local/bin/delta-setup y la configuración a /etc/delta-setup.
#
# Uso (como root):  sudo bash install.sh

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if (( EUID != 0 )); then
    echo "ERROR: ejecútalo como root: sudo bash install.sh" >&2
    exit 1
fi

if ! command -v whiptail >/dev/null 2>&1; then
    echo "==> Instalando libnewt (whiptail) para el menú"
    pacman -S --needed --noconfirm libnewt
fi

install -Dm755 "$DIR/delta-setup.sh" /usr/local/bin/delta-setup
install -Dm755 "$DIR/delta-optimizar.sh" /usr/local/bin/delta-optimizar
install -Dm644 "$DIR/config/apps.conf" /etc/delta-setup/apps.conf

echo "==> Instalado. Ejecuta: sudo delta-optimizar (ajustes) o delta-setup (apps)"
