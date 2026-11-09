#!/usr/bin/env python3
"""Nex Arch: instalador en pantalla completa, dentro de la terminal (curses).

Uso (como root, desde el ISO de Arch en modo UEFI):
    python3 nex_instalador.py

Opciones:
    --simular   recorre todas las pantallas sin tocar discos ni instalar nada

Las pantallas son: bienvenida, disco, confirmación del borrado, equipo,
tema, resumen y progreso. La instalación en sí la hace archinstall con la
configuración generada por generar_config.py.
"""

import curses
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
import generar_config as gc  # noqa: E402
import nex_motor as motor  # noqa: E402

TEMA_DIR = DIR / "tema"
MONTAJE = "/mnt"
SIMULAR = "--simular" in sys.argv

ZONA_DEFECTO = "Europe/Madrid"
HOST_DEFECTO = "nex-arch"
USUARIO_DEFECTO = "nex"
GIB = 1024 ** 3
MINIMO_DISCO_GIB = 9

# Pares de color
(PAR_NORMAL, PAR_TITULO, PAR_BANNER, PAR_SELECCION, PAR_AVISO, PAR_OK, PAR_ERROR,
 PAR_BORDE, PAR_NEON, PAR_DIM) = range(1, 11)

# Logo en bloques, estilo terminal de Linux
LOGO = [
    "███╗   ██╗███████╗██╗  ██╗",
    "████╗  ██║██╔════╝╚██╗██╔╝",
    "██╔██╗ ██║█████╗   ╚███╔╝ ",
    "██║╚██╗██║██╔══╝   ██╔██╗ ",
    "██║ ╚████║███████╗██╔╝ ██╗",
    "╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝",
]

PIE_MENU = "↑↓ mover · Enter elegir · Esc cancelar"
PIE_TEXTO = "Escribe y pulsa Enter · Esc cancelar"

ICONOS = {"pendiente": "○", "en curso": "◉", "hecho": "✔", "error": "✖"}


class Cancelado(Exception):
    """El usuario ha pulsado Esc en alguna pantalla."""


# --------------------------------------------------------------------------
# Lógica sin interfaz (se puede probar sin terminal)
# --------------------------------------------------------------------------

def ejecutar(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def parse_discos(texto_json):
    """Convierte la salida de `lsblk -J -b -d -p -o NAME,SIZE,TYPE,MODEL` en una lista."""
    datos = json.loads(texto_json)
    discos = []
    for d in datos.get("blockdevices", []):
        if d.get("type") != "disk":
            continue
        discos.append({
            "nombre": d["name"],
            "bytes": int(d.get("size") or 0),
            "modelo": (d.get("model") or "").strip() or "disco",
        })
    return discos


def filtrar_discos(discos, medio):
    """Quita el medio de instalación y los discos demasiado pequeños."""
    minimo = MINIMO_DISCO_GIB * GIB
    return [d for d in discos if d["nombre"] != medio and d["bytes"] >= minimo]


def disco_del_medio():
    """Disco del que arrancó el ISO, para no ofrecerlo como destino."""
    origen = ejecutar(["findmnt", "-no", "SOURCE", "/run/archiso/bootmnt"]).stdout.strip()
    if not origen:
        return None
    padre = ejecutar(["lsblk", "-no", "PKNAME", origen]).stdout.strip()
    return f"/dev/{padre}" if padre else None


def valido_host(texto):
    return re.fullmatch(r"[A-Za-z0-9-]{1,63}", texto) is not None


def valido_usuario(texto):
    return re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", texto) is not None


def valida_zona(texto):
    return re.fullmatch(r"[A-Za-z_]+(/[A-Za-z_+-]+)*", texto) is not None and \
        (Path("/usr/share/zoneinfo") / texto).exists()


def leer_cpu():
    try:
        for linea in Path("/proc/cpuinfo").read_text().splitlines():
            if linea.startswith("model name"):
                return linea.split(":", 1)[1].strip()
    except OSError:
        pass
    return "desconocido"


def leer_ram_gib():
    try:
        for linea in Path("/proc/meminfo").read_text().splitlines():
            if linea.startswith("MemTotal"):
                return round(int(linea.split()[1]) / 1024 / 1024, 1)
    except OSError:
        pass
    return 0.0


def leer_gpu():
    lineas = [l for l in ejecutar(["lspci"]).stdout.splitlines() if re.search(r"VGA|3D|Display", l)]
    return lineas[0].split(": ", 1)[-1] if lineas else "no detectada"


def info_sistema():
    """Líneas de la pantalla de bienvenida."""
    modo ="UEFI" if Path("/sys/firmware/efi").is_dir() else "BIOS (no compatible)"
    return [
        f"Procesador: {leer_cpu()}",
        f"Memoria RAM: {leer_ram_gib()} GiB",
        f"Gráficos: {leer_gpu()}",
        f"Arranque: {modo}",
    ]


def detectar_discos():
    """Devuelve (discos aptos, disco del medio de instalación)."""
    if SIMULAR:
        return [{"nombre": "/dev/sdz", "bytes": 512 * GIB, "modelo": "Disco de prueba"}], None
    salida = ejecutar(["lsblk", "-J", "-b", "-d", "-p", "-o", "NAME,SIZE,TYPE,MODEL"]).stdout
    medio = disco_del_medio()
    return filtrar_discos(parse_discos(salida), medio), medio


def gib(bytes_):
    return f"{bytes_ / GIB:.0f} GiB"


# --------------------------------------------------------------------------
# Capa de pantalla (curses)
# --------------------------------------------------------------------------

def iniciar_colores():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(PAR_NORMAL, curses.COLOR_WHITE, -1)
    curses.init_pair(PAR_TITULO, curses.COLOR_CYAN, -1)
    curses.init_pair(PAR_BANNER, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(PAR_SELECCION, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    curses.init_pair(PAR_AVISO, curses.COLOR_YELLOW, -1)
    curses.init_pair(PAR_OK, curses.COLOR_GREEN, -1)
    curses.init_pair(PAR_ERROR, curses.COLOR_RED, -1)
    curses.init_pair(PAR_BORDE, curses.COLOR_MAGENTA, -1)
    curses.init_pair(PAR_NEON, curses.COLOR_MAGENTA, -1)
    curses.init_pair(PAR_DIM, curses.COLOR_BLUE, -1)


def color(par, extra=0):
    return curses.color_pair(par) | extra


def escribir(scr, y, x, texto, atributo=0):
    alto, ancho = scr.getmaxyx()
    if y < 0 or y >= alto or x >= ancho:
        return
    try:
        scr.addnstr(y, x, texto, max(0, ancho - x - 1), atributo)
    except curses.error:
        pass


def caja(scr, y0, x0, y1, x1):
    """Marco redondeado en magenta, como las ventanas de los temas de Linux."""
    a = color(PAR_BORDE)
    escribir(scr, y0, x0, "╭" + "─" * (x1 - x0 - 1) + "╮", a)
    for y in range(y0 + 1, y1):
        escribir(scr, y, x0, "│", a)
        escribir(scr, y, x1, "│", a)
    escribir(scr, y1, x0, "╰" + "─" * (x1 - x0 - 1) + "╯", a)


def marco(scr, titulo, pie):
    scr.erase()
    alto, ancho = scr.getmaxyx()
    barra = f" ◆ nex@arch-live · instalador · {time.strftime('%H:%M')} "
    escribir(scr, 0, 0, barra.ljust(ancho), color(PAR_BANNER, curses.A_BOLD))
    caja(scr, 1, 1, alto - 2, ancho - 2)
    # Título en una barra rellena, como en el estilo del vídeo de referencia
    escribir(scr, 2, 3, f" ▸ {titulo} ".ljust(ancho - 6), color(PAR_BANNER, curses.A_BOLD))
    escribir(scr, alto - 1, 0, f" {pie} ".ljust(ancho), color(PAR_BANNER))


def pintar_logo(scr, y):
    for i, linea in enumerate(LOGO):
        escribir(scr, y + i, 4, linea, color(PAR_NEON, curses.A_BOLD))
    escribir(scr, y + len(LOGO), 4, "arch linux · hyprland · en español", color(PAR_DIM))
    return y + len(LOGO) + 1


def parrafo(scr, y, texto, atributo=None):
    """Escribe un texto con ajuste de línea y devuelve la siguiente fila libre."""
    ancho = scr.getmaxyx()[1]
    lineas = []
    for trozo in texto.split("\n"):
        lineas += textwrap.wrap(trozo, max(20, ancho - 8)) or [""]
    for i, linea in enumerate(lineas):
        escribir(scr, y + i, 4, linea, atributo if atributo is not None else color(PAR_NORMAL))
    return y + len(lineas)


def leer_tecla(scr):
    """Devuelve 'arriba', 'abajo', 'enter', 'esc', 'retroceso', un carácter, o None."""
    try:
        tecla = scr.get_wch()
    except curses.error:
        return None
    if isinstance(tecla, int):
        return {
            curses.KEY_UP: "arriba",
            curses.KEY_DOWN: "abajo",
            curses.KEY_BACKSPACE: "retroceso",
            curses.KEY_ENTER: "enter",
        }.get(tecla)
    if tecla in ("\n", "\r"):
        return "enter"
    if tecla == "\x1b":
        return "esc"
    if tecla in ("\x7f", "\b"):
        return "retroceso"
    return tecla


def menu(scr, titulo, texto, opciones):
    """opciones: lista de (valor, etiqueta). Devuelve el valor elegido."""
    indice = 0
    while True:
        marco(scr, titulo, PIE_MENU)
        fila = parrafo(scr, 4, texto) + 1
        for i, (_, etiqueta) in enumerate(opciones):
            if i == indice:
                escribir(scr, fila + i, 4, f" ▶ {etiqueta}  ", color(PAR_SELECCION, curses.A_BOLD))
            else:
                escribir(scr, fila + i, 4, f"   {etiqueta}", color(PAR_NORMAL))
        scr.refresh()
        tecla = leer_tecla(scr)
        if tecla == "arriba":
            indice = (indice - 1) % len(opciones)
        elif tecla == "abajo":
            indice = (indice + 1) % len(opciones)
        elif tecla == "enter":
            return opciones[indice][0]
        elif tecla == "esc":
            raise Cancelado()


def pedir_texto(scr, titulo, texto, defecto="", validar=None, secreto=False):
    valor = defecto
    aviso = ""
    while True:
        marco(scr, titulo, PIE_TEXTO)
        fila = parrafo(scr, 4, texto) + 1
        visible = "•" * len(valor) if secreto else valor
        escribir(scr, fila, 4, "─" * 44, color(PAR_DIM))
        escribir(scr, fila + 1, 4, f"❯ {visible}█", color(PAR_NEON, curses.A_BOLD))
        escribir(scr, fila + 2, 4, "─" * 44, color(PAR_DIM))
        fila += 2
        if aviso:
            escribir(scr, fila + 2, 6, aviso, color(PAR_ERROR, curses.A_BOLD))
        scr.refresh()
        tecla = leer_tecla(scr)
        if tecla == "esc":
            raise Cancelado()
        if tecla == "enter":
            if validar is None or validar(valor):
                return valor
            aviso = "Valor no válido. Prueba de nuevo."
        elif tecla == "retroceso":
            valor = valor[:-1]
        elif isinstance(tecla, str) and len(tecla) == 1 and tecla.isprintable():
            valor += tecla
            aviso = ""


def mostrar_aviso(scr, titulo, texto, pie="Pulsa cualquier tecla para continuar"):
    marco(scr, titulo, pie)
    parrafo(scr, 4, texto, color(PAR_AVISO))
    scr.refresh()
    leer_tecla(scr)


def pantalla_bienvenida(scr):
    marco(scr, "Bienvenido", "Enter empezar · Esc salir")
    fila = pintar_logo(scr, 4) + 1
    fila = parrafo(scr, fila, "Te guío paso a paso para instalar Arch Linux con el escritorio Nex.")
    fila = parrafo(scr, fila + 1, "\n".join(info_sistema()), color(PAR_TITULO))
    parrafo(scr, fila + 1, "⚠ El disco que elijas se borrará por completo.", color(PAR_AVISO))
    scr.refresh()
    while True:
        tecla = leer_tecla(scr)
        if tecla == "enter":
            return
        if tecla == "esc":
            raise Cancelado()


def pantalla_disco(scr, discos, medio):
    if not discos:
        mostrar_aviso(scr, "Sin discos", "No encuentro discos aptos (mínimo 9 GiB, sin el medio de instalación).")
        raise Cancelado()
    texto = "Elige el disco donde instalar Nex Arch. TODO su contenido se borrará."
    if medio:
        texto += f"\nEl medio de instalación ({medio}) no aparece porque es el USB o el ISO."
    opciones = [(d, f"{d['nombre']}   {gib(d['bytes'])}   {d['modelo']}") for d in discos]
    return menu(scr, "Disco de instalación", texto, opciones)


def pantalla_confirmar_disco(scr, disco):
    nombre = disco["nombre"]
    pedir_texto(
        scr,
        "Confirmar el borrado",
        f"Para confirmar, escribe el nombre exacto del disco ({nombre}).\nSe borrarán todos sus datos.",
        validar=lambda v: v == nombre,
    )


def pantalla_equipo(scr):
    host = pedir_texto(scr, "Equipo", "Nombre del equipo:", HOST_DEFECTO, valido_host)
    usuario = pedir_texto(scr, "Usuario", "Nombre de tu usuario (minúsculas, sin espacios):",
                          USUARIO_DEFECTO, valido_usuario)
    zona = pedir_texto(scr, "Zona horaria", "Zona horaria (por ejemplo Europe/Madrid):",
                       ZONA_DEFECTO, valida_zona)
    while True:
        pass_usuario = pedir_texto(scr, "Contraseña", f"Contraseña para {usuario}:",
                                   validar=lambda v: len(v) >= 1, secreto=True)
        repite = pedir_texto(scr, "Contraseña", "Repite la contraseña:", validar=lambda v: True, secreto=True)
        if pass_usuario == repite:
            break
        mostrar_aviso(scr, "Contraseña", "Las contraseñas no coinciden. Vuelve a escribirlas.")
    while True:
        pass_root = pedir_texto(scr, "Contraseña de root", "Contraseña para root:",
                                validar=lambda v: len(v) >= 1, secreto=True)
        repite = pedir_texto(scr, "Contraseña de root", "Repite la contraseña de root:",
                             validar=lambda v: True, secreto=True)
        if pass_root == repite:
            break
        mostrar_aviso(scr, "Contraseña de root", "Las contraseñas no coinciden. Vuelve a escribirlas.")
    return {"host": host, "usuario": usuario, "zona": zona,
            "pass_usuario": pass_usuario, "pass_root": pass_root}


def pantalla_tema(scr):
    catalogo = json.loads((TEMA_DIR / "catalogo.json").read_text(encoding="utf-8"))
    opciones = [(tema["id"], f'{tema["nombre"]} · {tema["descripcion"]}')
                for tema in catalogo]
    return menu(scr, "Tema", "Elige un diseño de escritorio. Podrás cambiarlo después.", opciones)


def pantalla_resumen(scr, disco, equipo, tema):
    texto = (
        f"Disco:         {disco['nombre']} ({gib(disco['bytes'])}) SE BORRARÁ\n"
        f"Equipo:        {equipo['host']}\n"
        f"Usuario:       {equipo['usuario']} (con sudo)\n"
        f"Zona horaria:  {equipo['zona']}\n"
        f"Tema:          {tema}\n"
        f"Idioma:        español (es_ES), teclado español\n\n"
        "¿Empezar la instalación?"
    )
    return menu(scr, "Resumen", texto, [("si", "Sí, instalar"), ("no", "No, volver atrás")]) == "si"


# --------------------------------------------------------------------------
# Instalación con barra de progreso
# --------------------------------------------------------------------------

PASOS = [
    "Preparar la configuración",
    "Instalar Arch con archinstall",
    "Montar la instalación",
    "Aplicar el tema Nex",
    "Instalar Nex Setup y el optimizador",
    "Desmontar",
]

# Herramientas de Nex Setup que se copian al sistema instalado (no el repositorio entero)
EXCLUIR_SETUP = shutil.ignore_patterns(".git", "tests", "docs", "__pycache__", "*.pyc", "*.md")


def pintar_progreso(scr, estados, registro):
    marco(scr, "Instalando Nex Arch", "Espera · no apagues el equipo")
    alto, ancho = scr.getmaxyx()
    hechos = sum(1 for e in estados if e == "hecho")
    total = len(PASOS)
    largo = max(10, min(50, ancho - 24))
    lleno = int(largo * hechos / total)
    # Barra con degradado: parte hecha en magenta, borde en cian y resto atenuado
    x = 4
    escribir(scr, 4, x, "█" * lleno, color(PAR_NEON, curses.A_BOLD))
    x += lleno
    if lleno < largo:
        escribir(scr, 4, x, "▓", color(PAR_TITULO, curses.A_BOLD))
        x += 1
        escribir(scr, 4, x, "░" * (largo - lleno - 1), color(PAR_DIM))
        x += largo - lleno - 1
    escribir(scr, 4, x + 2, f"{hechos * 100 // total:3d}%", color(PAR_TITULO, curses.A_BOLD))
    for i, paso in enumerate(PASOS):
        estado = estados[i]
        atributo = {"hecho": color(PAR_OK, curses.A_BOLD), "error": color(PAR_ERROR, curses.A_BOLD),
                    "en curso": color(PAR_NEON, curses.A_BOLD)}.get(estado, color(PAR_DIM))
        escribir(scr, 6 + i, 4, f" {ICONOS[estado]}  {paso}", atributo)
    base = 6 + total + 1
    escribir(scr, base, 4, "─── registro " + "─" * max(0, largo - 8), color(PAR_DIM))
    espacio = alto - base - 4
    if espacio > 0:
        for i, linea in enumerate(registro[-espacio:]):
            escribir(scr, base + 1 + i, 6, linea[:200], color(PAR_NORMAL))
    scr.refresh()


def comando(cmd, registro):
    """Ejecuta un comando y guarda su salida en el registro."""
    if SIMULAR:
        registro.append("[simulación] " + " ".join(cmd))
        time.sleep(0.2)
        return
    res = ejecutar(cmd)
    for linea in (res.stdout + res.stderr).splitlines():
        registro.append(linea)
    if res.returncode:
        raise RuntimeError(f"Falló: {' '.join(cmd)} (código {res.returncode})")


def instalar(scr, disco, equipo, tema):
    """Instala con el motor compartido y pinta el progreso en la terminal."""
    estados = ["pendiente"] * len(PASOS)
    registro = []
    peticion = motor.Peticion(
        disco=disco["nombre"], tamano_bytes=disco["bytes"], host=equipo["host"],
        usuario=equipo["usuario"], zona=equipo["zona"],
        pass_usuario=equipo["pass_usuario"], pass_root=equipo["pass_root"],
        tema=tema, simular=SIMULAR,
    )

    def log(texto):
        registro.append(texto)
        pintar_progreso(scr, estados, registro)

    def estado(indice, nuevo):
        estados[indice] = nuevo
        pintar_progreso(scr, estados, registro)

    ok = motor.instalar(peticion, log, estado, MONTAJE)
    return ok, registro


def pantalla_final(scr, ok, registro):
    if ok:
        titulo = "Nex Arch está instalado"
        texto = "Quita el USB y reinicia el equipo.\nPulsa cualquier tecla para salir."
        atributo = color(PAR_OK, curses.A_BOLD)
    else:
        titulo = "La instalación ha fallado"
        texto = "Revisa el registro. Pulsa cualquier tecla para salir."
        atributo = color(PAR_ERROR, curses.A_BOLD)
    marco(scr, titulo, "Pulsa cualquier tecla")
    parrafo(scr, 4, texto, atributo)
    ultimas = [l for l in registro if l][-8:]
    parrafo(scr, 8, "\n".join(ultimas), color(PAR_NORMAL))
    scr.refresh()
    leer_tecla(scr)


def hay_internet():
    """Comprueba que hay conexión con el repositorio de Arch (sin descargar nada)."""
    import socket
    try:
        with socket.create_connection(("geo.mirror.pkgbuild.com", 443), timeout=4):
            return True
    except OSError:
        return False


def pantalla_red(scr):
    """Menú de red: Wi-Fi, cable o Bluetooth con nmtui (NetworkManager), sin comandos."""
    while True:
        conectado = SIMULAR or hay_internet()
        estado = ("Modo simulación: no se necesita conexión." if SIMULAR else
                  "Conectado a internet." if conectado else "Sin conexión a internet.")
        opcion = menu(scr, "Red", f"{estado}\nConecta el equipo para descargar Arch y los paquetes.", [
            ("seguir", "Continuar" if conectado else "Continuar sin internet (no se podrá instalar)"),
            ("ajustar", "Configurar Wi-Fi o cable (menú guiado)"),
        ])
        if opcion == "ajustar":
            if shutil.which("nmtui") is None:
                mostrar_aviso(scr, "Red", "No está instalado nmtui (paquete networkmanager).")
                continue
            curses.endwin()
            try:
                subprocess.run(["nmtui"], check=False)
            finally:
                scr.refresh()
                curses.doupdate()
        else:
            return


def flujo(scr):
    iniciar_colores()
    curses.curs_set(0)
    pantalla_bienvenida(scr)
    pantalla_red(scr)
    discos, medio = detectar_discos()
    disco = pantalla_disco(scr, discos, medio)
    pantalla_confirmar_disco(scr, disco)
    equipo = pantalla_equipo(scr)
    tema = pantalla_tema(scr)
    if not pantalla_resumen(scr, disco, equipo, tema):
        raise Cancelado()
    ok, registro = instalar(scr, disco, equipo, tema)
    pantalla_final(scr, ok, registro)
    return ok


def principal(scr):
    try:
        return flujo(scr)
    except Cancelado:
        return None


def main():
    if not SIMULAR and os.geteuid() != 0:
        print("Ejecútalo como root: sudo python3 nex_instalador.py", file=sys.stderr)
        return 1
    if not SIMULAR and not Path("/sys/firmware/efi").is_dir():
        print("Nex Arch solo se instala en modo UEFI.", file=sys.stderr)
        return 1
    try:
        resultado = curses.wrapper(principal)
    except KeyboardInterrupt:
        print("Instalación interrumpida.")
        return 1
    if resultado is None:
        print("Instalación cancelada. No se ha tocado ningún disco.")
        return 0
    return 0 if resultado else 1


if __name__ == "__main__":
    sys.exit(main())
