#!/usr/bin/env python3
"""Páginas reales del panel de NEX OS: drivers, disco, cuenta e instalación.

Se conectan al motor de instalación (nex_motor.py). Con --simular no se toca
ningún disco: se recorren todos los pasos y se muestra el resultado.
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QConicalGradient, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import nex_motor as motor
import nex_instalador as ti  # discos y validadores; no abre curses al importarlo

SIMULAR = "--simular" in sys.argv

PAQUETES_GPU = {
    "INTEL": ["mesa", "vulkan-intel", "intel-media-driver"],
    "NVIDIA": ["nvidia-dkms", "nvidia-utils", "linux-headers"],
    "AMD": ["mesa", "vulkan-radeon"],
}

# Opciones adicionales de la primera pantalla -> paquetes de los repositorios oficiales
PAQUETES_FUNCIONES = {
    "Juegos": ["lutris", "gamemode", "mangohud"],
    "Desarrollo": ["base-devel", "git", "nodejs", "npm"],
    "Multimedia": ["vlc", "mpv", "obs-studio"],
    "Ahorro de energía": ["power-profiles-daemon"],
    "Rendimiento": ["cpupower"],
}


@dataclass
class Estado:
    """Elecciones del usuario, compartidas por todas las páginas."""

    gpu: Optional[str] = None
    disco: Optional[dict] = None
    tema: str = "neon"
    funciones: List[str] = field(default_factory=list)


def detectar_gpu() -> Optional[str]:
    try:
        salida = subprocess.run(["lspci"], capture_output=True, text=True).stdout
    except OSError:
        return None
    for linea in salida.splitlines():
        if re.search(r"VGA|3D|Display", linea):
            bajo = linea.lower()
            if "nvidia" in bajo:
                return "NVIDIA"
            if "amd" in bajo or "radeon" in bajo or "ati " in bajo:
                return "AMD"
            if "intel" in bajo:
                return "INTEL"
    return None


def paquetes_elegidos(estado: Estado) -> List[str]:
    paquetes = list(PAQUETES_GPU.get(estado.gpu or "", []))
    for funcion in estado.funciones:
        paquetes += PAQUETES_FUNCIONES.get(funcion, [])
    return sorted(set(paquetes))


def marcar(widget, propiedad, valor):
    widget.setProperty(propiedad, valor)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class PaginaDrivers(QScrollArea):
    """Controladores de gráficos: se detecta la GPU y se puede cambiar."""

    def __init__(self, estado, fabrica_tarjeta, etiqueta, seccion, logos):
        super().__init__()
        self.estado = estado
        self.setWidgetResizable(True)
        pagina = QWidget()
        capa = QVBoxLayout(pagina)
        capa.setContentsMargins(0, 4, 4, 4)
        capa.setSpacing(12)
        detectada = detectar_gpu()
        if estado.gpu is None:
            estado.gpu = detectada
        capa.addLayout(seccion(
            "Controladores de gráficos",
            f"GPU detectada: {detectada or 'no detectada'}. Elige los controladores que se instalarán."))
        fila = QGridLayout()
        fila.setSpacing(9)
        self.tarjetas = {}
        for i, (clave, titulo, detalle) in enumerate((
            ("INTEL", "Intel", "Mesa, Vulkan y vídeo acelerado"),
            ("NVIDIA", "NVIDIA", "Controlador propietario (DKMS)"),
            ("AMD", "AMD", "Mesa y Vulkan RADV"),
        )):
            tarjeta = fabrica_tarjeta("", titulo, detalle, True, estado.gpu == clave, 150,
                                      logo=logos.get(clave))
            tarjeta.clicked.connect(lambda c=clave: self.elegir(c))
            self.tarjetas[clave] = tarjeta
            fila.addWidget(tarjeta, 0, i)
        capa.addLayout(fila)
        aviso = etiqueta("Si tu GPU no aparece o no hay ninguna, se instala solo Mesa genérico.", "muted")
        aviso.setWordWrap(True)
        capa.addWidget(aviso)
        capa.addStretch()
        self.setWidget(pagina)

    def elegir(self, clave):
        self.estado.gpu = clave
        for nombre, tarjeta in self.tarjetas.items():
            marcar(tarjeta, "selected", nombre == clave)

    def validar(self):
        return None


class TarjetaDisco(QFrame):
    pulsada = pyqtSignal(object)

    def __init__(self, disco, etiqueta):
        super().__init__()
        self.disco = disco
        self.setObjectName("choiceCard")
        self.setProperty("available", True)
        self.setProperty("selected", False)
        self.setMinimumHeight(70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(14, 8, 14, 8)
        capa.setSpacing(2)
        titulo = etiqueta(f"{disco['nombre']}   ·   {ti.gib(disco['bytes'])}")
        titulo.setStyleSheet("font-size:14px;font-weight:700;")
        capa.addWidget(titulo)
        capa.addWidget(etiqueta(disco["modelo"], "muted"))

    def mousePressEvent(self, evento):
        self.pulsada.emit(self.disco)
        super().mousePressEvent(evento)


class PaginaAlmacenamiento(QScrollArea):
    """Elegir el disco donde se instala. El disco del propio ISO no aparece."""

    def __init__(self, estado, etiqueta, seccion, al_cambiar):
        super().__init__()
        self.estado = estado
        self.etiqueta = etiqueta
        self.al_cambiar = al_cambiar
        self.setWidgetResizable(True)
        self.pagina = QWidget()
        self.capa = QVBoxLayout(self.pagina)
        self.capa.setContentsMargins(0, 4, 4, 4)
        self.capa.setSpacing(10)
        self.capa.addLayout(seccion(
            "Disco de instalación",
            "Se borrará TODO el contenido del disco que elijas. Antes de instalar se pedirá confirmarlo."))
        self.lista = QVBoxLayout()
        self.lista.setSpacing(8)
        self.capa.addLayout(self.lista)
        actualizar = QPushButton("Actualizar lista de discos")
        actualizar.clicked.connect(self.cargar)
        self.capa.addWidget(actualizar, alignment=Qt.AlignmentFlag.AlignLeft)
        self.capa.addStretch()
        self.setWidget(self.pagina)
        self.tarjetas = []
        self.cargar()

    def cargar(self):
        while self.lista.count():
            item = self.lista.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tarjetas = []
        discos, medio = ti.detectar_discos()
        if not discos:
            self.lista.addWidget(self.etiqueta(
                "No hay discos aptos: hacen falta al menos 9 GiB y no se ofrece el USB de la ISO.", "muted"))
        if medio:
            self.lista.addWidget(self.etiqueta(f"El medio de instalación ({medio}) no se muestra.", "muted"))
        for disco in discos:
            tarjeta = TarjetaDisco(disco, self.etiqueta)
            tarjeta.pulsada.connect(self.elegir)
            self.tarjetas.append(tarjeta)
            self.lista.addWidget(tarjeta)
        seleccionado = self.estado.disco["nombre"] if self.estado.disco else None
        if seleccionado not in [d["nombre"] for d in discos]:
            self.estado.disco = None
        self.al_cambiar()

    def elegir(self, disco):
        self.estado.disco = disco
        for tarjeta in self.tarjetas:
            marcar(tarjeta, "selected", tarjeta.disco["nombre"] == disco["nombre"])
        self.al_cambiar()

    def validar(self):
        return None if self.estado.disco else "Elige un disco para continuar."


class PaginaCuenta(QScrollArea):
    """Nombre del equipo, usuario, zona horaria y contraseñas."""

    def __init__(self, etiqueta, seccion):
        super().__init__()
        self.setWidgetResizable(True)
        pagina = QWidget()
        capa = QVBoxLayout(pagina)
        capa.setContentsMargins(0, 4, 4, 4)
        capa.setSpacing(10)
        capa.addLayout(seccion("Tu equipo y tu cuenta", "Estos datos se usarán al crear el sistema."))
        rejilla = QGridLayout()
        rejilla.setVerticalSpacing(8)
        self.campos = {}
        definiciones = (
            ("host", "Nombre del equipo", ti.HOST_DEFECTO, False),
            ("usuario", "Usuario (minúsculas)", ti.USUARIO_DEFECTO, False),
            ("zona", "Zona horaria", ti.ZONA_DEFECTO, False),
            ("pass_usuario", "Contraseña del usuario", "", True),
            ("pass_usuario2", "Repite la contraseña", "", True),
            ("pass_root", "Contraseña de root", "", True),
            ("pass_root2", "Repite la contraseña de root", "", True),
        )
        for fila, (clave, titulo, defecto, secreto) in enumerate(definiciones):
            rejilla.addWidget(etiqueta(titulo), fila, 0)
            campo = QLineEdit(defecto)
            if secreto:
                campo.setEchoMode(QLineEdit.EchoMode.Password)
            campo.setMinimumHeight(34)
            campo.setStyleSheet("background:#1a2038;border:1px solid #3c466c;border-radius:8px;padding:4px 8px;")
            rejilla.addWidget(campo, fila, 1)
            self.campos[clave] = campo
        capa.addLayout(rejilla)
        capa.addStretch()
        self.setWidget(pagina)

    def valores(self):
        return {clave: campo.text().strip() if "pass" not in clave else campo.text()
                for clave, campo in self.campos.items()}

    def validar(self):
        v = self.valores()
        if not ti.valido_host(v["host"]):
            return "Nombre de equipo no válido (letras, números y guiones)."
        if not ti.valido_usuario(v["usuario"]):
            return "Usuario no válido: minúsculas, números, _ o -."
        if not ti.valida_zona(v["zona"]):
            return "La zona horaria no existe (por ejemplo Europe/Madrid)."
        if not v["pass_usuario"] or v["pass_usuario"] != v["pass_usuario2"]:
            return "Las contraseñas del usuario no coinciden o están vacías."
        if not v["pass_root"] or v["pass_root"] != v["pass_root2"]:
            return "Las contraseñas de root no coinciden o están vacías."
        return None


class Anillo(QWidget):
    """Anillo de progreso con degradado."""

    def __init__(self):
        super().__init__()
        self.valor = 0
        self.setMinimumSize(170, 170)

    def poner(self, valor):
        self.valor = max(0, min(100, int(valor)))
        self.update()

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        lado = min(self.width(), self.height()) - 26
        r = QRectF((self.width() - lado) / 2, (self.height() - lado) / 2, lado, lado)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#2a3050"), 13))
        p.drawArc(r, 0, 360 * 16)
        gradiente = QConicalGradient(r.center(), 90)
        gradiente.setColorAt(0.0, QColor("#4f8cff"))
        gradiente.setColorAt(0.5, QColor("#9b71ff"))
        gradiente.setColorAt(1.0, QColor("#ff5fd2"))
        pluma = QPen(QBrush(gradiente), 13)
        pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pluma)
        p.drawArc(r, 90 * 16, -int(360 * 16 * self.valor / 100))
        p.setPen(QColor("#f5f3ff"))
        p.setFont(QFont("DejaVu Sans", 20, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.valor}%")
        p.end()


class Trabajador(QThread):
    """Ejecuta el motor en segundo plano para que la ventana no se bloquee."""

    linea = pyqtSignal(str)
    estado = pyqtSignal(int, str)
    terminado = pyqtSignal(bool)

    def __init__(self, peticion):
        super().__init__()
        self.peticion = peticion

    def run(self):
        ok = motor.instalar(self.peticion, self.linea.emit,
                            lambda i, e: self.estado.emit(i, e))
        self.terminado.emit(ok)


class PaginaFinal(QWidget):
    """Resumen, progreso real y pantalla de éxito con reinicio."""

    def __init__(self, etiqueta, seccion):
        super().__init__()
        self.etiqueta = etiqueta
        self.trabajador = None
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 4, 4, 4)
        capa.setSpacing(10)
        capa.addLayout(seccion("Resumen e instalación", "Revisa los datos. La instalación empieza al pulsar Instalar."))
        fila = QHBoxLayout()
        fila.setSpacing(12)
        self.resumen = etiqueta("")
        self.resumen.setWordWrap(True)
        self.resumen.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.resumen.setStyleSheet("background:#151a2e;border:1px solid #3a4267;border-radius:12px;padding:12px;")
        fila.addWidget(self.resumen, 1)
        derecha = QVBoxLayout()
        self.anillo = Anillo()
        derecha.addWidget(self.anillo, alignment=Qt.AlignmentFlag.AlignCenter)
        self.titulo_estado = etiqueta("Listo para instalar", "section")
        self.titulo_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        derecha.addWidget(self.titulo_estado)
        self.barra = QProgressBar()
        self.barra.setRange(0, len(motor.PASOS))
        self.barra.setTextVisible(False)
        derecha.addWidget(self.barra)
        self.cuenta = etiqueta("", "muted")
        self.cuenta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        derecha.addWidget(self.cuenta)
        self.boton_reiniciar = QPushButton("Reiniciar sistema")
        self.boton_reiniciar.setObjectName("primary")
        self.boton_reiniciar.hide()
        self.boton_reiniciar.clicked.connect(self.pedir_reinicio)
        derecha.addWidget(self.boton_reiniciar)
        fila.addLayout(derecha, 1)
        capa.addLayout(fila, 3)
        self.registro = QPlainTextEdit()
        self.registro.setReadOnly(True)
        self.registro.setMaximumBlockCount(500)
        self.registro.setStyleSheet("background:#0b0e1b;border:1px solid #333a59;border-radius:10px;color:#abb3cf;")
        capa.addWidget(self.registro, 2)
        self.contador = 3
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def preparar(self, texto):
        self.resumen.setText(texto)

    def validar(self):
        return None

    def empezar(self, peticion, al_terminar):
        self.al_terminar = al_terminar
        self.barra.setValue(0)
        self.anillo.poner(0)
        self.registro.clear()
        self.titulo_estado.setText("Instalando…")
        self.trabajador = Trabajador(peticion)
        self.trabajador.linea.connect(self.registro.appendPlainText)
        self.trabajador.estado.connect(self._estado)
        self.trabajador.terminado.connect(self._terminado)
        self.trabajador.start()

    def _estado(self, indice, estado):
        hechos = indice + (1 if estado == "hecho" else 0)
        self.barra.setValue(hechos)
        self.anillo.poner(hechos * 100 // len(motor.PASOS))
        if estado == "en curso":
            self.titulo_estado.setText(motor.PASOS[indice])

    def _terminado(self, ok):
        if ok:
            self.barra.setValue(len(motor.PASOS))
            self.anillo.poner(100)
            self.titulo_estado.setText("¡Instalación completada con éxito!")
            self.cuenta.setText("Quita el USB cuando se reinicie." if not SIMULAR
                                else "Modo simulación: no se ha tocado ningún disco.")
            self.boton_reiniciar.show()
        else:
            self.titulo_estado.setText("La instalación ha fallado")
            self.cuenta.setText("Revisa el registro de abajo.")
        self.al_terminar(ok)

    def pedir_reinicio(self):
        respuesta = QMessageBox.question(self, "Reiniciar", "¿Reiniciar el equipo ahora?")
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self.contador = 3
        self.boton_reiniciar.setEnabled(False)
        self.cuenta.setText(f"Reiniciando en {self.contador}…")
        self.timer.start(1000)

    def _tick(self):
        self.contador -= 1
        if self.contador > 0:
            self.cuenta.setText(f"Reiniciando en {self.contador}…")
            return
        self.timer.stop()
        if SIMULAR:
            self.cuenta.setText("[simulación] systemctl reboot: no se reinicia nada.")
            self.boton_reiniciar.setEnabled(True)
        else:
            subprocess.Popen(["systemctl", "reboot"])


def confirmar_borrado(padre, disco) -> bool:
    """Obliga a escribir el nombre del disco antes de borrarlo."""
    if SIMULAR:
        return True
    texto, aceptado = QInputDialog.getText(
        padre, "Confirmar el borrado",
        f"Se borrará TODO el contenido de {disco['nombre']}.\nPara continuar, escribe su nombre exacto:")
    return bool(aceptado) and texto.strip() == disco["nombre"]
