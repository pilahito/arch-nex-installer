# NEX OS

Repositorio consolidado de NEX OS. Integra el instalador Arch, el asistente Nex Setup y el primer módulo de diagnóstico de NEX Rescue Center.

## Estado actual

- La ISO de prueba inicia en QEMU con UEFI y muestra la interfaz del instalador. La interfaz sigue siendo una vista previa y no ejecuta una instalación.
- El disco de prueba es un archivo qcow2 virtual de 30 GB; los discos físicos del PC no se conectan al emulador.
- Nex Rescue Center solo genera inventarios de almacenamiento de solo lectura.
- Las pruebas Python y shell de ambos proyectos se ejecutan en Linux/Arch.

## Componentes

- `generar_config.py`, `nex_instalador.py`, `nex_installer_gui.py`: instalador y sus flujos de configuración.
- `iso/`: perfil Archiso y arranque del entorno live.
- `post-instalacion/`, `tema/`: personalización de NEX.
- `nex_theme_store_gui.py`, `theme_store.py`: tienda de diseños con 14 temas incluidos, biblioteca personal y descarga de repositorios públicos de GitHub. Los repositorios descargados no ejecutan scripts; un paquete debe incluir `nex-theme.json`, `paleta.env` y `fondo.png` para importarlo como tema NEX.
- `setup/`: asistente de escritorio, optimizador, menú de aplicaciones, fondos, logotipos y pruebas.
- `rescue/`: inventario de discos en solo lectura y arquitectura de Rescue Center.
- `docs/UNIFICACION.md`: procedencia, estructura y estado de la migración.
- `THIRD_PARTY_NOTICES.md`: situación de licencias y atribuciones.

## Pruebas

```sh
python -m compileall -q generar_config.py nex_instalador.py nex_installer_gui.py nex_installer_dashboard.py nex_theme_store_gui.py theme_store.py tema/generar_fondos.py setup/nex_optimizador_gui.py setup/nex_plan.py rescue
python -m unittest discover -s tests -v
python -m unittest discover -s setup/tests -v
python -m unittest discover -s rescue/tests -v
bash tests/test_aplicar_tema.sh
bash setup/tests/test_optimizar.sh
```

GitHub Actions ejecuta los mismos controles en Linux.

## Construir ISO

En Arch Linux con `archiso`:

```sh
sudo pacman -S archiso
sudo bash iso/build-iso.sh
```

El script usa `setup/` del propio repositorio. Puedes cambiarlo con `NEX_SETUP_DIR`. Define `BUILD_DIR` y `SALIDA` para elegir carpetas de trabajo y salida. La ISO es experimental y solo debe probarse con una máquina virtual y un disco virtual descartable.

## Seguridad

No se debe instalar ni reparar un sistema en un equipo real con esta ISO. El flujo de instalación todavía no está implementado y las reparaciones del Rescue Center permanecen deshabilitadas.
