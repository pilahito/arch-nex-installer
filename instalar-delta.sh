#!/usr/bin/env bash
# Delta Arch: instalador guiado en español.
# Se ejecuta desde el ISO oficial de Arch, como root, en modo UEFI.
#
#   bash instalar-delta.sh
#
# Pasos: elegir disco, confirmar el borrado, datos del equipo, tema, y después
# archinstall hace la instalación. Al final se aplica el tema Delta.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRABAJO="$(mktemp -d)"
chmod 700 "$TRABAJO"
# Las contraseñas y los ficheros de configuración se borran al salir
trap 'rm -rf "$TRABAJO"' EXIT

TITULO="DELTA ARCH · Instalador"
MONTAJE=/mnt

# Colores del tema Delta para los menús
export NEWT_COLORS='
root=white,black
window=white,black
border=cyan,black
title=cyan,black
button=black,cyan
actbutton=white,blue
checkbox=white,black
actcheckbox=black,cyan
listbox=white,black
actlistbox=black,cyan
textbox=white,black
acttextbox=black,cyan
entry=white,black
'

error() {
    echo "ERROR: $*" >&2
    exit 1
}

# Cancelar un cuadro de diálogo termina sin cambiar nada
cancelado() {
    echo "Instalación cancelada. No se ha tocado ningún disco."
    exit 0
}

# Muestra una pregunta de sí/no; devuelve 0 si se acepta
preguntar() {
    whiptail --title "$TITULO" --yesno "$1" 14 74
}

# Pide un texto con un valor por defecto y lo valida con una expresión regular.
# Devuelve 1 si se cancela (el que llama debe usar: X=$(pedir_texto ...) || cancelado)
pedir_texto() {
    local mensaje="$1" defecto="$2" patron="$3" valor
    while true; do
        valor=$(whiptail --title "$TITULO" --inputbox "$mensaje" 10 70 "$defecto" 3>&1 1>&2 2>&3) || return 1
        if [[ "$valor" =~ $patron ]]; then
            echo "$valor"
            return 0
        fi
        whiptail --title "$TITULO" --msgbox "Valor no válido. Prueba de nuevo." 8 50
    done
}

# Pide una contraseña dos veces hasta que coincidan (misma regla que pedir_texto)
pedir_password() {
    local mensaje="$1" uno dos
    while true; do
        uno=$(whiptail --title "$TITULO" --passwordbox "$mensaje" 10 70 3>&1 1>&2 2>&3) || return 1
        dos=$(whiptail --title "$TITULO" --passwordbox "Repite la contraseña:" 10 70 3>&1 1>&2 2>&3) || return 1
        if [[ -n "$uno" && "$uno" == "$dos" ]]; then
            echo "$uno"
            return 0
        fi
        whiptail --title "$TITULO" --msgbox "Las contraseñas no coinciden o están vacías." 8 60
    done
}

# --- Comprobaciones previas ---
(( EUID == 0 )) || error "Ejecútalo como root desde el ISO de Arch: sudo bash instalar-delta.sh"
for orden in whiptail python3 openssl archinstall arch-chroot lsblk mountpoint; do
    command -v "$orden" >/dev/null 2>&1 || error "Falta el comando '$orden'."
done
[[ -d /sys/firmware/efi ]] || error "Delta Arch solo funciona con arranque UEFI."

# --- 1. Disco ---
opciones=()
while read -r nombre tamano tipo modelo; do
    [[ "$tipo" == "disk" ]] || continue
    opciones+=("$nombre" "$tamano ${modelo:-disco}")
done < <(lsblk -dpno NAME,SIZE,TYPE,MODEL)
(( ${#opciones[@]} > 0 )) || error "No encuentro discos instalables."

DISCO=$(whiptail --title "$TITULO" --menu \
    "Elige el disco donde instalar Delta Arch.\nTODO su contenido se borrará." \
    18 78 8 "${opciones[@]}" 3>&1 1>&2 2>&3) || cancelado

TAMANO_MIB=$(( $(lsblk -bdno SIZE "$DISCO") / 1048576 ))

confirmacion=$(whiptail --title "$TITULO" --inputbox \
    "Para confirmar, escribe el nombre exacto del disco ($DISCO).\nSe borrarán todos sus datos." \
    12 74 "" 3>&1 1>&2 2>&3) || cancelado
[[ "$confirmacion" == "$DISCO" ]] || { whiptail --title "$TITULO" --msgbox "No coincide. No se ha borrado nada." 8 50; exit 0; }

# --- 2. Datos del equipo ---
HOST=$(pedir_texto "Nombre del equipo:" "delta-arch" '^[a-zA-Z0-9-]{1,63}$') || cancelado
USUARIO=$(pedir_texto "Nombre de tu usuario (minúsculas):" "delta" '^[a-z_][a-z0-9_-]{0,31}$') || cancelado
ZONA=$(pedir_texto "Zona horaria:" "Europe/Madrid" '^[A-Za-z_]+(/[A-Za-z_+-]+)*$') || cancelado
[[ -e "/usr/share/zoneinfo/$ZONA" ]] || error "La zona horaria '$ZONA' no existe."

PASS_USUARIO=$(pedir_password "Contraseña para $USUARIO:") || cancelado
PASS_ROOT=$(pedir_password "Contraseña para root:") || cancelado

# --- 3. Tema ---
TEMA=$(whiptail --title "$TITULO" --menu "Elige el tema de Delta Arch:" 14 60 4 \
    "oscuro" "Delta oscuro (fondo azul marino, acento cian)" \
    "claro" "Delta claro (fondo blanco, acento azul)" \
    3>&1 1>&2 2>&3) || cancelado

# --- 4. Resumen y confirmación final ---
preguntar "Resumen:

  Disco:        $DISCO ($TAMANO_MIB MiB) SE BORRARÁ
  Equipo:       $HOST
  Usuario:      $USUARIO (con sudo)
  Zona horaria: $ZONA
  Tema:         $TEMA
  Idioma:       Español (es_ES), teclado español

¿Empezar la instalación?" || cancelado

# --- 5. Generar la configuración para archinstall ---
DELTA_DISCO="$DISCO" \
DELTA_TAMANO_MIB="$TAMANO_MIB" \
DELTA_HOST="$HOST" \
DELTA_USUARIO="$USUARIO" \
DELTA_ZONA="$ZONA" \
DELTA_PASS_USUARIO="$PASS_USUARIO" \
DELTA_PASS_ROOT="$PASS_ROOT" \
python3 "$DIR/generar_config.py" "$TRABAJO"

unset PASS_USUARIO PASS_ROOT

# --- 6. Instalación con archinstall (sin más preguntas, ya confirmado aquí) ---
echo "==> Instalando Arch con archinstall..."
archinstall --config "$TRABAJO/config.json" --creds "$TRABAJO/creds.json" --silent

# --- 7. Aplicar el tema Delta al usuario dentro de la instalación ---
echo "==> Aplicando el tema Delta..."
# shellcheck disable=SC1091
source "$TRABAJO/particiones.env"

if ! mountpoint -q "$MONTAJE"; then
    mount "$DELTA_PART_RAIZ" "$MONTAJE"
fi
if ! mountpoint -q "$MONTAJE/boot"; then
    mount "$DELTA_PART_EFI" "$MONTAJE/boot"
fi

DESTINO="$MONTAJE/usr/local/share/delta"
mkdir -p "$DESTINO"
install -m755 "$DIR/post-instalacion/aplicar-tema.sh" "$DESTINO/aplicar-tema.sh"
cp -r "$DIR/tema" "$DESTINO/"
arch-chroot "$MONTAJE" /usr/local/share/delta/aplicar-tema.sh "$USUARIO" "$TEMA"

umount -R "$MONTAJE" 2>/dev/null || true

whiptail --title "$TITULO" --msgbox \
    "Delta Arch está instalado.\n\nQuita el USB y reinicia con:  reboot" 10 60
