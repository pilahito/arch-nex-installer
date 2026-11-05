#!/usr/bin/env python3
"""NEX Installer graphical front end for the live ISO."""
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QVBoxLayout, QWidget, QStackedWidget,
)

BG = "#0b0e1a"
PANEL = "#111629"
CARD = "#151c33"
MUTED = "#a9b2d0"
ACCENT = "#8c5cff"


class Installer(QMainWindow):
    steps = ["Distribución", "Escritorio", "Drivers", "Almacenamiento", "Paquetes", "Finalizar"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NEX Installer · Arch Linux Setup Experience")
        self.resize(1120, 720)
        self.setMinimumSize(900, 620)
        self.setStyleSheet(f"QMainWindow,QWidget{{background:{BG};color:#f5f4ff;font-family:'Segoe UI',sans-serif}} QLabel#muted{{color:{MUTED}}} QPushButton{{background:{CARD};border:1px solid #354064;border-radius:12px;padding:13px;color:#f5f4ff}} QPushButton:hover{{border:1px solid #9b7aff;background:#202744}} QPushButton#primary{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c39f3,stop:1 #466fff);font-weight:700;border:0}}")
        outer = QVBoxLayout()
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(10)
        root = QWidget(); root.setLayout(outer); self.setCentralWidget(root)
        header = QHBoxLayout()
        logo = QLabel("NEX Installer")
        logo.setStyleSheet("font-size:24px;font-weight:800;color:#f7f5ff")
        tagline = QLabel("Arch Linux Setup Experience")
        tagline.setObjectName("muted")
        brand = QVBoxLayout(); brand.addWidget(logo); brand.addWidget(tagline)
        header.addLayout(brand); header.addStretch()
        badge = QLabel("Arch Linux   /   Hyprland Ready")
        badge.setStyleSheet("font-size:13px;color:#d8d2ff;padding:8px")
        header.addWidget(badge); outer.addLayout(header)

        body = QHBoxLayout(); body.setSpacing(10); outer.addLayout(body, 1)
        nav = QFrame(); nav.setStyleSheet(f"background:{PANEL};border:1px solid #292f4a;border-radius:16px")
        nav.setFixedWidth(174); nl = QVBoxLayout(nav); nl.setContentsMargins(10,14,10,10); nl.setSpacing(8)
        self.step_buttons = []
        for i, name in enumerate(self.steps):
            b = QPushButton(f"{i+1}    {name}"); b.setMinimumHeight(44)
            b.setStyleSheet("text-align:left;padding-left:12px;font-size:13px")
            b.setEnabled(i == 0)
            self.step_buttons.append(b); nl.addWidget(b)
        nl.addStretch(); nl.addWidget(QLabel("NEX OS · x86_64\nInstalación guiada"))
        body.addWidget(nav)

        main = QFrame(); main.setStyleSheet(f"background:{PANEL};border:1px solid #292f4a;border-radius:16px")
        ml = QVBoxLayout(main); ml.setContentsMargins(18,16,18,14); ml.setSpacing(10)
        self.title = QLabel("Elige tu distribución")
        self.title.setStyleSheet("font-size:23px;font-weight:750;border:0")
        ml.addWidget(self.title)
        self.subtitle = QLabel("Arch Linux es la opción principal de NEX. También puedes elegir Ubuntu o Debian.")
        self.subtitle.setObjectName("muted"); ml.addWidget(self.subtitle)
        self.pages = QStackedWidget(); ml.addWidget(self.pages, 1)
        self.selection = None
        self.pages.addWidget(self.distribution_page())
        self.pages.addWidget(self.info_page("Elige tu escritorio", "Hyprland es el escritorio recomendado para Arch. KDE Plasma, GNOME y XFCE también estarán disponibles según la distribución."))
        self.pages.addWidget(self.info_page("Controladores", "El instalador detectará el hardware y presentará las opciones compatibles."))
        self.pages.addWidget(self.info_page("Almacenamiento", "Selecciona el disco virtual de 30 GB. No se modificará nada hasta revisar el resumen y confirmar la instalación."))
        self.pages.addWidget(self.info_page("Paquetes", "Elige herramientas de desarrollo, multimedia y juegos para personalizar NEX."))
        self.pages.addWidget(self.info_page("Todo listo", "Revisa la distribución, escritorio y disco antes de empezar."))
        footer = QHBoxLayout(); self.status = QLabel("Arch Linux  ·  Hyprland  ·  Disco virtual de prueba: 30 GB")
        self.status.setObjectName("muted"); footer.addWidget(self.status); footer.addStretch()
        self.back = QPushButton("Atrás"); self.back.setEnabled(False); self.back.clicked.connect(self.previous)
        self.next = QPushButton("Continuar  →"); self.next.setObjectName("primary"); self.next.clicked.connect(self.advance)
        footer.addWidget(self.back); footer.addWidget(self.next); ml.addLayout(footer)
        body.addWidget(main, 1)
        side = QFrame(); side.setFixedWidth(222); side.setStyleSheet(f"background:{PANEL};border:1px solid #292f4a;border-radius:16px")
        sl=QVBoxLayout(side); sl.setContentsMargins(12,12,12,12); sl.setSpacing(9)
        preview=QLabel("NEX\n\nArch  /  Hyprland\n\nN   E   X")
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter); preview.setMinimumHeight(180)
        preview.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #171b37,stop:0.5 #32206d,stop:1 #101428);border:1px solid #7257dc;border-radius:14px;font-size:17px;font-weight:700;color:#dcd3ff")
        sl.addWidget(preview); sl.addWidget(QLabel("Información del equipo"))
        for a,b in [("Procesador","Detectado al arrancar"),("Memoria","4 GB para la VM"),("Disco","30 GB virtuales"),("Sistema","UEFI · prueba aislada")]:
            item=QLabel(f"{a}\n{b}"); item.setObjectName("muted"); item.setStyleSheet(f"background:{CARD};border:1px solid #303958;border-radius:10px;padding:8px;font-size:12px")
            sl.addWidget(item)
        sl.addStretch(); body.addWidget(side)

    def distribution_page(self):
        w=QWidget(); grid=QGridLayout(w); grid.setContentsMargins(0,8,0,0); grid.setSpacing(10)
        options=[("A","Arch Linux","Principal · flexible y personalizable","arch"),("U","Ubuntu","Sencillo y listo para usar","ubuntu"),("D","Debian","Base estable para usuarios avanzados","debian")]
        self.cards=[]
        for i,(icon,title,desc,key) in enumerate(options):
            card=DistributionCard(icon,title,desc,key,key=="arch")
            card.clicked.connect(lambda k=key, t=title: self.choose(k,t))
            grid.addWidget(card,0,i); self.cards.append(card)
        self.selection="arch"
        hint=QLabel("Arch Linux está seleccionado como sistema principal de NEX."); hint.setObjectName("muted")
        grid.addWidget(hint,1,0,1,3); grid.setRowStretch(2,1)
        return w

    def info_page(self,title,desc):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(10,30,10,10)
        t=QLabel(title); t.setStyleSheet("font-size:22px;font-weight:700")
        d=QLabel(desc); d.setWordWrap(True); d.setObjectName("muted"); d.setStyleSheet("font-size:16px;padding-top:10px")
        l.addWidget(t); l.addWidget(d); l.addStretch(); return w

    def choose(self,key,title):
        self.selection=key
        for c in self.cards: c.set_selected(c.key==key)
        self.status.setText(f"{title}  ·  seleccionado")

    def advance(self):
        i=self.pages.currentIndex()
        if i<5:
            self.pages.setCurrentIndex(i+1); self.back.setEnabled(True)
            self.step_buttons[i].setEnabled(True); self.step_buttons[i+1].setEnabled(True)
            self.title.setText(["Elige tu distribución","Elige tu escritorio","Controladores","Almacenamiento","Paquetes","Resumen de instalación"][i+1])
            if i==4: self.next.setText("Revisar  →")
            if i==5: self.next.setText("Instalar")
        else:
            self.title.setText("Revisión necesaria")
            self.subtitle.setText("Esta vista inicial permite recorrer la configuración. La instalación permanecerá bloqueada hasta integrar y verificar el backend de cada distribución.")
            self.next.setEnabled(False)

    def previous(self):
        i=max(0,self.pages.currentIndex()-1); self.pages.setCurrentIndex(i)
        self.back.setEnabled(i>0); self.next.setText("Continuar  →")
        self.title.setText(["Elige tu distribución","Elige tu escritorio","Controladores","Almacenamiento","Paquetes","Resumen de instalación"][i])


class DistributionCard(QFrame):
    from PyQt6.QtCore import pyqtSignal
    clicked = pyqtSignal()

    def __init__(self, icon, title, description, key, selected=False):
        super().__init__()
        self.key=key
        self.setObjectName("distributionCard")
        self.setMinimumHeight(180)
        self.set_selected(selected)
        layout=QVBoxLayout(self); layout.setContentsMargins(12,12,12,12); layout.setSpacing(8)
        badge=QLabel(icon); badge.setAlignment(Qt.AlignmentFlag.AlignCenter); badge.setFixedSize(42,42)
        badge.setStyleSheet("background:#30265e;color:#bca4ff;border-radius:21px;font-size:20px;font-weight:800")
        layout.addWidget(badge,0,Qt.AlignmentFlag.AlignHCenter)
        heading=QLabel(title + ("  ·  PRINCIPAL" if key=="arch" else ""))
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter); heading.setWordWrap(True)
        heading.setStyleSheet("font-size:14px;font-weight:700;color:#f5f4ff")
        layout.addWidget(heading)
        detail=QLabel(description); detail.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop); detail.setWordWrap(True)
        detail.setStyleSheet(f"font-size:12px;color:{MUTED}")
        layout.addWidget(detail,1)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_selected(self, selected):
        self.setProperty("selected", selected)
        self.setStyleSheet("QFrame#distributionCard{background:#131a2d;border:1px solid #343e5d;border-radius:14px} QFrame#distributionCard[selected='true']{background:#211b43;border:2px solid #9670ff}")

    def mousePressEvent(self,event):
        self.clicked.emit()
        super().mousePressEvent(event)


app=QApplication(sys.argv)
app.setFont(QFont("Segoe UI",10))
window=Installer(); window.showMaximized()
sys.exit(app.exec())
