# NEX Rescue Center

Centro de diagnóstico y recuperación para la futura ISO NEX Live.

## Principios
- Exploración del hardware y almacenamiento en modo de solo lectura por defecto.
- Distinguir discos físicos de letras de unidad de Windows.
- Mostrar el plan y las rutas afectadas antes de cualquier reparación.
- Requerir confirmación explícita para operaciones de escritura.
- Recuperar archivos a un destino distinto y con espacio suficiente.
- Registrar resultados sin exponer contraseñas ni datos personales.

## Objetivos
- Diagnóstico CPU, memoria, GPU, red y SMART/NVMe.
- Recuperación guiada de GRUB, systemd-boot, kernel e initramfs.
- Comprobación de fstab, UUID y montajes.
- Informes exportables y pruebas en máquina virtual.

No ejecutar reparaciones en un equipo real hasta que cada procedimiento esté implementado y probado.
