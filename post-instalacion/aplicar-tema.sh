#!/usr/bin/env bash
# Aplica el tema Nex al usuario indicado. Se ejecuta dentro de la instalación
# (arch-chroot), desde el instalador, o con NEX_RAIZ para pruebas.
#
# Uso:  aplicar-tema.sh USUARIO PALETA [RAIZ]
#   PALETA  identificador de tema/paletas/*.env
#   RAIZ    carpeta raíz del sistema (vacía dentro de arch-chroot)
#
# Variables opcionales:
#   NEX_TEMA_DIR  carpeta con paletas y plantillas (por defecto: ./tema junto al script)

set -euo pipefail

error() {
    echo "ERROR: $*" >&2
    exit 1
}

(( $# >= 2 )) || error "Uso: aplicar-tema.sh USUARIO PALETA [RAIZ]"
USUARIO="$1"
PALETA="$2"
RAIZ="${3:-}"
[[ "$PALETA" =~ ^[a-z0-9-]+$ ]] || error "Identificador de paleta no válido."

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMA_DIR="${NEX_TEMA_DIR:-$DIR/tema}"

PALETA_FILE="$TEMA_DIR/paletas/$PALETA.env"
[[ -f "$PALETA_FILE" ]] || error "No existe la paleta '$PALETA'."
# shellcheck disable=SC1090
source "$PALETA_FILE"

CASA="$RAIZ/home/$USUARIO"
CONF="$CASA/.config"
mkdir -p "$CONF/hypr" "$CONF/kitty" "$CONF/waybar"

# Colores opcionales: si una paleta no los define, se usan los principales
: "${PANEL:=$FONDO}"
: "${ACENTO2:=$ACENTO}"
: "${ACENTO3:=$ACENTO}"

# Sustituye los marcadores de color de una plantilla y guarda el resultado
generar() {
    sed -e "s/__FONDO__/$FONDO/g" -e "s/__PANEL__/$PANEL/g" \
        -e "s/__ACENTO__/$ACENTO/g" -e "s/__ACENTO2__/$ACENTO2/g" -e "s/__ACENTO3__/$ACENTO3/g" \
        -e "s/__TEXTO__/$TEXTO/g" "$1" > "$2"
}

# Guarda una copia de un fichero que ya existía antes de sobrescribirlo
respaldar() {
    if [[ -f "$1" ]]; then
        cp "$1" "$1.bak-nex"
    fi
}

generar "$TEMA_DIR/plantillas/hyprland-nex.conf" "$CONF/hypr/nex.conf"
generar "$TEMA_DIR/plantillas/kitty-nex.conf" "$CONF/kitty/nex.conf"

# Barra Waybar: reloj, CPU y RAM con los colores del tema (se respalda la anterior)
respaldar "$CONF/waybar/config.jsonc"
respaldar "$CONF/waybar/style.css"
generar "$TEMA_DIR/plantillas/waybar-config.jsonc" "$CONF/waybar/config.jsonc"
generar "$TEMA_DIR/plantillas/waybar-style.css" "$CONF/waybar/style.css"

# Fondo local y reproducible: cada paleta tiene un PNG propio en el repositorio.
FONDO_ORIGEN="$TEMA_DIR/fondos/$PALETA.png"
if [[ -f "$FONDO_ORIGEN" ]]; then
    FONDO_DESTINO="$CASA/.local/share/nex/fondos/$PALETA.png"
    mkdir -p "$(dirname "$FONDO_DESTINO")"
    cp "$FONDO_ORIGEN" "$FONDO_DESTINO"
    respaldar "$CONF/hypr/hyprpaper.conf"
    printf 'preload = %s\nwallpaper = ,%s\n' \
        "/home/$USUARIO/.local/share/nex/fondos/$PALETA.png" \
        "/home/$USUARIO/.local/share/nex/fondos/$PALETA.png" \
        > "$CONF/hypr/hyprpaper.conf"
fi

# Enlaza el tema desde la configuración del usuario si ya existe
if [[ -f "$CONF/hypr/hyprland.conf" ]] && ! grep -q 'nex.conf' "$CONF/hypr/hyprland.conf"; then
    echo 'source = ~/.config/hypr/nex.conf' >> "$CONF/hypr/hyprland.conf"
fi
if [[ -f "$CONF/kitty/kitty.conf" ]] && ! grep -q 'nex.conf' "$CONF/kitty/kitty.conf"; then
    echo 'include nex.conf' >> "$CONF/kitty/kitty.conf"
fi

# Nota de bienvenida en español
cat > "$CASA/LEEME-NEX.txt" <<EOF
Bienvenido a Nex Arch.

Tema instalado: $NOMBRE
Colores del tema: ~/.config/hypr/nex.conf y ~/.config/kitty/nex.conf
Para cambiarlos, edita esos archivos y recarga Hyprland con: hyprctl reload
Otros diseños disponibles: $(find "$TEMA_DIR/paletas" -maxdepth 1 -name '*.env' -printf '%f ' | sed 's/\.env//g')

Para instalar más aplicaciones usa: nex-setup
EOF

# Si el usuario ya existe en este sistema, dejamos los ficheros a su nombre
if (( EUID == 0 )) && id "$USUARIO" >/dev/null 2>&1; then
    chown "$USUARIO:$USUARIO" "$CONF/hypr/nex.conf" "$CONF/kitty/nex.conf" \
        "$CONF/waybar/config.jsonc" "$CONF/waybar/style.css" "$CASA/LEEME-NEX.txt"
    if [[ -f "${FONDO_DESTINO:-}" ]]; then
        chown "$USUARIO:$USUARIO" "$FONDO_DESTINO" "$CONF/hypr/hyprpaper.conf"
    fi
fi

echo "Tema '$NOMBRE' aplicado a $USUARIO."
