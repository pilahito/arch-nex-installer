#!/usr/bin/env python3
"""Genera fondos originales y ligeros para las paletas NEX.

Solo se necesita Pillow al regenerar los recursos; el sistema instalado usa PNG.
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw


DIR = Path(__file__).resolve().parent
ANCHO, ALTO = 1280, 720


def hex_rgb(valor):
    return tuple(bytes.fromhex(valor))


def leer_paleta(ruta):
    colores = {}
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        if '=' in linea and not linea.startswith('#'):
            clave, valor = linea.split('=', 1)
            colores[clave] = valor.strip('"')
    return colores


def mezclar(primero, segundo, proporcion):
    return tuple(round(a * (1 - proporcion) + b * proporcion) for a, b in zip(primero, segundo))


def generar(identificador):
    paleta = leer_paleta(DIR / 'paletas' / f'{identificador}.env')
    fondo = hex_rgb(paleta['FONDO'])
    panel = hex_rgb(paleta['PANEL'])
    acento = hex_rgb(paleta['ACENTO'])
    acento2 = hex_rgb(paleta['ACENTO2'])
    claro = identificador in ('claro', 'puntos-claro')

    # Una banda de color suave deja el texto del escritorio legible.
    imagen = Image.new('RGB', (ANCHO, ALTO), fondo)
    lienzo = ImageDraw.Draw(imagen)
    for y in range(ALTO):
        factor = 0.08 + 0.34 * y / ALTO
        lienzo.line((0, y, ANCHO, y), fill=mezclar(fondo, panel, factor))

    capa = Image.new('RGBA', (ANCHO, ALTO), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(capa)
    dibujo.ellipse((710, -260, 1480, 510), outline=(*acento, 75), width=7)
    dibujo.ellipse((810, -160, 1380, 410), outline=(*acento2, 55), width=4)
    dibujo.arc((-340, 360, 940, 1160), 190, 350, fill=(*acento, 65), width=9)

    # La variante Puntos usa una matriz marcada; las demás tienen una trama tenue.
    distancia = 24 if identificador.startswith('puntos') else 36
    radio = 3 if identificador.startswith('puntos') else 2
    for y in range(28, ALTO - 18, distancia):
        for x in range(34, ANCHO - 20, distancia):
            intensidad = 62 if identificador.startswith('puntos') else 26
            if x < ANCHO * 0.35:
                intensidad //= 3
            tono = acento if (x // distancia + y // distancia) % 11 == 0 else acento2
            dibujo.ellipse((x - radio, y - radio, x + radio, y + radio), fill=(*tono, intensidad))
    if claro:
        dibujo.rectangle((0, 0, ANCHO, ALTO), outline=(*acento, 35), width=2)
    imagen = Image.alpha_composite(imagen.convert('RGBA'), capa)
    salida = DIR / 'fondos' / f'{identificador}.png'
    imagen.convert('RGB').save(salida, optimize=True)
    print(salida.name)


def main():
    (DIR / 'fondos').mkdir(exist_ok=True)
    catalogo = json.loads((DIR / 'catalogo.json').read_text(encoding='utf-8'))
    for entrada in catalogo:
        generar(entrada['id'])


if __name__ == '__main__':
    main()
