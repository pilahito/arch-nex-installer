# Nex Arch: instalador guiado en español

Instalador de Arch Linux con el tema Nex, pensado para usuarios que no quieren configurar todo a mano. Usa `archinstall`, el instalador oficial de Arch, y añade:

- Menús en español con el estilo Nex.
- Elección de disco con confirmación escribiendo su nombre, para no borrar el disco equivocado.
- Particiones automáticas y fáciles: EFI de 1 GiB y raíz ext4 con el resto del disco. Swap en zram.
- Idioma español (es_ES), teclado español y zona horaria elegible.
- Escritorio Hyprland con SDDM, PipeWire y NetworkManager.
- Tema Nex aplicado al usuario, en dos paletas: `oscuro` y `claro`.

## Qué borra

**Borra por completo el disco que elijas.** El instalador no conserva particiones ni sistemas que ya tenga (por ejemplo, Windows). Úsalo solo en un disco que puedas vaciar.

## Requisitos

- ISO oficial de Arch Linux, arrancada en modo UEFI.
- Conexión a internet.
- Disco de al menos 9 GiB.

## Uso

Desde el ISO de Arch, como root:

```bash
bash instalar-nex.sh
```

Sigue los menús: disco, confirmación, nombre del equipo, usuario, zona horaria, contraseñas, tema y resumen final.

## Estructura

```
instalar-nex.sh          instalador (menús, archinstall y tema)
generar_config.py          genera config.json y creds.json para archinstall
post-instalacion/
  aplicar-tema.sh          aplica el tema al usuario (dentro de la instalación)
tema/
  paletas/oscuro.env       colores Nex oscuro
  paletas/claro.env        colores Nex claro
  plantillas/              configuración de Hyprland y kitty con marcadores de color
tests/
  test_generar_config.py   pruebas del generador (python3 -m unittest discover -s tests)
  test_aplicar_tema.sh     pruebas del tema sobre una raíz falsa
```

## Pruebas

```bash
python3 -m unittest discover -s tests -v
bash tests/test_aplicar_tema.sh
```

Estas pruebas no tocan discos. **La instalación completa no se ha probado todavía**: hay que hacerla en una máquina virtual o en un equipo de pruebas, nunca en el equipo real sin copia de seguridad.

## Pendiente

- Probar la instalación completa en una máquina virtual UEFI.
- Integrar el instalador dentro de la ISO (perfil de `archiso`).
- Añadir más temas o paletas.
