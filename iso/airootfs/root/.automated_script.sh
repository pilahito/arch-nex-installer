#!/usr/bin/env bash
# Delta Arch: al arrancar el ISO en la consola tty1 se abre el instalador en español.
# Con Ctrl+C se sale a la consola normal de Arch, por si quieres instalar a mano.

if [[ "$(tty)" == "/dev/tty1" && -f /root/delta-installer/instalar-delta.sh ]]; then
    clear
    bash /root/delta-installer/instalar-delta.sh || true
    echo
    echo "Instalador cerrado. Para abrirlo otra vez: bash /root/delta-installer/instalar-delta.sh"
fi
