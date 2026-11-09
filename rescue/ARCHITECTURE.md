# Arquitectura de Rescue Center

## Capas

1. **Interfaz**: presenta hallazgos y solicita una operación. No accede a dispositivos por su cuenta.
2. **Casos de uso**: recopilan diagnósticos, preparan un plan legible y coordinan la confirmación.
3. **Modelo**: representa dispositivos, hallazgos, severidad, rutas afectadas y plan propuesto.
4. **Proveedores**: consultan APIs del sistema. El proveedor inicial llama a `lsblk` sin privilegios y sin alterar estado.
5. **Acciones**: futuras operaciones de reparación, aisladas de los proveedores de diagnóstico. No hay acciones registradas todavía.

## Frontera de escritura

El inventario actual tiene una interfaz de solo lectura y no acepta comandos arbitrarios. No se deben añadir escrituras a los métodos de detección. Una futura reparación deberá:

- identificar el dispositivo por ruta y atributos verificables, y volver a leerlos justo antes de actuar;
- excluir discos del sistema anfitrión y mostrar dispositivo, particiones y efecto esperado;
- producir primero un plan sin ejecutarlo;
- exigir confirmación explícita por operación, nunca inferida de la selección;
- guardar el informe y el resultado en el destino elegido por el usuario;
- tener pruebas con dispositivos simulados y una prueba QEMU antes de habilitarse.

Las reparaciones deben permanecer ausentes del menú y de la ISO hasta cumplir esas condiciones.
