# NEX OS — repositorio único

## Destino
Este repositorio se convertirá en la fuente principal de NEX OS.

## Orígenes
- `pilahito/arch-nex-installer`: instalador, temas y generador de configuración.
- `pilahito/arch-nex-setup`: asistente PyQt6, optimización, aplicaciones y recursos.

## Estructura objetivo
- `installer/`: instalador (migración gradual desde la raíz).
- `setup/`: asistente de configuración y optimización (importar preservando historia y licencias).
- `rescue/`: diagnósticos de solo lectura y reparaciones supervisadas.
- `archiso/`: imagen Live USB y menú gráfico.
- `tests/`: simulación y pruebas automáticas.

## Migración segura
1. Comparar con las versiones locales en `G:\\Proyectos` antes de sustituir código.
2. Importar y revisar `arch-nex-setup` íntegramente, incluidos assets, atribuciones y pruebas.
3. Ejecutar las pruebas de ambos componentes y probar la ISO en VM UEFI.
4. Publicar NEX OS como único proyecto principal.
5. Solo después de verificar paridad, archivar el repositorio secundario (sin borrarlo de forma irreversible).

**Estado:** este documento es un plan de consolidación, no indica que los archivos se hayan fusionado.
**Seguridad:** la ISO no debe particionar, formatear ni reparar discos sin consentimiento explícito.
