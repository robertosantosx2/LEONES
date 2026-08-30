# LEONES — `STRICT`: limpiar, fijar y dar esplendor

**Estado:** FIJADO  
**Ámbito:** todo el trabajo realizado desde el 27 de agosto de 2026 hasta la fecha de este documento  
**Rama de integración:** `rc1-minimal-script-cleanup`

## 1. Qué significa `STRICT`

Cuando el usuario pide **«limpia, fija y da esplendor»**, LEONES entra en modo `STRICT`.

No significa simplemente formatear código ni hacer que pasen los tests. Significa revisar el bloque completo como si fuera a ser mantenido por otra persona dentro de seis meses: entender qué hace, qué no hace, por qué existe, cómo se ejecuta, qué evidencia produce y qué decisiones quedan cerradas.

### Limpiar

- Eliminar duplicidades y rutas paralelas.
- Retirar restos de diseños anteriores que ya no sean parte del contrato.
- Separar código activo de material deliberadamente retirado o histórico.
- Evitar nombres, campos o mecanismos que creen una segunda semántica para selección, benchmark, scoring o evidencia.
- Mantener los runners pequeños y específicos.

### Fijar

- Identificar una única fuente canónica para cada decisión.
- Convertir las reglas importantes en contratos, schemas, tests e invariantes.
- Registrar explícitamente el estado de cada jalón.
- Conservar la procedencia de la evidencia real.
- No reabrir un jalón cerrado salvo que aparezca una contradicción demostrable.

### Dar esplendor

- Documentar internamente el código con comentarios y docstrings pedagógicos.
- Escribir documentación externa `.md` que permita utilizar cada componente sin conocer previamente su implementación.
- Explicar entradas, salidas, propósito, límites, errores y ejemplos.
- Explicar el motivo de las decisiones no obvias, no sólo repetir qué hace una línea.
- Hacer que los nombres, contratos y rutas sean coherentes entre sí.

## 2. Regla de documentación interna

Todo script operativo nuevo o modificado debe poder ser leído por una persona con conocimientos básicos de programación.

Debe explicar, cuando sea relevante:

1. **Qué problema resuelve.**
2. **Qué recibe.**
3. **Qué produce.**
4. **Qué NO hace.**
5. **Por qué existe esa frontera.**
6. **Qué error significa un fallo del contrato.**

Los comentarios deben explicar intención y contexto. No se deben llenar los archivos de comentarios que simplemente traduzcan literalmente el código.

Ejemplo del nivel esperado:

```python
# Este paso no calcula una puntuación nueva. Sólo comprueba que la decisión
# ya tomada por el contrato canónico está respaldada por la evidencia que
# corresponde a esa decisión. Mantener esta frontera evita que el gate se
# convierta accidentalmente en un segundo motor de scoring.
```

## 3. Regla de documentación externa

Cada superficie operativa debe tener una explicación `.md` accesible desde la documentación del proyecto.

Como mínimo debe quedar claro:

- cuándo usarla;
- cuándo no usarla;
- comando de ejecución;
- formato de entrada;
- formato de salida;
- artefactos conservados;
- errores habituales;
- relación con el contrato anterior y posterior;
- si necesita ejecución física en Ubuntu o puede verificarse sólo de forma declarativa.

## 4. Regla de arquitectura

La cadena canónica es:

`selection → runtime → execution → measurement → evidence → decision → validation → promotion → publication → recommendation → output → E2E trace`

No se debe introducir otra cadena que compita con ella.

En particular:

- ODS/Magnitude aportan las señales externas que el contrato les asigna.
- La evidencia de ejecución local permanece separada de esas señales.
- El benchmark real no se sustituye por una estimación declarativa.
- La recomendación reutiliza decisión y evidencia; no vuelve a puntuar.
- La capa de salida transporta la recomendación canónica; no la reinterpreta.
- Los runners auditan contratos; no son otra fuente de verdad.

## 5. Regla de Ubuntu

Ubuntu se utiliza sólo cuando una comprobación necesita ejecución física real.

Todo lo que pueda quedar resuelto mediante contratos, schemas, tests, documentación, análisis estático o construcción Git debe hacerse antes de pedir intervención manual en Ubuntu.

Cuando Ubuntu sea imprescindible, la operación debe ser concreta:

`sincronizar → ejecutar → medir → conservar evidencia → validar → publicar`

No se debe volver a diseñar la arquitectura durante una ejecución física.

## 6. Criterio de cierre STRICT

Un bloque sólo se considera cerrado cuando:

- existe un contrato canónico;
- existe la documentación necesaria;
- existen tests/invariantes adecuados;
- los artefactos importantes tienen procedencia identificable;
- no hay una ruta paralela accidental;
- `git diff --check` pasa;
- el runner o gate correspondiente pasa cuando existe;
- y el estado queda registrado de forma reproducible.

## 7. Qué se conserva

La limpieza no significa borrar historia útil. Se conserva:

- decisiones cerradas;
- contratos y schemas;
- evidencia real;
- auditorías;
- trazabilidad;
- conocimiento de runtimes retirados cuando explica una frontera vigente;
- material deprecated cuando sea necesario para entender compatibilidad o migración.

Lo que se elimina es la ambigüedad, no la historia.

## 8. Aplicación automática

Esta regla queda asociada a la petición literal:

> **«limpia, fija y da esplendor»**

La petición activa `STRICT` y debe interpretarse con este documento como contrato operativo.