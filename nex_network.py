"""Acceso a NetworkManager para los menús de red de NEX OS.

La contraseña de Wi-Fi se entrega mediante un fichero temporal privado. Nunca
se añade a la línea de comandos ni al registro del instalador.
"""

import os
import shutil
import subprocess
import tempfile


class ErrorRed(RuntimeError):
    pass


def campos_nmcli(linea):
    """Divide campos de nmcli -t respetando dos puntos y barras escapados."""
    campos, actual, escape = [], [], False
    for caracter in linea:
        if escape:
            actual.append(caracter)
            escape = False
        elif caracter == '\\':
            escape = True
        elif caracter == ':':
            campos.append(''.join(actual))
            actual = []
        else:
            actual.append(caracter)
    if escape:
        actual.append('\\')
    campos.append(''.join(actual))
    return campos


class Red:
    def __init__(self, ejecutar=None):
        self.ejecutar = ejecutar or subprocess.run

    def _nmcli(self, *argumentos, espera=20):
        if shutil.which('nmcli') is None and self.ejecutar is subprocess.run:
            raise ErrorRed('NetworkManager no está disponible en este entorno.')
        comando = ['nmcli', '--wait', str(espera), *argumentos]
        entorno = {**os.environ, 'LC_ALL': 'C'}
        try:
            resultado = self.ejecutar(comando, capture_output=True, text=True,
                                      timeout=espera + 5, env=entorno, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ErrorRed(f'NetworkManager no respondió: {error}') from error
        if resultado.returncode:
            raise ErrorRed((resultado.stderr or resultado.stdout).strip() or
                           'No se pudo completar la operación de red.')
        return resultado.stdout.strip()

    def estado(self):
        salida = self._nmcli('-t', '-e', 'yes', '-f', 'DEVICE,TYPE,STATE,CONNECTION',
                             'device', 'status')
        dispositivos = []
        for linea in salida.splitlines():
            campos = campos_nmcli(linea)
            if len(campos) >= 4 and campos[1] in ('wifi', 'ethernet'):
                dispositivos.append({'nombre': campos[0], 'tipo': campos[1],
                                     'estado': campos[2], 'conexion': campos[3]})
        wifi_activo = self._nmcli('radio', 'wifi') == 'enabled'
        redes = []
        wifi = next((d for d in dispositivos if d['tipo'] == 'wifi'), None)
        if wifi and wifi_activo:
            salida = self._nmcli('-t', '-e', 'yes', '-f', 'IN-USE,SSID,SIGNAL,SECURITY',
                                 'device', 'wifi', 'list', 'ifname', wifi['nombre'],
                                 '--rescan', 'yes', espera=25)
            vistos = set()
            for linea in salida.splitlines():
                campos = campos_nmcli(linea)
                if len(campos) < 4 or not campos[1] or campos[1] in vistos:
                    continue
                vistos.add(campos[1])
                redes.append({'activo': campos[0] == '*', 'ssid': campos[1],
                              'senal': campos[2], 'seguridad': campos[3],
                              'dispositivo': wifi['nombre']})
        return {'dispositivos': dispositivos, 'wifi_activo': wifi_activo,
                'redes': redes}

    def wifi(self, activar):
        self._nmcli('radio', 'wifi', 'on' if activar else 'off')

    def cable(self, dispositivo):
        self._nmcli('device', 'connect', dispositivo, espera=40)

    def conectar(self, ssid, seguridad, dispositivo, clave='', oculta=False):
        if (not ssid or len(ssid.encode('utf-8')) > 32 or
                any(c in ssid for c in '\r\n\x00')):
            raise ErrorRed('El nombre de la red Wi-Fi debe tener entre 1 y 32 bytes.')
        if not dispositivo:
            raise ErrorRed('No hay adaptador Wi-Fi disponible.')
        seguridad = seguridad.upper()
        if seguridad in ('', '--'):
            opciones = ['hidden', 'yes'] if oculta else []
            self._nmcli('device', 'wifi', 'connect', ssid, 'ifname', dispositivo,
                        *opciones, espera=45)
            return
        if any(tipo in seguridad for tipo in ('802.1X', 'ENTERPRISE', 'WEP')):
            raise ErrorRed('Esta red necesita ajustes avanzados de NetworkManager.')
        if not any(tipo in seguridad for tipo in ('WPA', 'SAE')):
            raise ErrorRed('Tipo de seguridad Wi-Fi no compatible con el menú rápido.')
        if not 8 <= len(clave) <= 63 or any(c in clave for c in '\r\n\x00'):
            raise ErrorRed('La contraseña Wi-Fi debe tener entre 8 y 63 caracteres.')

        nombre = f'NEX Wi-Fi {ssid}'
        existe = self.ejecutar(['nmcli', 'connection', 'show', 'id', nombre],
                               capture_output=True, text=True, timeout=10,
                               env={**os.environ, 'LC_ALL': 'C'}, check=False).returncode == 0
        creado = False
        ruta = None
        try:
            if not existe:
                self._nmcli('connection', 'add', 'type', 'wifi', 'ifname', dispositivo,
                            'con-name', nombre, 'ssid', ssid)
                creado = True
                if oculta:
                    self._nmcli('connection', 'modify', 'id', nombre,
                                '802-11-wireless.hidden', 'yes')
                tipo = ('sae' if ('SAE' in seguridad or 'WPA3' in seguridad)
                        and 'WPA2' not in seguridad else 'wpa-psk')
                self._nmcli('connection', 'modify', 'id', nombre,
                            '802-11-wireless-security.key-mgmt', tipo)
            descriptor, ruta = tempfile.mkstemp(prefix='nex-wifi-', suffix='.secret')
            with os.fdopen(descriptor, 'w', encoding='utf-8') as archivo:
                archivo.write(f'802-11-wireless-security.psk:{clave}\n')
            self._nmcli('connection', 'up', 'id', nombre, 'ifname', dispositivo,
                        'passwd-file', ruta, espera=50)
        except Exception:
            if creado:
                try:
                    self._nmcli('connection', 'delete', 'id', nombre)
                except ErrorRed:
                    pass
            raise
        finally:
            if ruta is not None:
                os.unlink(ruta)
