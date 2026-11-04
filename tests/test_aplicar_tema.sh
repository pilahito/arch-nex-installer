#!/usr/bin/env bash
# Prueba de post-instalacion/aplicar-tema.sh sobre una raíz falsa (no toca el sistema).
# Uso: bash tests/test_aplicar_tema.sh

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEX_TEMA_DIR="$DIR/tema"
SCRIPT="$DIR/post-instalacion/aplicar-tema.sh"

RAIZ="$(mktemp -d)"
trap 'rm -rf "$RAIZ"' EXIT

fallo() {
    echo "FALLO: $*" >&2
    exit 1
}

CASA="$RAIZ/home/tester"
mkdir -p "$CASA/.config/hypr" "$CASA/.config/kitty"
echo "monitor=,preferred,auto,1" > "$CASA/.config/hypr/hyprland.conf"
echo "font_size 12" > "$CASA/.config/kitty/kitty.conf"

# 1. Tema oscuro
bash "$SCRIPT" tester oscuro "$RAIZ" >/dev/null
grep -q 'rgb(00d4ff)' "$CASA/.config/hypr/nex.conf" || fallo "acento oscuro no aplicado en Hyprland"
grep -q 'background #0b1020' "$CASA/.config/kitty/nex.conf" || fallo "fondo oscuro no aplicado en kitty"
grep -q '__' "$CASA/.config/hypr/nex.conf" && fallo "quedan marcadores sin sustituir"
grep -q 'source = ~/.config/hypr/nex.conf' "$CASA/.config/hypr/hyprland.conf" || fallo "Hyprland no enlaza el tema"
grep -q 'include nex.conf' "$CASA/.config/kitty/kitty.conf" || fallo "kitty no incluye el tema"
[[ -f "$CASA/LEEME-NEX.txt" ]] || fallo "falta LEEME-NEX.txt"

# 2. Ejecutar otra vez no debe duplicar los enlaces
bash "$SCRIPT" tester claro "$RAIZ" >/dev/null
enlaces=$(grep -c 'nex.conf' "$CASA/.config/hypr/hyprland.conf")
[[ "$enlaces" == "1" ]] || fallo "el enlace de Hyprland se duplicó ($enlaces)"
grep -q 'background #f5f7fa' "$CASA/.config/kitty/nex.conf" || fallo "tema claro no aplicado"

# 3. Paleta neón: colores de la captura y barra Waybar
bash "$SCRIPT" tester neon "$RAIZ" >/dev/null
grep -q 'rgb(ff2fb3)' "$CASA/.config/hypr/nex.conf" || fallo "acento 2 neón no aplicado"
grep -q 'exec-once = waybar' "$CASA/.config/hypr/nex.conf" || fallo "Hyprland no arranca Waybar"
grep -q '"clock"' "$CASA/.config/waybar/config.jsonc" || fallo "falta el reloj en Waybar"
grep -q '#2ee6ff' "$CASA/.config/waybar/style.css" || fallo "color cian no aplicado en Waybar"
grep -q '__' "$CASA/.config/waybar/style.css" && fallo "quedan marcadores en Waybar"

# 4. Paleta inexistente debe fallar
if bash "$SCRIPT" tester inexistente "$RAIZ" >/dev/null 2>&1; then
    fallo "una paleta inexistente no dio error"
fi

echo "OK: aplicar-tema.sh pasa todas las pruebas."
