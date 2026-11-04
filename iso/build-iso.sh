#!/usr/bin/env bash
# Construye la ISO de Arch con la opción Delta Arch ya incluida.
#
# Parte del perfil oficial "releng" (paquete archiso) y le añade:
#   - el instalador guiado en /root/delta-installer
#   - arranque automático del instalador en tty1
#   - etiquetas del menú de arranque en español
#
# Uso (como root, dentro de la distro Arch):
#   bash iso/build-iso.sh
# Variables opcionales:
#   SALIDA      carpeta donde queda la ISO (por defecto /mnt/d/ISO-DELTA)
#   BUILD_DIR   carpeta de trabajo, en ext4 (por defecto /var/tmp/delta-iso)

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PERFIL_BASE=/usr/share/archiso/configs/releng
BUILD="${BUILD_DIR:-/var/tmp/delta-iso}"
PERFIL="$BUILD/perfil"
TRABAJO="$BUILD/trabajo"
SALIDA="${SALIDA:-/mnt/d/ISO-DELTA}"

error() {
    echo "ERROR: $*" >&2
    exit 1
}

(( EUID == 0 )) || error "Ejecútalo como root."
command -v mkarchiso >/dev/null 2>&1 || error "Falta archiso: pacman -S archiso"
[[ -d "$PERFIL_BASE" ]] || error "No encuentro el perfil base en $PERFIL_BASE"

echo "==> Preparando el perfil en $PERFIL"
rm -rf "$PERFIL" "$TRABAJO"
mkdir -p "$BUILD" "$SALIDA"
cp -r "$PERFIL_BASE" "$PERFIL"

echo "==> Etiquetas del menú de arranque en español"
sed -i 's/Arch Linux install medium/Delta Arch · instalador/g' \
    "$PERFIL"/syslinux/*.cfg "$PERFIL"/grub/*.cfg "$PERFIL"/efiboot/loader/entries/*.conf

echo "==> Identidad de la ISO"
sed -i \
    -e 's/^iso_name=.*/iso_name="delta-arch"/' \
    -e 's/^iso_application=.*/iso_application="Delta Arch instalador"/' \
    -e 's/^iso_publisher=.*/iso_publisher="Delta Arch"/' \
    "$PERFIL/profiledef.sh"

echo "==> Paquetes adicionales"
cat "$DIR/iso/packages.x86_64" >> "$PERFIL/packages.x86_64"

echo "==> Instalador y arranque automático"
INSTALADOR="$PERFIL/airootfs/root/delta-installer"
mkdir -p "$INSTALADOR"
install -m755 "$DIR/instalar-delta.sh" "$INSTALADOR/instalar-delta.sh"
install -m755 "$DIR/generar_config.py" "$INSTALADOR/generar_config.py"
cp -r "$DIR/post-instalacion" "$DIR/tema" "$INSTALADOR/"
install -m755 "$DIR/iso/airootfs/root/.automated_script.sh" "$PERFIL/airootfs/root/.automated_script.sh"

echo "==> Permisos de los ficheros del instalador"
sed -i '/^file_permissions=(/a\
  ["/root/delta-installer/instalar-delta.sh"]="0:0:755"\
  ["/root/delta-installer/generar_config.py"]="0:0:755"\
  ["/root/delta-installer/post-instalacion/aplicar-tema.sh"]="0:0:755"' "$PERFIL/profiledef.sh"

echo "==> Construyendo la ISO (tarda bastante: descarga paquetes)"
mkarchiso -v -w "$TRABAJO" -o "$SALIDA" "$PERFIL"

echo "==> Listo. ISO en: $SALIDA"
