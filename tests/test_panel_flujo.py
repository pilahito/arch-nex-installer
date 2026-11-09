"""Prueba del panel gráfico conectado al motor (sin pantalla y sin tocar discos)."""

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


@unittest.skipUnless(importlib.util.find_spec("PyQt6") and importlib.util.find_spec("PyQt6.QtSvg"),
                     "necesita PyQt6 con QtSvg")
class PanelFlujoTest(unittest.TestCase):
    def test_recorrido_completo_en_simulacion(self):
        entorno = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        res = subprocess.run(
            [sys.executable, str(RAIZ / "tests" / "flujo_panel_simulado.py")],
            capture_output=True, text=True, env=entorno, timeout=180,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("OK: recorrido completo", res.stdout)


if __name__ == "__main__":
    unittest.main()
