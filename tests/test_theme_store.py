"""Pruebas de biblioteca y descargas sin acceder a la red ni al equipo real."""

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from theme_store import ErrorTienda, ThemeStore, origen_github


class Respuesta:
    def __init__(self, contenido):
        self.contenido = io.BytesIO(contenido)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.contenido.close()

    def read(self, limite):
        return self.contenido.read(limite)


def zip_de(archivos):
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, 'w') as paquete:
        for ruta, contenido in archivos.items():
            paquete.writestr(ruta, contenido)
    return salida.getvalue()


class PruebasTienda(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.tienda = ThemeStore(Path(self.temporal.name) / 'tienda')

    def test_catalogo_y_copia_editable(self):
        self.assertEqual(len(self.tienda.catalogo()), 14)
        copia = self.tienda.duplicar('puntos')
        self.assertTrue((copia / 'paletas/puntos.env').is_file())
        self.assertTrue((copia / 'fondos/puntos.png').is_file())
        self.assertTrue((copia / 'plantillas/hyprland-nex.conf').is_file())

    def test_descarga_guarda_archivos_sin_ejecutar(self):
        comprimido = zip_de({'autor-repo-abc/nex-theme.json': '{}',
                             'autor-repo-abc/install.sh': 'exit 99'})
        destino = self.tienda.descargar('https://github.com/autor/repo',
                                       abrir=lambda *_args, **_kwargs: Respuesta(comprimido))
        self.assertEqual((destino / 'install.sh').read_text(), 'exit 99')
        self.assertTrue((destino / 'nex-source.json').is_file())

    def test_rechaza_rutas_peligrosas(self):
        with self.assertRaises(ErrorTienda):
            origen_github('https://example.com/autor/repo')
        comprimido = zip_de({'autor-repo/../../fuera.txt': 'x'})
        with self.assertRaises(ErrorTienda):
            self.tienda.descargar('https://github.com/autor/repo',
                                 abrir=lambda *_args, **_kwargs: Respuesta(comprimido))

    def test_importa_paquete_compatible_con_paleta_saneada(self):
        origen = self.tienda.root / 'github' / 'autor-repo'
        origen.mkdir()
        (origen / 'nex-theme.json').write_text(json.dumps({
            'schema_version': 1, 'id': 'prueba', 'nombre': 'Mi diseño'}))
        (origen / 'paleta.env').write_text(
            'NOMBRE="Inyectado"\nFONDO=101010\nPANEL=202020\nACENTO=303030\n'
            'ACENTO2=404040\nACENTO3=505050\nTEXTO=ffffff\n')
        (origen / 'fondo.png').write_bytes(b'\x89PNG\r\n\x1a\nresto')
        destino = self.tienda.importar_paquete(origen)
        paleta = (destino / 'paletas/prueba.env').read_text(encoding='utf-8')
        self.assertIn('NOMBRE="Mi diseño"', paleta)
        self.assertNotIn('Inyectado', paleta)


if __name__ == '__main__':
    unittest.main()
