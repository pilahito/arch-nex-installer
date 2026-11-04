#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nex Arch · Asistente gráfico de optimización (PyQt6), estilo futurista.

Recorre 9 pantallas (GPU, almacenamiento, equipo, LibreOffice, aplicaciones,
escritorio Hyprland, modo, limpieza y resumen). Al final muestra el plan completo
para confirmarlo y, si se acepta, lo aplica con nex_plan.py. La contraseña de
sudo se pide una sola vez.

Uso:
    python3 nex_optimizador_gui.py            aplica los cambios
    python3 nex_optimizador_gui.py --simular  solo muestra lo que haría
"""

import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, QEasingCurve, QPropertyAnimation, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QConicalGradient, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFrame, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QAbstractItemView, QMainWindow, QMessageBox, QProgressBar, QPushButton, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

DIR = Path(__file__).resolve().parent
RUTA_ASSETS = DIR / "assets"
sys.path.insert(0, str(DIR))
import nex_plan  # noqa: E402

# Imagen de fondo de cada tema (generadas con tools/generar_imagenes.py)
ARCHIVO_FONDO = {"NEX NEÓN": "neon", "OSCURO": "oscuro", "CLARO": "claro", "HYDE": "hyde"}


def fondo_de(tema):
    return QPixmap(str(RUTA_ASSETS / "fondos" / f"{ARCHIVO_FONDO.get(tema, 'neon')}.png"))

# Paleta neón, la misma de la paleta "neon" de Nex
COLORES = {
    "@cian": "#2ee6ff",
    "@magenta": "#ff2fb3",
    "@violeta": "#9d5cff",
    "@texto": "#f4eaff",
    "@dim": "#6b7aa1",
}

PLANTILLA_QSS = """
QMainWindow, QDialog { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #05070f, stop:1 #120a24); }
QWidget { color: @texto; font-family: 'JetBrains Mono', 'DejaVu Sans Mono', sans-serif; font-size: 13px; }
QLabel { background: transparent; }
QLabel#Marca { color: @magenta; font-size: 22px; font-weight: bold; }
QLabel#Titulo { color: #ffffff; font-size: 20px; font-weight: bold; }
QLabel#Etiqueta { color: @cian; font-size: 12px; font-weight: bold; }
QLabel#Subtitulo { color: @dim; font-size: 13px; }
QLabel#Paso { color: @dim; font-size: 12px; }
QLabel#Info { color: @texto; font-size: 13px; }
QFrame#Barra { background: #070b16; border-top: 1px solid #1f2d52; }
QFrame#Card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f1a30, stop:1 #161033);
    border: 1px solid #1f2d52; border-radius: 16px;
}
QFrame#Card:hover { border: 1px solid @cian; }
QFrame#CardSel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a1440, stop:1 #241652);
    border: 2px solid @magenta; border-radius: 16px;
}
QPushButton {
    background: transparent; color: @cian; border: 1px solid @cian;
    border-radius: 10px; padding: 9px 20px; font-weight: bold;
}
QPushButton:hover { background: rgba(46, 230, 255, 40); }
QPushButton#Primario {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 @magenta, stop:1 @violeta);
    color: #ffffff; border: none;
}
QPushButton#Primario:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5cc4, stop:1 #b07cff);
}
QCheckBox { color: @texto; spacing: 10px; font-size: 13px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid @cian; border-radius: 4px; background: #070b16; }
QCheckBox::indicator:checked { background: @cian; }
QComboBox {
    background: #0a1224; color: @texto; border: 1px solid #1f2d52;
    border-radius: 8px; padding: 6px 10px;
}
QComboBox QAbstractItemView { background: #0a1224; color: @texto; selection-background-color: @magenta; }
QTextEdit, QLineEdit {
    background: #070b16; color: @texto; border: 1px solid #1f2d52; border-radius: 8px; padding: 8px;
}
QTableWidget {
    background: #070b16; color: @texto; gridline-color: #1f2d52;
    border: 1px solid #1f2d52; border-radius: 8px;
}
QTableWidget::item:selected { background: @magenta; color: #ffffff; }
QHeaderView::section { background: #0a1224; color: @cian; border: none; padding: 6px; }
QProgressBar {
    background: #0a1224; border: 1px solid #1f2d52; border-radius: 8px;
    text-align: center; color: #ffffff; font-weight: bold; min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 @magenta, stop:0.5 @violeta, stop:1 @cian);
    border-radius: 7px;
}
"""


def estilo():
    qss = PLANTILLA_QSS
    for clave, valor in COLORES.items():
        qss = qss.replace(clave, valor)
    return qss


def brillo(widget, color="#ff2fb3", radio=28):
    """Halo de color alrededor de un widget."""
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(radio)
    efecto.setColor(QColor(color))
    efecto.setOffset(0, 0)
    widget.setGraphicsEffect(efecto)
    return efecto


def leer_info_sistema():
    # Todo se detecta del sistema donde se ejecuta. Si algo no se puede leer,
    # se muestra "No detectado" en vez de un valor inventado.
    cpu = "No detectado"
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                if "model name" in linea:
                    cpu = linea.split(":", 1)[1].strip()
                    break
    except OSError:
        pass

    placa = "No detectada"
    try:
        with open("/sys/devices/virtual/dmi/id/board_name", "r", encoding="utf-8") as f:
            placa = f.read().strip() or placa
    except OSError:
        pass

    ram_total_gb, ram_pct = "No detectada", 0
    try:
        info = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for linea in f:
                partes = linea.split(":")
                if len(partes) == 2:
                    info[partes[0].strip()] = int(partes[1].strip().split()[0])
        total_kb = info.get("MemTotal", 8388608)
        disp_kb = info.get("MemAvailable", 5242880)
        ram_total_gb = f"{round(total_kb / 1048576, 1)} GB"
        ram_pct = int(100 - (disp_kb * 100 / max(total_kb, 1)))
    except (OSError, ValueError):
        pass

    discos = []
    for nombre, ruta in (("Raíz (/)", "/"), ("Inicio (/home)", "/home"), ("Arranque (/boot)", "/boot")):
        if os.path.exists(ruta):
            uso = shutil.disk_usage(ruta)
            discos.append((nombre, round(uso.total / 1024**3, 1), int(uso.used * 100 / max(uso.total, 1))))

    return {"cpu": cpu, "placa": placa, "ram_gb": ram_total_gb, "ram_pct": ram_pct, "discos": discos}


def leer_cpu_muestra():
    """Devuelve (total, inactivo) de /proc/stat para calcular el uso de CPU."""
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            valores = [int(v) for v in f.readline().split()[1:]]
        return sum(valores), valores[3] + valores[4]
    except (OSError, ValueError, IndexError):
        return 0, 0


class AcercaDeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NEX Arch · Acerca de")
        self.setMinimumWidth(420)
        capa = QVBoxLayout(self)

        titulo = QLabel("◆ NEX ARCH OPTIMIZER v1.1")
        titulo.setObjectName("Marca")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lofi = os.environ.get("NEX_LOFI_URL", "")
        enlace_lofi = f'<a href="{lofi}">Lo-Fi</a>' if lofi else "Lo-Fi: pendiente de enlace"
        info = QLabel(
            "Desarrollo: pilahito<br><br>"
            '<a href="https://github.com/pilahito">GitHub · github.com/pilahito</a><br>'
            '<a href="https://paypal.me/pilahito">PayPal · paypal.me/pilahito</a><br>'
            f"{enlace_lofi}"
        )
        info.setOpenExternalLinks(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setTextFormat(Qt.TextFormat.RichText)

        ok = QPushButton("OK")
        ok.setObjectName("Primario")
        ok.clicked.connect(self.accept)

        capa.addWidget(titulo)
        capa.addWidget(info)
        capa.addWidget(ok, alignment=Qt.AlignmentFlag.AlignRight)


class PlanDialog(QDialog):
    """Muestra el plan completo y pide confirmación antes de tocar el sistema."""

    def __init__(self, parent, texto, simular):
        super().__init__(parent)
        self.setWindowTitle("Nex Arch · Plan de cambios")
        self.setMinimumSize(720, 480)
        capa = QVBoxLayout(self)
        titulo = QLabel("REVISA EL PLAN ANTES DE APLICAR")
        titulo.setObjectName("Titulo")
        aviso = "Modo simulación: no se cambiará nada." if simular else \
            "Estos cambios modifican el sistema. Se pedirá la contraseña de administrador una sola vez."
        subtitulo = QLabel(aviso)
        subtitulo.setObjectName("Subtitulo")
        subtitulo.setWordWrap(True)
        detalle = QTextEdit()
        detalle.setReadOnly(True)
        detalle.setPlainText(texto)
        botones = QHBoxLayout()
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        aplicar = QPushButton("Aplicar cambios")
        aplicar.setObjectName("Primario")
        aplicar.clicked.connect(self.accept)
        botones.addStretch()
        botones.addWidget(cancelar)
        botones.addWidget(aplicar)
        capa.addWidget(titulo)
        capa.addWidget(subtitulo)
        capa.addWidget(detalle, 1)
        capa.addLayout(botones)


class Trabajador(QThread):
    """Ejecuta el plan en segundo plano para que la ventana no se bloquee."""

    linea = pyqtSignal(str)
    avance = pyqtSignal(int, int)
    terminado = pyqtSignal(bool)

    def __init__(self, pasos, password, simular):
        super().__init__()
        self.pasos = pasos
        self.password = password
        self.simular = simular

    def run(self):
        ok = nex_plan.ejecutar_plan(
            self.pasos, self.password, self.simular,
            self.linea.emit,
            lambda i, n: self.avance.emit(i, n),
        )
        self.terminado.emit(ok)


# Colores de acento para iconos y categorías
COLOR_CIAN = "#2ee6ff"
COLOR_MAGENTA = "#ff2fb3"
COLOR_VIOLETA = "#9d5cff"
COLOR_VERDE = "#80fab4"
COLOR_AMBAR = "#ffc857"

# Icono de cada opción de tarjeta y de cada página
ICONO_OPCION = {
    "INTEL": "intel", "NVIDIA": "nvidia", "AMD": "amd",
    "SSD / M.2": "disco", "SATA SSD": "disco", "HDD": "disco",
    "Escritorio": "escritorio", "Portátil": "portatil",
    "Seguro": "escudo", "Medio": "gauge", "Extremo": "rayo",
}
ICONO_PAGINA = {
    "Gráficos": "gpu",
    "Almacenamiento": "disco",
    "Tipo de equipo": "portatil",
    "Oficina · LibreOffice": "oficina",
    "Aplicaciones": "apps",
    "Escritorio · Hyprland": "hyprland",
    "Modo de optimización": "gauge",
    "Limpieza del sistema": "limpieza",
}


def _poligono(p, puntos):
    from PyQt6.QtGui import QPolygonF
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in puntos]))


def _dibujar_icono(p, tipo, m, w, c):
    from PyQt6.QtCore import QRectF
    relleno = QColor(c)
    relleno.setAlpha(45)
    p.setBrush(relleno)
    if tipo == "gpu":
        p.drawRoundedRect(QRectF(m, m + w * 0.18, w, w * 0.6), 6, 6)
        for i in range(5):
            x = m + w * (0.12 + i * 0.19)
            p.drawLine(QPointF(x, m + w * 0.78), QPointF(x, m + w))
    elif tipo == "disco":
        p.drawRoundedRect(QRectF(m, m + w * 0.1, w, w * 0.8), 8, 8)
        p.drawEllipse(QPointF(m + w * 0.72, m + w * 0.5), w * 0.1, w * 0.1)
        p.drawLine(QPointF(m + w * 0.12, m + w * 0.62), QPointF(m + w * 0.55, m + w * 0.62))
    elif tipo == "portatil":
        p.drawRoundedRect(QRectF(m + w * 0.12, m + w * 0.08, w * 0.76, w * 0.56), 4, 4)
        p.drawRoundedRect(QRectF(m, m + w * 0.7, w, w * 0.14), 4, 4)
    elif tipo == "escritorio":
        p.drawRoundedRect(QRectF(m, m + w * 0.05, w, w * 0.65), 5, 5)
        p.drawLine(QPointF(m + w / 2, m + w * 0.7), QPointF(m + w / 2, m + w * 0.9))
        p.drawLine(QPointF(m + w * 0.25, m + w * 0.92), QPointF(m + w * 0.75, m + w * 0.92))
    elif tipo == "gauge":
        p.drawArc(QRectF(m, m, w, w), 210 * 16, -240 * 16)
        p.drawLine(QPointF(m + w / 2, m + w / 2), QPointF(m + w * 0.78, m + w * 0.3))
    elif tipo == "oficina":
        p.drawRoundedRect(QRectF(m + w * 0.15, m, w * 0.7, w), 4, 4)
        for i in range(3):
            y = m + w * (0.3 + i * 0.2)
            p.drawLine(QPointF(m + w * 0.3, y), QPointF(m + w * 0.7, y))
    elif tipo == "apps":
        for x in (0, 1):
            for y in (0, 1):
                p.drawRoundedRect(QRectF(m + x * w * 0.55, m + y * w * 0.55, w * 0.42, w * 0.42), 4, 4)
    elif tipo == "hyprland":
        _poligono(p, [(m + w * 0.5 + w * 0.5 * math.cos(math.radians(a)),
                       m + w * 0.5 + w * 0.5 * math.sin(math.radians(a))) for a in range(0, 360, 60)])
    elif tipo == "limpieza":
        p.drawLine(QPointF(m + w * 0.15, m + w * 0.2), QPointF(m + w * 0.85, m + w * 0.2))
        p.drawRoundedRect(QRectF(m + w * 0.25, m + w * 0.3, w * 0.5, w * 0.65), 4, 4)
    elif tipo == "escudo":
        _poligono(p, [(m + w * 0.5, m), (m + w, m + w * 0.2), (m + w * 0.9, m + w * 0.7),
                      (m + w * 0.5, m + w), (m + w * 0.1, m + w * 0.7), (m, m + w * 0.2)])
    elif tipo == "rayo":
        _poligono(p, [(m + w * 0.6, m), (m + w * 0.15, m + w * 0.6), (m + w * 0.5, m + w * 0.6),
                      (m + w * 0.4, m + w), (m + w * 0.85, m + w * 0.4), (m + w * 0.5, m + w * 0.4)])
    else:
        p.drawEllipse(QRectF(m, m, w, w))


# Fabricantes de GPU: etiqueta y color de la marca (sin logotipos, solo el nombre y su color)
MARCAS_GPU_NOMBRE = ("INTEL", "NVIDIA", "AMD")  # nombres de tarjeta que usan un icono de marca
RUTA_MARCAS = RUTA_ASSETS / "marcas"
MARCAS_SVG = {"intel": "intel.svg", "nvidia": "nvidia.svg", "amd": "amd.svg"}  # logotipos (ver assets/marcas/ORIGEN.md)
# Versión más clara de cada color de marca, para que se vea bien sobre fondo oscuro
MARCAS_CLARO = {"intel": "#5cb3ff", "nvidia": "#b8f35a", "amd": "#ff7a7e"}
MARCAS_GPU = {
    "intel": ("intel", "#0071c5"),
    "nvidia": ("NV", "#76b900"),
    "amd": ("AMD", "#ed1c24"),
}


RUTA_LOGOS = RUTA_ASSETS / "logos"
# Aplicación -> archivo de logotipo libre (ver assets/logos/ORIGEN.md)
LOGOS_APP = {
    "Lutris": "lutris.svg", "Prism Launcher": "prismlauncher.svg", "OBS Studio": "obs-studio.svg",
    "Kdenlive": "kdenlive.svg", "Firefox": "firefox.svg", "Brave": "brave.svg",
    "Node.js": "nodejs.svg", "Git": "git.svg",
}


class LogoApp(QWidget):
    """Logotipo libre de una aplicación; si no hay, una ficha de color con sus iniciales."""

    def __init__(self, nombre, tamano=26):
        super().__init__()
        self.nombre = nombre
        self.setFixedSize(tamano, tamano)
        self.render = None
        if nombre in LOGOS_APP:
            from PyQt6.QtSvg import QSvgRenderer
            svg = QSvgRenderer(str(RUTA_LOGOS / LOGOS_APP[nombre]))
            if svg.isValid():
                self.render = svg

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.width()
        if self.render is not None:
            tam = self.render.defaultSize()
            escala = min(t / tam.width(), t / tam.height())
            ancho_f, alto_f = tam.width() * escala, tam.height() * escala
            self.render.render(p, QRectF((t - ancho_f) / 2, (t - alto_f) / 2, ancho_f, alto_f))
        else:
            # Ficha de color estable para cada nombre, con las dos primeras letras
            tonos = [COLOR_CIAN, COLOR_MAGENTA, COLOR_VIOLETA, COLOR_VERDE, COLOR_AMBAR]
            color = QColor(tonos[sum(map(ord, self.nombre)) % len(tonos)])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color.darker(300))
            p.drawRoundedRect(QRectF(0, 0, t, t), t * 0.25, t * 0.25)
            p.setPen(color.lighter(130))
            p.setFont(QFont("DejaVu Sans", max(6, int(t * 0.36)), QFont.Weight.Bold))
            p.drawText(QRectF(0, 0, t, t), Qt.AlignmentFlag.AlignCenter, self.nombre[:2].upper())
        p.end()


class Icono(QWidget):
    """Icono vectorial de color, dibujado con QPainter (sin ficheros externos)."""

    def __init__(self, tipo, color=COLOR_CIAN, tamano=56):
        super().__init__()
        self.tipo = tipo
        # Todos los iconos salen un poco más claros para que se vean bien sobre el fondo oscuro
        self.color = QColor(color).lighter(125)
        self.setFixedSize(tamano, tamano)

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tamano = self.width()
        m, w = tamano * 0.14, tamano * 0.72
        if self.tipo in MARCAS_SVG:
            # Logotipo oficial del fabricante, dibujado como SVG y centrado
            from PyQt6.QtSvg import QSvgRenderer
            render = QSvgRenderer(str(RUTA_MARCAS / MARCAS_SVG[self.tipo]))
            if render.isValid():
                tam = render.defaultSize()
                escala = min(w / tam.width(), w / tam.height())
                ancho_f, alto_f = tam.width() * escala, tam.height() * escala
                destino = QRectF(m + (w - ancho_f) / 2, m + (w - alto_f) / 2, ancho_f, alto_f)
                # Se pinta el logo sobre una capa y se tiñe con una versión más clara del color
                capa = QPixmap(tamano, tamano)
                capa.fill(Qt.GlobalColor.transparent)
                q = QPainter(capa)
                render.render(q, destino)
                q.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                q.fillRect(capa.rect(), QColor(MARCAS_CLARO[self.tipo]))
                q.end()
                p.drawPixmap(0, 0, capa)
        else:
            pen = QPen(self.color, max(2, tamano // 16))
            p.setPen(pen)
            _dibujar_icono(p, self.tipo, m, w, self.color)
        p.end()


def icono_ventana(tipo=None, color=COLOR_CIAN, tamano=64):
    """Imagen para usar como icono de la ventana o del programa."""
    from PyQt6.QtGui import QIcon, QPixmap
    pixmap = QPixmap(tamano, tamano)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(2, tamano // 16)))
    _dibujar_icono(p, tipo or "rayo", tamano * 0.14, tamano * 0.72, QColor(color))
    p.end()
    return QIcon(pixmap)


# Colores de cada tema para las miniaturas: (fondo, acento, secundario)
PALETAS_VISTA = {
    "NEX NEÓN": ("#120a24", "#2ee6ff", "#ff2fb3"),
    "OSCURO": ("#0b1020", "#00d4ff", "#7b5cff"),
    "CLARO": ("#f5f7fa", "#0077b6", "#5b3fd6"),
    "HYDE": ("#0f0f14", "#9d9dff", "#5f5fb0"),
}


class VistaTema(QFrame):
    """Miniatura de un tema: una ventana de muestra con sus colores."""

    pulsada = pyqtSignal(str)

    def __init__(self, nombre):
        super().__init__()
        self.nombre = nombre
        self.seleccionada = False
        self.fondo = fondo_de(nombre)
        self.setMinimumSize(150, 110)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_seleccionada(self, valor):
        self.seleccionada = valor
        self.update()

    def mousePressEvent(self, evento):
        self.pulsada.emit(self.nombre)

    def paintEvent(self, evento):
        _, acento, _ = PALETAS_VISTA.get(self.nombre, ("#111111", "#2ee6ff", "#ff2fb3"))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(3, 3, -3, -3)
        ancho, alto = r.width(), r.height()

        # Fondo de pantalla recortado con esquinas redondeadas
        recorte = QPainterPath()
        recorte.addRoundedRect(float(r.x()), float(r.y()), float(ancho), float(alto), 12, 12)
        p.setClipPath(recorte)
        if not self.fondo.isNull():
            escalada = self.fondo.scaled(ancho, alto, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                         Qt.TransformationMode.SmoothTransformation)
            sx = (escalada.width() - ancho) // 2
            sy = (escalada.height() - alto) // 2
            p.drawPixmap(r.x(), r.y(), escalada, sx, sy, ancho, alto)
        else:
            p.fillRect(r, QColor("#120a24"))

        # Banda inferior con el nombre del tema
        p.fillRect(r.x(), r.bottom() - 30, ancho, 30, QColor(0, 0, 0, 170))
        p.setClipping(False)
        p.setPen(QColor("#f4eaff"))
        p.setFont(QFont("DejaVu Sans Mono", 9, QFont.Weight.Bold))
        p.drawText(r.x(), r.bottom() - 30, ancho, 30, Qt.AlignmentFlag.AlignCenter, self.nombre)

        # Borde: cian/magenta si está elegido
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(acento) if self.seleccionada else QColor("#1f2d52"), 2 if self.seleccionada else 1))
        p.drawRoundedRect(r, 12, 12)
        p.end()


class CheckGlow(QWidget):
    """Insignia de éxito: anillo con halo, rayos animados y una marca de verificación."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 190)
        self.fase = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._avanzar)
        self.timer.start(60)

    def _avanzar(self):
        self.fase = (self.fase + 1) % 120
        self.update()

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        radio = min(self.width(), self.height()) / 3

        p.setPen(QPen(QColor("#2ee6ff"), 2))
        for i in range(24):
            angulo = i * math.pi / 12 + self.fase * 0.01
            r_dentro = radio * 1.15
            r_fuera = radio * (1.5 + 0.2 * math.sin(self.fase / 10 + i))
            p.drawLine(
                QPointF(cx + r_dentro * math.cos(angulo), cy + r_dentro * math.sin(angulo)),
                QPointF(cx + r_fuera * math.cos(angulo), cy + r_fuera * math.sin(angulo)),
            )

        for k in range(6):
            p.setPen(QPen(QColor(46, 230, 255, max(10, 60 - k * 9)), 6 - k))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), radio + k * 3, radio + k * 3)

        p.setPen(QPen(QColor("#80fab4"), 8))
        p.drawEllipse(QPointF(cx, cy), radio, radio)

        p.setPen(QPen(QColor("#80fab4"), 10, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(QPointF(cx - radio * 0.45, cy), QPointF(cx - radio * 0.1, cy + radio * 0.35))
        p.drawLine(QPointF(cx - radio * 0.1, cy + radio * 0.35), QPointF(cx + radio * 0.5, cy - radio * 0.35))
        p.end()


class AnilloProgreso(QWidget):
    """Anillo de progreso con degradado cian, violeta y magenta, y el porcentaje en el centro."""

    def __init__(self):
        super().__init__()
        self.valor = 0
        self.setMinimumSize(200, 200)

    def setValor(self, valor):
        self.valor = max(0, min(100, int(valor)))
        self.update()

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        lado = min(self.width(), self.height()) - 28
        r = QRectF((self.width() - lado) / 2, (self.height() - lado) / 2, lado, lado)
        grosor = 14

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#1f2d52"), grosor))
        p.drawArc(r, 0, 360 * 16)

        degradado = QConicalGradient(r.center(), 90)
        degradado.setColorAt(0.0, QColor(COLOR_CIAN))
        degradado.setColorAt(0.5, QColor(COLOR_VIOLETA))
        degradado.setColorAt(1.0, QColor(COLOR_MAGENTA))
        pluma = QPen(QBrush(degradado), grosor)
        pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pluma)
        p.drawArc(r, 90 * 16, -int(360 * 16 * self.valor / 100))

        p.setPen(QColor("#f4eaff"))
        p.setFont(QFont("DejaVu Sans", 20, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.valor}%")
        p.end()


def leer_discos(simular):
    """Discos para la tabla de almacenamiento (solo lectura)."""
    if simular:
        return [{"nombre": "/dev/sdz", "tamano": "512 GB", "modelo": "Disco de prueba"}]
    try:
        salida = subprocess.run(["lsblk", "-J", "-b", "-d", "-p", "-o", "NAME,SIZE,TYPE,MODEL"],
                                capture_output=True, text=True).stdout
        datos = json.loads(salida)
    except (OSError, ValueError):
        return []
    filas = []
    for d in datos.get("blockdevices", []):
        if d.get("type") == "disk":
            tamano = int(d.get("size") or 0) / 1024**3
            filas.append({"nombre": d["name"], "tamano": f"{tamano:.0f} GB",
                          "modelo": (d.get("model") or "").strip() or "disco"})
    return filas


class NexOptimizerGUI(QMainWindow):
    PASOS = [
        "GPU", "Almacenamiento", "Equipo", "Oficina", "Aplicaciones",
        "Escritorio", "Modo", "Limpieza", "Resumen",
    ]

    def __init__(self, simular=False):
        super().__init__()
        self.simular = simular
        self.sys_info = leer_info_sistema()
        self.estado = {
            "gpu": "NVIDIA",
            "almacenamiento": "SSD / M.2",
            "equipo": "Escritorio",
            "oficina": ["Writer", "Calc", "Impress"],
            "apps": ["GameMode", "VLC", "Firefox"],
            "widgets_hyprland": "Eww (widgets Hyprland)",
            "barra_menu": "Waybar + Rofi",
            "dock": "nwg-dock-hyprland",
            "wallpaper": "hyprpaper (ligero)",
            "tema": "NEX NEÓN",
            "modo": "Medio",
            "debloat": [],
        }
        self.tarjetas = {}
        self._anim = None
        self.trabajador = None
        self.lineas_registro = []
        self._cpu_previa = leer_cpu_muestra()

        self.setWindowTitle("Nex Arch · Asistente de optimización")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(estilo())

        central = QWidget()
        central.setObjectName("Raiz")
        self.setCentralWidget(central)
        capa = QVBoxLayout(central)
        capa.setContentsMargins(22, 16, 22, 0)
        capa.setSpacing(12)

        capa.addLayout(self.crear_cabecera())
        self.stack = QStackedWidget()
        capa.addWidget(self.stack, 1)

        self.crear_pantalla_gpu()
        self.crear_pantalla_almacenamiento()
        self.crear_pantalla_equipo()
        self.crear_pantalla_oficina()
        self.crear_pantalla_apps()
        self.crear_pantalla_hyprland()
        self.crear_pantalla_modo()
        self.crear_pantalla_debloat()
        self.crear_pantalla_final()

        capa.addWidget(self.crear_barra_inferior())
        self.actualizar_paso()

        self.timer_telemetria = QTimer(self)
        self.timer_telemetria.timeout.connect(self.actualizar_telemetria)
        self.timer_telemetria.start(1500)

    # ------------------------------------------------------------------
    # Estructura común
    # ------------------------------------------------------------------

    def crear_cabecera(self):
        fila = QHBoxLayout()
        marca = QLabel()
        logo = QPixmap(str(RUTA_ASSETS / "logo-nex.png"))
        if logo.isNull():
            marca.setText("◆ NEX ARCH")
            marca.setObjectName("Marca")
        else:
            marca.setPixmap(logo.scaledToHeight(46, Qt.TransformationMode.SmoothTransformation))
        brillo(marca, "#ff2fb3", 24)

        self.lbl_paso = QLabel("")
        self.lbl_paso.setObjectName("Paso")
        self.barra_pasos = QProgressBar()
        self.barra_pasos.setTextVisible(False)
        self.barra_pasos.setFixedWidth(260)
        self.barra_pasos.setMaximum(len(self.PASOS))

        fila.addWidget(marca)
        fila.addStretch()
        fila.addWidget(self.lbl_paso)
        fila.addSpacing(16)
        fila.addWidget(self.barra_pasos)
        return fila

    def actualizar_paso(self):
        idx = self.stack.currentIndex()
        self.lbl_paso.setText(f"PASO {idx + 1:02d} / {len(self.PASOS):02d} · {self.PASOS[idx].upper()}")
        self.barra_pasos.setValue(idx + 1)

    def encabezado(self, titulo, subtitulo):
        caja = QVBoxLayout()
        if titulo in ICONO_PAGINA:
            caja.addWidget(Icono(ICONO_PAGINA[titulo], COLOR_CIAN, 52), alignment=Qt.AlignmentFlag.AlignCenter)
        lbl_t = QLabel(titulo)
        lbl_t.setObjectName("Titulo")
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_s = QLabel(subtitulo)
        lbl_s.setObjectName("Subtitulo")
        lbl_s.setWordWrap(True)
        lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caja.addWidget(lbl_t)
        caja.addWidget(lbl_s)
        return caja

    def nueva_pagina(self):
        page = QWidget()
        capa = QVBoxLayout(page)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(16)
        self.stack.addWidget(page)
        return page, capa

    def tarjeta(self, seleccionada=False):
        card = QFrame()
        card.setObjectName("CardSel" if seleccionada else "Card")
        return card

    def ir_a(self, idx):
        self.stack.setCurrentIndex(idx)
        pagina = self.stack.currentWidget()
        efecto = QGraphicsOpacityEffect(pagina)
        pagina.setGraphicsEffect(efecto)
        anim = QPropertyAnimation(efecto, b"opacity", self)
        anim.setDuration(340)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anim = anim
        self.actualizar_paso()

    def siguiente_pagina(self):
        idx = self.stack.currentIndex()
        if idx + 1 < self.stack.count():
            self.ir_a(idx + 1)

    # ------------------------------------------------------------------
    # Tarjetas de selección (GPU, almacenamiento, equipo, modo)
    # ------------------------------------------------------------------

    def crear_tarjetas_seleccion(self, titulo, subtitulo, opciones, clave):
        page, capa = self.nueva_pagina()
        capa.addLayout(self.encabezado(titulo, subtitulo))
        fila = QHBoxLayout()
        fila.setSpacing(18)
        self.tarjetas[clave] = []
        for nombre, desc in opciones:
            card = self.tarjeta(self.estado[clave] == nombre)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(20, 22, 20, 22)
            if nombre in ICONO_OPCION:
                color = MARCAS_GPU[ICONO_OPCION[nombre]][1] if nombre in MARCAS_GPU_NOMBRE \
                    else (COLOR_MAGENTA if self.estado[clave] == nombre else COLOR_CIAN)
                cl.addWidget(Icono(ICONO_OPCION[nombre], color, 64), alignment=Qt.AlignmentFlag.AlignCenter)
            lbl_n = QLabel(nombre)
            lbl_n.setObjectName("Titulo")
            lbl_n.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_d = QLabel(desc)
            lbl_d.setObjectName("Subtitulo")
            lbl_d.setWordWrap(True)
            lbl_d.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn = QPushButton("Seleccionar")
            btn.setObjectName("Primario" if self.estado[clave] == nombre else "")
            btn.clicked.connect(lambda _, v=nombre, c=clave: self.elegir(c, v))
            cl.addStretch()
            cl.addWidget(lbl_n)
            cl.addSpacing(6)
            cl.addWidget(lbl_d)
            cl.addStretch()
            cl.addWidget(btn)
            fila.addWidget(card)
            self.tarjetas[clave].append((nombre, card, btn))
        capa.addLayout(fila, 1)
        return page

    def elegir(self, clave, valor):
        self.estado[clave] = valor
        for nombre, card, btn in self.tarjetas[clave]:
            seleccionada = nombre == valor
            card.setObjectName("CardSel" if seleccionada else "Card")
            card.style().unpolish(card)
            card.style().polish(card)
            btn.setObjectName("Primario" if seleccionada else "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            if seleccionada:
                brillo(card, "#ff2fb3", 30)
            else:
                card.setGraphicsEffect(None)
        QTimer.singleShot(260, self.siguiente_pagina)

    def crear_pantalla_gpu(self):
        self.crear_tarjetas_seleccion(
            "Gráficos",
            "Elige la GPU de tu equipo. Se preparan Mesa, Vulkan y los drivers correspondientes.",
            [
                ("INTEL", "vulkan-intel · intel-media-driver"),
                ("NVIDIA", "nvidia-open · nvidia-utils"),
                ("AMD", "vulkan-radeon"),
            ],
            "gpu",
        )

    def crear_pantalla_almacenamiento(self):
        pagina = self.crear_tarjetas_seleccion(
            "Almacenamiento",
            "En SSD o M.2 se activa el recorte semanal (fstrim).",
            [
                ("SSD / M.2", "Recomendado · fstrim.timer activado"),
                ("SATA SSD", "fstrim.timer activado"),
                ("HDD", "sin recorte: el disco mecánico no lo necesita"),
            ],
            "almacenamiento",
        )
        self.agregar_tabla_discos(pagina)

    def crear_pantalla_equipo(self):
        self.crear_tarjetas_seleccion(
            "Tipo de equipo",
            "Escritorio prioriza el rendimiento sostenido. Portátil prioriza la batería.",
            [
                ("Escritorio", "Rendimiento sostenido y estabilidad"),
                ("Portátil", "power-profiles-daemon · ahorro de batería"),
            ],
            "equipo",
        )

    def crear_pantalla_modo(self):
        self.crear_tarjetas_seleccion(
            "Modo de optimización",
            "Cada nivel incluye el anterior. Extremo cambia el gobernador de CPU y los espejos.",
            [
                ("Seguro", "ZRAM · descargas paralelas · limpieza de caché"),
                ("Medio", "Seguro + swap y caché de ficheros ajustados"),
                ("Extremo", "Medio + CPU en rendimiento, espejos rápidos, sin hibernación"),
            ],
            "modo",
        )

    # ------------------------------------------------------------------
    # Páginas con casillas
    # ------------------------------------------------------------------

    def crear_pantalla_oficina(self):
        page, capa = self.nueva_pagina()
        capa.addLayout(self.encabezado(
            "Oficina · LibreOffice",
            "Se instala LibreOffice con el paquete en español si marcas algún módulo.",
        ))
        grid = QGridLayout()
        grid.setSpacing(16)
        modulos = [
            ("Writer", "Procesador de texto"), ("Calc", "Hojas de cálculo"),
            ("Impress", "Presentaciones"), ("Draw", "Diagramas y esquemas"),
            ("Base", "Bases de datos"), ("Math", "Fórmulas"),
        ]
        self.checks_oficina = []
        for i, (mod, desc) in enumerate(modulos):
            card = self.tarjeta()
            cl = QVBoxLayout(card)
            chk = QCheckBox(f"{mod} · {desc}")
            chk.setChecked(mod in self.estado["oficina"])
            self.checks_oficina.append((mod, chk))
            cl.addWidget(chk)
            grid.addWidget(card, i // 3, i % 3)
        capa.addLayout(grid, 1)
        fila = QHBoxLayout()
        fila.addStretch()
        omitir = QPushButton("Omitir")
        omitir.clicked.connect(lambda: self.cerrar_con("oficina", []))
        guardar = QPushButton("Guardar selección")
        guardar.setObjectName("Primario")
        guardar.clicked.connect(lambda: self.cerrar_con("oficina", [m for m, c in self.checks_oficina if c.isChecked()]))
        fila.addWidget(omitir)
        fila.addWidget(guardar)
        capa.addLayout(fila)

    def cerrar_con(self, clave, valor):
        self.estado[clave] = valor
        self.siguiente_pagina()

    def crear_pantalla_apps(self):
        page, capa = self.nueva_pagina()
        capa.addLayout(self.encabezado(
            "Aplicaciones",
            "Selecciona lo que quieres instalar. Las marcadas como AUR se instalan con yay.",
        ))
        categorias = {
            "GAMING": ["Steam", "Lutris", "Heroic Launcher", "GameMode", "MangoHud", "Prism Launcher"],
            "MULTIMEDIA": ["VLC", "MPV", "OBS Studio", "Kdenlive", "Audacity"],
            "INTERNET": ["Brave", "Firefox", "Chromium", "Vesktop", "qBittorrent"],
            "VARIOS": ["7-Zip / Ark", "btop", "Fastfetch"],
            "DESARROLLO": ["VS Code", "Node.js", "Git", "Docker"],
            "DISEÑO": ["GIMP", "Inkscape", "Krita", "Blender"],
        }
        grid = QGridLayout()
        grid.setSpacing(16)
        self.checks_apps = []
        for col, (cat, apps) in enumerate(categorias.items()):
            card = self.tarjeta()
            cl = QVBoxLayout(card)
            color_cat = [COLOR_MAGENTA, COLOR_CIAN, COLOR_VIOLETA, COLOR_AMBAR][col % 4]
            fila_cat = QHBoxLayout()
            fila_cat.addWidget(Icono({"GAMING": "rayo", "MULTIMEDIA": "apps", "INTERNET": "hyprland",
                                      "VARIOS": "gauge", "DESARROLLO": "apps", "DISEÑO": "hyprland"}[cat], color_cat, 34))
            etiqueta = QLabel(cat)
            etiqueta.setObjectName("Etiqueta")
            etiqueta.setStyleSheet(f"color: {color_cat};")
            fila_cat.addWidget(etiqueta)
            fila_cat.addStretch()
            cl.addLayout(fila_cat)
            for app in apps:
                chk = QCheckBox(app)
                chk.setChecked(app in self.estado["apps"])
                self.checks_apps.append((app, chk))
                fila_app = QHBoxLayout()
                fila_app.addWidget(LogoApp(app, 26))
                fila_app.addWidget(chk, 1)
                cl.addLayout(fila_app)
            cl.addStretch()
            grid.addWidget(card, col // 3, col % 3)
        capa.addLayout(grid, 1)
        continuar = QPushButton("Continuar")
        continuar.setObjectName("Primario")
        continuar.clicked.connect(lambda: self.cerrar_con("apps", [a for a, c in self.checks_apps if c.isChecked()]))
        capa.addWidget(continuar, alignment=Qt.AlignmentFlag.AlignRight)

    def crear_pantalla_hyprland(self):
        page, capa = self.nueva_pagina()
        capa.addLayout(self.encabezado(
            "Escritorio · Hyprland",
            "Hyprland sustituye a Rainmeter y RocketDock: widgets, barra, dock y fondo en Wayland.",
        ))
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(18)

        izquierda = self.tarjeta()
        rejilla = QGridLayout(izquierda)
        rejilla.setContentsMargins(20, 20, 20, 20)
        rejilla.setVerticalSpacing(14)
        self.cmb_wallpaper = self.combo(["hyprpaper (ligero)", "swww (dinámico, AUR)"], self.estado["wallpaper"])
        self.cmb_widgets = self.combo(["Eww (widgets Hyprland)", "AGS (Aylur GTK Shell)", "Conky Wayland", "Ninguno"],
                                      self.estado["widgets_hyprland"])
        self.cmb_barra = self.combo(["Waybar + Rofi", "Waybar + Wofi", "Hyprpanel"], self.estado["barra_menu"])
        self.cmb_dock = self.combo(["nwg-dock-hyprland", "Sin dock"], self.estado["dock"])
        filas = [
            ("Fondo de pantalla", self.cmb_wallpaper),
            ("Widgets", self.cmb_widgets),
            ("Barra y lanzador", self.cmb_barra),
            ("Dock", self.cmb_dock),
        ]
        for i, (etiqueta, combo) in enumerate(filas):
            lbl = QLabel(etiqueta)
            lbl.setObjectName("Etiqueta")
            rejilla.addWidget(lbl, i, 0)
            rejilla.addWidget(combo, i, 1)

        derecha = self.tarjeta()
        dl = QVBoxLayout(derecha)
        dl.setContentsMargins(20, 20, 20, 20)
        etiqueta = QLabel("TEMA")
        etiqueta.setObjectName("Etiqueta")
        self.vista_tema = QLabel("")
        self.vista_tema.setObjectName("Titulo")
        self.vista_tema.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.addWidget(etiqueta)
        self.preview = QLabel()
        self.preview.setFixedSize(320, 180)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.addWidget(self.preview)
        dl.addWidget(self.vista_tema, 1)
        rejilla_temas = QGridLayout()
        self.vistas_tema = []
        for i, nombre in enumerate(["NEX NEÓN", "OSCURO", "CLARO", "HYDE"]):
            vista = VistaTema(nombre)
            vista.pulsada.connect(self.fijar_tema)
            self.vistas_tema.append(vista)
            rejilla_temas.addWidget(vista, i // 2, i % 2)
        dl.addLayout(rejilla_temas)
        self.fijar_tema(self.estado["tema"], animar=False)

        cuerpo.addWidget(izquierda, 1)
        cuerpo.addWidget(derecha, 1)
        capa.addLayout(cuerpo, 1)

        aplicar = QPushButton("Guardar y continuar")
        aplicar.setObjectName("Primario")
        aplicar.clicked.connect(self.guardar_hyprland)
        capa.addWidget(aplicar, alignment=Qt.AlignmentFlag.AlignRight)

    def combo(self, opciones, actual):
        cmb = QComboBox()
        cmb.addItems(opciones)
        if actual in opciones:
            cmb.setCurrentText(actual)
        return cmb

    def fijar_tema(self, nombre, animar=True):
        self.estado["tema"] = nombre
        self.vista_tema.setText(f"{nombre}\nHyprland · Kitty · Waybar")
        imagen = fondo_de(nombre)
        if not imagen.isNull():
            self.preview.setPixmap(imagen.scaled(320, 180, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                 Qt.TransformationMode.SmoothTransformation))
        brillo(self.vista_tema, "#2ee6ff" if nombre == "NEX NEÓN" else "#9d5cff", 26)
        for vista in self.vistas_tema:
            vista.set_seleccionada(vista.nombre == nombre)

    def guardar_hyprland(self):
        self.estado["wallpaper"] = self.cmb_wallpaper.currentText()
        self.estado["widgets_hyprland"] = self.cmb_widgets.currentText()
        self.estado["barra_menu"] = self.cmb_barra.currentText()
        self.estado["dock"] = self.cmb_dock.currentText()
        self.siguiente_pagina()

    def crear_pantalla_debloat(self):
        page, capa = self.nueva_pagina()
        capa.addLayout(self.encabezado(
            "Limpieza del sistema",
            "Tareas de mantenimiento para mantener Arch ligero. Revisarás el plan antes de aplicarlo.",
        ))
        opciones = [
            "Eliminar paquetes huérfanos (pacman -Qtdq)",
            "Limpiar caché antigua de pacman (paccache -rk1)",
            "Desactivar servicios que no uses (bluetooth, cups)",
            "Reducir el diario de systemd a 50 MB",
        ]
        card = self.tarjeta()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(12)
        self.checks_debloat = []
        for op in opciones:
            chk = QCheckBox(op)
            chk.setChecked(True)
            self.checks_debloat.append((op, chk))
            cl.addWidget(chk)
        capa.addWidget(card, 1)
        iniciar = QPushButton("Revisar el plan")
        iniciar.setObjectName("Primario")
        iniciar.clicked.connect(self.ejecutar_optimizacion)
        capa.addWidget(iniciar, alignment=Qt.AlignmentFlag.AlignRight)

    # ------------------------------------------------------------------
    # Resumen final: plan confirmado, ejecución y progreso real
    # ------------------------------------------------------------------

    def crear_pantalla_final(self):
        page, capa = self.nueva_pagina()
        fila = QHBoxLayout()
        fila.setSpacing(18)

        izquierda = self.tarjeta()
        il = QVBoxLayout(izquierda)
        il.setContentsMargins(26, 24, 26, 24)
        il.setSpacing(14)
        self.lbl_estado_final = QLabel("ESPERANDO CONFIRMACIÓN")
        self.lbl_estado_final.setObjectName("Titulo")
        self.progreso = QProgressBar()
        self.progreso.setValue(0)
        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setObjectName("Info")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setTextFormat(Qt.TextFormat.PlainText)
        self.anillo = AnilloProgreso()
        il.addWidget(self.anillo, alignment=Qt.AlignmentFlag.AlignCenter)
        self.check = CheckGlow()
        self.check.setVisible(False)
        il.addWidget(self.check, alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_cuenta = QLabel("")
        self.lbl_cuenta.setObjectName("Info")
        il.addWidget(self.lbl_cuenta, alignment=Qt.AlignmentFlag.AlignCenter)
        il.addWidget(self.lbl_estado_final)
        il.addWidget(self.progreso)
        il.addWidget(self.lbl_resumen, 1)

        botones = QHBoxLayout()
        acerca = QPushButton("Acerca de")
        acerca.clicked.connect(lambda: AcercaDeDialog(self).exec())
        salir = QPushButton("Salir")
        salir.setObjectName("Primario")
        salir.clicked.connect(self.close)
        self.boton_reiniciar = QPushButton("Reiniciar sistema")
        self.boton_reiniciar.setVisible(False)
        self.boton_reiniciar.clicked.connect(self.pedir_reinicio)
        botones.addWidget(acerca)
        botones.addStretch()
        botones.addWidget(self.boton_reiniciar)
        botones.addWidget(salir)
        il.addLayout(botones)

        derecha = self.tarjeta()
        dl = QVBoxLayout(derecha)
        dl.setContentsMargins(24, 24, 24, 24)
        dl.setSpacing(8)
        etiqueta = QLabel("SISTEMA")
        etiqueta.setObjectName("Etiqueta")
        dl.addWidget(etiqueta)
        datos = [
            ("Arch Linux · Hyprland", ""),
            ("Placa", self.sys_info["placa"]),
            ("Procesador", self.sys_info["cpu"]),
            ("Memoria RAM", f"{self.sys_info['ram_gb']} · {self.sys_info['ram_pct']}% en uso"),
        ]
        for titulo, valor in datos:
            lbl = QLabel(f"▸ {titulo}" + (f": {valor}" if valor else ""))
            lbl.setObjectName("Info")
            lbl.setWordWrap(True)
            dl.addWidget(lbl)
        for nombre, total, pct in self.sys_info["discos"]:
            lbl = QLabel(f"▸ {nombre}: {total} GB · {pct}% usado")
            lbl.setObjectName("Info")
            dl.addWidget(lbl)
        dl.addStretch()

        fila.addWidget(izquierda, 3)
        fila.addWidget(derecha, 2)
        capa.addLayout(fila, 1)

    def ejecutar_optimizacion(self):
        self.estado["debloat"] = [o for o, c in self.checks_debloat if c.isChecked()]
        pasos, avisos = nex_plan.construir_plan(self.estado)
        if not pasos:
            self.lbl_resumen.setText("No hay ningún cambio que aplicar.")
            self.siguiente_pagina()
            return

        dialogo = PlanDialog(self, nex_plan.texto_plan(pasos, avisos), self.simular)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return

        password = None
        necesita_root = any(p.root for p in pasos) and os.geteuid() != 0
        if necesita_root and not self.simular:
            password, ok = QInputDialog.getText(
                self, "Contraseña de administrador",
                "Contraseña de sudo (se usa una sola vez):",
                QLineEdit.EchoMode.Password,
            )
            if not ok:
                return

        self.ir_a(self.stack.count() - 1)
        self.progreso.setMaximum(len(pasos))
        self.progreso.setValue(0)
        self.lineas_registro = []
        self.lbl_estado_final.setText("APLICANDO CAMBIOS…")
        self.lbl_resumen.setText("")
        brillo(self.progreso, "#2ee6ff", 22)

        self.trabajador = Trabajador(pasos, password, self.simular)
        self.trabajador.linea.connect(self.recibir_linea)
        self.trabajador.avance.connect(self.recibir_avance)
        self.trabajador.terminado.connect(self.terminar_plan)
        self.trabajador.start()
        password = None  # no guardar la contraseña más tiempo del necesario

    def agregar_tabla_discos(self, pagina):
        """Tabla de discos (solo lectura) bajo las tarjetas de almacenamiento."""
        filas = leer_discos(self.simular)
        tabla = QTableWidget(len(filas), 3)
        tabla.setHorizontalHeaderLabels(["Dispositivo", "Tamaño", "Modelo"])
        tabla.verticalHeader().setVisible(False)
        tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabla.horizontalHeader().setStretchLastSection(True)
        tabla.setMaximumHeight(150)
        for i, fila in enumerate(filas):
            tabla.setItem(i, 0, QTableWidgetItem(fila["nombre"]))
            tabla.setItem(i, 1, QTableWidgetItem(fila["tamano"]))
            tabla.setItem(i, 2, QTableWidgetItem(fila["modelo"]))
        if filas:
            tabla.selectRow(0)
        pagina.layout().addWidget(tabla)
        self.tabla_discos = tabla

    def pedir_reinicio(self):
        """Reinicio con confirmación y cuenta atrás de 3 segundos."""
        respuesta = QMessageBox.question(
            self, "Reiniciar", "¿Reiniciar el equipo ahora? Guarda tu trabajo antes.",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self.cuenta = 3
        self.boton_reiniciar.setEnabled(False)
        self.lbl_cuenta.setText(f"Reiniciando en {self.cuenta}…")
        self.timer_cuenta = QTimer(self)
        self.timer_cuenta.timeout.connect(self._tick_cuenta)
        self.timer_cuenta.start(1000)

    def _tick_cuenta(self):
        self.cuenta -= 1
        if self.cuenta > 0:
            self.lbl_cuenta.setText(f"Reiniciando en {self.cuenta}…")
            return
        self.timer_cuenta.stop()
        self.reiniciar()

    def reiniciar(self):
        if self.simular:
            self.lbl_cuenta.setText("[simulación] systemctl reboot: no se reinicia nada.")
            return
        if os.geteuid() == 0:
            subprocess.Popen(["systemctl", "reboot"])
            return
        clave, ok = QInputDialog.getText(
            self, "Contraseña de administrador", "Contraseña de sudo para reiniciar:",
            QLineEdit.EchoMode.Password,
        )
        if ok:
            subprocess.run(["sudo", "-S", "-p", "", "systemctl", "reboot"], input=clave + "\n", text=True)

    def recibir_linea(self, texto):
        self.lineas_registro.append(texto)
        self.lbl_resumen.setText("\n".join(self.lineas_registro[-12:]))

    def recibir_avance(self, hecho, total):
        self.progreso.setValue(hecho)
        self.anillo.setValor(int(hecho * 100 / max(total, 1)))
        self.lbl_estado_final.setText(f"PASO {hecho} DE {total}")

    def terminar_plan(self, ok):
        self.check.setVisible(ok)
        self.boton_reiniciar.setVisible(ok)
        if ok:
            self.anillo.setValor(100)
        if ok:
            self.progreso.setValue(self.progreso.maximum())
            self.lbl_estado_final.setText("✔ TU EQUIPO ESTÁ LISTO")
            self.lbl_estado_final.setStyleSheet("color: #80fab4;")
        else:
            self.lbl_estado_final.setText("✖ ALGO HA FALLADO · revisa el registro")
            self.lbl_estado_final.setStyleSheet("color: #ff5f7a;")
        if self.simular:
            self.lbl_resumen.setText(self.lbl_resumen.text() + "\n\n(Modo simulación: no se ha cambiado nada.)")

    # ------------------------------------------------------------------
    # Barra inferior con telemetría en vivo
    # ------------------------------------------------------------------

    def crear_barra_inferior(self):
        barra = QFrame()
        barra.setObjectName("Barra")
        bl = QHBoxLayout(barra)
        bl.setContentsMargins(16, 8, 16, 8)
        self.lbl_cpu = QLabel("CPU --%")
        self.lbl_cpu.setObjectName("Etiqueta")
        self.lbl_ram = QLabel(f"RAM {self.sys_info['ram_pct']}%")
        self.lbl_ram.setObjectName("Etiqueta")
        self.lbl_hw = QLabel(f"{self.sys_info['cpu']}  ·  {self.sys_info['ram_gb']}")
        self.lbl_hw.setObjectName("Subtitulo")
        bl.addWidget(self.lbl_hw)
        bl.addStretch()
        bl.addWidget(self.lbl_cpu)
        bl.addSpacing(24)
        bl.addWidget(self.lbl_ram)
        return barra

    def actualizar_telemetria(self):
        total, inactivo = leer_cpu_muestra()
        previa_total, previa_inactivo = self._cpu_previa
        self._cpu_previa = (total, inactivo)
        delta_total = total - previa_total
        if delta_total > 0:
            uso = int(100 * (1 - (inactivo - previa_inactivo) / delta_total))
            self.lbl_cpu.setText(f"CPU {max(0, min(100, uso))}%")
        self.sys_info = leer_info_sistema()
        self.lbl_ram.setText(f"RAM {self.sys_info['ram_pct']}%")


def main():
    simular = "--simular" in sys.argv
    app = QApplication(sys.argv)
    app.setWindowIcon(icono_ventana("rayo", COLOR_CIAN))
    ventana = NexOptimizerGUI(simular=simular)
    ventana.setWindowIcon(icono_ventana("rayo", COLOR_CIAN))
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
