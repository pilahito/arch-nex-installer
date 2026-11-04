#!/usr/bin/env bash
# Prueba de delta-optimizar.sh en modo simulación (no cambia el sistema).
# Uso: bash tests/test_optimizar.sh

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

fallo() {
    echo "FALLO: $*" >&2
    exit 1
}

# Cargamos el script sin ejecutar el asistente
SIMULAR=1
# shellcheck disable=SC1091
source "$DIR/delta-optimizar.sh"
SIMULAR=1

AJUSTES="zram pacman limpieza fstrim espejos energia sinhib rendimiento"
salida="$(aplicar 2>&1)" || fallo "aplicar falló en simulación"

for esperado in \
    "pacman -S --needed --noconfirm zram-generator" \
    "systemd-zram-setup@zram0.service" \
    "ParallelDownloads = 10" \
    "pacman-contrib" \
    "paccache.timer" \
    "fstrim.timer" \
    "reflector --latest 20" \
    "power-profiles-daemon" \
    "hibernate.target" \
    "cpupower" \
    "vm.swappiness = 10" \
    "governor='performance'"; do
    grep -qF -- "$esperado" <<< "$salida" || fallo "no aparece en la simulación: $esperado"
done

# Un solo ajuste no debe tocar el resto
salida_sinhib="$(AJUSTES="sinhib" aplicar 2>&1)"
grep -qF "hibernate.target" <<< "$salida_sinhib" || fallo "sinhib no simula bien"
grep -qF "zram-generator" <<< "$salida_sinhib" && fallo "sinhib ha tocado zram"

# Las escrituras de ficheros en simulación solo se muestran
grep -qF "escribir /etc/systemd/zram-generator.conf" <<< "$salida" || fallo "no muestra la escritura de zram"
[[ ! -e /etc/systemd/zram-generator.conf.delta-test ]] || fallo "se escribió un fichero real"

echo "OK: delta-optimizar.sh pasa las pruebas de simulación."
