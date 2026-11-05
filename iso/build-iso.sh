#!/usr/bin/env bash
# Construye la ISO de Arch con la opción Nex Arch ya incluida.
#
# Parte del perfil oficial "releng" (paquete archiso) y le añade:
#   - el instalador guiado en /root/nex-installer
#   - arranque automático del instalador en tty1
#   - etiquetas del menú de arranque en español
#
# Uso (como root, dentro de la distro Arch):
#   bash iso/build-iso.sh
# Variables opcionales:
#   SALIDA      carpeta donde queda la ISO (por defecto /mnt/d/ISO-NEX)
#   BUILD_DIR   carpeta de trabajo, en ext4 (por defecto /var/tmp/nex-iso)

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PERFIL_BASE=/usr/share/archiso/configs/releng
BUILD="${BUILD_DIR:-/var/tmp/nex-iso}"
PERFIL="$BUILD/perfil"
TRABAJO="$BUILD/trabajo"
SALIDA="${SALIDA:-/mnt/d/ISO-NEX}"

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
sed -i 's/Arch Linux install medium/Nex Arch · instalador/g' \
    "$PERFIL"/syslinux/*.cfg "$PERFIL"/grub/*.cfg "$PERFIL"/efiboot/loader/entries/*.conf

echo "==> Identidad de la ISO"
sed -i \
    -e 's/^iso_name=.*/iso_name="nex-arch"/' \
    -e 's/^iso_application=.*/iso_application="Nex Arch instalador"/' \
    -e 's/^iso_publisher=.*/iso_publisher="Nex Arch"/' \
    "$PERFIL/profiledef.sh"

echo "==> Paquetes adicionales"
cat "$DIR/iso/packages.x86_64" >> "$PERFIL/packages.x86_64"

echo "==> Instalador y arranque automático"
INSTALADOR="$PERFIL/airootfs/root/nex-installer"
mkdir -p "$INSTALADOR"
install -m755 "$DIR/instalar-nex.sh" "$INSTALADOR/instalar-nex.sh"
install -m755 "$DIR/generar_config.py" "$INSTALADOR/generar_config.py"
install -m755 "$DIR/nex_instalador.py" "$INSTALADOR/nex_instalador.py"
install -m755 "$DIR/nex_installer_gui.py" "$INSTALADOR/nex_installer_gui.py"
install -m755 "$DIR/iso/nex-start-gui.sh" "$INSTALADOR/nex-start-gui.sh"
cp -r "$DIR/post-instalacion" "$DIR/tema" "$INSTALADOR/"
install -m755 "$DIR/iso/airootfs/root/.automated_script.sh" "$PERFIL/airootfs/root/.automated_script.sh"

echo "==> Nex Setup (optimizador, menú de apps y asistente gráfico) dentro de la ISO"
SETUP="${NEX_SETUP_DIR:-$DIR/setup}"
[[ -f "$SETUP/nex_optimizador_gui.py" ]] || error "No encuentro Nex Setup en $SETUP (define NEX_SETUP_DIR)"
mkdir -p "$INSTALADOR/nex-setup"
tar -C "$SETUP" --exclude=./.git --exclude=./tests --exclude=./docs --exclude=./__pycache__ -cf - . \
    | tar -C "$INSTALADOR/nex-setup" -xf -

echo "==> Comandos en la ISO"
mkdir -p "$PERFIL/airootfs/usr/local/bin"
printf '#!/usr/bin/env bash\nexec bash /root/nex-installer/nex-setup/nex-setup.sh "$@"\n' \
    > "$PERFIL/airootfs/usr/local/bin/nex-setup"
printf '#!/usr/bin/env bash\nexec bash /root/nex-installer/nex-setup/nex-optimizar.sh "$@"\n' \
    > "$PERFIL/airootfs/usr/local/bin/nex-optimizar"
chmod 755 "$PERFIL/airootfs/usr/local/bin/nex-setup" "$PERFIL/airootfs/usr/local/bin/nex-optimizar"

echo "==> Permisos de los ficheros del instalador"
sed -i '/^file_permissions=(/a\
  ["/root/nex-installer/instalar-nex.sh"]="0:0:755"\
  ["/root/nex-installer/generar_config.py"]="0:0:755"\
  ["/root/nex-installer/nex_instalador.py"]="0:0:755"\
  ["/root/nex-installer/nex_installer_gui.py"]="0:0:755"\
  ["/root/nex-installer/nex-start-gui.sh"]="0:0:755"\
  ["/root/nex-installer/post-instalacion/aplicar-tema.sh"]="0:0:755"\
  ["/root/nex-installer/nex-setup/nex-setup.sh"]="0:0:755"\
  ["/root/nex-installer/nex-setup/nex-optimizar.sh"]="0:0:755"\
  ["/root/nex-installer/nex-setup/nex_optimizador_gui.py"]="0:0:755"\
  ["/root/nex-installer/nex-setup/nex_plan.py"]="0:0:755"\
  ["/usr/local/bin/nex-setup"]="0:0:755"\
  ["/usr/local/bin/nex-optimizar"]="0:0:755"' "$PERFIL/profiledef.sh"

echo "==> Construyendo la ISO (tarda bastante: descarga paquetes)"
mkarchiso -v -w "$TRABAJO" -o "$SALIDA" "$PERFIL"

echo "==> Listo. ISO en: $SALIDA"
