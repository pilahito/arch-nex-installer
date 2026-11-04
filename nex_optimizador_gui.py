#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nex Arch - Asistente gráfico de optimización (PyQt6) inspirado en paneles de tarjetas."""

import os
import sys
import shutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QStackedWidget, QFrame,
    QCheckBox, QComboBox, QProgressBar, QDialog
)

ESTILO_NEX = """
QMainWindow, QDialog { background-color: #0b1320; color: #e2e8f0; font-family: 'Noto Sans', sans-serif; }
QLabel { color: #cbd5e1; }
QLabel#Titulo { color: #ffffff; font-size: 18px; font-weight: bold; }
QLabel#Subtitulo { color: #94a3b8; font-size: 12px; }
QFrame#Card {
    background-color: #111c2d;
    border: 1px solid #1e293b;
    border-radius: 12px;
}
QFrame#CardSeleccionada {
    background-color: #16243a;
    border: 2px solid #00f0ff;
    border-radius: 12px;
}
QFrame#BarraInferior {
    background-color: #080e18;
    border-top: 1px solid #1e293b;
}
QPushButton {
    background-color: #17253b;
    color: #38bdf8;
    border: 1px solid #0284c7;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}
QPushButton:hover { background-color: #0284c7; color: #ffffff; }
QPushButton#BotonPrimario {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
}
QPushButton#BotonPrimario:hover { background-color: #1d4ed8; }
QComboBox {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 4px 8px;
}
QCheckBox { color: #e2e8f0; spacing: 8px; }
QProgressBar {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 5px;
    text-align: center;
    color: #ffffff;
}
QProgressBar::chunk { background-color: #00f0ff; border-radius: 4px; }
"""


def leer_info_sistema():
    cpu = "Procesador Linux"
    if os.path.exists("/proc/cpuinfo"):
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "model name" in line:
                    cpu = line.split(":", 1)[1].strip()
                    break

    placa = "Placa Base Estándar / WSL"
    ruta_placa = "/sys/devices/virtual/dmi/id/board_name"
    if os.path.exists(ruta_placa):
        try:
            with open(ruta_placa, "r", encoding="utf-8") as f:
                placa = f.read().strip()
        except OSError:
            pass

    ram_total_gb = "8 GB"
    ram_pct = 35
    if os.path.exists("/proc/meminfo"):
        info = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                partes = line.split(":")
                if len(partes) == 2:
                    info[partes[0].strip()] = int(partes[1].strip().split()[0])
        total_kb = info.get("MemTotal", 8388608)
        disp_kb = info.get("MemAvailable", 5242880)
        ram_total_gb = f"{round(total_kb / 1048576, 1)} GB"
        ram_pct = int(100 - (disp_kb * 100 / max(total_kb, 1)))

    uso_disco = shutil.disk_usage("/")
    disco_pct = int((uso_disco.used / max(uso_disco.total, 1)) * 100)
    disco_total_gb = f"{round(uso_disco.total / (1024**3), 1)} GB"

    return {
        "cpu": cpu,
        "placa": placa,
        "ram_gb": ram_total_gb,
        "ram_pct": ram_pct,
        "disco_pct": disco_pct,
        "disco_gb": disco_total_gb,
    }


class AcercaDeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NEX Arch · Acerca de")
        self.setFixedSize(380, 230)
        layout = QVBoxLayout(self)

        titulo = QLabel("◆ NEX Arch Optimizer v1.0")
        titulo.setObjectName("Titulo")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        autor = QLabel(
            "Desarrollo: pilahito\n"
            "GitHub: github.com/pilahito\n"
            "PayPal: paypal.me/pilahito\n"
            f"Lo-Fi: {os.environ.get('NEX_LOFI_URL', 'Pendiente de configurar')}"
        )
        autor.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_ok = QPushButton("OK")
        btn_ok.setObjectName("BotonPrimario")
        btn_ok.clicked.connect(self.accept)

        layout.addWidget(titulo)
        layout.addWidget(autor)
        layout.addWidget(btn_ok)


class NexOptimizerGUI(QMainWindow):
    def __init__(self, simular=True):
        super().__init__()
        self.simular = simular
        self.sys_info = leer_info_sistema()
        self.estado = {
            "gpu": "NVIDIA",
            "almacenamiento": "SSD / M.2",
            "equipo": "Escritorio",
            "oficina": ["Writer", "Calc", "Impress"],
            "apps": ["Steam", "GameMode", "VLC", "Brave"],
            "widgets_hyprland": "Eww (Widgets)",
            "barra_menu": "Waybar + Rofi",
            "dock": "nwg-dock-hyprland",
            "wallpaper": "swww (Dinámico)",
            "tema": "NEX NEÓN",
            "modo": "Medio",
            "debloat": ["Limpiar huérfanos pacman", "Limpiar caché pkg"],
        }

        self.setWindowTitle("Nex Arch · Asistente de Optimización")
        self.resize(960, 600)
        self.setStyleSheet(ESTILO_NEX)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 0)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        # Crear las 9 pantallas del flujo
        self.crear_pantalla_gpu()            # 0: Gráficos
        self.crear_pantalla_almacenamiento() # 1: Almacenamiento
        self.crear_pantalla_equipo()         # 2: Tipo de equipo
        self.crear_pantalla_oficina()        # 3: LibreOffice (en lugar de MS Office)
        self.crear_pantalla_apps()           # 4: Aplicaciones por categorías
        self.crear_pantalla_hyprland()       # 5: Personalización (Hyprland en vez de Rainmeter)
        self.crear_pantalla_modo()           # 6: Modo Seguro / Medio / Extremo
        self.crear_pantalla_debloat()        # 7: Debloatware
        self.crear_pantalla_final()          # 8: Progreso + Info del sistema + Listo

        # Barra inferior de telemetría (CPU, Placa, RAM, %)
        main_layout.addWidget(self.crear_barra_inferior())

    def crear_encabezado(self, titulo, subtitulo):
        box = QVBoxLayout()
        lbl_t = QLabel(titulo)
        lbl_t.setObjectName("Titulo")
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_s = QLabel(subtitulo)
        lbl_s.setObjectName("Subtitulo")
        lbl_s.setWordWrap(True)
        lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(lbl_t)
        box.addWidget(lbl_s)
        return box

    def crear_tarjetas_seleccion(self, titulo, subtitulo, opciones, clave_estado):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self.crear_encabezado(titulo, subtitulo))

        cards_layout = QHBoxLayout()
        for nombre, desc in opciones:
            card = QFrame()
            card.setObjectName("Card")
            c_layout = QVBoxLayout(card)
            lbl_n = QLabel(nombre)
            lbl_n.setObjectName("Titulo")
            lbl_n.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_d = QLabel(desc)
            lbl_d.setObjectName("Subtitulo")
            lbl_d.setWordWrap(True)
            lbl_d.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn = QPushButton("Seleccionar")
            btn.clicked.connect(lambda _, v=nombre: self.avanzar_con_valor(clave_estado, v))

            c_layout.addStretch()
            c_layout.addWidget(lbl_n)
            c_layout.addWidget(lbl_d)
            c_layout.addStretch()
            c_layout.addWidget(btn)
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout, 1)
        self.stack.addWidget(page)

    def avanzar_con_valor(self, clave, valor):
        self.estado[clave] = valor
        self.siguiente_pagina()

    def siguiente_pagina(self):
        idx = self.stack.currentIndex()
        if idx + 1 < self.stack.count():
            self.stack.setCurrentIndex(idx + 1)

    def crear_pantalla_gpu(self):
        self.crear_tarjetas_seleccion(
            "Gráficos",
            "Seleccione la GPU de su equipo (Intel, NVIDIA o AMD) para instalar drivers de Arch Linux y Vulkan.",
            [
                ("INTEL", "Mesa + vulkan-intel + intel-media-driver"),
                ("NVIDIA", "nvidia-dkms + nvidia-utils + CUDA/Wayland"),
                ("AMD", "Mesa + xf86-video-amdgpu + vulkan-radeon"),
            ],
            "gpu",
        )

    def crear_pantalla_almacenamiento(self):
        self.crear_tarjetas_seleccion(
            "Almacenamiento",
            "Seleccione el tipo de almacenamiento donde está instalado Arch Linux para ajustar fstrim y el planificador I/O.",
            [
                ("SSD / M.2", "Activa fstrim.timer y scheduler nvme/mq-deadline"),
                ("HDD", "Activa scheduler BFQ y optimiza caché de escritura"),
            ],
            "almacenamiento",
        )

    def crear_pantalla_equipo(self):
        self.crear_tarjetas_seleccion(
            "Tipo de equipo",
            "Seleccione si utiliza un equipo de escritorio o portátil para ajustar la gestión de energía.",
            [
                ("Escritorio", "Ajustes orientados al máximo rendimiento sostenido"),
                ("Portátil", "Activa power-profiles-daemon / TLP para optimizar batería"),
            ],
            "equipo",
        )

    def crear_pantalla_oficina(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self.crear_encabezado(
            "Suite de Oficina (LibreOffice)",
            "Seleccione los módulos de LibreOffice en español que desea instalar o pulse Omitir."
        ))

        grid = QGridLayout()
        modulos = [
            ("Writer", "Procesador de texto"),
            ("Calc", "Hojas de cálculo"),
            ("Impress", "Presentaciones"),
            ("Draw", "Diagramas y esquemas"),
            ("Base", "Base de datos"),
            ("Math", "Fórmulas matemáticas"),
        ]
        self.checks_oficina = []
        for i, (mod, desc) in enumerate(modulos):
            card = QFrame()
            card.setObjectName("Card")
            cl = QVBoxLayout(card)
            chk = QCheckBox(f"{mod} · {desc}")
            chk.setChecked(mod in ("Writer", "Calc", "Impress"))
            self.checks_oficina.append((mod, chk))
            cl.addWidget(chk)
            grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(grid, 1)
        btns = QHBoxLayout()
        btn_inst = QPushButton("Instalar selección")
        btn_inst.setObjectName("BotonPrimario")
        btn_inst.clicked.connect(self.guardar_oficina)
        btn_omitir = QPushButton("Omitir")
        btn_omitir.clicked.connect(lambda: self.avanzar_con_valor("oficina", []))
        btns.addStretch()
        btns.addWidget(btn_inst)
        btns.addWidget(btn_omitir)
        btns.addStretch()
        layout.addLayout(btns)
        self.stack.addWidget(page)

    def guardar_oficina(self):
        self.estado["oficina"] = [m for m, c in self.checks_oficina if c.isChecked()]
        self.siguiente_pagina()

    def crear_pantalla_apps(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self.crear_encabezado(
            "Aplicaciones (apps.conf)",
            "Seleccione las aplicaciones que desea instalar desde los repositorios de Arch Linux."
        ))

        categorias = {
            "GAMING": ["Steam", "Lutris", "Heroic Launcher", "GameMode", "MangoHud", "Prism Launcher"],
            "MULTIMEDIA": ["VLC", "MPV", "OBS Studio", "Kdenlive", "Audacity"],
            "INTERNET": ["Brave", "Firefox", "Chromium", "Discord / Vesktop", "qBittorrent"],
            "VARIOS": ["7-Zip / Ark", "btop", "Fastfetch", "GIMP", "Blender"],
        }
        grid = QGridLayout()
        self.checks_apps = []
        for col, (cat, apps) in enumerate(categorias.items()):
            card = QFrame()
            card.setObjectName("Card")
            cl = QVBoxLayout(card)
            lbl = QLabel(cat)
            lbl.setObjectName("Titulo")
            cl.addWidget(lbl)
            for app in apps:
                chk = QCheckBox(app)
                chk.setChecked(app in self.estado["apps"])
                self.checks_apps.append((app, chk))
                cl.addWidget(chk)
            cl.addStretch()
            grid.addWidget(card, 0, col)

        layout.addLayout(grid, 1)
        btn = QPushButton("Continuar")
        btn.setObjectName("BotonPrimario")
        btn.clicked.connect(self.guardar_apps)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.stack.addWidget(page)

    def guardar_apps(self):
        self.estado["apps"] = [a for a, c in self.checks_apps if c.isChecked()]
        self.siguiente_pagina()

    def crear_pantalla_hyprland(self):
        """Reemplaza Rainmeter, RocketDock y Temas Windows por el ecosistema Hyprland."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self.crear_encabezado(
            "Personalización · Escritorio Hyprland",
            "Configure sus widgets (alternativa a Rainmeter), barra superior, dock y paleta de temas Nex / HyDE."
        ))

        cuerpo = QHBoxLayout()
        panel_izq = QFrame()
        panel_izq.setObjectName("Card")
        izq_l = QGridLayout(panel_izq)

        # Selectores equivalentes a la captura pero para Hyprland
        self.cmb_wallpaper = QComboBox()
        self.cmb_wallpaper.addItems(["swww (Dinámico)", "hyprpaper (Ligero)", "mpvpaper (Video)"])

        self.cmb_widgets = QComboBox()
        self.cmb_widgets.addItems(["Eww (Widgets Hyprland)", "AGS (Aylur Gtk Shell)", "Conky Wayland", "Ninguno"])

        self.cmb_iconos = QComboBox()
        self.cmb_iconos.addItems(["Papirus-Dark", "Tela-Circle-Neon", "Catppuccin-SE"])

        self.cmb_barra = QComboBox()
        self.cmb_barra.addItems(["Waybar + Rofi", "Waybar + Wofi", "Hyprpanel"])

        self.cmb_dock = QComboBox()
        self.cmb_dock.addItems(["nwg-dock-hyprland", "Sin Dock (Tiling puro)"])

        izq_l.addWidget(QLabel("Fondo (Wallpaper):"), 0, 0)
        izq_l.addWidget(self.cmb_wallpaper, 0, 1)
        izq_l.addWidget(QLabel("Widgets (Rainmeter ➔ Hyprland):"), 1, 0)
        izq_l.addWidget(self.cmb_widgets, 1, 1)
        izq_l.addWidget(QLabel("Iconos GTK/Qt:"), 2, 0)
        izq_l.addWidget(self.cmb_iconos, 2, 1)
        izq_l.addWidget(QLabel("Barra y Lanzador:"), 3, 0)
        izq_l.addWidget(self.cmb_barra, 3, 1)
        izq_l.addWidget(QLabel("Dock (RocketDock ➔ Wayland):"), 4, 0)
        izq_l.addWidget(self.cmb_dock, 4, 1)

        panel_der = QFrame()
        panel_der.setObjectName("Card")
        der_l = QVBoxLayout(panel_der)
        lbl_preview = QLabel("Vista previa de Tema: NEX NEÓN\n(Hyprland + Kitty + Waybar)")
        lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        der_l.addWidget(lbl_preview, 1)

        temas_grid = QGridLayout()
        temas = ["NEX NEÓN", "OSCURO", "CLARO", "HYDE", "CATPPUCCIN", "TOKYONIGHT"]
        for i, t in enumerate(temas):
            b_tema = QPushButton(t)
            b_tema.clicked.connect(
                lambda _, nombre=t, lbl=lbl_preview: self.seleccionar_tema(nombre, lbl)
            )
            temas_grid.addWidget(b_tema, i // 3, i % 3)
        der_l.addLayout(temas_grid)

        cuerpo.addWidget(panel_izq, 1)
        cuerpo.addWidget(panel_der, 1)
        layout.addLayout(cuerpo, 1)

        btn_cont = QPushButton("Aplicar y Continuar")
        btn_cont.setObjectName("BotonPrimario")
        btn_cont.clicked.connect(self.guardar_hyprland)
        layout.addWidget(btn_cont, alignment=Qt.AlignmentFlag.AlignRight)
        self.stack.addWidget(page)

    def seleccionar_tema(self, nombre_tema, label_widget):
        self.estado["tema"] = nombre_tema
        label_widget.setText(f"Vista previa de Tema: {nombre_tema}\n(Hyprland + Kitty + Waybar)")

    def guardar_hyprland(self):
        self.estado["wallpaper"] = self.cmb_wallpaper.currentText()
        self.estado["widgets_hyprland"] = self.cmb_widgets.currentText()
        self.estado["barra_menu"] = self.cmb_barra.currentText()
        self.estado["dock"] = self.cmb_dock.currentText()
        self.siguiente_pagina()

    def crear_pantalla_modo(self):
        self.crear_tarjetas_seleccion(
            "Modo de Optimización",
            "Seleccione la intensidad de los ajustes de kernel (sysctl), memoria ZRAM y CPU.",
            [
                ("Seguro", "Recomendado: ZRAM, fstrim y ajustes estables sin riesgo"),
                ("Medio", "Equilibrado: vm.swappiness=10, mejora de watchers y red"),
                ("Extremo", "Máximo rendimiento: gobernador performance y baja latencia"),
            ],
            "modo",
        )

    def crear_pantalla_debloat(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self.crear_encabezado(
            "Debloatware y Limpieza en Arch",
            "Seleccione las tareas de limpieza para mantener el sistema ligero."
        ))

        opciones = [
            "Eliminar paquetes huérfanos (pacman -Qtdq)",
            "Limpiar caché antigua de pacman (paccache -rk1)",
            "Desactivar servicios innecesarios en el arranque (bluetooth/cups si no se usan)",
            "Limpiar registros antiguos de systemd-journald (--vacuum-size=50M)",
        ]
        self.checks_debloat = []
        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        for op in opciones:
            chk = QCheckBox(op)
            chk.setChecked(True)
            self.checks_debloat.append((op, chk))
            cl.addWidget(chk)

        layout.addWidget(card, 1)
        btn = QPushButton("Iniciar Optimización")
        btn.setObjectName("BotonPrimario")
        btn.clicked.connect(self.ejecutar_optimizacion)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.stack.addWidget(page)

    def crear_pantalla_final(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        izq = QFrame()
        izq.setObjectName("Card")
        il = QVBoxLayout(izq)
        self.lbl_estado_final = QLabel("OPTIMIZANDO TU SISTEMA...\nMEJORANDO TU EXPERIENCIA EN ARCH LINUX")
        self.lbl_estado_final.setObjectName("Titulo")
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setValue(0)
        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setWordWrap(True)

        botones_fin = QHBoxLayout()
        btn_acerca = QPushButton("Acerca de")
        btn_acerca.clicked.connect(lambda: AcercaDeDialog(self).exec())
        btn_salir = QPushButton("Salir")
        btn_salir.setObjectName("BotonPrimario")
        btn_salir.clicked.connect(self.close)
        botones_fin.addWidget(btn_acerca)
        botones_fin.addWidget(btn_salir)

        il.addWidget(self.lbl_estado_final)
        il.addWidget(self.barra_progreso)
        il.addWidget(self.lbl_resumen, 1)
        il.addLayout(botones_fin)

        der = QFrame()
        der.setObjectName("Card")
        dl = QVBoxLayout(der)
        t_info = QLabel("Información del sistema:")
        t_info.setObjectName("Titulo")
        dl.addWidget(t_info)
        datos = [
            ("Sistema Operativo", "Arch Linux · Hyprland"),
            ("Placa Madre", self.sys_info["placa"]),
            ("Procesador", self.sys_info["cpu"]),
            ("Memoria RAM", f"{self.sys_info['ram_gb']} ({self.sys_info['ram_pct']}% en uso)"),
            ("Unidad Raíz (/)", f"{self.sys_info['disco_gb']} ({self.sys_info['disco_pct']}% usado)"),
        ]
        for titulo_d, valor_d in datos:
            f_item = QLabel(f"▸ {titulo_d}: {valor_d}")
            dl.addWidget(f_item)
        dl.addStretch()

        layout.addWidget(izq, 3)
        layout.addWidget(der, 2)
        self.stack.addWidget(page)

    def ejecutar_optimizacion(self):
        self.estado["debloat"] = [o for o, c in self.checks_debloat if c.isChecked()]
        self.siguiente_pagina()
        self.barra_progreso.setValue(100)
        modo_txt = "SIMULACIÓN (sin tocar discos)" if self.simular else "REAL"
        self.lbl_estado_final.setText("✔ TU EQUIPO ESTÁ LISTO")
        self.lbl_resumen.setText(
            f"Modo: {modo_txt}\n"
            f"• GPU: {self.estado['gpu']} | Disco: {self.estado['almacenamiento']} | Equipo: {self.estado['equipo']}\n"
            f"• Hyprland: {self.estado['widgets_hyprland']} + {self.estado['barra_menu']} + {self.estado['dock']}\n"
            f"• Tema: {self.estado['tema']} | Nivel: {self.estado['modo']}\n"
            f"• LibreOffice: {', '.join(self.estado['oficina']) or 'Omitido'}\n"
            f"• Apps seleccionadas: {', '.join(self.estado['apps'])}"
        )

    def crear_barra_inferior(self):
        barra = QFrame()
        barra.setObjectName("BarraInferior")
        bl = QHBoxLayout(barra)
        bl.setContentsMargins(12, 6, 12, 6)
        texto_hw = (
            f"CPU: {self.sys_info['cpu']}   |   "
            f"PCB: {self.sys_info['placa']}   |   "
            f"RAM: {self.sys_info['ram_gb']}"
        )
        lbl_hw = QLabel(texto_hw)
        lbl_hw.setObjectName("Subtitulo")
        lbl_medidores = QLabel(
            f"RAM: {self.sys_info['ram_pct']}%   ·   Raíz (/): {self.sys_info['disco_pct']}%"
        )
        bl.addWidget(lbl_hw)
        bl.addStretch()
        bl.addWidget(lbl_medidores)
        return barra


if __name__ == "__main__":
    simular_modo = "--simular" in sys.argv or True
    app = QApplication(sys.argv)
    ventana = NexOptimizerGUI(simular=simular_modo)
    ventana.show()
    sys.exit(app.exec())
