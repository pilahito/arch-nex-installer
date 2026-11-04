#!/usr/bin/env bash
# Nex Arch: lanza el instalador de pantalla completa (nex_instalador.py).
# Se ejecuta desde el ISO oficial de Arch, como root, en modo UEFI.
#
#   sudo bash instalar-nex.sh
#
# Opciones que se pasan al instalador:  --simular  (recorre las pantallas sin tocar discos)

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v python3 >/dev/null 2>&1 || { echo "ERROR: falta python3." >&2; exit 1; }

exec python3 "$DIR/nex_instalador.py" "$@"
