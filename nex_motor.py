#!/usr/bin/env python3
"""Motor de instalación de NEX OS, sin interfaz.

Lo usan el instalador de terminal (nex_instalador.py) y el panel gráfico
(nex_installer_dashboard.py). Con `simular=True` recorre todos los pasos sin
tocar discos ni ejecutar archinstall.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

import generar_config as gc

DIR = Path(__file__).resolve().parent
TEMA_DIR = DIR / "tema"
MONTAJE = "/mnt"

PASOS = [
    "Preparar la configuración",
    "Instalar Arch con archinstall",
    "Montar la instalación",
    "Aplicar el tema Nex",
    "Instalar Nex Setup y el optimizador",
    "Desmontar",
]

# Del repositorio de Nex Setup se copia lo necesario, no todo
EXCLUIR_SETUP = shutil.ignore_patterns(".git", "tests", "docs", "__pycache__", "*.pyc", "*.md")


@dataclass
class Peticion:
    """Todo lo que hace falta para instalar: se valida antes de ejecutar nada."""

    disco: str                       # por ejemplo /dev/sda
    tamano_bytes: int
    host: str
    usuario: str
    zona: str
    pass_usuario: str = field(repr=False)
    pass_root: str = field(repr=False)
    tema: str = "neon"
    paquetes: List[str] = field(default_factory=list)   # paquetes extra de los repositorios oficiales
    particionado: str = "auto"                           # auto | home | recuperacion
    simular: bool = True


def origen_setup() -> Optional[Path]:
    """Carpeta de Nex Setup: en la ISO es nex-setup/, en el repositorio es setup/."""
    for nombre in ("nex-setup", "setup"):
        candidato = DIR / nombre
        if candidato.is_dir():
            return candidato
    return None


def ejecutar(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def comando(cmd, log: Callable[[str], None], simular: bool):
    """Ejecuta un comando y vuelca su salida en el registro."""
    if simular:
        log("[simulación] " + " ".join(cmd))
        time.sleep(0.2)
        return
    res = ejecutar(cmd)
    for linea in (res.stdout + res.stderr).splitlines():
        log(linea)
    if res.returncode:
        raise RuntimeError(f"Falló: {' '.join(cmd)} (código {res.returncode})")


def validar(p: Peticion) -> None:
    """Rechaza datos que no deberían llegar a archinstall."""
    if not p.disco.startswith("/dev/"):
        raise ValueError("El disco debe ser un dispositivo /dev/…")
    if p.tamano_bytes < 9 * 1024 ** 3:
        raise ValueError("El disco es demasiado pequeño (mínimo 9 GiB).")
    if not p.usuario or not p.pass_usuario or not p.pass_root:
        raise ValueError("Faltan el usuario o las contraseñas.")
    for paquete in p.paquetes:
        if not paquete or not all(c.isalnum() or c in "+-._@" for c in paquete):
            raise ValueError(f"Nombre de paquete no válido: {paquete!r}")


def instalar(p: Peticion, log: Callable[[str], None],
             estado: Callable[[int, str], None], montaje: str = MONTAJE) -> bool:
    """Ejecuta todos los pasos. `estado(i, "en curso"|"hecho"|"error")` informa del avance."""
    validar(p)
    simular = p.simular
    if not simular:
        log("Instalación real bloqueada hasta validar NEX OS en una máquina virtual.")
        estado(0, "error")
        return False
    trabajo = Path(tempfile.mkdtemp(prefix="nex-"))
    os.chmod(trabajo, 0o700)
    particion_efi = gc.particion_de(p.disco, 1)
    particion_raiz = gc.particion_de(p.disco, 2)
    datos = {
        "disco": p.disco,
        "tamano_mib": p.tamano_bytes // (1024 * 1024),
        "host": p.host,
        "usuario": p.usuario,
        "zona": p.zona,
        "pass_usuario": p.pass_usuario,
        "pass_root": p.pass_root,
        "paquetes": list(p.paquetes),
        "particionado": p.particionado,
    }

    def preparar():
        os.umask(0o077)
        config = gc.construir_config(datos)
        creds = gc.construir_credenciales(datos)
        (trabajo / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False))
        (trabajo / "creds.json").write_text(json.dumps(creds, indent=2))
        log("Configuración preparada.")

    def archinstall():
        cmd = ["archinstall", "--config", str(trabajo / "config.json"),
               "--creds", str(trabajo / "creds.json"), "--silent"]
        if simular:
            log("[simulación] " + " ".join(cmd))
            time.sleep(0.5)
            return
        proceso = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for linea in proceso.stdout:
            log(linea.rstrip())
        if proceso.wait():
            raise RuntimeError(f"archinstall terminó con código {proceso.returncode}")

    def montar():
        if simular:
            log(f"[simulación] montar {particion_raiz} en {montaje}")
            return
        if ejecutar(["mountpoint", "-q", montaje]).returncode:
            comando(["mount", particion_raiz, montaje], log, False)
        if ejecutar(["mountpoint", "-q", f"{montaje}/boot"]).returncode:
            comando(["mount", particion_efi, f"{montaje}/boot"], log, False)

    def aplicar_tema():
        destino = Path(montaje) / "usr/local/share/nex"
        if simular:
            log(f"[simulación] tema {p.tema} para {p.usuario}")
            return
        destino.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DIR / "post-instalacion" / "aplicar-tema.sh", destino / "aplicar-tema.sh")
        os.chmod(destino / "aplicar-tema.sh", 0o755)
        shutil.copytree(TEMA_DIR, destino / "tema", dirs_exist_ok=True)
        comando(["arch-chroot", montaje, "/usr/local/share/nex/aplicar-tema.sh", p.usuario, p.tema],
                log, False)

    def instalar_setup():
        """Copia Nex Setup y la tienda de temas al sistema instalado y crea sus comandos."""
        origen = origen_setup()
        destino = Path(montaje) / "usr/local/share/nex-setup"
        comandos = {
            "nex-setup": "/usr/local/share/nex-setup/nex-setup.sh",
            "nex-optimizar": "/usr/local/share/nex-setup/nex-optimizar.sh",
            "nex-actualizar": "/usr/local/share/nex-setup/nex-actualizar.sh",
            "nex-optimizar-gui": "/usr/local/share/nex-setup/nex_optimizador_gui.py",
            "nex-theme-store": "/usr/local/share/nex/nex_theme_store_gui.py",
        }
        if simular:
            log(f"[simulación] copiar Nex Setup a {destino} y crear {', '.join(comandos)}")
            return
        if origen is None:
            raise RuntimeError("No encuentro Nex Setup junto al instalador.")
        shutil.copytree(origen, destino, ignore=EXCLUIR_SETUP, dirs_exist_ok=True)
        tienda = Path(montaje) / "usr/local/share/nex"
        tienda.mkdir(parents=True, exist_ok=True)
        for archivo in ("nex_theme_store_gui.py", "theme_store.py"):
            shutil.copy2(DIR / archivo, tienda / archivo)
        for nombre, ruta in comandos.items():
            ejecutable = Path(montaje) / "usr/local/bin" / nombre
            ejecutable.parent.mkdir(parents=True, exist_ok=True)
            interprete = "python3" if ruta.endswith(".py") else "bash"
            ejecutable.write_text(f'#!/usr/bin/env bash\nexec {interprete} {ruta} "$@"\n')
            os.chmod(ejecutable, 0o755)
        log("Nex Setup instalado.")

    def desmontar():
        if not simular:
            ejecutar(["umount", "-R", montaje])
        log("Listo.")

    pasos = [preparar, archinstall, montar, aplicar_tema, instalar_setup, desmontar]
    ok = True
    try:
        for indice, funcion in enumerate(pasos):
            estado(indice, "en curso")
            try:
                funcion()
            except Exception as error:  # noqa: BLE001 - se muestra al usuario
                log(f"ERROR: {error}")
                estado(indice, "error")
                ok = False
                break
            estado(indice, "hecho")
    finally:
        shutil.rmtree(trabajo, ignore_errors=True)
    return ok
