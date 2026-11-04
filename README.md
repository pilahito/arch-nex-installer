# Delta Setup para Arch Linux

Menú de instalación con estilo "Delta Assistant" para elegir las aplicaciones que quieres instalar en Arch Linux. Las apps se configuran en un archivo de texto simple.

## Configurar las apps

Edita `config/apps.conf`. Cada categoría es una sección `[Nombre]` y cada app una línea:

```
paquete | Nombre visible | origen | estado
```

- `origen`: `pacman` (repositorios oficiales) o `aur` (necesita `yay`).
- `estado`: `on` (marcada por defecto) u `off`.

## Uso

Instalar en un Arch ya instalado:

```bash
sudo bash install.sh
delta-setup
```

Sin instalar, desde la carpeta del proyecto:

```bash
bash delta-setup.sh                  # menú interactivo
bash delta-setup.sh --list           # ver las apps configuradas
bash delta-setup.sh --dry-run        # ver qué instalaría sin instalar nada
bash delta-setup.sh --select steam,vlc
```

El menú usa `whiptail` (paquete `libnewt`).

## Integrar en la ISO de Arch

```bash
sudo pacman -S archiso
sudo bash archiso/build-iso.sh
```

Copia el perfil oficial `releng`, añade los paquetes de `archiso/packages.x86_64` y mete `delta-setup` dentro de la ISO. La ISO queda en `build/salida/`. La carpeta `build/` no se sube al repositorio.
