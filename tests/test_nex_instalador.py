"""Pruebas de la interfaz de pantalla completa (nex_instalador.py).

Ejecutar desde la carpeta del proyecto:
    python3 -m unittest discover -s tests -v

Las pruebas de lógica no necesitan terminal. La de recorrido completo usa una
pseudo-terminal y el modo --simular, así que no toca ningún disco.
"""

import os
import pty
import select
import sys
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import nex_instalador as ni  # noqa: E402

LSBLK_EJEMPLO = """{"blockdevices": [
  {"name": "/dev/sda", "size": "512110190592", "type": "disk", "model": "Samsung SSD"},
  {"name": "/dev/sdb", "size": "15938355200", "type": "disk", "model": "USB Flash"},
  {"name": "/dev/sr0", "size": "1073741824", "type": "rom", "model": "DVD"},
  {"name": "/dev/loop0", "size": "3000000000", "type": "loop", "model": null},
  {"name": "/dev/sdc", "size": "4294967296", "type": "disk", "model": "Pequeño"}
]}"""


class LogicaDiscosTest(unittest.TestCase):
    def test_parse_solo_discos(self):
        discos = ni.parse_discos(LSBLK_EJEMPLO)
        self.assertEqual([d["nombre"] for d in discos], ["/dev/sda", "/dev/sdb", "/dev/sdc"])
        self.assertEqual(discos[0]["modelo"], "Samsung SSD")

    def test_filtra_medio_y_pequenos(self):
        discos = ni.parse_discos(LSBLK_EJEMPLO)
        aptos = ni.filtrar_discos(discos, medio="/dev/sdb")
        self.assertEqual([d["nombre"] for d in aptos], ["/dev/sda"])

    def test_gib_formato(self):
        self.assertEqual(ni.gib(512 * ni.GIB), "512 GiB")


class ValidadoresTest(unittest.TestCase):
    def test_host(self):
        self.assertTrue(ni.valido_host("nex-arch"))
        self.assertFalse(ni.valido_host("mal host"))
        self.assertFalse(ni.valido_host(""))

    def test_usuario(self):
        self.assertTrue(ni.valido_usuario("nex"))
        self.assertFalse(ni.valido_usuario("Nex"))
        self.assertFalse(ni.valido_usuario("1nex"))

    def test_zona(self):
        self.assertFalse(ni.valida_zona("No/Existe"))
        self.assertFalse(ni.valida_zona(""))


class RecorridoSimuladoTest(unittest.TestCase):
    """Recorre todas las pantallas en modo simulación, con una pseudo-terminal."""

    TECLAS = [
        "\n",               # bienvenida
        "\n",               # elegir el disco de prueba
        "/dev/sdz\n",       # confirmar el borrado escribiendo el nombre
        "\n", "\n", "\n",   # equipo, usuario y zona por defecto
        "clave\n", "clave\n",   # contraseña de usuario y repetición
        "raiz\n", "raiz\n",     # contraseña de root y repetición
        "\n",               # tema (el primero: neón)
        "\n",               # resumen: Sí, instalar
        "\n",               # pantalla final: salir
    ]

    def leer(self, fd, espera=0.5):
        salida = b""
        fin = time.time() + espera
        while time.time() < fin:
            listos, _, _ = select.select([fd], [], [], 0.1)
            if listos:
                try:
                    trozo = os.read(fd, 4096)
                except OSError:
                    break
                if not trozo:
                    break
                salida += trozo
        return salida

    @unittest.skipUnless(sys.platform.startswith("linux"), "necesita pseudo-terminal Linux")
    def test_recorrido_completo(self):
        pid, fd = pty.fork()
        if pid == 0:
            os.environ.setdefault("LANG", "C.UTF-8")
            os.environ["TERM"] = "xterm-256color"
            os.execvp(sys.executable, [sys.executable, str(RAIZ / "nex_instalador.py"), "--simular"])
        salida = self.leer(fd, 1.5)
        for tecla in self.TECLAS:
            os.write(fd, tecla.encode())
            salida += self.leer(fd, 0.4)
        salida += self.leer(fd, 2.0)
        _, estado = os.waitpid(pid, 0)
        texto = salida.decode("utf-8", errors="replace")
        self.assertIn("instalado", texto)
        self.assertIn("simulación", texto)
        self.assertEqual(os.WEXITSTATUS(estado), 0)


if __name__ == "__main__":
    unittest.main()
