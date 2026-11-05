#!/usr/bin/env bash
# Nex Installer: arranca la interfaz gráfica al iniciar el ISO.

cd /root/nex-installer
exec startx /root/nex-installer/nex-start-gui.sh -- :0 vt1 -nolisten tcp -logfile /tmp/nex-xorg.log >/dev/null 2>&1
