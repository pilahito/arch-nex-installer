#!/usr/bin/env bash
# Comprueba nex-actualizar con un repositorio local y destinos descartables.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$DIR/setup/nex-actualizar.sh"
PRUEBA="$(mktemp -d "$DIR/.nex-actualizar-test.XXXXXX")"
trap 'rm -rf -- "$PRUEBA"' EXIT
ORIGEN="$PRUEBA/origen"
DESTINO="$PRUEBA/instalado"
mkdir -p "$ORIGEN/setup" "$DESTINO"
for archivo in nex-setup.sh nex_optimizador_gui.py nex_plan.py; do
    printf 'version nueva\n' > "$ORIGEN/setup/$archivo"
done
cp "$SCRIPT" "$ORIGEN/setup/nex-actualizar.sh"
git -C "$ORIGEN" init -q -b main
git -C "$ORIGEN" config user.name 'NEX Test'
git -C "$ORIGEN" config user.email 'nex-test@example.invalid'
git -C "$ORIGEN" add .
git -C "$ORIGEN" commit -qm 'Paquete NEX de prueba'
printf 'version vieja\n' > "$DESTINO/nex-setup.sh"
printf 'preferencias personales\n' > "$DESTINO/mi-config.conf"

export NEX_REPO_URL="$ORIGEN" NEX_BRANCH=main NEX_DESTINO="$DESTINO"
bash "$SCRIPT" --simular | grep -q 'simulación'
[[ "$(cat "$DESTINO/nex-setup.sh")" == 'version vieja' ]]
bash "$SCRIPT" --comprobar | grep -q 'Disponible:'
bash "$SCRIPT" >/dev/null
[[ "$(cat "$DESTINO/nex-setup.sh")" == 'version nueva' ]]
[[ -f "$DESTINO/VERSION" ]]
RESPALDO=("$DESTINO".anterior.*)
[[ -f "${RESPALDO[0]}/mi-config.conf" ]]
bash "$SCRIPT" | grep -q 'ya está actualizado'
echo 'OK: nex-actualizar conserva la versión anterior y usa el repositorio unificado.'
