"""Menú gráfico de Wi-Fi y cable integrado en el instalador NEX."""

import shutil
import subprocess

from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QInputDialog, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QPushButton, QVBoxLayout)

from nex_network import Red


class TrabajoRed(QThread):
    listo = pyqtSignal(object)
    fallo = pyqtSignal(str)

    def __init__(self, red, accion, *argumentos):
        super().__init__()
        self.red, self.accion, self.argumentos = red, accion, argumentos

    def run(self):
        try:
            resultado = getattr(self.red, self.accion)(*self.argumentos)
            self.listo.emit(resultado)
        except Exception as error:
            self.fallo.emit(str(error))
        finally:
            self.argumentos = ()


class DialogoRed(QDialog):
    def __init__(self, padre=None, red=None):
        super().__init__(padre)
        self.red = red or Red()
        self.trabajo = None
        self.datos = {'dispositivos': [], 'redes': [], 'wifi_activo': False}
        self.setWindowTitle('NEX OS · Conexión de red')
        self.resize(620, 590)
        capa = QVBoxLayout(self)
        capa.setSpacing(11)
        titulo = QLabel('Conexión de red')
        titulo.setStyleSheet('font-size:22px;font-weight:bold;')
        capa.addWidget(titulo)
        capa.addWidget(QLabel('Elige una red. Las contraseñas se escriben en este menú.'))

        self.cable_estado = QLabel('Cable: comprobando…')
        self.cable_estado.setStyleSheet('background:#17233b;border:1px solid #35496d;border-radius:9px;padding:10px;')
        capa.addWidget(self.cable_estado)
        fila_cable = QHBoxLayout()
        self.boton_cable = QPushButton('Conectar cable')
        self.boton_cable.clicked.connect(self.conectar_cable)
        fila_cable.addWidget(self.boton_cable)
        fila_cable.addStretch()
        capa.addLayout(fila_cable)

        self.wifi_estado = QLabel('Wi-Fi: comprobando…')
        self.wifi_estado.setStyleSheet('background:#17233b;border:1px solid #35496d;border-radius:9px;padding:10px;')
        capa.addWidget(self.wifi_estado)
        self.lista = QListWidget()
        self.lista.setStyleSheet('QListWidget {background:#111629;border:1px solid #354061;border-radius:10px;}'
                                 'QListWidget::item {padding:8px;}'
                                 'QListWidget::item:selected {background:#51378d;border-radius:7px;}')
        capa.addWidget(self.lista, 1)
        fila = QHBoxLayout()
        self.boton_actualizar = QPushButton('Actualizar redes')
        self.boton_actualizar.clicked.connect(self.actualizar)
        fila.addWidget(self.boton_actualizar)
        self.boton_wifi = QPushButton('Activar Wi-Fi')
        self.boton_wifi.clicked.connect(self.alternar_wifi)
        fila.addWidget(self.boton_wifi)
        capa.addLayout(fila)
        fila = QHBoxLayout()
        self.boton_oculta = QPushButton('Red oculta…')
        self.boton_oculta.clicked.connect(self.red_oculta)
        fila.addWidget(self.boton_oculta)
        self.boton_conectar = QPushButton('Conectar a la red elegida')
        self.boton_conectar.setObjectName('primary')
        self.boton_conectar.clicked.connect(self.conectar_elegida)
        fila.addWidget(self.boton_conectar)
        capa.addLayout(fila)
        fila = QHBoxLayout()
        avanzado = QPushButton('Ajustes avanzados…')
        avanzado.clicked.connect(self.ajustes_avanzados)
        fila.addWidget(avanzado)
        fila.addStretch()
        cerrar = QPushButton('Cerrar')
        cerrar.clicked.connect(self.accept)
        fila.addWidget(cerrar)
        capa.addLayout(fila)
        self.mensaje = QLabel('')
        self.mensaje.setWordWrap(True)
        capa.addWidget(self.mensaje)
        self.actualizar()

    def ejecutar(self, accion, *argumentos):
        if self.trabajo and self.trabajo.isRunning():
            return
        self.boton_actualizar.setEnabled(False)
        self.boton_conectar.setEnabled(False)
        self.boton_cable.setEnabled(False)
        self.mensaje.setText('Comprobando la red…' if accion == 'estado' else 'Conectando…')
        self.trabajo = TrabajoRed(self.red, accion, *argumentos)
        self.trabajo.listo.connect(self.terminado)
        self.trabajo.fallo.connect(self.error)
        self.trabajo.finished.connect(self.desbloquear)
        self.trabajo.start()

    def desbloquear(self):
        self.boton_actualizar.setEnabled(True)
        self.boton_conectar.setEnabled(True)
        self.boton_cable.setEnabled(True)

    def actualizar(self):
        self.ejecutar('estado')

    def terminado(self, resultado):
        if isinstance(resultado, dict):
            self.datos = resultado
            self.mostrar_estado()
        else:
            self.mensaje.setText('Conexión actualizada.')
            self.trabajo.finished.connect(self.actualizar)

    def mostrar_estado(self):
        cable = next((d for d in self.datos['dispositivos'] if d['tipo'] == 'ethernet'), None)
        wifi = next((d for d in self.datos['dispositivos'] if d['tipo'] == 'wifi'), None)
        self.cable_estado.setText('Cable: ' + (f"{cable['nombre']} · {cable['estado']}" if cable else 'no detectado'))
        self.boton_cable.setEnabled(cable is not None)
        self.wifi_estado.setText('Wi-Fi: ' + ('activado' if self.datos['wifi_activo'] else 'desactivado') +
                                (f" · {wifi['nombre']}" if wifi else ' · sin adaptador'))
        self.boton_wifi.setText('Desactivar Wi-Fi' if self.datos['wifi_activo'] else 'Activar Wi-Fi')
        self.lista.clear()
        for red in self.datos['redes']:
            nombre = (f"{'● ' if red['activo'] else '○ '}{red['ssid']}\n"
                      f"   Señal {red['senal']} %  ·  {red['seguridad']}")
            elemento = QListWidgetItem(nombre)
            elemento.setSizeHint(QSize(0, 54))
            elemento.setData(Qt.ItemDataRole.UserRole, red)
            self.lista.addItem(elemento)
        self.mensaje.setText(f"{len(self.datos['redes'])} redes disponibles.")

    def alternar_wifi(self):
        self.ejecutar('wifi', not self.datos['wifi_activo'])

    def conectar_cable(self):
        cable = next((d for d in self.datos['dispositivos'] if d['tipo'] == 'ethernet'), None)
        if cable:
            self.ejecutar('cable', cable['nombre'])

    def conectar_elegida(self):
        elemento = self.lista.currentItem()
        if elemento is None:
            self.error('Elige primero una red Wi-Fi.')
            return
        red = elemento.data(Qt.ItemDataRole.UserRole)
        self.pedir_clave_y_conectar(red)

    def red_oculta(self):
        wifi = next((d for d in self.datos['dispositivos'] if d['tipo'] == 'wifi'), None)
        if wifi is None:
            self.error('No hay adaptador Wi-Fi disponible.')
            return
        nombre, ok = QInputDialog.getText(self, 'Red oculta', 'Nombre de la red (SSID):')
        if not ok or not nombre:
            return
        seguridad, ok = QInputDialog.getItem(self, 'Seguridad', 'Tipo de red:',
                                             ['WPA2/WPA3 personal', 'Abierta'], 0, False)
        if ok:
            self.pedir_clave_y_conectar({'ssid': nombre, 'seguridad': 'WPA2' if seguridad != 'Abierta' else '--',
                                         'dispositivo': wifi['nombre'], 'oculta': True})

    def pedir_clave_y_conectar(self, red):
        seguridad = red['seguridad']
        clave = ''
        if seguridad not in ('', '--'):
            clave, ok = QInputDialog.getText(self, 'Contraseña Wi-Fi',
                                             f"Contraseña de {red['ssid']}:",
                                             QLineEdit.EchoMode.Password)
            if not ok:
                return
        self.ejecutar('conectar', red['ssid'], seguridad, red['dispositivo'], clave,
                     red.get('oculta', False))

    def ajustes_avanzados(self):
        programa = shutil.which('nm-connection-editor')
        if programa:
            subprocess.Popen([programa])
        else:
            self.error('El editor gráfico avanzado no está disponible.')

    def error(self, mensaje):
        self.mensaje.setText(str(mensaje))
        QMessageBox.warning(self, 'NEX OS · Red', str(mensaje))

    def accept(self):
        if self.trabajo and self.trabajo.isRunning():
            self.mensaje.setText('Espera a que termine la operación de red.')
            return
        super().accept()

    def reject(self):
        if self.trabajo and self.trabajo.isRunning():
            self.mensaje.setText('Espera a que termine la operación de red.')
            return
        super().reject()
