#!/usr/bin/env python3
"""Tienda de diseños NEX: catálogo, biblioteca y descargas de GitHub."""

import json
import sys
import webbrowser
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (QApplication, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                             QMessageBox, QPushButton, QTabWidget, QVBoxLayout,
                             QWidget)

from theme_store import ErrorTienda, ThemeStore


ESTILO = """
QWidget { background:#0b0e1b; color:#f4f0ff; font-family:'DejaVu Sans'; font-size:13px; }
QFrame { background:#15192d; border:1px solid #41486c; border-radius:13px; }
QLabel { background:transparent; border:none; }
QLabel#title { font-size:25px; font-weight:bold; }
QLabel#muted { color:#b8bed4; }
QPushButton { background:#28234b; border:1px solid #7654b9; border-radius:9px; padding:10px; }
QPushButton:hover { background:#413174; }
QPushButton#primary { background:#7040db; font-weight:bold; }
QLineEdit,QListWidget { background:#15192d; border:1px solid #41486c; border-radius:9px; padding:7px; }
QListWidget::item { padding:8px; }
QListWidget::item:selected { background:#5535a0; }
QTabBar::tab { padding:12px 20px; background:#171a2e; }
QTabBar::tab:selected { background:#51388f; }
"""


class Descarga(QThread):
    terminada = pyqtSignal(str)
    fallo = pyqtSignal(str)

    def __init__(self, tienda, url):
        super().__init__()
        self.tienda, self.url = tienda, url

    def run(self):
        try:
            self.terminada.emit(str(self.tienda.descargar(self.url)))
        except Exception as error:
            self.fallo.emit(str(error))


class Tienda(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tienda = ThemeStore()
        self.worker = None
        self.resultados = []
        self.setWindowTitle('NEX Tienda · Diseños')
        self.resize(1050, 760)
        self.setStyleSheet(ESTILO)
        base = QWidget()
        self.setCentralWidget(base)
        layout = QVBoxLayout(base)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.addWidget(self.texto('NEX Tienda', 'title'))
        layout.addWidget(self.texto('Explora, descarga y organiza diseños para tu escritorio.', 'muted'))
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self.pagina_incluidos(), 'Incluidos')
        self.tabs.addTab(self.pagina_github(), 'GitHub')
        self.tabs.addTab(self.pagina_biblioteca(), 'Mis diseños y carpetas')
        self.estado = self.texto('Los repositorios descargados se guardan sin ejecutar sus scripts.', 'muted')
        layout.addWidget(self.estado)
        self.rellenar_incluidos()
        self.rellenar_biblioteca()

    @staticmethod
    def texto(valor, estilo=None):
        widget = QLabel(valor)
        if estilo:
            widget.setObjectName(estilo)
        widget.setWordWrap(True)
        return widget

    @staticmethod
    def boton(texto, funcion, principal=False):
        widget = QPushButton(texto)
        if principal:
            widget.setObjectName('primary')
        widget.clicked.connect(funcion)
        return widget

    def pagina_incluidos(self):
        pagina = QWidget()
        layout = QHBoxLayout(pagina)
        izquierda = QVBoxLayout()
        izquierda.addWidget(self.texto('14 diseños NEX incluidos: elige uno para ver su fondo.'))
        self.incluidos = QListWidget()
        self.incluidos.setIconSize(QSize(96, 54))
        self.incluidos.currentRowChanged.connect(self.ver_incluido)
        izquierda.addWidget(self.incluidos)
        fila = QHBoxLayout()
        fila.addWidget(self.boton('Duplicar para editar', self.duplicar))
        fila.addWidget(self.boton('Aplicar diseño', self.aplicar_incluido, True))
        izquierda.addLayout(fila)
        layout.addLayout(izquierda, 2)
        derecha = QVBoxLayout()
        self.previsualizacion = self.texto('Selecciona un diseño.')
        self.previsualizacion.setMinimumSize(390, 260)
        self.previsualizacion.setScaledContents(False)
        derecha.addWidget(self.previsualizacion)
        self.detalle = self.texto('', 'muted')
        derecha.addWidget(self.detalle)
        derecha.addStretch()
        layout.addLayout(derecha, 2)
        return pagina

    def pagina_github(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.addWidget(self.texto('Busca diseños de Hyprland o pega la URL principal de un repositorio público.'))
        fila = QHBoxLayout()
        self.buscar_texto = QLineEdit()
        self.buscar_texto.setPlaceholderText('Hyprland, glyph rice, temas...')
        fila.addWidget(self.buscar_texto)
        fila.addWidget(self.boton('Buscar', self.buscar))
        layout.addLayout(fila)
        self.resultados_lista = QListWidget()
        self.resultados_lista.currentRowChanged.connect(self.seleccionar_resultado)
        layout.addWidget(self.resultados_lista, 1)
        self.url = QLineEdit('https://github.com/Nebelung-cloud/glyph-rice')
        layout.addWidget(self.url)
        fila = QHBoxLayout()
        fila.addWidget(self.boton('Abrir en GitHub', self.abrir_github))
        self.descargar_boton = self.boton('Descargar a mi biblioteca', self.descargar, True)
        fila.addWidget(self.descargar_boton)
        layout.addLayout(fila)
        layout.addWidget(self.texto('Los proyectos externos requieren revisión. Solo los paquetes compatibles con NEX se pueden importar y aplicar.', 'muted'))
        return pagina

    def pagina_biblioteca(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.addWidget(self.texto('Tus copias editables y repositorios descargados. Puedes abrir cualquier carpeta con el gestor de archivos.'))
        self.biblioteca = QListWidget()
        layout.addWidget(self.biblioteca, 1)
        fila = QHBoxLayout()
        fila.addWidget(self.boton('Abrir carpeta', self.abrir_carpeta))
        fila.addWidget(self.boton('Importar paquete NEX', self.importar))
        fila.addWidget(self.boton('Aplicar tema personal', self.aplicar_personal, True))
        layout.addLayout(fila)
        layout.addWidget(self.boton('Actualizar biblioteca', self.rellenar_biblioteca))
        return pagina

    def rellenar_incluidos(self):
        self.catalogo = self.tienda.catalogo()
        self.incluidos.clear()
        for entrada in self.catalogo:
            fondo = self.tienda.builtin / 'fondos' / f"{entrada['id']}.png"
            self.incluidos.addItem(QListWidgetItem(
                QIcon(str(fondo)), f"  {entrada['nombre']}\n  {entrada.get('grupo', 'NEX')}  ·  Incluido"))
        self.incluidos.setCurrentRow(0)

    def ver_incluido(self, indice):
        if indice < 0:
            return
        entrada = self.catalogo[indice]
        fondo = self.tienda.builtin / 'fondos' / f"{entrada['id']}.png"
        imagen = QPixmap(str(fondo))
        self.previsualizacion.setPixmap(imagen.scaled(390, 260))
        self.detalle.setText(entrada.get('descripcion', entrada['nombre']))

    def seleccionado(self):
        indice = self.incluidos.currentRow()
        return self.catalogo[indice] if indice >= 0 else None

    def duplicar(self):
        entrada = self.seleccionado()
        if entrada:
            self.ejecutar(lambda: self.tienda.duplicar(entrada['id']), 'Copia editable creada')
            self.rellenar_biblioteca()

    def aplicar_incluido(self):
        entrada = self.seleccionado()
        if entrada:
            self.ejecutar(lambda: self.tienda.aplicar(entrada['id']), 'Diseño aplicado')

    def buscar(self):
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.resultados = self.tienda.buscar(self.buscar_texto.text())
            self.resultados_lista.clear()
            for entrada in self.resultados:
                self.resultados_lista.addItem(f"{entrada['nombre']}  ·  {entrada['licencia']}\n{entrada['descripcion'][:130]}")
            self.estado.setText(f'{len(self.resultados)} repositorios encontrados.')
        except Exception as error:
            self.error(error)
        finally:
            QApplication.restoreOverrideCursor()

    def seleccionar_resultado(self, indice):
        if 0 <= indice < len(self.resultados):
            self.url.setText(self.resultados[indice]['url'])

    def abrir_github(self):
        from theme_store import origen_github
        try:
            autor, repo = origen_github(self.url.text())
            webbrowser.open(f'https://github.com/{autor}/{repo}')
        except ErrorTienda as error:
            self.error(error)

    def descargar(self):
        if self.worker and self.worker.isRunning():
            return
        self.descargar_boton.setEnabled(False)
        self.estado.setText('Descargando repositorio público a la biblioteca...')
        self.worker = Descarga(self.tienda, self.url.text())
        self.worker.terminada.connect(self.descarga_lista)
        self.worker.fallo.connect(self.error)
        self.worker.finished.connect(lambda: self.descargar_boton.setEnabled(True))
        self.worker.start()

    def descarga_lista(self, carpeta):
        self.estado.setText(f'Descargado en {carpeta}. Revisa su contenido antes de importar.')
        self.rellenar_biblioteca()
        self.tabs.setCurrentIndex(2)

    def rellenar_biblioteca(self):
        self.rutas = [(ruta, 'Personal') for ruta in self.tienda.personales()]
        self.rutas += [(ruta, 'GitHub') for ruta in self.tienda.descargados()]
        self.biblioteca.clear()
        for ruta, tipo in self.rutas:
            self.biblioteca.addItem(f'{tipo}  ·  {ruta.name}')

    def ruta_seleccionada(self):
        indice = self.biblioteca.currentRow()
        return self.rutas[indice] if indice >= 0 else None

    def abrir_carpeta(self):
        seleccion = self.ruta_seleccionada()
        if seleccion:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(seleccion[0])))

    def importar(self):
        seleccion = self.ruta_seleccionada()
        if not seleccion or seleccion[1] != 'GitHub':
            self.error('Selecciona primero un repositorio descargado.')
            return
        self.ejecutar(lambda: self.tienda.importar_paquete(seleccion[0]), 'Paquete NEX importado')
        self.rellenar_biblioteca()

    def aplicar_personal(self):
        seleccion = self.ruta_seleccionada()
        if not seleccion or seleccion[1] != 'Personal':
            self.error('Selecciona un diseño personal.')
            return
        carpeta = seleccion[0]
        try:
            catalogo = json.loads((carpeta / 'catalogo.json').read_text(encoding='utf-8'))
            identificador = catalogo[0]['id']
        except (OSError, ValueError, KeyError, IndexError) as error:
            self.error(f'La carpeta no contiene un catálogo NEX válido: {error}')
            return
        self.ejecutar(lambda: self.tienda.aplicar(identificador, carpeta), 'Diseño personal aplicado')

    def ejecutar(self, accion, mensaje):
        try:
            resultado = accion()
            if hasattr(resultado, 'returncode') and resultado.returncode:
                raise ErrorTienda(resultado.stderr.strip() or 'No se pudo aplicar el diseño.')
            self.estado.setText(f'{mensaje}: {resultado if isinstance(resultado, Path) else "correcto"}')
        except Exception as error:
            self.error(error)

    def error(self, error):
        self.estado.setText(str(error))
        QMessageBox.warning(self, 'NEX Tienda', str(error))


def main():
    app = QApplication(sys.argv)
    ventana = Tienda()
    ventana.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
