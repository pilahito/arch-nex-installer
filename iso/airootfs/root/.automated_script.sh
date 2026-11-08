#!/usr/bin/env bash
# NEX Installer: arranca el panel gráfico en tty1.
# Si el entorno gráfico no arranca, abre el instalador de terminal para no dejar
# la ISO sin forma de instalar. Los registros quedan visibles para diagnosticar.

set -u
echo "NEX OS: preparando el instalador gráfico..."
# El inicio automático sucede tras el login live; no bloquear aquí esperando
# servicios opcionales que pueden permanecer en estado «starting» en QEMU.
systemctl is-system-running || true

cd /root/nex-installer
echo "NEX OS: iniciando Xorg y el instalador..."
startx /root/nex-installer/nex-start-gui.sh -- :0 vt1 -nolisten tcp -logfile /tmp/nex-xorg.log
status=$?

echo "NEX OS: la interfaz gráfica terminó con código $status."
echo "Registro de Xorg: /tmp/nex-xorg.log"

if [[ "$status" -ne 0 && -f /root/nex-installer/instalar-nex.sh ]]; then
    echo "NEX OS: abriendo el instalador de terminal como respaldo..."
    sleep 3
    bash /root/nex-installer/instalar-nex.sh || true
fi
