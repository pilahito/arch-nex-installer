#!/usr/bin/env bash
# NEX Installer: espera al sistema live y arranca la interfaz gráfica en tty1.
# Los registros se dejan visibles para poder diagnosticar un arranque de ISO.

set -u
echo "NEX OS: preparando el instalador gráfico..."
systemctl is-system-running --wait || true

cd /root/nex-installer
echo "NEX OS: iniciando Xorg y el instalador..."
startx /root/nex-installer/nex-start-gui.sh -- :0 vt1 -nolisten tcp -logfile /tmp/nex-xorg.log
status=$?

echo "NEX OS: la interfaz gráfica terminó con código $status."
echo "Registro de Xorg: /tmp/nex-xorg.log"
sleep 30
exit "$status"
