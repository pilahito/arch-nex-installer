# NEX OS: repositorio único

## Estado de la consolidación

La rama de trabajo conserva el historial y la base del PR #1 de `arch-nex-installer`, incorpora los cambios locales más recientes del instalador y añade `arch-nex-setup` como subtree Git en `setup/`. La copia original de ambos repositorios permanece intacta.

## Componentes

- Raíz y `iso/`: instalador NEX, su interfaz, perfil Archiso y personalización posterior.
- `setup/`: asistente PyQt6, optimizador, menú de aplicaciones, catálogo, recursos, capturas y pruebas del repositorio Setup.
- `rescue/`: inventario de bloques en solo lectura y arquitectura para diagnósticos.
- `tests/`, `setup/tests/` y `rescue/tests/`: pruebas de cada componente.

El subtree conserva los archivos y commits de Setup. Sus documentos de atribución (`assets/logos/ORIGEN.md` y `assets/marcas/ORIGEN.md`) se mantienen junto a los recursos.

## Licencias y atribuciones

Ninguno de los dos repositorios de origen contiene un archivo de licencia general. No se asigna una licencia nueva a su código. Se conservan las atribuciones/licencias declaradas para los logotipos y se documenta la situación en `THIRD_PARTY_NOTICES.md`. Antes de redistribuir el código como producto, sus titulares deben elegir y añadir la licencia del proyecto.

## Construcción y validación

- `iso/build-iso.sh` empaqueta Setup desde `setup/` por defecto; `NEX_SETUP_DIR` permite seleccionar otra ubicación.
- CI compila los módulos y ejecuta las suites Python y shell en Linux.
- La ISO debe probarse con UEFI en QEMU usando únicamente el disco qcow2 de prueba.
- La interfaz actual del instalador es una vista previa; el flujo de instalación sigue bloqueado hasta implementar y verificar todas las protecciones del disco.

## Límites de seguridad

La primera versión de Rescue Center solo enumera dispositivos. No monta, desmonta, repara, particiona, formatea ni escribe en discos. Toda futura reparación debe ser una función separada, con selección inequívoca del dispositivo, previsualización de operaciones y confirmación explícita.
