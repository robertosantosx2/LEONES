# LEONES — archivo de transición a RC1

> Estado: **archivo histórico**. No es arquitectura activa.

Esta rama (`deprecated/pre-rc1-legacy`) conserva el punto de partida completo anterior a la reorganización de RC1. Se crea para que la limpieza sea reversible y auditable.

## Qué se considera legado

Se consideran candidatos a quedar fuera del camino canónico de RC1:

- prototipos y rutas alternativas de selección/runtime que duplican contratos ya cerrados;
- experimentos de JALÓN 2/3 que ya fueron sustituidos por los contratos finales;
- documentación de diseños que fueron superseded por la arquitectura post-JALÓN 3;
- integraciones no demostradas físicamente que no sean necesarias para el MVP;
- scripts auxiliares que no participan en el recorrido canónico `hardware → selection → runtime → evidence → recommendation`.

## Qué NO se elimina

No se archivan automáticamente:

- contratos de JALÓN 1–3 que sean necesarios como autoridad histórica;
- tests que protejan comportamiento vigente;
- esquemas de evidencia usados por el camino canónico;
- datos/fixtures reproducibles;
- componentes de Atlas/Prospector que todavía sean dependencias reales del producto.

## Regla de transición

Primero se identifica dependencia real; después se archiva. Ningún archivo se elimina por nombre o antigüedad solamente.

La rama activa de RC1 debe poder mantenerse mínima sin perder trazabilidad histórica.

## Ramas históricas

Las numerosas ramas `jalon2-*`, `jalon3-*`, `jalon4-*` y `jalon5-*` anteriores a esta reorganización se consideran **historial de desarrollo**, no rutas de producto. Este manifiesto no las borra: su función es preservar el historial sin obligar a RC1 a mantener sus decisiones como arquitectura vigente.
