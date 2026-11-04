#!/usr/bin/env bash
# Prueba de post-instalacion/aplicar-tema.sh sobre una raíz falsa (no toca el sistema).
# Uso: bash tests/test_aplicar_tema.sh

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DELTA_TEMA_DIR="$DIR/tema"
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
grep -q 'rgb(00d4ff)' "$CASA/.config/hypr/delta.conf" || fallo "acento oscuro no aplicado en Hyprland"
grep -q 'background #0b1020' "$CASA/.config/kitty/delta.conf" || fallo "fondo oscuro no aplicado en kitty"
grep -q '__' "$CASA/.config/hypr/delta.conf" && fallo "quedan marcadores sin sustituir"
grep -q 'source = ~/.config/hypr/delta.conf' "$CASA/.config/hypr/hyprland.conf" || fallo "Hyprland no enlaza el tema"
grep -q 'include delta.conf' "$CASA/.config/kitty/kitty.conf" || fallo "kitty no incluye el tema"
[[ -f "$CASA/LEEME-DELTA.txt" ]] || fallo "falta LEEME-DELTA.txt"

# 2. Ejecutar otra vez no debe duplicar los enlaces
bash "$SCRIPT" tester claro "$RAIZ" >/dev/null
enlaces=$(grep -c 'delta.conf' "$CASA/.config/hypr/hyprland.conf")
[[ "$enlaces" == "1" ]] || fallo "el enlace de Hyprland se duplicó ($enlaces)"
grep -q 'background #f5f7fa' "$CASA/.config/kitty/delta.conf" || fallo "tema claro no aplicado"

# 3. Paleta inexistente debe fallar
if bash "$SCRIPT" tester inexistente "$RAIZ" >/dev/null 2>&1; then
    fallo "una paleta inexistente no dio error"
fi

echo "OK: aplicar-tema.sh pasa todas las pruebas."
