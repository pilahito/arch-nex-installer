#!/usr/bin/env bash
# Nex Arch: al arrancar el ISO en la consola tty1 se abre el instalador en español.
# Con Ctrl+C se sale a la consola normal de Arch, por si quieres instalar a mano.

if [[ "$(tty)" == "/dev/tty1" && -f /root/nex-installer/instalar-nex.sh ]]; then
    clear
    bash /root/nex-installer/instalar-nex.sh || true
    echo
    echo "Instalador cerrado. Para abrirlo otra vez: bash /root/nex-installer/instalar-nex.sh"
fi
