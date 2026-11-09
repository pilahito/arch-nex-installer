#!/usr/bin/env python3
"""Biblioteca de temas NEX y descarga de recursos públicos de GitHub.

Los repositorios externos se guardan como archivos para revisar. Nunca se
ejecutan sus scripts. Solo un paquete con manifiesto NEX puede importarse.
"""

import getpass
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


DIR = Path(__file__).resolve().parent
REPOSITORIO = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$')
IDENTIFICADOR = re.compile(r'^[a-z0-9][a-z0-9-]{0,39}$')
MAX_DESCARGA = 30 * 1024 * 1024
MAX_EXTRAIDO = 100 * 1024 * 1024
MAX_ARCHIVOS = 5000


class ErrorTienda(ValueError):
    """Error visible en la interfaz de la tienda."""


def origen_github(url):
    coincidencia = REPOSITORIO.fullmatch(url.strip())
    if not coincidencia or '..' in coincidencia.groups():
        raise ErrorTienda('Usa la dirección principal de un repositorio público de GitHub.')
    autor, repo = coincidencia.groups()
    return autor, repo


def peticion_json(url, abrir=urllib.request.urlopen):
    solicitud = urllib.request.Request(url, headers={'User-Agent': 'NEX-Theme-Store/1'})
    with abrir(solicitud, timeout=20) as respuesta:
        contenido = respuesta.read(1024 * 1024 + 1)
    if len(contenido) > 1024 * 1024:
        raise ErrorTienda('La respuesta de GitHub excede el límite permitido.')
    return json.loads(contenido)


class ThemeStore:
    def __init__(self, root=None, builtin=None):
        self.root = Path(root or os.environ.get('NEX_THEME_STORE_DIR',
                                              Path.home() / '.local/share/nex/theme-store')).expanduser()
        self.builtin = Path(builtin or self.buscar_temas_incluidos())
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / 'personal').mkdir(exist_ok=True)
        (self.root / 'github').mkdir(exist_ok=True)

    @staticmethod
    def buscar_temas_incluidos():
        for candidato in (DIR / 'tema', Path('/usr/local/share/nex/tema'),
                          Path('/root/nex-installer/tema')):
            if (candidato / 'catalogo.json').is_file():
                return candidato
        raise ErrorTienda('No se encuentra el catálogo de diseños de NEX.')

    def catalogo(self):
        return json.loads((self.builtin / 'catalogo.json').read_text(encoding='utf-8'))

    def buscar(self, consulta, abrir=urllib.request.urlopen):
        termino = consulta.strip()[:80]
        if not termino:
            return []
        consulta_api = urllib.parse.urlencode({'q': f'{termino} hyprland theme',
                                               'sort': 'stars', 'per_page': 12})
        datos = peticion_json('https://api.github.com/search/repositories?' + consulta_api, abrir)
        return [{'nombre': item['full_name'], 'descripcion': item.get('description') or '',
                 'url': item['html_url'], 'licencia': (item.get('license') or {}).get('spdx_id') or 'Sin indicar'}
                for item in datos.get('items', []) if item.get('html_url', '').startswith('https://github.com/')]

    def descargados(self):
        return sorted((ruta for ruta in (self.root / 'github').iterdir() if ruta.is_dir()),
                      key=lambda ruta: ruta.name.lower())

    def personales(self):
        return sorted((ruta for ruta in (self.root / 'personal').iterdir() if ruta.is_dir()),
                      key=lambda ruta: ruta.name.lower())

    @staticmethod
    def _nombre_libre(carpeta, nombre):
        destino = carpeta / nombre
        numero = 2
        while destino.exists():
            destino = carpeta / f'{nombre}-{numero}'
            numero += 1
        return destino

    def descargar(self, url, abrir=urllib.request.urlopen):
        autor, repo = origen_github(url)
        api = f'https://api.github.com/repos/{autor}/{repo}/zipball'
        solicitud = urllib.request.Request(api, headers={'User-Agent': 'NEX-Theme-Store/1'})
        with abrir(solicitud, timeout=40) as respuesta:
            comprimido = respuesta.read(MAX_DESCARGA + 1)
        if len(comprimido) > MAX_DESCARGA:
            raise ErrorTienda('El repositorio supera el límite de 30 MB comprimidos.')

        destino = self._nombre_libre(self.root / 'github', f'{autor}-{repo}'.lower())
        temporal = Path(tempfile.mkdtemp(prefix='descarga-', dir=self.root / 'github'))
        try:
            with zipfile.ZipFile(io.BytesIO(comprimido)) as paquete:
                archivos = paquete.infolist()
                if len(archivos) > MAX_ARCHIVOS:
                    raise ErrorTienda('Demasiados archivos en el repositorio.')
                total = 0
                for entrada in archivos:
                    if entrada.filename.startswith('/') or entrada.filename.startswith('\\'):
                        raise ErrorTienda('El repositorio contiene rutas absolutas.')
                    partes = Path(entrada.filename.replace('\\', '/')).parts
                    if len(partes) == 1 and entrada.is_dir():
                        continue
                    if len(partes) < 2 or any(parte in ('.', '..') for parte in partes):
                        raise ErrorTienda('El repositorio contiene rutas no válidas.')
                    if ((entrada.external_attr >> 16) & 0o170000) == 0o120000:
                        raise ErrorTienda('No se aceptan enlaces simbólicos en descargas.')
                    ruta = temporal.joinpath(*partes[1:])
                    if not ruta.resolve().is_relative_to(temporal.resolve()):
                        raise ErrorTienda('El repositorio intenta salir de su carpeta.')
                    if entrada.is_dir():
                        ruta.mkdir(parents=True, exist_ok=True)
                        continue
                    total += entrada.file_size
                    if total > MAX_EXTRAIDO:
                        raise ErrorTienda('El repositorio supera el límite de 100 MB extraídos.')
                    ruta.parent.mkdir(parents=True, exist_ok=True)
                    with paquete.open(entrada) as origen, ruta.open('xb') as salida:
                        shutil.copyfileobj(origen, salida)
            (temporal / 'nex-source.json').write_text(json.dumps({
                'repositorio': f'{autor}/{repo}', 'url': url,
                'descargado': datetime.now(timezone.utc).isoformat(),
                'estado': 'Archivo externo; no se ejecuta automáticamente',
            }, ensure_ascii=False, indent=2), encoding='utf-8')
            temporal.rename(destino)
        except Exception:
            shutil.rmtree(temporal)
            raise
        return destino

    def duplicar(self, identificador):
        if not IDENTIFICADOR.fullmatch(identificador):
            raise ErrorTienda('Identificador de diseño no válido.')
        entrada = next((tema for tema in self.catalogo() if tema['id'] == identificador), None)
        if not entrada:
            raise ErrorTienda('El diseño no pertenece al catálogo NEX.')
        destino = self._nombre_libre(self.root / 'personal', identificador + '-personal')
        destino.mkdir()
        for subcarpeta in ('paletas', 'fondos'):
            (destino / subcarpeta).mkdir()
        shutil.copytree(self.builtin / 'plantillas', destino / 'plantillas')
        shutil.copy2(self.builtin / 'paletas' / f'{identificador}.env',
                     destino / 'paletas' / f'{identificador}.env')
        shutil.copy2(self.builtin / 'fondos' / f'{identificador}.png',
                     destino / 'fondos' / f'{identificador}.png')
        (destino / 'catalogo.json').write_text(json.dumps([entrada], ensure_ascii=False, indent=2),
                                               encoding='utf-8')
        return destino

    def importar_paquete(self, carpeta):
        """Convierte un repositorio de datos NEX en un tema personal aplicable."""
        origen = Path(carpeta).resolve()
        if not origen.is_relative_to((self.root / 'github').resolve()):
            raise ErrorTienda('Solo se importan repositorios descargados con NEX Tienda.')
        manifiesto = origen / 'nex-theme.json'
        if not manifiesto.is_file() or manifiesto.stat().st_size > 20000:
            raise ErrorTienda('El repositorio no contiene un manifiesto NEX válido.')
        datos = json.loads(manifiesto.read_text(encoding='utf-8'))
        identificador = datos.get('id', '')
        nombre = datos.get('nombre', '')
        if (datos.get('schema_version') != 1 or not isinstance(identificador, str)
                or not IDENTIFICADOR.fullmatch(identificador)):
            raise ErrorTienda('El identificador o versión del paquete NEX no es válido.')
        if (not isinstance(nombre, str) or not 1 <= len(nombre) <= 80 or
                not re.fullmatch(r'[\w .áéíóúÁÉÍÓÚñÑ()_-]+', nombre)):
            raise ErrorTienda('El nombre del paquete NEX no es válido.')
        paleta = origen / 'paleta.env'
        fondo = origen / 'fondo.png'
        if not paleta.is_file() or not fondo.is_file() or fondo.stat().st_size > 5 * 1024 * 1024:
            raise ErrorTienda('El paquete debe incluir paleta.env y fondo.png (máximo 5 MB).')
        valores = {}
        for linea in paleta.read_text(encoding='utf-8').splitlines():
            if not linea or linea.startswith('#'):
                continue
            if '=' not in linea:
                raise ErrorTienda('La paleta contiene una línea no válida.')
            clave, valor = linea.split('=', 1)
            if clave not in ('NOMBRE', 'FONDO', 'PANEL', 'ACENTO', 'ACENTO2', 'ACENTO3', 'TEXTO'):
                raise ErrorTienda('La paleta contiene una variable no permitida.')
            valores[clave] = valor.strip('"')
        for clave in ('FONDO', 'PANEL', 'ACENTO', 'ACENTO2', 'ACENTO3', 'TEXTO'):
            if not re.fullmatch(r'[0-9a-fA-F]{6}', valores.get(clave, '')):
                raise ErrorTienda('Los colores de la paleta deben ser hexadecimales de seis cifras.')
        with fondo.open('rb') as archivo_fondo:
            cabecera = archivo_fondo.read(8)
        if cabecera != b'\x89PNG\r\n\x1a\n':
            raise ErrorTienda('El fondo del paquete no es un PNG válido.')
        destino = self._nombre_libre(self.root / 'personal', identificador)
        destino.mkdir()
        (destino / 'paletas').mkdir()
        (destino / 'fondos').mkdir()
        shutil.copytree(self.builtin / 'plantillas', destino / 'plantillas')
        colores = '\n'.join(f'{clave}={valores[clave].lower()}' for clave in
                            ('FONDO', 'PANEL', 'ACENTO', 'ACENTO2', 'ACENTO3', 'TEXTO'))
        (destino / 'paletas' / f'{identificador}.env').write_text(
            f'NOMBRE="{nombre}"\n{colores}\n', encoding='utf-8')
        shutil.copy2(fondo, destino / 'fondos' / f'{identificador}.png')
        (destino / 'catalogo.json').write_text(json.dumps([{
            'id': identificador, 'nombre': nombre, 'grupo': 'Personal',
            'descripcion': datos.get('descripcion', 'Diseño importado'),
        }], ensure_ascii=False, indent=2), encoding='utf-8')
        return destino

    def aplicar(self, identificador, carpeta=None, usuario=None, raiz=None):
        if not IDENTIFICADOR.fullmatch(identificador):
            raise ErrorTienda('Identificador de diseño no válido.')
        temas = Path(carpeta or self.builtin)
        if not (temas / 'paletas' / f'{identificador}.env').is_file():
            raise ErrorTienda('Falta la paleta del diseño seleccionado.')
        script = DIR / 'post-instalacion' / 'aplicar-tema.sh'
        if not script.is_file():
            script = Path('/usr/local/share/nex/aplicar-tema.sh')
        if not script.is_file():
            raise ErrorTienda('No se encuentra el aplicador de temas NEX.')
        entorno = os.environ.copy()
        entorno['NEX_TEMA_DIR'] = str(temas)
        comando = ['bash', str(script), usuario or getpass.getuser(), identificador]
        if raiz is not None:
            comando.append(str(raiz))
        return subprocess.run(comando, env=entorno, capture_output=True, text=True, check=False)
