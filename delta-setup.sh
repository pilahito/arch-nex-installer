#!/usr/bin/env bash
# Delta Setup para Arch Linux: un menú tipo "Delta Assistant" para elegir
# las apps que quieres instalar. Las apps se configuran en config/apps.conf.
#
# Uso:
#   delta-setup.sh                 menú interactivo (por defecto)
#   delta-setup.sh --list          muestra las apps configuradas
#   delta-setup.sh --dry-run       muestra qué instalaría sin instalar nada
#   delta-setup.sh --select a,b    instala esas apps sin menú
#   delta-setup.sh --config RUTA   usa otro archivo de configuración
#   delta-setup.sh --help          muestra esta ayuda

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Orden para buscar la configuración: variable DELTA_CONFIG, carpeta del proyecto
# o la copia instalada en el sistema (/etc/delta-setup/apps.conf, usada por la ISO)
if [[ -n "${DELTA_CONFIG:-}" ]]; then
    CONFIG="$DELTA_CONFIG"
elif [[ -f "$DIR/config/apps.conf" ]]; then
    CONFIG="$DIR/config/apps.conf"
else
    CONFIG="/etc/delta-setup/apps.conf"
fi
MODO="menu"
SIMULAR=0
SELECCION_MANUAL=""

# Colores del tema "Delta" para el menú (fondo oscuro, acento cian)
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

uso() {
    sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

error() {
    echo "ERROR: $*" >&2
    exit 1
}

# Quita espacios al principio y al final de un texto
recortar() {
    local v="$1"
    v="${v#"${v%%[![:space:]]*}"}"
    v="${v%"${v##*[![:space:]]}"}"
    printf '%s' "$v"
}

# Lee el archivo de configuración y muestra una línea por app:
#   categoría|paquete|nombre|origen|estado
leer_config() {
    local categoria="" linea pkg nombre origen estado
    while IFS= read -r linea || [[ -n "$linea" ]]; do
        linea="${linea%%#*}"
        linea="$(recortar "$linea")"
        [[ -z "$linea" ]] && continue

        if [[ "$linea" =~ ^\[(.+)\]$ ]]; then
            categoria="${BASH_REMATCH[1]}"
            continue
        fi

        IFS='|' read -r pkg nombre origen estado <<< "$linea"
        pkg="$(recortar "${pkg:-}")"
        nombre="$(recortar "${nombre:-$pkg}")"
        origen="$(recortar "${origen:-pacman}")"
        estado="$(recortar "${estado:-off}")"

        [[ -z "$pkg" ]] && continue
        echo "$categoria|$pkg|$nombre|$origen|$estado"
    done < "$CONFIG"
}

listar() {
    printf '%-14s %-18s %-28s %-7s %s\n' "CATEGORÍA" "PAQUETE" "NOMBRE" "ORIGEN" "DEFECTO"
    while IFS='|' read -r cat pkg nombre origen estado; do
        printf '%-14s %-18s %-28s %-7s %s\n' "$cat" "$pkg" "$nombre" "$origen" "$estado"
    done < <(leer_config)
}

# Muestra el menú de selección y devuelve los paquetes elegidos (uno por línea)
mostrar_menu() {
    local -a opciones=()
    local cat pkg nombre origen estado marca resultado
    while IFS='|' read -r cat pkg nombre origen estado; do
        marca="OFF"
        [[ "$estado" == "on" ]] && marca="ON"
        opciones+=("$pkg" "[$cat] $nombre ($origen)" "$marca")
    done < <(leer_config)

    local total=${#opciones[@]}
    local alto=$(( total / 3 + 10 ))
    (( alto > 24 )) && alto=24

    # whiptail escribe la selección por el descriptor 2; la recogemos aquí
    resultado=$(whiptail --title "DELTA ASSISTANT · Arch Edition" \
        --checklist "Selecciona las aplicaciones que quieres instalar en tu sistema:" \
        "$alto" 78 $(( alto - 8 )) \
        "${opciones[@]}" 3>&1 1>&2 2>&3) || return 1

    # whiptail devuelve los nombres entre comillas: "steam" "lutris"
    tr -d '"' <<< "$resultado" | tr ' ' '\n' | sed '/^$/d'
}

# Ejecuta un comando (o solo lo muestra si estamos en simulación)
ejecutar() {
    if (( SIMULAR )); then
        echo "[simulación] $*"
    else
        "$@"
    fi
}

# Instala yay (ayudante de AUR) compilándolo desde el AUR si no está presente
asegurar_yay() {
    command -v yay >/dev/null 2>&1 && return 0
    if (( EUID == 0 && SIMULAR == 0 )); then
        error "Instalar yay necesita tu usuario normal, no root."
    fi

    echo "==> Instalando yay desde el AUR"
    if (( SIMULAR )); then
        echo "[simulación] git clone https://aur.archlinux.org/yay.git && makepkg -si"
        return 0
    fi

    local tmp
    tmp="$(mktemp -d)"
    git clone https://aur.archlinux.org/yay.git "$tmp/yay"
    (cd "$tmp/yay" && makepkg -si --noconfirm)
    rm -rf "$tmp"
}

# Instala HyDE (dotfiles de Hyprland) con su script oficial.
# Es interactivo y tarda 20-30 min. Solo tiene sentido en un Arch real con escritorio.
instalar_hyde() {
    local destino="$HOME/HyDE"

    if (( EUID == 0 && SIMULAR == 0 )); then
        error "HyDE no se instala como root. Ejecuta el script como tu usuario normal."
    fi
    echo "AVISO: HyDE necesita un Arch real con sesión gráfica. En WSL no se verá el escritorio." >&2

    ejecutar sudo pacman -S --needed --noconfirm git base-devel wget curl
    asegurar_yay

    if [[ ! -d "$destino/.git" ]]; then
        ejecutar git clone --depth 1 https://github.com/HyDE-Project/HyDE "$destino"
    fi

    if (( SIMULAR )); then
        echo "[simulación] (cd $destino/Scripts && ./install.sh)"
    else
        (cd "$destino/Scripts" && ./install.sh)
    fi
}

instalar() {
    local -a seleccion=("$@")
    local -a repos=() aur=()
    local cat pkg nombre origen estado existe quiere_hyde=0

    for elegido in "${seleccion[@]}"; do
        existe=0
        while IFS='|' read -r cat pkg nombre origen estado; do
            if [[ "$pkg" == "$elegido" ]]; then
                existe=1
                case "$origen" in
                    aur)  aur+=("$pkg") ;;
                    hyde) quiere_hyde=1 ;;
                    *)    repos+=("$pkg") ;;
                esac
            fi
        done < <(leer_config)
        (( existe )) || echo "AVISO: '$elegido' no está en $CONFIG, se omite." >&2
    done

    if (( ${#repos[@]} == 0 && ${#aur[@]} == 0 && quiere_hyde == 0 )); then
        echo "No hay nada que instalar."
        return 0
    fi

    if (( ${#repos[@]} > 0 )); then
        local -a prefijo=()
        (( EUID == 0 )) || prefijo=(sudo)
        ejecutar "${prefijo[@]}" pacman -S --needed --noconfirm "${repos[@]}"
    fi

    if (( ${#aur[@]} > 0 )); then
        if (( EUID == 0 && SIMULAR == 0 )); then
            error "Los paquetes AUR se instalan con tu usuario normal, no como root."
        fi
        asegurar_yay
        ejecutar yay -S --needed --noconfirm "${aur[@]}"
    fi

    # HyDE al final: es lo más largo e interactivo
    if (( quiere_hyde )); then
        instalar_hyde
    fi

    echo "Listo."
}

# --- Procesar argumentos ---
while (( $# > 0 )); do
    case "$1" in
        --list)     MODO="listar" ;;
        --dry-run)  SIMULAR=1 ;;
        --select)
            (( $# >= 2 )) || error "--select necesita una lista, por ejemplo: --select steam,vlc"
            MODO="seleccion"; SELECCION_MANUAL="$2"; shift ;;
        --config)
            (( $# >= 2 )) || error "--config necesita una ruta"
            CONFIG="$2"; shift ;;
        -h|--help)  uso; exit 0 ;;
        *)          echo "Opción desconocida: $1" >&2; uso >&2; exit 1 ;;
    esac
    shift
done

[[ -f "$CONFIG" ]] || error "No encuentro el archivo de configuración: $CONFIG"

case "$MODO" in
    listar)
        listar
        ;;
    seleccion)
        [[ -n "$SELECCION_MANUAL" ]] || error "--select necesita una lista, por ejemplo: --select steam,vlc"
        IFS=',' read -ra elegidos <<< "$SELECCION_MANUAL"
        instalar "${elegidos[@]}"
        ;;
    menu)
        command -v whiptail >/dev/null 2>&1 || error "Falta whiptail. Instálalo con: pacman -S libnewt"
        if ! seleccion_menu="$(mostrar_menu)"; then
            echo "Cancelado. No se ha instalado nada."
            exit 0
        fi
        if [[ -z "$seleccion_menu" ]]; then
            echo "No has elegido ninguna aplicación."
            exit 0
        fi
        mapfile -t elegidos <<< "$seleccion_menu"
        instalar "${elegidos[@]}"
        ;;
esac
