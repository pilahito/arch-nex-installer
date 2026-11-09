"""Pruebas de los menús de red con un NetworkManager simulado."""

import os
import stat
import unittest
from types import SimpleNamespace

from nex_network import ErrorRed, Red, campos_nmcli


class NetworkManagerFalso:
    def __init__(self):
        self.comandos = []
        self.secreto = None

    def __call__(self, comando, **_):
        self.comandos.append(comando)
        if 'passwd-file' in comando:
            ruta = comando[comando.index('passwd-file') + 1]
            with open(ruta, encoding='utf-8') as archivo:
                self.secreto = (ruta, archivo.read(),
                                stat.S_IMODE(os.stat(ruta).st_mode))
        if comando[-2:] == ['device', 'status']:
            return SimpleNamespace(returncode=0, stdout=(
                'enp0s3:ethernet:connected:Wired connection 1\n'
                'wlan0:wifi:disconnected:--\n'), stderr='')
        if comando[-2:] == ['radio', 'wifi']:
            return SimpleNamespace(returncode=0, stdout='enabled\n', stderr='')
        if 'list' in comando and 'wifi' in comando:
            return SimpleNamespace(returncode=0, stdout=(
                '*:Mi\\:Red:82:WPA2\n:Abierta:46:--\n'), stderr='')
        if len(comando) >= 4 and comando[-4:-1] == ['connection', 'show', 'id']:
            return SimpleNamespace(returncode=10, stdout='', stderr='No existe')
        return SimpleNamespace(returncode=0, stdout='', stderr='')


class PruebasRed(unittest.TestCase):
    def test_parsea_escapes_y_lista_dispositivos(self):
        self.assertEqual(campos_nmcli(r'*:Mi\:Red:82:WPA2'), ['*', 'Mi:Red', '82', 'WPA2'])
        falso = NetworkManagerFalso()
        datos = Red(falso).estado()
        self.assertEqual(datos['dispositivos'][0]['tipo'], 'ethernet')
        self.assertEqual(datos['redes'][0]['ssid'], 'Mi:Red')
        self.assertTrue(datos['redes'][0]['activo'])

    def test_conecta_con_contrasena_fuera_de_argumentos(self):
        falso = NetworkManagerFalso()
        Red(falso).conectar('Mi:Red', 'WPA2', 'wlan0', 'clave-segura')
        self.assertTrue(all('clave-segura' not in ' '.join(cmd) for cmd in falso.comandos))
        ruta, contenido, permisos = falso.secreto
        self.assertIn('802-11-wireless-security.psk:clave-segura', contenido)
        self.assertFalse(os.path.exists(ruta))
        if os.name != 'nt':
            self.assertEqual(permisos, 0o600)

    def test_rechaza_redes_no_compatibles_y_claves_inseguras(self):
        falso = NetworkManagerFalso()
        cliente = Red(falso)
        with self.assertRaises(ErrorRed):
            cliente.conectar('Oficina', 'WPA2 802.1X', 'wlan0', 'clave-segura')
        with self.assertRaises(ErrorRed):
            cliente.conectar('Casa', 'WPA2', 'wlan0', '12345678\ninyectar')
        self.assertEqual(falso.comandos, [])

    def test_red_oculta_indica_el_modo_en_la_conexion(self):
        falso = NetworkManagerFalso()
        Red(falso).conectar('Mi Casa', '--', 'wlan0', oculta=True)
        self.assertIn(['nmcli', '--wait', '45', 'device', 'wifi', 'connect',
                       'Mi Casa', 'ifname', 'wlan0', 'hidden', 'yes'], falso.comandos)

    def test_fallo_de_conexion_limpia_el_perfil_y_el_secreto(self):
        class FallaAlConectar(NetworkManagerFalso):
            def __call__(self, comando, **opciones):
                resultado = super().__call__(comando, **opciones)
                if 'passwd-file' in comando:
                    return SimpleNamespace(returncode=1, stdout='', stderr='Clave incorrecta')
                return resultado

        falso = FallaAlConectar()
        with self.assertRaises(ErrorRed):
            Red(falso).conectar('Casa', 'WPA2', 'wlan0', 'clave-segura')
        self.assertTrue(any('delete' in comando for comando in falso.comandos))
        self.assertFalse(os.path.exists(falso.secreto[0]))


if __name__ == '__main__':
    unittest.main()
