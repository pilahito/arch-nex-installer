"""Pruebas de generar_config.py (sin tocar ningún disco).

Ejecutar desde la carpeta del proyecto:
    python3 -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import generar_config as gc

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "generar_config.py"


def generar(disco="/dev/sda", tamano_mib="476940", **extra):
    """Ejecuta el generador con datos de prueba y devuelve (código, carpeta)."""
    carpeta = tempfile.mkdtemp()
    entorno = {
        **os.environ,
        "NEX_DISCO": disco,
        "NEX_TAMANO_MIB": tamano_mib,
        "NEX_HOST": "nex-test",
        "NEX_USUARIO": "nex",
        "NEX_ZONA": "Europe/Madrid",
        "NEX_PASS_USUARIO": "clave-usuario",
        "NEX_PASS_ROOT": "clave-root",
        **extra,
    }
    res = subprocess.run(
        [sys.executable, str(SCRIPT), carpeta],
        env=entorno,
        capture_output=True,
        text=True,
    )
    return res, Path(carpeta)


class GenerarConfigTest(unittest.TestCase):
    def test_recuperacion_no_se_ofrece_hasta_tener_contenido(self):
        self.assertNotIn("recuperacion", gc.PARTICIONADOS)
        datos = {"disco": "/dev/sdz", "tamano_mib": 32768,
                 "host": "nex", "usuario": "nex", "zona": "UTC",
                 "particionado": "recuperacion"}
        with self.assertRaises(SystemExit):
            gc.construir_config(datos)

    def test_configuracion_basica(self):
        res, carpeta = generar()
        self.assertEqual(res.returncode, 0, res.stderr)
        config = json.loads((carpeta / "config.json").read_text())

        self.assertEqual(config["archinstall-language"], "Spanish")
        self.assertEqual(config["locale_config"]["sys_lang"], "es_ES")
        self.assertEqual(config["locale_config"]["kb_layout"], "es")
        self.assertEqual(config["timezone"], "Europe/Madrid")
        self.assertEqual(config["hostname"], "nex-test")
        self.assertEqual(config["profile_config"]["profile"]["details"], ["Hyprland"])

    def test_particiones_efi_y_raiz(self):
        res, carpeta = generar(tamano_mib="476940")
        self.assertEqual(res.returncode, 0, res.stderr)
        config = json.loads((carpeta / "config.json").read_text())
        disco = config["disk_config"]["device_modifications"][0]
        self.assertTrue(disco["wipe"])

        efi, raiz = disco["partitions"]
        self.assertEqual(efi["mountpoint"], "/boot")
        self.assertEqual(efi["fs_type"], "fat32")
        self.assertIn("boot", efi["flags"])
        self.assertEqual(efi["size"]["value"], 1024)

        self.assertEqual(raiz["mountpoint"], "/")
        self.assertEqual(raiz["fs_type"], "ext4")
        # 476940 MiB - 1 MiB (inicio EFI) - 1024 MiB (EFI) - 1 MiB de margen
        self.assertEqual(raiz["size"]["value"], 476940 - 1 - 1024 - 1)
        self.assertEqual(raiz["start"]["value"], 1025)

    def test_nombres_de_particion(self):
        res, carpeta = generar(disco="/dev/nvme0n1")
        self.assertEqual(res.returncode, 0, res.stderr)
        env = (carpeta / "particiones.env").read_text()
        self.assertIn("NEX_PART_EFI=/dev/nvme0n1p1", env)
        self.assertIn("NEX_PART_RAIZ=/dev/nvme0n1p2", env)

        res, carpeta = generar(disco="/dev/sdb")
        env = (carpeta / "particiones.env").read_text()
        self.assertIn("NEX_PART_RAIZ=/dev/sdb2", env)

    def test_credenciales_con_hash(self):
        res, carpeta = generar()
        self.assertEqual(res.returncode, 0, res.stderr)
        creds = json.loads((carpeta / "creds.json").read_text())
        usuario = creds["users"][0]
        self.assertEqual(usuario["username"], "nex")
        self.assertTrue(usuario["sudo"])
        # La contraseña nunca se guarda en claro
        self.assertNotIn("clave-usuario", (carpeta / "creds.json").read_text())
        self.assertTrue(usuario["enc_password"].startswith("$6$"))
        self.assertTrue(creds["root_enc_password"].startswith("$6$"))

    def test_disco_pequeno_se_rechaza(self):
        res, _ = generar(tamano_mib="4096")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("demasiado pequeño", res.stderr + res.stdout)

    def test_usuario_no_valido(self):
        carpeta = tempfile.mkdtemp()
        entorno = {
            **os.environ,
            "NEX_DISCO": "/dev/sda",
            "NEX_TAMANO_MIB": "476940",
            "NEX_HOST": "h",
            "NEX_USUARIO": "Mal Usuario",
            "NEX_ZONA": "UTC",
            "NEX_PASS_USUARIO": "a",
            "NEX_PASS_ROOT": "b",
        }
        res = subprocess.run([sys.executable, str(SCRIPT), carpeta], env=entorno, capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
