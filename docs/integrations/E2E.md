# Plan E2E ODS/Magnitude

## Objetivo

Demostrar que una instalación puede ser reproducida, validada y medida sin confundir los datos del producto con evidencia LEONES.

## ODS

1. Preflight limpio.
2. Mostrar plan y consentimiento.
3. Instalar una versión fijada o release explícito.
4. Capturar versión/ref.
5. Capturar hardware y configuración.
6. Ejecutar `ods status` y `ods doctor`.
7. Comprobar endpoint local.
8. Ejecutar prompt de humo.
9. Ejecutar benchmark LEONES.
10. Comprobar que la medición queda como `measured`.
11. Ejecutar uninstall/recovery en entorno de prueba.
12. Comprobar que no hubo publicación de telemetría sin consentimiento.

## Magnitude

1. Preflight Node.js/npm.
2. Mostrar plan y consentimiento.
3. Instalar `@magnitudedev/cli`.
4. Capturar versión.
5. Ejecutar Magnitude en proyecto temporal.
6. Capturar modelo, repositorio/archivo, cuantización y runtime cuando estén expuestos.
7. Confirmar antes de una descarga grande.
8. Ejecutar una tarea controlada de edición de archivo.
9. Ejecutar benchmark independiente LEONES.
10. Separar recomendación de Magnitude de medición LEONES.
11. Comprobar governance metadata de skills.
12. Ejecutar cleanup del proyecto de prueba.

## Casos de fallo obligatorios

- Docker ausente para ODS.
- GPU no detectable.
- RAM insuficiente.
- almacenamiento insuficiente.
- Node/npm ausente para Magnitude.
- red caída durante descarga.
- modelo no accesible.
- servicio local no responde.
- usuario rechaza consentimiento.
- usuario rechaza descarga grande.

Un fallo de preflight debe detener la instalación antes de modificar el sistema cuando sea posible.
