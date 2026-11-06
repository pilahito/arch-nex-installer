#!/usr/bin/env bash
openbox --sm-disable >/tmp/nex-openbox.log 2>&1 &
exec /usr/bin/python3 /root/nex-installer/nex_installer_dashboard.py
