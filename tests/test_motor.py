"""Pruebas del motor de instalación (siempre en simulación: no toca discos)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import generar_config as gc  # noqa: E402
import nex_motor as motor  # noqa: E402

GIB = 1024 ** 3


def peticion(**cambios):
    datos = dict(disco="/dev/sdz", tamano_bytes=512 * GIB, host="nex-arch", usuario="nex",
                 zona="Europe/Madrid", pass_usuario="uno", pass_root="dos", tema="neon", simular=True)
    datos.update(cambios)
    return motor.Peticion(**datos)


class MotorSimuladoTest(unittest.TestCase):
    def test_recorre_todos_los_pasos(self):
        registro, estados = [], {}
        ok = motor.instalar(peticion(), registro.append, lambda i, e: estados.__setitem__(i, e))
        self.assertTrue(ok)
        self.assertEqual(sorted(estados), list(range(len(motor.PASOS))))
        self.assertTrue(all(e == "hecho" for e in estados.values()))
        texto = "\n".join(registro)
        self.assertIn("archinstall --config", texto)
        self.assertIn("[simulación] tema neon", texto)

    def test_la_contrasena_no_aparece_en_el_registro(self):
        registro = []
        motor.instalar(peticion(pass_usuario="secreto-usuario", pass_root="secreto-root"),
                       registro.append, lambda i, e: None)
        self.assertNotIn("secreto-usuario", "\n".join(registro))
        self.assertNotIn("secreto-root", "\n".join(registro))

    def test_repr_no_muestra_contrasenas(self):
        self.assertNotIn("uno", repr(peticion(pass_usuario="clave-visible")).replace("usuario", ""))

    def test_rechaza_disco_que_no_es_dev(self):
        with self.assertRaises(ValueError):
            motor.instalar(peticion(disco="sda"), lambda t: None, lambda i, e: None)

    def test_rechaza_disco_pequeno(self):
        with self.assertRaises(ValueError):
            motor.instalar(peticion(tamano_bytes=4 * GIB), lambda t: None, lambda i, e: None)

    def test_rechaza_paquete_con_caracteres_raros(self):
        with self.assertRaises(ValueError):
            motor.instalar(peticion(paquetes=["vlc; rm -rf /"]), lambda t: None, lambda i, e: None)

    def test_paquetes_extra_llegan_a_archinstall(self):
        datos = {"disco": "/dev/sdz", "tamano_mib": 512 * 1024, "host": "h", "usuario": "u",
                 "zona": "UTC", "paquetes": ["vlc", "nvidia-dkms"]}
        paquetes = gc.construir_config(datos)["packages"]
        self.assertIn("vlc", paquetes)
        self.assertIn("nvidia-dkms", paquetes)
        self.assertIn("git", paquetes)          # los básicos siguen estando
        self.assertEqual(paquetes, sorted(set(paquetes)))


if __name__ == "__main__":
    unittest.main()
