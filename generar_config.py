#!/usr/bin/env python3
"""Genera la configuración de archinstall para Delta Arch.

Los datos llegan por variables de entorno, así las contraseñas no aparecen
en la línea de comandos ni en el historial:

  DELTA_DISCO          disco a borrar y particionar, por ejemplo /dev/sda
  DELTA_TAMANO_MIB     tamaño total del disco en MiB
  DELTA_HOST           nombre del equipo
  DELTA_USUARIO        nombre del usuario principal (tendrá sudo)
  DELTA_ZONA           zona horaria, por ejemplo Europe/Madrid
  DELTA_PASS_USUARIO   contraseña del usuario
  DELTA_PASS_ROOT      contraseña de root

Uso:  python3 generar_config.py CARPETA_SALIDA
Escribe config.json y creds.json en CARPETA_SALIDA.
"""

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

EFI_MIB = 1024          # partición EFI (/boot)
INICIO_EFI_MIB = 1      # la primera partición empieza en 1 MiB
MIN_RAIZ_MIB = 8 * 1024  # mínimo razonable para la raíz (8 GiB)


def particion_de(disco, numero):
    """Nombre de una partición: /dev/sda1 o /dev/nvme0n1p1."""
    return f"{disco}p{numero}" if disco[-1].isdigit() else f"{disco}{numero}"


def tamano(valor_mib):
    return {"sector_size": {"unit": "B", "value": 512}, "unit": "MiB", "value": valor_mib}


def hash_de(password):
    """Hash SHA-512 compatible con /etc/shadow, generado con openssl."""
    if not password:
        raise SystemExit("Falta una contraseña.")
    res = subprocess.run(
        ["openssl", "passwd", "-6", "-stdin"],
        input=(password + "\n").encode(),
        capture_output=True,
        check=True,
    )
    return res.stdout.decode().strip()


def leer_entorno(nombre):
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise SystemExit(f"Falta la variable {nombre}.")
    return valor


def construir_config(datos):
    disco = datos["disco"]
    total = int(datos["tamano_mib"])
    raiz_inicio = INICIO_EFI_MIB + EFI_MIB
    raiz_tamano = total - raiz_inicio - 1  # 1 MiB de margen al final
    if raiz_tamano < MIN_RAIZ_MIB:
        raise SystemExit("El disco es demasiado pequeño para Delta Arch (mínimo unos 9 GiB).")

    particion_efi = {
        "btrfs": [],
        "dev_path": None,
        "flags": ["boot"],
        "fs_type": "fat32",
        "size": tamano(EFI_MIB),
        "mount_options": [],
        "mountpoint": "/boot",
        "obj_id": str(uuid.uuid4()),
        "start": tamano(INICIO_EFI_MIB),
        "status": "create",
        "type": "primary",
    }
    particion_raiz = {
        "btrfs": [],
        "dev_path": None,
        "flags": [],
        "fs_type": "ext4",
        "size": tamano(raiz_tamano),
        "mount_options": [],
        "mountpoint": "/",
        "obj_id": str(uuid.uuid4()),
        "start": tamano(raiz_inicio),
        "status": "create",
        "type": "primary",
    }

    return {
        "archinstall-language": "Spanish",
        "audio_config": {"audio": "pipewire"},
        "bootloader_config": {"bootloader": "Systemd-boot", "uki": False, "removable": False},
        "disk_config": {
            "config_type": "default_layout",
            "device_modifications": [
                {
                    "device": disco,
                    "partitions": [particion_efi, particion_raiz],
                    "wipe": True,
                }
            ],
        },
        "hostname": datos["host"],
        "kernels": ["linux"],
        "locale_config": {"kb_layout": "es", "sys_enc": "UTF-8", "sys_lang": "es_ES"},
        "network_config": {"type": "nm"},
        "ntp": True,
        "packages": ["git", "kitty", "firefox", "btop", "wofi"],
        "pacman_config": {"color": True, "parallel_downloads": 5},
        "profile_config": {
            "gfx_driver": "All open-source",
            "greeter": "sddm",
            "profile": {"details": ["Hyprland"], "main": "Desktop"},
        },
        "script": "guided",
        "swap": {"enabled": True, "algorithm": "zstd"},
        "timezone": datos["zona"],
    }


def construir_credenciales(datos):
    return {
        "users": [
            {
                "sudo": True,
                "username": datos["usuario"],
                "enc_password": hash_de(datos["pass_usuario"]),
            }
        ],
        "root_enc_password": hash_de(datos["pass_root"]),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)

    salida = Path(sys.argv[1])
    salida.mkdir(parents=True, exist_ok=True)

    nombre_usuario = leer_entorno("DELTA_USUARIO")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", nombre_usuario):
        raise SystemExit("El nombre de usuario solo puede tener minúsculas, números, _ o -.")

    datos = {
        "disco": leer_entorno("DELTA_DISCO"),
        "tamano_mib": leer_entorno("DELTA_TAMANO_MIB"),
        "host": leer_entorno("DELTA_HOST"),
        "usuario": nombre_usuario,
        "zona": leer_entorno("DELTA_ZONA"),
        "pass_usuario": leer_entorno("DELTA_PASS_USUARIO"),
        "pass_root": leer_entorno("DELTA_PASS_ROOT"),
    }

    config = construir_config(datos)
    credenciales = construir_credenciales(datos)

    os.umask(0o077)  # ficheros solo legibles por root
    (salida / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False))
    (salida / "creds.json").write_text(json.dumps(credenciales, indent=2))

    # Nombres de las particiones, para montarlas después de la instalación
    (salida / "particiones.env").write_text(
        f"DELTA_PART_EFI={particion_de(datos['disco'], 1)}\n"
        f"DELTA_PART_RAIZ={particion_de(datos['disco'], 2)}\n"
    )
    print(f"Configuración escrita en {salida}")


if __name__ == "__main__":
    main()
