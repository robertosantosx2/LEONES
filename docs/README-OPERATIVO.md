# LEONES — Mapa operativo de documentación

Este documento explica dónde buscar cuando se retoma LEONES después de varios días.

## 1. Primero: contrato STRICT

Lee [`STRICT-LIMPIA-FIJA-ESPLENDOR.md`](STRICT-LIMPIA-FIJA-ESPLENDOR.md).

Si la petición es **«limpia, fija y da esplendor»**, ese documento define el procedimiento obligatorio.

## 2. Después: estado de los jalones

Lee [`jalones/JALONES-1-10-BASELINE.md`](jalones/JALONES-1-10-BASELINE.md) y, cuando exista un jalón activo posterior, su contrato específico.

Es el mapa compacto de lo que está cerrado y de las fronteras que no deben romperse.

## 3. Arquitectura

La documentación de arquitectura explica la separación entre selección, runtime, ejecución, medición, evidencia, decisión y recomendación.

La regla esencial es que una capa posterior consume la salida contractual de la anterior; no vuelve a inventar su propia versión de la responsabilidad.

## 4. Runtimes

La taxonomía y los adapters describen qué runtimes están contemplados y bajo qué condiciones pueden ejecutarse.

La documentación declarativa nunca debe presentarse como prueba de rendimiento físico.

## 5. Evidencia

Los documentos y artefactos de runtime explican cómo se conserva una ejecución real. Una medición sólo es evidencia física cuando procede de una ejecución real y conserva su identidad y procedencia.

## 6. Decisión y recomendación

- JALÓN 5: decisión y bridge ODS/Magnitude.
- JALÓN 6: frontera evidencia → recomendación.
- JALÓN 7: validación → promoción → publicación.
- JALÓN 8: trazabilidad E2E.
- JALÓN 9: recomendación canónica.
- JALÓN 10: salida fiel de recomendación.
- JALÓN 11: operación E2E que conecta los contratos anteriores.

## 7. Scripts

La documentación específica de scripts se encuentra en `scripts/README.md` y `docs/SCRIPTS-OPERATIVOS.md`. Los scripts operativos deben tener comentarios/docstrings que expliquen su intención y sus fronteras.

Los runners `run_jalon*.sh` son auditores. No son una segunda implementación de los contratos.

## 8. Qué hacer al retomar el proyecto

1. Sincronizar la rama de trabajo.
2. Leer el baseline consolidado.
3. Leer el contrato del jalón activo.
4. Ejecutar primero los tests/gates existentes.
5. Sólo después modificar código.
6. Si se solicita «limpia, fija y da esplendor», aplicar `STRICT` antes de construir la siguiente pieza.
7. En JALÓN 11, demostrar primero la cadena declarativa y reservar la ejecución física para Ubuntu.

## 9. Regla de lenguaje

En la documentación se distingue cuidadosamente:

- **declarativo:** el sistema sabe cómo debería funcionar;
- **autorizado:** el contrato permite una ejecución concreta;
- **ejecutado:** el runtime ha corrido realmente;
- **medido:** se han obtenido métricas de una ejecución;
- **evidenciado:** la medición está conservada con procedencia;
- **recomendado:** una decisión ya validada se presenta al usuario.

No deben utilizarse estos términos como sinónimos.
