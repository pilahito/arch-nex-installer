"""Recorre el panel de NEX OS en modo simulación y comprueba cada paso.

Lo ejecuta tests/test_panel_flujo.py en un proceso aparte (con --simular y sin
pantalla). Termina con código 0 si todo va bien.
"""

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.argv = [sys.argv[0], "--simular"]          # antes de importar los módulos del panel
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
import nex_installer_dashboard as panel  # noqa: E402

ventana = panel.Installer()
ventana.resize(1400, 900)
ventana.show()


def espera(ms):
    fin = time.time() + ms / 1000
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.01)


def comprobar(condicion, mensaje):
    if not condicion:
        print("FALLO:", mensaje)
        sys.exit(1)


espera(300)
comprobar(ventana.next.text().startswith("Continuar"), "el botón debería ser Continuar")

# Distribución -> tema -> drivers -> disco
for _ in range(3):
    ventana.advance()
    espera(100)
comprobar(ventana.pages.currentWidget() is ventana.pagina_disco, "debería estar en la página de disco")

# Sin disco elegido no se puede avanzar
ventana.advance()
espera(100)
comprobar(ventana.pages.currentWidget() is ventana.pagina_disco, "no debe avanzar sin disco")
comprobar("disco" in ventana.status.text().lower(), "debe avisar de que falta el disco")

ventana.pagina_disco.elegir(ventana.pagina_disco.tarjetas[0].disco)
ventana.advance()
espera(100)
comprobar(ventana.pages.currentWidget() is ventana.pagina_cuenta, "debería estar en la cuenta")

# Con las contraseñas vacías no se puede avanzar
ventana.advance()
comprobar(ventana.pages.currentWidget() is ventana.pagina_cuenta, "no debe avanzar con contraseñas vacías")

# Contraseñas que no coinciden
for clave, valor in (("pass_usuario", "uno"), ("pass_usuario2", "otro"), ("pass_root", "r"), ("pass_root2", "r")):
    ventana.pagina_cuenta.campos[clave].setText(valor)
ventana.advance()
comprobar(ventana.pages.currentWidget() is ventana.pagina_cuenta, "no debe avanzar si no coinciden")

ventana.pagina_cuenta.campos["pass_usuario2"].setText("uno")
ventana.advance()
espera(100)
comprobar(ventana.pages.currentWidget() is ventana.pagina_final, "debería llegar al resumen")
comprobar(ventana.next.text() == "Instalar", "el último botón debe ser Instalar")
comprobar("SE BORRARÁ" in ventana.pagina_final.resumen.text(), "el resumen debe avisar del borrado")

# Instalar (simulado)
ventana.advance()
for _ in range(100):
    espera(100)
    if ventana.pagina_final.barra.value() == panel.paginas.motor.PASOS.__len__():
        break
espera(300)
comprobar("completada" in ventana.pagina_final.titulo_estado.text(), "la instalación simulada debe terminar bien")
comprobar(ventana.next.text() == "Terminado", "el botón final debe ser Terminado")
registro = ventana.pagina_final.registro.toPlainText()
comprobar("[simulación]" in registro and "archinstall" in registro, "el registro debe mostrar los pasos simulados")
print("OK: recorrido completo del panel en simulación.")
