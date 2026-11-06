#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera las imágenes de Nex Arch: un fondo de pantalla por tema y el logotipo.

Las imágenes se pintan con PyQt6 (no se descargan de ningún sitio), así que son
propias y se pueden volver a generar con:

    QT_QPA_PLATFORM=offscreen python3 tools/generar_imagenes.py
"""

import sys
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt6.QtWidgets import QApplication

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "assets"
ANCHO, ALTO = 1920, 1080

# Cada tema: colores del cielo, del sol y de la rejilla
TEMAS = {
    "neon": {"cielo": ("#12082a", "#3a0f4f"), "sol": "#ff2fb3", "rejilla": "#2ee6ff", "con_sol": True},
    "oscuro": {"cielo": ("#05070f", "#14204a"), "sol": "#00d4ff", "rejilla": "#00d4ff", "con_sol": False},
    "claro": {"cielo": ("#f5f7fa", "#cfdcf0"), "sol": "#5b3fd6", "rejilla": "#0077b6", "con_sol": False},
    "hyde": {"cielo": ("#0f0f14", "#1d1a33"), "sol": "#9d9dff", "rejilla": "#9d9dff", "con_sol": False},
}


def pintar_fondo(tema):
    img = QImage(ANCHO, ALTO, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    cielo = QLinearGradient(0, 0, 0, ALTO)
    cielo.setColorAt(0.0, QColor(tema["cielo"][0]))
    cielo.setColorAt(1.0, QColor(tema["cielo"][1]))
    p.fillRect(0, 0, ANCHO, ALTO, cielo)

    horizonte = int(ALTO * 0.62)
    if tema["con_sol"]:
        centro = QPointF(ANCHO / 2, horizonte - 40)
        sol = QRadialGradient(centro, 300)
        sol.setColorAt(0.0, QColor("#ffd0ef"))
        sol.setColorAt(0.35, QColor(tema["sol"]))
        sol.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(sol)
        p.drawEllipse(centro, 300, 300)

    # Rejilla en perspectiva hacia el horizonte
    base = QColor(tema["rejilla"])
    base.setAlpha(110)
    p.setPen(QPen(base, 2))
    for i in range(-22, 23):
        p.drawLine(QPointF(ANCHO / 2 + i * 14, horizonte), QPointF(ANCHO / 2 + i * 170, ALTO))
    for k in range(1, 15):
        y = horizonte + (ALTO - horizonte) * (k / 14) ** 2
        p.drawLine(QPointF(0, y), QPointF(ANCHO, y))

    # Resplandor suave en la línea del horizonte
    brillo = QLinearGradient(0, horizonte - 6, 0, horizonte + 6)
    brillo.setColorAt(0.0, QColor(0, 0, 0, 0))
    brillo.setColorAt(0.5, QColor(tema["rejilla"]))
    brillo.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(brillo)
    p.drawRect(0, horizonte - 6, ANCHO, 12)

    p.end()
    return img


def pintar_logo():
    img = QImage(900, 300, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    fuente = QFont("DejaVu Sans", 150, QFont.Weight.Bold)
    ruta = QPainterPath()
    ruta.addText(40, 220, fuente, "NEX")

    # Halo de neón: trazos anchos y semitransparentes detrás de la letra
    for grosor, alfa in ((26, 40), (14, 90)):
        halo = QColor("#ff2fb3")
        halo.setAlpha(alfa)
        p.setPen(QPen(halo, grosor))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(ruta)

    relleno = QLinearGradient(0, 0, 900, 0)
    relleno.setColorAt(0.0, QColor("#ff2fb3"))
    relleno.setColorAt(1.0, QColor("#2ee6ff"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(relleno)
    p.drawPath(ruta)
    p.end()
    return img


def main():
    app = QApplication(sys.argv)  # noqa: F841 - necesario para pintar con Qt
    (SALIDA / "fondos").mkdir(parents=True, exist_ok=True)
    for nombre, tema in TEMAS.items():
        destino = SALIDA / "fondos" / f"{nombre}.png"
        pintar_fondo(tema).save(str(destino))
        print("escrito", destino)
    destino = SALIDA / "logo-nex.png"
    pintar_logo().save(str(destino))
    print("escrito", destino)


if __name__ == "__main__":
    main()
