#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nex Arch · Plan de cambios y ejecución.

A partir de las elecciones de la interfaz gráfica (GPU, disco, equipo, paquetes,
escritorio, modo y limpieza) construye una lista de pasos. Cada paso es:

  - "cmd":     un comando (root o usuario)
  - "archivo": un fichero que se escribe en una ruta del sistema (root o usuario)

Antes de ejecutar nada, la interfaz muestra la lista completa para confirmarla.
La contraseña de sudo se pide una sola vez y se usa solo para los pasos de root.
"""

import getpass
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

DIR = Path(__file__).resolve().parent

# Paquetes de los repositorios oficiales (verificados en Arch)
PAQUETES_GPU = {
    "INTEL": ["vulkan-intel", "intel-media-driver"],
    "NVIDIA": ["nvidia-dkms", "nvidia-utils"],
    "AMD": ["vulkan-radeon"],
}

PAQUETES_APPS = {
    "Lutris": "lutris",
    "GameMode": "gamemode",
    "MangoHud": "mangohud",
    "Prism Launcher": "prismlauncher",
    "VLC": "vlc",
    "MPV": "mpv",
    "OBS Studio": "obs-studio",
    "Kdenlive": "kdenlive",
    "Audacity": "audacity",
    "Firefox": "firefox",
    "Chromium": "chromium",
    "qBittorrent": "qbittorrent",
    "7-Zip / Ark": "ark",
    "btop": "btop",
    "Fastfetch": "fastfetch",
    "GIMP": "gimp",
    "Blender": "blender",
    "VS Code": "code",
    "Node.js": "nodejs npm",
    "Git": "git",
    "Docker": "docker",
}

# Estas apps no están en los repositorios oficiales: se instalan con yay (AUR)
PAQUETES_AUR = {
    "Brave": "brave-bin",
    "Heroic Launcher": "heroic-games-launcher-bin",
    "Vesktop": "vesktop",
}

# Temas de la interfaz -> paletas que existen en el instalador (tema/paletas/*.env)
PALETAS_TEMA = {
    "NEX NEÓN": "neon",
    "OSCURO": "oscuro",
    "CLARO": "claro",
}

# Steam está en el repositorio multilib: hay que tenerlo activado en pacman.conf
PAQUETE_STEAM = "steam"

PAQUETES_OFICINA = {
    "Writer": "libreoffice-fresh",
    "Calc": "libreoffice-fresh",
    "Impress": "libreoffice-fresh",
    "Draw": "libreoffice-fresh",
    "Base": "libreoffice-fresh",
    "Math": "libreoffice-fresh",
}

PAQUETES_HYPRLAND = ["hyprland", "waybar", "wofi", "kitty", "xdg-desktop-portal-hyprland", "hyprpaper"]

AVISOS_NO_REPO = {
    "Eww (widgets Hyprland)": "Eww no está en los repositorios oficiales: se omite.",
    "AGS (Aylur GTK Shell)": "AGS no está en los repositorios oficiales: se omite.",
    "Conky Wayland": "Conky Wayland no está en los repositorios oficiales: se omite.",
    "nwg-dock-hyprland": "nwg-dock-hyprland no está en los repositorios oficiales: se omite.",
    "swww (dinámico, AUR)": "swww está en el AUR y no se instala en modo directo: se usa hyprpaper.",
    "Hyprpanel": "Hyprpanel no está en los repositorios oficiales: se usa Waybar.",
}

ZRAM_CONF = """# Nex Arch: swap comprimido en RAM
[zram0]
zram-size = min(ram / 2, 8192)
compression-algorithm = zstd
swap-priority = 100
"""

SYSCTL_MEDIO = """# Nex Arch: menos uso del swap y mejor caché de ficheros
vm.swappiness = 10
vm.vfs_cache_pressure = 50
"""

CPUPOWER_EXTREMO = """# Nex Arch: gobernador de CPU
governor='performance'
"""


@dataclass
class Paso:
    texto: str
    tipo: str                      # "cmd" o "archivo"
    args: List[str] = field(default_factory=list)
    root: bool = True
    contenido: str = ""            # solo para tipo "archivo"
    destino: str = ""              # solo para tipo "archivo"


def _pacman(paquetes: List[str], texto: str) -> Paso:
    paquetes = sorted(set(paquetes))
    return Paso(texto, "cmd", ["pacman", "-S", "--needed", "--noconfirm", *paquetes])


def _systemctl(accion: List[str], unidades: List[str], texto: str) -> Paso:
    return Paso(texto, "cmd", ["systemctl", *accion, *unidades])


def construir_plan(estado: dict) -> Tuple[List[Paso], List[str]]:
    """Devuelve (pasos, avisos) a partir de las elecciones de la interfaz."""
    pasos: List[Paso] = []
    avisos: List[str] = []
    repo: List[str] = []

    # 1. GPU
    gpu = estado.get("gpu")
    if gpu in PAQUETES_GPU:
        repo += PAQUETES_GPU[gpu]

    # 2. Almacenamiento
    if estado.get("almacenamiento") in ("SSD / M.2", "SATA SSD"):
        pasos.append(_systemctl(["enable", "--now"], ["fstrim.timer"], "Activar el recorte semanal del SSD"))

    # 3. Equipo portátil: perfil de energía
    if estado.get("equipo") == "Portátil":
        repo.append("power-profiles-daemon")
        pasos.append(_systemctl(["enable", "--now"], ["power-profiles-daemon.service"],
                                "Activar el perfil de energía"))

    # 4. Modo de optimización (acumulativo)
    modo = estado.get("modo", "Medio")
    repo.append("zram-generator")
    pasos.append(Paso("Memoria comprimida ZRAM", "archivo", contenido=ZRAM_CONF,
                      destino="/etc/systemd/zram-generator.conf"))
    pasos.append(Paso("Descargas paralelas en pacman", "cmd",
                      ["sed", "-i", "s/^#\\?ParallelDownloads.*/ParallelDownloads = 10/", "/etc/pacman.conf"]))
    repo.append("pacman-contrib")
    pasos.append(_systemctl(["enable", "--now"], ["paccache.timer"], "Limpieza automática de la caché"))
    if modo in ("Medio", "Extremo"):
        pasos.append(Paso("Ajustes de memoria (swap y caché)", "archivo", contenido=SYSCTL_MEDIO,
                          destino="/etc/sysctl.d/99-nex.conf"))
        pasos.append(Paso("Aplicar los ajustes de memoria", "cmd", ["sysctl", "--system"]))
    if modo == "Extremo":
        repo.append("cpupower")
        pasos.append(Paso("Gobernador de CPU en rendimiento", "archivo", contenido=CPUPOWER_EXTREMO,
                          destino="/etc/default/cpupower"))
        pasos.append(_systemctl(["enable", "--now"], ["cpupower.service"], "Activar el gobernador de CPU"))
        repo.append("reflector")
        pasos.append(Paso("Espejos de descarga más rápidos", "cmd",
                          ["reflector", "--latest", "20", "--protocol", "https", "--sort", "rate",
                           "--save", "/etc/pacman.d/mirrorlist"]))
        pasos.append(_systemctl(["mask"], ["hibernate.target", "hybrid-sleep.target",
                                           "suspend-then-hibernate.target"],
                                "Desactivar la hibernación"))

    # 5. Oficina (LibreOffice con paquete en español)
    oficina = estado.get("oficina") or []
    if oficina:
        repo += ["libreoffice-fresh", "libreoffice-fresh-es"]

    # 6. Aplicaciones
    aur: List[str] = []
    for app in estado.get("apps") or []:
        if app == "Steam":
            avisos.append("Steam está en multilib: actívalo en /etc/pacman.conf antes de instalarlo.")
            repo.append(PAQUETE_STEAM)
        elif app in PAQUETES_APPS:
            repo += PAQUETES_APPS[app].split()
        elif app in PAQUETES_AUR:
            aur.append(PAQUETES_AUR[app])
        else:
            avisos.append(f"No conozco el paquete de '{app}': se omite.")

    # 7. Escritorio Hyprland
    widgets = estado.get("widgets_hyprland", "")
    barra = estado.get("barra_menu", "")
    dock = estado.get("dock", "")
    wallpaper = estado.get("wallpaper", "")
    repo += PAQUETES_HYPRLAND
    if "Rofi" in barra:
        repo.append("rofi")
    if "Wofi" in barra:
        repo.append("wofi")
    for elegido in (widgets, dock, wallpaper, barra):
        if elegido in AVISOS_NO_REPO:
            avisos.append(AVISOS_NO_REPO[elegido])

    # Un único pacman para todos los paquetes de repositorio
    if repo:
        pasos.insert(0, _pacman(repo, f"Instalar {len(set(repo))} paquetes de los repositorios"))

    if aur:
        pasos.append(Paso(f"Instalar {len(aur)} paquetes del AUR con yay", "cmd",
                          ["yay", "-S", "--needed", "--noconfirm", *sorted(set(aur))], root=False))

    # 8. Tema de escritorio (se aplica al usuario, sin root)
    tema = estado.get("tema", "")
    paleta = PALETAS_TEMA.get(tema)
    if paleta:
        pasos.append(Paso(f"Aplicar el tema {tema}", "cmd", ["__TEMA__", paleta], root=False))
        pasos += _pasos_fondo(paleta)
    elif tema:
        avisos.append(f"El tema '{tema}' todavía no tiene paleta: se usa el tema neón.")
        pasos.append(Paso("Aplicar el tema neón", "cmd", ["__TEMA__", "neon"], root=False))

    # 9. Limpieza
    limpieza = estado.get("debloat") or []
    if any("huérfanos" in t for t in limpieza):
        pasos.append(Paso("Eliminar paquetes huérfanos", "cmd",
                          ["bash", "-c",
                           "orfos=$(pacman -Qtdq || true); "
                           "[ -n \"$orfos\" ] && pacman -Rns --noconfirm $orfos || true"]))
    if any("caché" in t for t in limpieza):
        pasos.append(Paso("Limpiar la caché antigua de pacman", "cmd", ["paccache", "-rk1"]))
    if any("servicios" in t for t in limpieza):
        pasos.append(Paso("Desactivar servicios que no se usan", "cmd",
                          ["bash", "-c", "systemctl disable --now bluetooth cups 2>/dev/null || true"]))
    if any("journal" in t.lower() or "diario" in t.lower() for t in limpieza):
        pasos.append(Paso("Reducir el diario de systemd a 50 MB", "cmd",
                          ["journalctl", "--vacuum-size=50M"]))

    return pasos, avisos


def _pasos_fondo(paleta: str) -> List[Paso]:
    """Copia el fondo del tema a la carpeta del usuario y lo fija en hyprpaper."""
    origen = DIR / "assets" / "fondos" / f"{paleta}.png"
    carpeta = Path.home() / ".local" / "share" / "nex" / "fondos"
    destino = carpeta / f"{paleta}.png"
    return [
        Paso("Copiar el fondo de pantalla del tema", "cmd",
             ["bash", "-c", f"mkdir -p '{carpeta}' && cp '{origen}' '{destino}'"], root=False),
        Paso("Configurar el fondo en hyprpaper", "archivo",
             contenido=f"preload = {destino}\nwallpaper = ,{destino}\n",
             destino=str(Path.home() / ".config" / "hypr" / "hyprpaper.conf"), root=False),
    ]


def buscar_script_tema() -> Optional[Path]:
    for candidato in (Path("/usr/local/share/nex/aplicar-tema.sh"),
                      DIR.parent / "arch-nex-installer" / "post-instalacion" / "aplicar-tema.sh",
                      DIR.parent / "arch-delta-installer" / "post-instalacion" / "aplicar-tema.sh"):
        if candidato.exists():
            return candidato
    return None


def texto_plan(pasos: List[Paso], avisos: List[str]) -> str:
    lineas = []
    for i, p in enumerate(pasos, 1):
        quien = "root" if p.root else "usuario"
        if p.tipo == "archivo":
            lineas.append(f"{i:2d}. {p.texto}  →  escribe {p.destino} ({quien})")
        else:
            lineas.append(f"{i:2d}. {p.texto}  ({quien})")
    if avisos:
        lineas.append("")
        lineas.append("Avisos:")
        lineas += [f"  · {a}" for a in avisos]
    return "\n".join(lineas)


def _ejecutar_paso(paso: Paso, password: Optional[str], simular: bool, log: Callable[[str], None],
                   carpeta: Path) -> bool:
    es_root = paso.root and os.geteuid() != 0

    if paso.tipo == "archivo":
        if simular:
            log(f"[simulación] escribir {paso.destino}")
            return True
        origen = carpeta / Path(paso.destino).name
        origen.write_text(paso.contenido, encoding="utf-8")
        if es_root:
            cmd = ["sudo", "-S", "-p", "", "install", "-Dm644", str(origen), paso.destino]
            res = subprocess.run(cmd, input=(password or "") + "\n", text=True, capture_output=True)
        else:
            Path(paso.destino).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origen, paso.destino)
            res = subprocess.CompletedProcess([], 0, "", "")
        if res.returncode:
            log(res.stderr.strip() or "Error al escribir el fichero")
            return False
        log(f"Escrito {paso.destino}")
        return True

    args = list(paso.args)
    if args and args[0] == "__TEMA__":
        script = buscar_script_tema()
        if script is None:
            log("No encuentro aplicar-tema.sh: se omite el tema.")
            return True
        args = ["bash", str(script), getpass.getuser(), args[1]]

    if simular:
        log("[simulación] " + " ".join(args))
        return True

    if es_root:
        cmd = ["sudo", "-S", "-p", ""] + args
        res = subprocess.run(cmd, input=(password or "") + "\n", text=True, capture_output=True)
    else:
        res = subprocess.run(args, text=True, capture_output=True)
    for linea in (res.stdout + res.stderr).splitlines():
        if linea.strip():
            log(linea)
    if res.returncode:
        log(f"Falló (código {res.returncode}): {paso.texto}")
        return False
    return True


def ejecutar_plan(pasos: List[Paso], password: Optional[str], simular: bool,
                  log: Callable[[str], None], progreso: Callable[[int, int], None]) -> bool:
    """Ejecuta los pasos en orden. Se detiene en el primer error."""
    carpeta = Path(tempfile.mkdtemp(prefix="nex-plan-"))
    os.chmod(carpeta, 0o700)
    try:
        total = len(pasos)
        for i, paso in enumerate(pasos, 1):
            log(f"▸ {paso.texto}")
            if not _ejecutar_paso(paso, password, simular, log, carpeta):
                progreso(i, total)
                return False
            progreso(i, total)
        log("✔ Plan terminado.")
        return True
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)
