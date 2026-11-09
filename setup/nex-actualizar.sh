#!/usr/bin/env bash
# Actualiza Nex Setup desde el repositorio unificado de NEX OS.
# --comprobar consulta la versión; --simular no descarga ni modifica archivos.
set -euo pipefail

REPO="${NEX_REPO_URL:-https://github.com/pilahito/arch-nex-installer.git}"
RAMA="${NEX_BRANCH:-feature/nex-rescue-foundation}"
DESTINO="${NEX_DESTINO:-/usr/local/share/nex-setup}"
MODO="instalar"

for arg in "$@"; do
    case "$arg" in
        --comprobar) MODO="comprobar" ;;
        --simular) MODO="simular" ;;
        -h|--help)
            echo 'Uso: nex-actualizar [--comprobar|--simular]'
            exit 0 ;;
        *) echo "Opción desconocida: $arg" >&2; exit 1 ;;
    esac
done

[[ "$DESTINO" == /* && "$DESTINO" != / && "$DESTINO" != */.. && "$DESTINO" != */../* ]] || {
    echo 'Destino de actualización no válido.' >&2; exit 1;
}

if [[ "$MODO" == simular ]]; then
    echo "[simulación] Consultaría $REPO ($RAMA) y copiaría setup/ a $DESTINO"
    exit 0
fi

command -v git >/dev/null || { echo 'Falta git.' >&2; exit 1; }
TRABAJO="$(mktemp -d)"
trap 'rm -rf -- "$TRABAJO"' EXIT
git clone --depth 1 --branch "$RAMA" --quiet "$REPO" "$TRABAJO/repo" || {
    echo 'No se pudo descargar el repositorio unificado.' >&2; exit 1;
}

ORIGEN="$TRABAJO/repo/setup"
for archivo in nex-setup.sh nex_optimizador_gui.py nex_plan.py nex-actualizar.sh; do
    [[ -f "$ORIGEN/$archivo" ]] || {
        echo "El repositorio unificado no contiene setup/$archivo." >&2; exit 1;
    }
done

NUEVA="$(git -C "$TRABAJO/repo" rev-parse HEAD)"
ACTUAL="$(cat "$DESTINO/VERSION" 2>/dev/null || true)"
if [[ "$MODO" == comprobar ]]; then
    echo "Instalada: ${ACTUAL:-desconocida}"
    echo "Disponible: $NUEVA"
    exit 0
fi
if [[ "$ACTUAL" == "$NUEVA" ]]; then
    echo 'Nex Setup ya está actualizado.'
    exit 0
fi
if [[ "$DESTINO" == /usr/local/share/* ]] && (( EUID != 0 )); then
    echo 'Ejecuta la actualización con sudo.' >&2
    exit 1
fi

PADRE="$(dirname "$DESTINO")"
[[ -d "$PADRE" && ! -L "$DESTINO" ]] || {
    echo 'El destino no existe o es un enlace simbólico.' >&2; exit 1;
}
ETAPA="$(mktemp -d "$PADRE/.nex-setup-nuevo.XXXXXX")"
RESPALDO="${DESTINO}.anterior.$(date +%Y%m%d%H%M%S)"
trap 'rm -rf -- "$TRABAJO" "$ETAPA"' EXIT
cp -a "$ORIGEN/." "$ETAPA/"
printf '%s\n' "$NUEVA" > "$ETAPA/VERSION"
if [[ -d "$DESTINO" ]]; then
    mv -- "$DESTINO" "$RESPALDO"
fi
if ! mv -- "$ETAPA" "$DESTINO"; then
    if [[ -d "$RESPALDO" ]]; then mv -- "$RESPALDO" "$DESTINO"; fi
    echo 'No se pudo activar la actualización; se restauró la versión anterior.' >&2
    exit 1
fi
echo "Nex Setup actualizado a $NUEVA. Copia anterior: $RESPALDO"
