#!/usr/bin/env bash
# Instala Nex Setup en un Arch Linux ya instalado.
# Copia el script a /usr/local/bin/nex-setup y la configuración a /etc/nex-setup.
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

install -Dm755 "$DIR/nex-setup.sh" /usr/local/bin/nex-setup
install -Dm755 "$DIR/nex-optimizar.sh" /usr/local/bin/nex-optimizar
install -Dm644 "$DIR/config/apps.conf" /etc/nex-setup/apps.conf

echo "==> Instalado. Ejecuta: sudo nex-optimizar (ajustes) o nex-setup (apps)"
