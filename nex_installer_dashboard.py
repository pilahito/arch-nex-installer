#!/usr/bin/env python3
"""Pantalla inicial de NEX OS para el entorno live (vista previa segura)."""

import os
import sys
import json
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtSvg import QSvgRenderer

import nex_installer_pages as paginas
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)


STYLE = """
QWidget { background: #0b0e1b; color: #f5f3ff; font-family: 'DejaVu Sans'; }
QLabel { background: transparent; border: none; }
QLabel#muted { color: #abb3cf; }
QLabel#section { font-size: 17px; font-weight: 700; }
QLabel#brand { font-size: 25px; font-weight: 800; }
QFrame#panel, QFrame#side, QFrame#navigation {
  background: #111527; border: 1px solid #333a59; border-radius: 16px;
}
QFrame#header {
  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
    stop:0 #0b0e1b,stop:0.48 #121329,stop:0.78 #281748,stop:1 #0b0e1b);
  border: none; border-radius: 12px;
}
QFrame#info { background: #1a2038; border: 1px solid #3a4267; border-radius: 12px; }
QFrame#choiceCard { background: #1a2035; border: 1px solid #455074; border-radius: 15px; }
QFrame#choiceCard[selected="true"] { background: #242044; border: 2px solid #ad75ff; }
QFrame#choiceCard[available="false"] { background: #151a2b; border: 1px solid #333b58; }
QFrame#choiceCard[available="false"] QLabel { color: #858eac; }
QPushButton { background: #1a2038; border: 1px solid #3c466c; border-radius: 12px;
  padding: 8px; color: #f5f3ff; font-weight: 600; }
QPushButton:hover { border: 1px solid #b46cff; background: #25284b; }
QPushButton#feature { text-align: left; padding-left: 11px; background: #1b2037; }
QPushButton#feature:checked { background: #33265b; border: 1px solid #a374ff; }
QPushButton#step { text-align: left; padding-left: 13px; border: none; background: transparent; }
QPushButton#step[active="true"] { background: #42328f; border: 1px solid #9b71ff; }
QPushButton#step:disabled { color: #9299b3; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #852fff,stop:1 #476fff); border: 1px solid #b590ff; font-size: 15px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: #111527; width: 8px; }
QScrollBar::handle:vertical { background: #5b4a9c; border-radius: 4px; }
"""

DIR = Path(__file__).resolve().parent


def catalogo_temas():
    ruta = DIR / 'tema' / 'catalogo.json'
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.is_file() else []


def colores_tema(identificador):
    ruta = DIR / 'tema' / 'paletas' / f'{identificador}.env'
    valores = {}
    if ruta.is_file():
        for linea in ruta.read_text(encoding='utf-8').splitlines():
            if '=' in linea and not linea.startswith('#'):
                clave, valor = linea.split('=', 1)
                valores[clave] = valor.strip('"')
    return valores


def color(value):
    return QColor(value)


class NexMark(QWidget):
    """Marca vectorial que se mantiene nítida en cualquier resolución."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(68, 59)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        font = QFont('DejaVu Sans', 48, QFont.Weight.Black)
        font.setItalic(True)
        path.addText(0, 51, font, 'N')
        gradient = QLinearGradient(0, 0, 66, 55)
        gradient.setColorAt(0, color('#2dd7ff'))
        gradient.setColorAt(0.5, color('#497cff'))
        gradient.setColorAt(1, color('#a34bff'))
        painter.fillPath(path, gradient)


class MountainArt(QWidget):
    """Paisaje decorativo de la barra de pasos."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(155)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 205, self.height() / 155)
        sky = QLinearGradient(0, 0, 205, 155)
        sky.setColorAt(0, color('#171b40'))
        sky.setColorAt(1, color('#4e36a2'))
        painter.fillRect(QRectF(0, 0, 205, 155), sky)
        ridge = QPainterPath()
        ridge.moveTo(0, 120)
        ridge.lineTo(42, 73)
        ridge.lineTo(90, 107)
        ridge.lineTo(141, 35)
        ridge.lineTo(205, 89)
        ridge.lineTo(205, 155)
        ridge.lineTo(0, 155)
        painter.fillPath(ridge, color('#a46bfa'))
        shadow = QPainterPath()
        shadow.moveTo(0, 133)
        shadow.lineTo(47, 94)
        shadow.lineTo(92, 120)
        shadow.lineTo(141, 41)
        shadow.lineTo(205, 106)
        shadow.lineTo(205, 155)
        shadow.lineTo(0, 155)
        painter.fillPath(shadow, color('#281e64'))
        snow = QPainterPath()
        snow.moveTo(126, 65)
        snow.lineTo(141, 41)
        snow.lineTo(165, 67)
        snow.lineTo(148, 58)
        snow.lineTo(137, 66)
        painter.fillPath(snow, color('#dcb4ff'))
        trees = QPainterPath()
        for x, height in ((8, 34), (31, 47), (65, 31), (81, 42), (181, 29)):
            trees.moveTo(x, 155)
            trees.lineTo(x + 8, 155 - height)
            trees.lineTo(x + 17, 155)
        painter.fillPath(trees, color('#0d1431'))


class MiniDesktop(QWidget):
    """Miniatura vectorial del escritorio NEX/Hyprland."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(245)
        self.theme_id = 'neon'

    def set_theme(self, identificador):
        self.theme_id = identificador
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 500, self.height() / 300)
        if self.theme_id != 'neon':
            self.paint_theme(painter)
            return
        wall = QLinearGradient(0, 0, 500, 300)
        wall.setColorAt(0, color('#15172f'))
        wall.setColorAt(0.54, color('#62309b'))
        wall.setColorAt(1, color('#111629'))
        painter.setPen(QPen(color('#a260eb'), 2))
        painter.setBrush(wall)
        painter.drawRoundedRect(QRectF(2, 2, 496, 296), 17, 17)
        painter.setPen(Qt.PenStyle.NoPen)
        ribbon = QPainterPath()
        ribbon.moveTo(190, 0)
        ribbon.cubicTo(350, 85, 280, 105, 500, 15)
        ribbon.lineTo(500, 76)
        ribbon.cubicTo(290, 142, 343, 132, 120, 300)
        ribbon.lineTo(25, 300)
        ribbon.cubicTo(270, 130, 300, 127, 190, 0)
        painter.fillPath(ribbon, color('#a95aee'))
        shine = QPainterPath()
        shine.moveTo(305, 0)
        shine.cubicTo(408, 79, 325, 150, 490, 300)
        shine.lineTo(500, 300)
        shine.lineTo(500, 0)
        painter.fillPath(shine, color('#492783'))
        painter.setBrush(color('#0d1123'))
        painter.setPen(QPen(color('#b778ec'), 1))
        painter.drawRoundedRect(QRectF(13, 14, 474, 25), 10, 10)
        painter.setPen(color('#eee3ff'))
        painter.setFont(QFont('DejaVu Sans', 10, QFont.Weight.Bold))
        painter.drawText(QRectF(25, 17, 80, 20), 'NEX  ●  1  2  3')
        painter.drawText(QRectF(410, 17, 68, 20), '23:47')
        painter.setBrush(color('#0c1020'))
        painter.setPen(QPen(color('#8265bc'), 1))
        painter.drawRoundedRect(QRectF(28, 78, 275, 155), 13, 13)
        painter.setPen(color('#dbaeff'))
        painter.setFont(QFont('DejaVu Sans Mono', 10))
        for line, text in enumerate(('nex@arch ~', 'OS: Arch Linux', 'DE: Hyprland', 'Shell: zsh', 'nex@arch ~ $')):
            painter.drawText(QRectF(44, 93 + 25 * line, 250, 21), text)
        painter.setBrush(color('#12182d'))
        painter.setPen(QPen(color('#9985db'), 1))
        painter.drawRoundedRect(QRectF(222, 126, 245, 142), 12, 12)
        painter.setPen(color('#ede3ff'))
        painter.setFont(QFont('DejaVu Sans', 10, QFont.Weight.Bold))
        painter.drawText(QRectF(239, 133, 200, 20), 'Home                        ×')
        painter.setBrush(color('#a881f7'))
        painter.setPen(Qt.PenStyle.NoPen)
        for x, y in ((248, 174), (313, 174), (378, 174), (248, 225), (313, 225), (378, 225)):
            painter.drawRoundedRect(QRectF(x, y, 30, 20), 4, 4)
        painter.setPen(color('#d5c8f7'))
        painter.setFont(QFont('DejaVu Sans', 8))
        for x, text in ((241, 'Desktop'), (310, 'Docs'), (377, 'Media')):
            painter.drawText(QRectF(x, 197, 55, 15), text)

    def paint_theme(self, painter):
        valores = colores_tema(self.theme_id)
        fondo = color('#' + valores.get('FONDO', '0b0e1b'))
        panel = color('#' + valores.get('PANEL', '1a2038'))
        acento = color('#' + valores.get('ACENTO', 'a47cff'))
        texto = color('#' + valores.get('TEXTO', 'f5f3ff'))
        ruta = DIR / 'tema' / 'fondos' / f'{self.theme_id}.png'
        imagen = QPixmap(str(ruta))
        painter.setPen(QPen(acento, 2))
        painter.setBrush(fondo)
        painter.drawRoundedRect(QRectF(2, 2, 496, 296), 15, 15)
        if not imagen.isNull():
            recorte = QPainterPath()
            recorte.addRoundedRect(QRectF(3, 3, 494, 294), 14, 14)
            painter.setClipPath(recorte)
            painter.drawPixmap(QRectF(3, 3, 494, 294), imagen, QRectF(imagen.rect()))
            painter.setClipping(False)
        painter.setPen(QPen(acento, 1))
        painter.setBrush(panel)
        painter.drawRoundedRect(QRectF(13, 15, 474, 25), 11, 11)
        painter.setPen(texto)
        painter.setFont(QFont('DejaVu Sans Mono', 10, QFont.Weight.Bold))
        painter.drawText(QRectF(25, 19, 240, 18), 'NEX  ●  1  2  3')
        painter.drawText(QRectF(421, 19, 60, 18), '23:47')
        if self.theme_id.startswith('puntos'):
            self.paint_dots(painter, acento, panel, texto)
        else:
            painter.setBrush(panel)
            painter.setPen(QPen(acento, 1))
            painter.drawRoundedRect(QRectF(26, 83, 267, 153), 12, 12)
            painter.setPen(texto)
            painter.setFont(QFont('DejaVu Sans Mono', 11))
            for index, linea in enumerate(('nex@arch ~', 'OS: Arch Linux', 'DE: Hyprland',
                                           'Tema: ' + self.theme_id, '$ _')):
                painter.drawText(QRectF(43, 99 + 24 * index, 235, 21), linea)
            painter.setBrush(panel)
            painter.setPen(QPen(acento, 1))
            painter.drawRoundedRect(QRectF(224, 130, 245, 134), 12, 12)
            painter.setPen(texto)
            painter.drawText(QRectF(241, 144, 190, 20), 'Escritorio NEX')
            painter.setBrush(acento)
            painter.setPen(Qt.PenStyle.NoPen)
            for x, y in ((248, 186), (313, 186), (378, 186),
                         (248, 225), (313, 225), (378, 225)):
                painter.drawRoundedRect(QRectF(x, y, 30, 19), 4, 4)

    @staticmethod
    def paint_dots(painter, acento, panel, texto):
        painter.setBrush(panel)
        painter.setPen(QPen(acento, 1))
        for rect in (QRectF(22, 76, 290, 185), QRectF(324, 76, 154, 86),
                     QRectF(324, 173, 154, 88)):
            painter.drawRoundedRect(rect, 15, 15)
        patrones = {
            '2': ('111', '001', '111', '100', '111'),
            '3': ('111', '001', '111', '001', '111'),
            ':': ('000', '010', '000', '010', '000'),
            '4': ('101', '101', '111', '001', '001'),
            '7': ('111', '001', '010', '010', '010'),
        }
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(texto)
        for indice, digito in enumerate('23:47'):
            for fila, bits in enumerate(patrones[digito]):
                for columna, bit in enumerate(bits):
                    if bit == '1':
                        x = 44 + indice * 48 + columna * 12
                        y = 126 + fila * 13
                        painter.drawEllipse(QRectF(x, y, 7, 7))
        painter.setPen(texto)
        painter.setFont(QFont('DejaVu Sans Mono', 9))
        painter.drawText(QRectF(42, 214, 250, 21), 'Buenas noches · NEX OS')
        painter.setPen(acento)
        painter.setFont(QFont('DejaVu Sans Mono', 20, QFont.Weight.Bold))
        painter.drawText(QRectF(341, 91, 126, 55), '◌ 23°')
        painter.drawText(QRectF(341, 192, 126, 50), 'CPU  8%')


class ThemeCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, entrada):
        super().__init__()
        self.entrada = entrada
        self.selected = entrada['id'] == 'neon'
        self.wallpaper = QPixmap(str(DIR / 'tema' / 'fondos' / f"{entrada['id']}.png"))
        self.setMinimumHeight(118)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(entrada['descripcion'])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        acento = color('#' + colores_tema(self.entrada['id']).get('ACENTO', 'a47cff'))
        painter.setPen(QPen(acento if self.selected else color('#47506d'), 2 if self.selected else 1))
        painter.setBrush(color('#151a2e'))
        painter.drawRoundedRect(rect, 12, 12)
        if not self.wallpaper.isNull():
            recorte = QPainterPath()
            recorte.addRoundedRect(rect.adjusted(2, 2, -2, -2), 10, 10)
            painter.setClipPath(recorte)
            painter.drawPixmap(rect.adjusted(3, 3, -3, -3), self.wallpaper, QRectF(self.wallpaper.rect()))
            painter.setClipping(False)
        painter.fillRect(QRectF(rect.left() + 3, rect.bottom() - 35, rect.width() - 6, 32), color('#cc101424'))
        painter.setPen(color('#f6f3ff'))
        painter.setFont(QFont('DejaVu Sans', 11, QFont.Weight.Bold))
        painter.drawText(QRectF(rect.left() + 12, rect.bottom() - 31, rect.width() - 24, 24),
                         Qt.AlignmentFlag.AlignVCenter, self.entrada['nombre'])

    def mousePressEvent(self, event):
        self.clicked.emit(self.entrada['id'])
        super().mousePressEvent(event)


CARPETAS_LOGOS = ('assets/logos', 'assets/marcas', 'setup/assets/logos', 'setup/assets/marcas',
                  'nex-setup/assets/logos', 'nex-setup/assets/marcas')
ARCHIVO_LOGO = {
    'Arch Linux': 'arch.svg', 'Ubuntu': 'ubuntu.svg', 'Linux genérico': 'tux.svg',
    'Hyprland': 'hyprland.svg', 'KDE Plasma': 'kde.svg', 'GNOME': 'gnome.svg', 'XFCE': 'xfce.svg',
    'Intel': 'intel.svg', 'NVIDIA': 'nvidia.svg', 'AMD': 'amd.svg',
}


def ruta_logo(nombre):
    """Logotipo libre guardado en assets/ (o en el Nex Setup incluido); None si no existe."""
    archivo = ARCHIVO_LOGO.get(nombre)
    if not archivo:
        return None
    for carpeta in CARPETAS_LOGOS:
        ruta = DIR / carpeta / archivo
        if ruta.is_file():
            return ruta
    return None


def logos_gpu():
    return {clave: ruta_logo(nombre) for clave, nombre in (('INTEL', 'Intel'), ('NVIDIA', 'NVIDIA'), ('AMD', 'AMD'))}


class LogoSvg(QWidget):
    """Dibuja un logotipo SVG centrado y a su proporción."""

    def __init__(self, ruta, lado=52):
        super().__init__()
        self.render = QSvgRenderer(str(ruta))
        self.setFixedSize(lado + 24, lado)
        self.lado = lado

    def paintEvent(self, event):
        if not self.render.isValid():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tam = self.render.defaultSize()
        escala = min((self.width()) / max(tam.width(), 1), self.height() / max(tam.height(), 1))
        ancho, alto = tam.width() * escala, tam.height() * escala
        self.render.render(painter, QRectF((self.width() - ancho) / 2, (self.height() - alto) / 2, ancho, alto))
        painter.end()


class ChoiceCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon, title, description, available, selected, height, logo=None):
        super().__init__()
        self.setObjectName('choiceCard')
        self.setProperty('available', available)
        self.setProperty('selected', selected)
        self.available = available
        self.setMinimumHeight(height)
        self.setCursor(Qt.CursorShape.PointingHandCursor if available else Qt.CursorShape.ArrowCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 8, 9, 8)
        layout.setSpacing(3)
        if logo is not None and Path(logo).is_file():
            layout.addWidget(LogoSvg(logo), alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            symbol = label(icon)
            symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
            symbol.setStyleSheet('font-size:31px;font-weight:800;color:#a47cff;')
            layout.addWidget(symbol)
        heading = label(title)
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setStyleSheet('font-size:14px;font-weight:700;')
        layout.addWidget(heading)
        detail = label(description, 'muted')
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setWordWrap(True)
        layout.addWidget(detail)

    def mousePressEvent(self, event):
        if self.available:
            self.clicked.emit()
        super().mousePressEvent(event)


def label(text, kind=None):
    item = QLabel(text)
    if kind:
        item.setObjectName(kind)
    return item


def section(title, subtitle):
    box = QVBoxLayout()
    box.setSpacing(2)
    box.addWidget(label(title, "section"))
    caption = label(subtitle, "muted")
    caption.setWordWrap(True)
    box.addWidget(caption)
    return box


def ram_text():
    try:
        with open('/proc/meminfo', encoding='utf-8') as source:
            for line in source:
                if line.startswith('MemTotal:'):
                    return f"{int(line.split()[1]) / 1024 / 1024:.1f} GB detectados"
    except OSError:
        pass
    return "Pendiente de detectar"


def cpu_text():
    try:
        with open('/proc/cpuinfo', encoding='utf-8') as source:
            for line in source:
                if line.startswith('model name'):
                    return line.split(':', 1)[1].strip()[:42]
    except OSError:
        pass
    return f"{os.cpu_count() or '?'} núcleos detectados"


class Installer(QMainWindow):
    steps = ('Distribución', 'Escritorio', 'Drivers', 'Almacenamiento', 'Cuenta', 'Finalizar')

    def __init__(self):
        super().__init__()
        self.setWindowTitle('NEX Installer · Arch Linux Setup Experience')
        self.setMinimumSize(1050, 680)
        self.setStyleSheet(STYLE)
        self.theme_catalog = catalogo_temas()
        self.selected_theme = 'neon'
        self.theme_cards = []
        self.feature_buttons = []
        self.step_buttons = []

        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(9)
        self.setCentralWidget(root)

        header_panel = QFrame()
        header_panel.setObjectName('header')
        header = QHBoxLayout(header_panel)
        header.setContentsMargins(5, 0, 7, 0)
        header.addWidget(NexMark())
        brand = QVBoxLayout()
        brand.setSpacing(0)
        brand.addWidget(label('NEX Installer', 'brand'))
        brand.addWidget(label('Arch Linux Setup Experience', 'muted'))
        header.addLayout(brand)
        header.addStretch()
        header.addWidget(label('♧  Arch Linux     │     ╱╱  Hyprland Ready', 'muted'))
        outer.addWidget(header_panel)

        body = QHBoxLayout()
        body.setSpacing(10)
        outer.addLayout(body, 1)
        nav = QFrame()
        nav.setObjectName('navigation')
        self.navigation = nav
        nav.setFixedWidth(205)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(9, 24, 9, 12)
        nav_layout.setSpacing(6)
        for index, step in enumerate(self.steps):
            button = QPushButton(f'  {index + 1}     {step}')
            button.setObjectName('step')
            button.setProperty('active', index == 0)
            button.setMinimumHeight(42)
            button.setEnabled(index == 0)
            self.step_buttons.append(button)
            nav_layout.addWidget(button)
        nav_layout.addStretch()
        nav_layout.addWidget(MountainArt())
        body.addWidget(nav)

        content = QFrame()
        content.setObjectName('panel')
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 14, 16, 14)
        content_layout.setSpacing(10)
        self.title = label('Selecciona tu distribución', 'section')
        content_layout.addWidget(self.title)
        self.subtitle = label('Elige la base de NEX OS y personaliza tu escritorio.', 'muted')
        content_layout.addWidget(self.subtitle)
        self.title.hide()
        self.subtitle.hide()
        self.pages = QStackedWidget()
        self.pages.addWidget(self.first_page())
        self.pages.addWidget(self.theme_page())
        # Páginas reales conectadas al motor de instalación (nex_motor.py)
        self.estado = paginas.Estado()
        self.info_labels = {}
        self.pagina_drivers = paginas.PaginaDrivers(self.estado, ChoiceCard, label, section, logos_gpu())
        self.pagina_disco = paginas.PaginaAlmacenamiento(self.estado, label, section, self.actualizar_disco)
        self.pagina_cuenta = paginas.PaginaCuenta(label, section)
        self.pagina_final = paginas.PaginaFinal(label, section)
        for pagina in (self.pagina_drivers, self.pagina_disco, self.pagina_cuenta, self.pagina_final):
            self.pages.addWidget(pagina)
        content_layout.addWidget(self.pages, 1)
        body.addWidget(content, 1)

        side = QFrame()
        side.setObjectName('side')
        self.side_panel = side
        side.setFixedWidth(340)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(10)
        self.desktop_preview = MiniDesktop()
        side_layout.addWidget(self.desktop_preview, 3)
        side_layout.addLayout(section('Información del equipo', 'Datos detectados en el entorno live.'))
        info_grid = QGridLayout()
        info_grid.setSpacing(7)
        for index, (title, value) in enumerate((
            ('CPU', cpu_text()), ('RAM', ram_text()),
            ('GPU', 'Se revisará en Drivers'), ('Disco', 'Sin seleccionar'),
        )):
            card = QFrame()
            card.setObjectName('info')
            card.setMinimumHeight(74)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 7, 10, 7)
            card_layout.setSpacing(1)
            card_layout.addWidget(label(title))
            detail = label(value, 'muted')
            detail.setWordWrap(True)
            self.info_labels[title] = detail
            card_layout.addWidget(detail)
            info_grid.addWidget(card, index // 2, index % 2)
        side_layout.addLayout(info_grid, 2)
        side_layout.addStretch()
        body.addWidget(side)

        footer = QFrame()
        footer.setObjectName('panel')
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 12, 8)
        footer_layout.addWidget(label('△  Arch Linux Installer (NEX)'))
        footer_layout.addStretch()
        self.status = label('╱╱  Hyprland   │   ' + ('Modo simulación: no se toca ningún disco'
                                                   if paginas.SIMULAR else 'Listo para instalar'), 'muted')
        footer_layout.addWidget(self.status)
        footer_layout.addStretch()
        self.back = QPushButton('Atrás')
        self.back.setEnabled(False)
        self.back.clicked.connect(self.previous)
        footer_layout.addWidget(self.back)
        self.next = QPushButton('Continuar  →')
        self.next.setObjectName('primary')
        self.next.clicked.connect(self.advance)
        footer_layout.addWidget(self.next)
        outer.addWidget(footer)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'navigation'):
            self.navigation.setFixedWidth(max(175, min(245, int(self.width() * 0.15))))
        if hasattr(self, 'side_panel'):
            self.side_panel.setFixedWidth(max(315, min(515, int(self.width() * 0.30))))

    def first_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 4, 4)
        layout.setSpacing(12)
        layout.addLayout(section('◈  Selecciona tu distribución', 'Escoge la base de NEX OS que quieres instalar y personalizar.'))
        row = QGridLayout()
        row.setSpacing(9)
        for index, (icon, title, description, available) in enumerate((
            ('▲', 'Arch Linux', 'Base NEX disponible', True),
            ('◉', 'Ubuntu', 'Próximamente', False),
            ('♧', 'Linux genérico', 'Próximamente', False),
        )):
            button = ChoiceCard(icon, title, description, available, index == 0, 130, logo=ruta_logo(title))
            row.addWidget(button, 0, index)
        layout.addLayout(row)
        layout.addLayout(section('▣  Escritorio / compositor', 'Elige la experiencia de escritorio para NEX OS.'))
        desktop_row = QGridLayout()
        desktop_row.setSpacing(9)
        for index, (icon, title, description, available) in enumerate((
            ('╱╱', 'Hyprland', 'Recomendado', True),
            ('K', 'KDE Plasma', 'Próximamente', False),
            ('●', 'GNOME', 'Próximamente', False),
            ('✦', 'XFCE', 'Próximamente', False),
        )):
            button = ChoiceCard(icon, title, description, available, index == 0, 112, logo=ruta_logo(title))
            desktop_row.addWidget(button, 0, index)
        layout.addLayout(desktop_row)
        layout.addLayout(section('◇  Opciones adicionales', 'Selección visual; se revisará antes de habilitar la instalación.'))
        features = QGridLayout()
        features.setSpacing(8)
        for index, (icon, title) in enumerate((
            ('⚒', 'Juegos'), ('◈', 'Drivers NVIDIA'), ('</>', 'Desarrollo'),
            ('▣', 'Multimedia'), ('◌', 'Ahorro de energía'), ('⚡', 'Rendimiento'),
            ('Aa', 'Fuentes Nerd'), ('◎', 'Iconos Papirus'), ('✉', 'Notificaciones'),
            ('⌗', 'Capturas de pantalla'), ('⎘', 'Portapapeles'), ('ᛒ', 'Bluetooth'),
            ('☼', 'Brillo de pantalla'),
        )):
            button = QPushButton(f'{icon}  {title}    ○')
            button.setObjectName('feature')
            button.setCheckable(True)
            button.setMinimumHeight(52)
            button.setToolTip('Selección de vista previa; no instala paquetes')
            button.toggled.connect(lambda checked, target=button: self.toggle_feature(target, checked))
            button.setProperty('feature_name', title)
            self.feature_buttons.append(button)
            features.addWidget(button, index // 3, index % 3)
        layout.addLayout(features)
        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def theme_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 5, 4, 5)
        layout.setSpacing(12)
        layout.addLayout(section('Elige un diseño para Hyprland',
                                 '14 temas incluidos; descarga y organiza más diseños en NEX Tienda.'))
        tienda = QPushButton('◈  Abrir NEX Tienda  ·  GitHub y mis carpetas')
        tienda.setObjectName('primary')
        tienda.clicked.connect(self.abrir_tienda)
        layout.addWidget(tienda)
        grid = QGridLayout()
        grid.setSpacing(9)
        for index, entrada in enumerate(self.theme_catalog):
            card = ThemeCard(entrada)
            card.clicked.connect(self.select_theme)
            self.theme_cards.append(card)
            grid.addWidget(card, index // 2, index % 2)
        layout.addLayout(grid)
        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def abrir_tienda(self):
        programa = Path(__file__).with_name('nex_theme_store_gui.py')
        if not programa.is_file():
            self.status.setText('NEX Tienda no está disponible en este entorno.')
            return
        subprocess.Popen([sys.executable, str(programa)], cwd=str(programa.parent))

    def select_theme(self, identificador):
        self.selected_theme = identificador
        self.estado.tema = identificador
        for card in self.theme_cards:
            card.selected = card.entrada['id'] == identificador
            card.update()
        self.desktop_preview.set_theme(identificador)
        nombre = next((tema['nombre'] for tema in self.theme_catalog
                       if tema['id'] == identificador), identificador)
        self.status.setText(f'╱╱  Hyprland   │   {nombre}')

    @staticmethod
    def toggle_feature(button, checked):
        button.setProperty('selected', checked)
        button.style().unpolish(button)
        button.style().polish(button)

    @staticmethod
    def info_page(title, description):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(label(title, 'section'))
        detail = label(description, 'muted')
        detail.setWordWrap(True)
        layout.addWidget(detail)
        layout.addStretch()
        return page

    SUBTITULOS = {
        1: 'Elige un diseño de NEX OS para Hyprland.',
        2: 'Controladores de la tarjeta gráfica.',
        3: 'Disco donde se instalará el sistema. Se borrará por completo.',
        4: 'Nombre del equipo, usuario y contraseñas.',
        5: 'Revisa el resumen y pulsa Instalar.',
    }

    def mostrar_pagina(self, index):
        self.pages.setCurrentIndex(index)
        self.title.setVisible(index > 0)
        self.subtitle.setVisible(index > 0)
        self.title.setText('Selecciona tu distribución' if index == 0 else self.steps[index])
        self.subtitle.setText(self.SUBTITULOS.get(index, ''))
        self.back.setEnabled(index > 0)
        self.update_steps(index)
        ultima = index == len(self.steps) - 1
        self.next.setText('Instalar' if ultima else 'Continuar  →')
        self.next.setEnabled(True)
        if ultima:
            self.pagina_final.preparar(self.resumen_texto())

    def advance(self):
        index = self.pages.currentIndex()
        pagina = self.pages.currentWidget()
        error = pagina.validar() if hasattr(pagina, 'validar') else None
        if error:
            self.status.setText('⚠  ' + error)
            return
        if index < len(self.steps) - 1:
            self.mostrar_pagina(index + 1)
        else:
            self.iniciar_instalacion()

    def previous(self):
        self.mostrar_pagina(max(0, self.pages.currentIndex() - 1))

    def funciones_elegidas(self):
        elegidas = [boton.property('feature_name') for boton in self.feature_buttons if boton.isChecked()]
        if 'Drivers NVIDIA' in elegidas and self.estado.gpu is None:
            self.estado.gpu = 'NVIDIA'
        return [nombre for nombre in elegidas if nombre in paginas.PAQUETES_FUNCIONES]

    def actualizar_disco(self):
        detalle = self.info_labels.get('Disco')
        if detalle is not None:
            disco = self.estado.disco
            detalle.setText(f"{disco['nombre']} · {paginas.ti.gib(disco['bytes'])}" if disco else 'Sin seleccionar')

    def resumen_texto(self):
        self.estado.funciones = self.funciones_elegidas()
        v = self.pagina_cuenta.valores()
        disco = self.estado.disco
        paquetes = paginas.paquetes_elegidos(self.estado)
        nombre_tema = next((t['nombre'] for t in self.theme_catalog if t['id'] == self.estado.tema),
                           self.estado.tema)
        return (
            f"Disco:  {disco['nombre']} ({paginas.ti.gib(disco['bytes'])}) — SE BORRARÁ\n"
            f"Equipo:  {v['host']}\n"
            f"Usuario:  {v['usuario']} (con sudo)\n"
            f"Zona horaria:  {v['zona']}\n"
            f"Tema:  {nombre_tema}\n"
            f"Repartido:  {paginas.PARTICIONADOS_UI.get(self.estado.particionado, '')}\n"
            f"Gráficos:  {self.estado.gpu or 'Mesa genérico'}\n"
            f"Funciones:  {', '.join(self.estado.funciones) or 'ninguna'}\n"
            f"Paquetes extra:  {len(paquetes)}"
        )

    def iniciar_instalacion(self):
        disco = self.estado.disco
        if not paginas.confirmar_borrado(self, disco):
            self.status.setText('⚠  Instalación cancelada: no se ha tocado ningún disco.')
            return
        v = self.pagina_cuenta.valores()
        peticion = paginas.motor.Peticion(
            disco=disco['nombre'], tamano_bytes=disco['bytes'], host=v['host'], usuario=v['usuario'],
            zona=v['zona'], pass_usuario=v['pass_usuario'], pass_root=v['pass_root'],
            tema=self.estado.tema, paquetes=paginas.paquetes_elegidos(self.estado),
            particionado=self.estado.particionado,
            simular=paginas.SIMULAR,
        )
        self.next.setEnabled(False)
        self.back.setEnabled(False)
        self.next.setText('Instalando…')
        self.status.setText('╱╱  Hyprland   │   Instalando: no apagues el equipo')
        self.pagina_final.empezar(peticion, self.instalacion_terminada)

    def instalacion_terminada(self, ok):
        self.next.setText('Terminado' if ok else 'Reintentar')
        self.next.setEnabled(not ok)
        self.back.setEnabled(not ok)
        self.status.setText('╱╱  Hyprland   │   ' + ('Instalación completada' if ok else 'La instalación falló'))

    def update_steps(self, current):
        for index, button in enumerate(self.step_buttons):
            button.setEnabled(index <= current)
            button.setProperty('active', index == current)
            button.style().unpolish(button)
            button.style().polish(button)


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont('DejaVu Sans', 9))
    window = Installer()
    window.showMaximized()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
