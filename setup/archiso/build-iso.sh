#!/usr/bin/env bash
# Construye una ISO de Arch Linux con Nex Setup incluido.
#
# Parte del perfil "releng" oficial (paquete archiso), le añade los paquetes de
# packages.x86_64 y copia nex-setup y apps.conf dentro de la ISO.
#
# Uso (como root):  sudo bash archiso/build-iso.sh
# Requisitos: archiso instalado (pacman -S archiso) y unos 10 GB libres.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PERFIL_BASE=/usr/share/archiso/configs/releng
BUILD="$DIR/build"
PERFIL="$BUILD/perfil"
TRABAJO="$BUILD/trabajo"
SALIDA="$BUILD/salida"

error() {
    echo "ERROR: $*" >&2
    exit 1
}

(( EUID == 0 )) || error "Ejecútalo como root: sudo bash archiso/build-iso.sh"
command -v mkarchiso >/dev/null 2>&1 || error "Falta archiso. Instálalo con: pacman -S archiso"
[[ -d "$PERFIL_BASE" ]] || error "No encuentro el perfil base en $PERFIL_BASE"

echo "==> Preparando el perfil en $PERFIL"
rm -rf "$PERFIL" "$TRABAJO" "$SALIDA"
mkdir -p "$BUILD"
cp -r "$PERFIL_BASE" "$PERFIL"

echo "==> Añadiendo paquetes"
cat "$DIR/archiso/packages.x86_64" >> "$PERFIL/packages.x86_64"

echo "==> Copiando Nex Setup dentro de la ISO"
install -Dm755 "$DIR/nex-setup.sh" "$PERFIL/airootfs/usr/local/bin/nex-setup"
install -Dm644 "$DIR/config/apps.conf" "$PERFIL/airootfs/etc/nex-setup/apps.conf"

echo "==> Construyendo la ISO (puede tardar bastante)"
mkarchiso -v -w "$TRABAJO" -o "$SALIDA" "$PERFIL"

echo "==> Listo. ISO en: $SALIDA"
