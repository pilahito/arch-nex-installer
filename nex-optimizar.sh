#!/usr/bin/env bash
# Nex Optimizar: asistente en español para optimizar Arch Linux, con el estilo
# de los optimizadores Nex. Pasos: equipo, modo, ajustes, resumen y aplicar.
# Al final ofrece elegir las aplicaciones con nex-setup.
#
# Uso:
#   sudo bash nex-optimizar.sh            asistente real (necesita root)
#   bash nex-optimizar.sh --dry-run       muestra lo que haría, sin cambiar nada

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TITULO="NEX ARCH · Optimizador"
SIMULAR=0
[[ "${1:-}" == "--dry-run" ]] && SIMULAR=1

# Colores del tema Nex para los menús
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

cancelado() {
    echo "Asistente cancelado. No se ha cambiado nada."
    exit 0
}

# Ejecuta un comando, o solo lo muestra si estamos en --dry-run
ejecutar() {
    if (( SIMULAR )); then
        echo "[simulación] $*"
    else
        "$@"
    fi
}

# Escribe un fichero (desde stdin), o solo lo muestra en --dry-run
escribir() {
    local destino="$1"
    if (( SIMULAR )); then
        echo "[simulación] escribir $destino:"
        sed 's/^/    /'
    else
        mkdir -p "$(dirname "$destino")"
        cat > "$destino"
    fi
}

# --- Datos del sistema, para la pantalla de bienvenida ---
info_sistema() {
    local cpu ram disco
    cpu=$(lscpu | awk -F: '/Model name/ {gsub(/^ +/, "", $2); print $2; exit}')
    ram=$(free -h | awk '/^Mem:/ {print $2}')
    disco=$(df -h / | awk 'NR==2 {print $2" total, "$5" usado"}')
    printf 'Procesador: %s\nMemoria RAM: %s\nDisco (/): %s' "${cpu:-desconocido}" "${ram:-?}" "${disco:-?}"
}

# --- Optimizaciones ---
# Cada función aplica un ajuste. Son reversibles: se pueden quitar a mano.

ajuste_zram() {
    echo "==> Memoria comprimida (zram)"
    ejecutar pacman -S --needed --noconfirm zram-generator
    escribir /etc/systemd/zram-generator.conf <<'EOF'
# Nex Optimizar: swap comprimido en RAM
[zram0]
zram-size = min(ram / 2, 8192)
compression-algorithm = zstd
swap-priority = 100
EOF
    ejecutar systemctl daemon-reload
    ejecutar systemctl start systemd-zram-setup@zram0.service || true
}

ajuste_pacman() {
    echo "==> Descargas paralelas y colores en pacman"
    if (( SIMULAR )); then
        echo "[simulación] ajustar ParallelDownloads = 10 y Color en /etc/pacman.conf"
        return 0
    fi
    sed -i 's/^#\?ParallelDownloads.*/ParallelDownloads = 10/' /etc/pacman.conf
    grep -q '^ParallelDownloads' /etc/pacman.conf || echo 'ParallelDownloads = 10' >> /etc/pacman.conf
    sed -i 's/^#\?Color$/Color/' /etc/pacman.conf
}

ajuste_limpieza() {
    echo "==> Limpieza automática de la caché de pacman"
    ejecutar pacman -S --needed --noconfirm pacman-contrib
    ejecutar systemctl enable --now paccache.timer
}

ajuste_fstrim() {
    echo "==> Recorte semanal del SSD (fstrim)"
    ejecutar systemctl enable --now fstrim.timer
}

ajuste_espejos() {
    echo "==> Mejores espejos de descarga (reflector, puede tardar)"
    ejecutar pacman -S --needed --noconfirm reflector
    ejecutar reflector --latest 20 --protocol https --sort rate --save /etc/pacman.d/mirrorlist
}

ajuste_energia() {
    echo "==> Perfil de energía equilibrado (power-profiles-daemon)"
    ejecutar pacman -S --needed --noconfirm power-profiles-daemon
    ejecutar systemctl enable --now power-profiles-daemon.service
    ejecutar powerprofilesctl set balanced || true
}

ajuste_sin_hibernacion() {
    echo "==> Sin hibernación (ahorra espacio en disco)"
    ejecutar systemctl mask hibernate.target hybrid-sleep.target suspend-then-hibernate.target
}

ajuste_rendimiento() {
    echo "==> Rendimiento (BETA, experimental)"
    ejecutar pacman -S --needed --noconfirm cpupower
    escribir /etc/sysctl.d/99-nex-rendimiento.conf <<'EOF'
# Nex Optimizar (beta): menos uso del swap y mejor caché de ficheros
vm.swappiness = 10
vm.vfs_cache_pressure = 50
EOF
    escribir /etc/default/cpupower <<'EOF'
# Nex Optimizar (beta): gobernador de CPU
governor='performance'
EOF
    ejecutar sysctl --system
    ejecutar systemctl enable --now cpupower.service || true
}

# --- Pantallas del asistente ---

paso_bienvenida() {
    whiptail --title "$TITULO" --msgbox \
        "Bienvenido al optimizador de Nex Arch.\n\n$(info_sistema)\n\nTe preguntaré el tipo de equipo, el modo y los ajustes. Nada cambia hasta el final." \
        16 72 || cancelado
}

paso_equipo() {
    EQUIPO=$(whiptail --title "$TITULO" --menu "Tipo de equipo:" 12 60 2 \
        "escritorio" "Equipo de escritorio" \
        "portatil" "Portátil (ahorro de batería)" \
        3>&1 1>&2 2>&3) || cancelado
}

paso_modo() {
    MODO=$(whiptail --title "$TITULO" --menu "Modo de optimización:" 13 66 2 \
        "seguro" "Seguro (recomendado): ajustes probados" \
        "beta" "Beta (experimental): más rendimiento, más riesgo" \
        3>&1 1>&2 2>&3) || cancelado
}

# Marca por defecto según el equipo y el modo
paso_ajustes() {
    local portatil=OFF beta=OFF
    [[ "$EQUIPO" == "portatil" ]] && portatil=ON
    [[ "$MODO" == "beta" ]] && beta=ON

    local -a opciones=(
        zram "Memoria comprimida (zram)" ON
        pacman "Descargas paralelas en pacman" ON
        limpieza "Limpieza automática de caché" ON
        fstrim "Recorte semanal del SSD (fstrim)" ON
        espejos "Mejores espejos de descarga (lento)" OFF
        energia "Perfil de energía equilibrado" "$portatil"
        sinhib "Sin hibernación" OFF
        rendimiento "Rendimiento CPU y memoria (BETA)" "$beta"
    )

    AJUSTES=$(whiptail --title "$TITULO" --checklist \
        "Elige los ajustes que quieres aplicar:" 22 74 12 \
        "${opciones[@]}" 3>&1 1>&2 2>&3) || cancelado
    AJUSTES=$(tr -d '"' <<< "$AJUSTES")
}

paso_resumen() {
    local lista
    lista=$(tr ' ' '\n' <<< "$AJUSTES" | sed '/^$/d' | sed 's/^/  - /')
    [[ -n "$lista" ]] || { whiptail --title "$TITULO" --msgbox "No has elegido ningún ajuste." 8 50; exit 0; }
    whiptail --title "$TITULO" --yesno \
        "Equipo: $EQUIPO\nModo: $MODO\n\nSe aplicarán:\n$lista\n\n¿Aplicar ahora?" 20 66 || cancelado
}

aplicar() {
    local ajuste
    for ajuste in $AJUSTES; do
        case "$ajuste" in
            zram)         ajuste_zram ;;
            pacman)       ajuste_pacman ;;
            limpieza)     ajuste_limpieza ;;
            fstrim)       ajuste_fstrim ;;
            espejos)      ajuste_espejos ;;
            energia)      ajuste_energia ;;
            sinhib)       ajuste_sin_hibernacion ;;
            rendimiento)  ajuste_rendimiento ;;
        esac
    done
}

paso_final() {
    local mensaje="Optimización terminada.\n\nReinicia el equipo para que todos los cambios se apliquen."
    if whiptail --title "$TITULO" --yesno "$mensaje\n\n¿Elegir ahora las aplicaciones a instalar?" 14 66; then
        # nex-setup usa yay para el AUR, que no funciona como root: volvemos a tu usuario
        if [[ -n "${SUDO_USER:-}" ]]; then
            exec sudo -u "$SUDO_USER" -H bash "$DIR/nex-setup.sh"
        fi
        exec bash "$DIR/nex-setup.sh"
    fi
    whiptail --title "$TITULO" --msgbox "$mensaje" 10 60
}

principal() {
    command -v whiptail >/dev/null 2>&1 || error "Falta whiptail. Instálalo con: pacman -S libnewt"
    if (( ! SIMULAR )) && (( EUID != 0 )); then
        error "Ejecútalo con sudo: sudo bash nex-optimizar.sh (o usa --dry-run para probar)"
    fi

    paso_bienvenida
    paso_equipo
    paso_modo
    paso_ajustes
    paso_resumen
    aplicar
    paso_final
}

# Solo arranca el asistente si se ejecuta directamente (así se puede probar con source)
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    principal
fi
