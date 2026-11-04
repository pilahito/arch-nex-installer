"""Pruebas de nex_plan.py (sin tocar el sistema).

Ejecutar desde la carpeta del proyecto:
    python3 -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import nex_plan as np  # noqa: E402


def estado_base(**cambios):
    estado = {
        "gpu": "NVIDIA",
        "almacenamiento": "SSD / M.2",
        "equipo": "Escritorio",
        "oficina": ["Writer"],
        "apps": ["VLC"],
        "widgets_hyprland": "Ninguno",
        "barra_menu": "Waybar + Rofi",
        "dock": "Sin dock",
        "wallpaper": "hyprpaper (ligero)",
        "tema": "NEX NEÓN",
        "modo": "Seguro",
        "debloat": [],
    }
    estado.update(cambios)
    return estado


class PlanTest(unittest.TestCase):
    def test_instala_drivers_y_apps_en_un_solo_pacman(self):
        pasos, _ = np.construir_plan(estado_base(apps=["VLC", "Firefox"]))
        pacman = [p for p in pasos if p.args[:2] == ["pacman", "-S"]]
        self.assertEqual(len(pacman), 1)
        paquetes = pacman[0].args
        for esperado in ("nvidia-open", "vlc", "firefox", "hyprland", "libreoffice-fresh-es"):
            self.assertIn(esperado, paquetes)

    def test_ssd_activa_fstrim_y_hdd_no(self):
        pasos_ssd, _ = np.construir_plan(estado_base(almacenamiento="SSD / M.2"))
        pasos_hdd, _ = np.construir_plan(estado_base(almacenamiento="HDD"))
        self.assertTrue(any("fstrim.timer" in " ".join(p.args) for p in pasos_ssd))
        self.assertFalse(any("fstrim.timer" in " ".join(p.args) for p in pasos_hdd))

    def test_portatil_activa_perfil_de_energia(self):
        pasos, _ = np.construir_plan(estado_base(equipo="Portátil"))
        self.assertTrue(any("power-profiles-daemon" in " ".join(p.args) for p in pasos))

    def test_modo_extremo_incluye_todo(self):
        seguro, _ = np.construir_plan(estado_base(modo="Seguro"))
        extremo, _ = np.construir_plan(estado_base(modo="Extremo"))
        self.assertGreater(len(extremo), len(seguro))
        self.assertTrue(any("cpupower" in " ".join(p.args) for p in extremo))
        self.assertTrue(any("hibernate.target" in " ".join(p.args) for p in extremo))
        self.assertFalse(any("cpupower" in " ".join(p.args) for p in seguro))

    def test_steam_avisa_de_multilib(self):
        _, avisos = np.construir_plan(estado_base(apps=["Steam"]))
        self.assertTrue(any("multilib" in a for a in avisos))

    def test_apps_aur_van_con_yay_sin_root(self):
        pasos, _ = np.construir_plan(estado_base(apps=["Brave"]))
        yay = [p for p in pasos if p.args[:1] == ["yay"]]
        self.assertEqual(len(yay), 1)
        self.assertFalse(yay[0].root)

    def test_app_desconocida_avisa(self):
        _, avisos = np.construir_plan(estado_base(apps=["AppInventada"]))
        self.assertTrue(any("AppInventada" in a for a in avisos))

    def test_tema_se_mapea_a_paleta(self):
        pasos, _ = np.construir_plan(estado_base(tema="CLARO"))
        tema = [p for p in pasos if p.args[:1] == ["__TEMA__"]]
        self.assertEqual(tema[0].args[1], "claro")
        self.assertFalse(tema[0].root)

    def test_tema_sin_paleta_avisa_y_usa_neon(self):
        pasos, avisos = np.construir_plan(estado_base(tema="HYDE"))
        tema = [p for p in pasos if p.args[:1] == ["__TEMA__"]]
        self.assertEqual(tema[0].args[1], "neon")
        self.assertTrue(any("HYDE" in a for a in avisos))

    def test_limpieza_segun_casillas(self):
        pasos, _ = np.construir_plan(estado_base(debloat=["Limpiar caché antigua de pacman (paccache -rk1)"]))
        textos = [p.texto for p in pasos]
        self.assertIn("Limpiar la caché antigua de pacman", textos)
        self.assertNotIn("Eliminar paquetes huérfanos", textos)

    def test_texto_del_plan_numerado(self):
        pasos, avisos = np.construir_plan(estado_base())
        texto = np.texto_plan(pasos, avisos)
        self.assertIn(" 1. ", texto)
        self.assertIn("ZRAM", texto)


class EjecucionTest(unittest.TestCase):
    def test_simulacion_no_cambia_nada_y_avanza(self):
        pasos, _ = np.construir_plan(estado_base())
        lineas, avances = [], []
        ok = np.ejecutar_plan(pasos, None, True, lineas.append, lambda i, n: avances.append((i, n)))
        self.assertTrue(ok)
        self.assertTrue(any("[simulación]" in l for l in lineas))
        self.assertEqual(avances[-1], (len(pasos), len(pasos)))

    def test_se_detiene_en_el_primer_error(self):
        pasos = [np.Paso("falla", "cmd", ["false"], root=False), np.Paso("no debe correr", "cmd", ["true"], root=False)]
        lineas = []
        ok = np.ejecutar_plan(pasos, None, False, lineas.append, lambda i, n: None)
        self.assertFalse(ok)
        self.assertFalse(any("no debe correr" in l for l in lineas))


if __name__ == "__main__":
    unittest.main()
