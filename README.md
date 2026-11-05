# NEX Installer

Asistente gráfico para preparar instalaciones de Linux. **Arch Linux es la distribución principal**; Ubuntu y Debian aparecen como alternativas.

## Estado

La interfaz gráfica está en desarrollo. Permite recorrer las pantallas de selección y mostrar la configuración inicial, pero todavía no instala ninguna distribución. El botón final permanece bloqueado hasta que los instaladores y las protecciones del disco estén implementados y verificados.

La ISO de pruebas arranca en una máquina virtual QEMU con un disco virtual de 30 GB. No expone los discos físicos del equipo. No se debe usar todavía para instalar un sistema.

## Proyecto

- `nex_installer_gui.py`: interfaz gráfica PyQt6.
- `nex_instalador.py`: instalador anterior basado en terminal para Arch.
- `generar_config.py`: generación de configuración para `archinstall`.
- `iso/`: perfil de `archiso`, paquetes y arranque del asistente.
- `post-instalacion/` y `tema/`: personalización de NEX.

## Crear una ISO de prueba

El perfil de construcción está en `iso/build-iso.sh`. Se ejecuta en un entorno Arch Linux con `archiso` y necesita acceso de red para obtener los paquetes. El resultado es una ISO live para pruebas; no equivale a un instalador terminado.

## Próximos pasos

1. Completar las pantallas gráficas y su adaptación a distintos tamaños.
2. Conectar el flujo de Arch con `archinstall` y probarlo solo en una VM.
3. Incorporar Ubuntu y Debian con instaladores separados.
4. Mantener la instalación bloqueada hasta detectar y confirmar el disco virtual de destino.
