# NEX Rescue Center

Centro de diagnóstico para la futura ISO NEX Live. La primera función disponible es un inventario de dispositivos de bloque que solo consulta `lsblk`.

## Uso

En Arch Linux:

```sh
python3 rescue/nex_rescue.py
python3 rescue/nex_rescue.py --output informe-nex.json
```

Sin `--output`, el informe JSON se escribe en la salida estándar. La opción de archivo crea un archivo nuevo y falla si ya existe, para no sobrescribir informes.

## Garantías de la primera versión

- No requiere privilegios de administrador.
- No ejecuta montaje, desmontaje, reparación ni comandos de particionado.
- Marca el informe como solo lectura y declara las operaciones de escritura deshabilitadas.
- Solo muestra tipo, tamaño, modelo, sistema de archivos, estado de solo lectura, si es extraíble y puntos de montaje.
- No recopila números de serie.

## Arquitectura

La guía de separación entre interfaz, casos de uso, proveedores de solo lectura y futuras acciones está en [ARCHITECTURE.md](ARCHITECTURE.md). Las reparaciones no están implementadas ni disponibles en esta versión.
