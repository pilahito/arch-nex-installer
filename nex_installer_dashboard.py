#!/usr/bin/env python3
"""Pantalla inicial de NEX OS para el entorno live (vista previa segura)."""

import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
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
QFrame#preview {
  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
    stop:0 #171b42,stop:0.35 #442772,stop:0.7 #8842b7,stop:1 #121735);
  border: 1px solid #a45eff; border-radius: 15px;
}
QFrame#info { background: #1a2038; border: 1px solid #3a4267; border-radius: 12px; }
QPushButton { background: #1a2038; border: 1px solid #3c466c; border-radius: 12px;
  padding: 8px; color: #f5f3ff; font-weight: 600; }
QPushButton:hover { border: 1px solid #b46cff; background: #25284b; }
QPushButton#choice { font-size: 13px; }
QPushButton#choice[selected="true"] { background: #252049; border: 2px solid #aa70ff; }
QPushButton#choice:disabled { color: #79819e; background: #151a2d; border: 1px solid #303754; }
QPushButton#step { text-align: left; padding-left: 13px; border: none; background: transparent; }
QPushButton#step[active="true"] { background: #42328f; border: 1px solid #9b71ff; }
QPushButton#step:disabled { color: #9299b3; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 #852fff,stop:1 #476fff); border: 1px solid #b590ff; font-size: 15px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: #111527; width: 8px; }
QScrollBar::handle:vertical { background: #5b4a9c; border-radius: 4px; }
"""


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
    steps = ('Distribución', 'Escritorio', 'Drivers', 'Almacenamiento', 'Paquetes', 'Finalizar')

    def __init__(self):
        super().__init__()
        self.setWindowTitle('NEX Installer · Arch Linux Setup Experience')
        self.setMinimumSize(1050, 680)
        self.setStyleSheet(STYLE)
        self.feature_buttons = []
        self.step_buttons = []

        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(9)
        self.setCentralWidget(root)

        header = QHBoxLayout()
        mark = label('N', 'brand')
        mark.setStyleSheet('font-size:34px;font-weight:900;color:#9b65ff;')
        header.addWidget(mark)
        brand = QVBoxLayout()
        brand.setSpacing(0)
        brand.addWidget(label('NEX Installer', 'brand'))
        brand.addWidget(label('Arch Linux Setup Experience', 'muted'))
        header.addLayout(brand)
        header.addStretch()
        header.addWidget(label('♧  Arch Linux     ╱╱  Hyprland Ready', 'muted'))
        outer.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(10)
        outer.addLayout(body, 1)
        nav = QFrame()
        nav.setObjectName('navigation')
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
        nav_layout.addWidget(label('NEX OS  ·  x86_64\nVista previa segura', 'muted'))
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
        self.pages = QStackedWidget()
        self.pages.addWidget(self.first_page())
        for title, description in (
            ('Escritorio', 'Hyprland es el escritorio preparado para esta vista previa.'),
            ('Drivers', 'Aquí se revisarán los controladores compatibles con el equipo.'),
            ('Almacenamiento', 'La selección de disco requiere una comprobación y confirmación independientes.'),
            ('Paquetes', 'Las herramientas opcionales se revisarán antes de conectar el instalador real.'),
            ('Resumen', 'Vista previa: la instalación está desactivada hasta verificar el proceso completo.'),
        ):
            self.pages.addWidget(self.info_page(title, description))
        content_layout.addWidget(self.pages, 1)
        body.addWidget(content, 1)

        side = QFrame()
        side.setObjectName('side')
        side.setFixedWidth(250)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(8)
        preview = QFrame()
        preview.setObjectName('preview')
        preview.setMinimumHeight(210)
        preview_layout = QVBoxLayout(preview)
        preview_layout.addWidget(label('NEX OS  ·  HYPRLAND', 'muted'))
        preview_layout.addStretch()
        preview_title = label('N E X', 'brand')
        preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_title.setStyleSheet('font-size:32px;font-weight:900;color:#f1d8ff;')
        preview_layout.addWidget(preview_title)
        preview_subtitle = label('Arch Linux  /  Hyprland', 'muted')
        preview_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_subtitle)
        preview_layout.addStretch()
        side_layout.addWidget(preview)
        side_layout.addLayout(section('Información del equipo', 'Datos detectados en el entorno live.'))
        for title, value in (
            ('CPU', cpu_text()), ('RAM', ram_text()),
            ('GPU', 'Se revisará en Drivers'), ('Disco', 'Sin seleccionar'),
        ):
            card = QFrame()
            card.setObjectName('info')
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 7, 10, 7)
            card_layout.setSpacing(1)
            card_layout.addWidget(label(title))
            detail = label(value, 'muted')
            detail.setWordWrap(True)
            card_layout.addWidget(detail)
            side_layout.addWidget(card)
        side_layout.addStretch()
        body.addWidget(side)

        footer = QFrame()
        footer.setObjectName('panel')
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 12, 8)
        footer_layout.addWidget(label('△  Arch Linux Installer (NEX)'))
        footer_layout.addStretch()
        self.status = label('Hyprland  ·  Vista previa  ·  Sin cambios en discos', 'muted')
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

    def first_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 4, 4)
        layout.setSpacing(12)
        layout.addLayout(section('◈  Distribución', 'Arch Linux es la base disponible en esta ISO.'))
        row = QGridLayout()
        row.setSpacing(9)
        for index, (icon, title, description, available) in enumerate((
            ('△', 'Arch Linux', 'Flexible y personalizable', True),
            ('◉', 'Ubuntu', 'Próximamente', False),
            ('◇', 'Generic Linux', 'Próximamente', False),
        )):
            button = self.choice(icon, title, description, 100, available, index == 0)
            row.addWidget(button, 0, index)
        layout.addLayout(row)
        layout.addLayout(section('▣  Escritorio / compositor', 'Elige el aspecto del entorno NEX.'))
        desktop_row = QGridLayout()
        desktop_row.setSpacing(9)
        for index, (icon, title, description, available) in enumerate((
            ('╱╱', 'Hyprland', 'Recomendado', True),
            ('K', 'KDE Plasma', 'Próximamente', False),
            ('●', 'GNOME', 'Próximamente', False),
            ('✦', 'XFCE', 'Próximamente', False),
        )):
            button = self.choice(icon, title, description, 100, available, index == 0)
            desktop_row.addWidget(button, 0, index)
        layout.addLayout(desktop_row)
        layout.addLayout(section('◇  Opciones adicionales', 'Selección visual; se revisará antes de habilitar la instalación.'))
        features = QGridLayout()
        features.setSpacing(8)
        for index, (icon, title) in enumerate((
            ('⚒', 'Juegos'), ('◈', 'Drivers NVIDIA'), ('</>', 'Desarrollo'),
            ('▣', 'Multimedia'), ('◌', 'Ahorro de energía'), ('⚡', 'Rendimiento'),
        )):
            button = QPushButton(f'{icon}  {title}    ○')
            button.setCheckable(True)
            button.setMinimumHeight(43)
            button.setToolTip('Selección de vista previa; no instala paquetes')
            button.toggled.connect(lambda checked, target=button: self.toggle_feature(target, checked))
            self.feature_buttons.append(button)
            features.addWidget(button, index // 3, index % 3)
        layout.addLayout(features)
        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    @staticmethod
    def choice(icon, title, description, height, available, selected):
        button = QPushButton(f'{icon}\n{title}\n{description}')
        button.setObjectName('choice')
        button.setMinimumHeight(height)
        button.setEnabled(available)
        button.setProperty('selected', selected)
        return button

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

    def advance(self):
        index = self.pages.currentIndex()
        if index < len(self.steps) - 1:
            self.pages.setCurrentIndex(index + 1)
            self.title.setText(self.steps[index + 1])
            self.back.setEnabled(True)
            self.update_steps(index + 1)
            if index + 1 == len(self.steps) - 1:
                self.next.setText('Instalación desactivada')
                self.next.setEnabled(False)
        else:
            self.subtitle.setText('La instalación está desactivada hasta completar la validación.')
            self.next.setEnabled(False)

    def previous(self):
        index = max(0, self.pages.currentIndex() - 1)
        self.pages.setCurrentIndex(index)
        self.title.setText('Selecciona tu distribución' if index == 0 else self.steps[index])
        self.back.setEnabled(index > 0)
        self.update_steps(index)
        self.next.setEnabled(True)
        self.next.setText('Continuar  →')
        self.subtitle.setText('Elige la base de NEX OS y personaliza tu escritorio.')

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
