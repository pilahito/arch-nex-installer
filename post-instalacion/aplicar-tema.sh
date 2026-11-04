#!/usr/bin/env bash
# Aplica el tema Delta al usuario indicado. Se ejecuta dentro de la instalación
# (arch-chroot), desde el instalador, o con DELTA_RAIZ para pruebas.
#
# Uso:  aplicar-tema.sh USUARIO PALETA [RAIZ]
#   PALETA  oscuro | claro
#   RAIZ    carpeta raíz del sistema (vacía dentro de arch-chroot)
#
# Variables opcionales:
#   DELTA_TEMA_DIR  carpeta con paletas y plantillas (por defecto: ./tema junto al script)

set -euo pipefail

error() {
    echo "ERROR: $*" >&2
    exit 1
}

(( $# >= 2 )) || error "Uso: aplicar-tema.sh USUARIO PALETA [RAIZ]"
USUARIO="$1"
PALETA="$2"
RAIZ="${3:-}"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMA_DIR="${DELTA_TEMA_DIR:-$DIR/tema}"

PALETA_FILE="$TEMA_DIR/paletas/$PALETA.env"
[[ -f "$PALETA_FILE" ]] || error "No existe la paleta '$PALETA'."
# shellcheck disable=SC1090
source "$PALETA_FILE"

CASA="$RAIZ/home/$USUARIO"
CONF="$CASA/.config"
mkdir -p "$CONF/hypr" "$CONF/kitty"

# Sustituye los marcadores de color de una plantilla y guarda el resultado
generar() {
    sed -e "s/__FONDO__/$FONDO/g" -e "s/__ACENTO__/$ACENTO/g" -e "s/__TEXTO__/$TEXTO/g" "$1" > "$2"
}

generar "$TEMA_DIR/plantillas/hyprland-delta.conf" "$CONF/hypr/delta.conf"
generar "$TEMA_DIR/plantillas/kitty-delta.conf" "$CONF/kitty/delta.conf"

# Enlaza el tema desde la configuración del usuario si ya existe
if [[ -f "$CONF/hypr/hyprland.conf" ]] && ! grep -q 'delta.conf' "$CONF/hypr/hyprland.conf"; then
    echo 'source = ~/.config/hypr/delta.conf' >> "$CONF/hypr/hyprland.conf"
fi
if [[ -f "$CONF/kitty/kitty.conf" ]] && ! grep -q 'delta.conf' "$CONF/kitty/kitty.conf"; then
    echo 'include delta.conf' >> "$CONF/kitty/kitty.conf"
fi

# Nota de bienvenida en español
cat > "$CASA/LEEME-DELTA.txt" <<EOF
Bienvenido a Delta Arch.

Tema instalado: $NOMBRE
Colores del tema: ~/.config/hypr/delta.conf y ~/.config/kitty/delta.conf
Para cambiarlos, edita esos archivos y recarga Hyprland con: hyprctl reload

Para instalar más aplicaciones usa: delta-setup
EOF

# Si el usuario ya existe en este sistema, dejamos los ficheros a su nombre
if id "$USUARIO" >/dev/null 2>&1; then
    chown -R "$USUARIO:$USUARIO" "$CASA"
fi

echo "Tema '$NOMBRE' aplicado a $USUARIO."
