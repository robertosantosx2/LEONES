# H06 — Decisiones de arquitectura

## D01 — El feed no es el Atlas canónico

El feed operativo alimenta el pipeline diario. El Atlas canónico representa entidades, relaciones y evidencia. Se necesita una capa explícita de normalización.

**Motivación:** evitar que la estructura tabular del pipeline determine accidentalmente el modelo de conocimiento.

## D02 — Identidad antes que cobertura

La expansión del catálogo se hará después de establecer reglas para identidad, variante, versión, familia, organización, repositorio y artefacto.

**Motivación:** ampliar un catálogo con identidad inestable multiplica duplicados y contradicciones.

## D03 — Evidencia por separado

La procedencia y el estado de evidencia son dimensiones independientes del contenido técnico. `reported`, `reproducible`, `verified` y `rejected` mantienen significado propio.

**Motivación:** una URL encontrada no equivale a una medición ni a una verificación LEONES.

## D04 — No inventar ni convertir ausencia en cero

Los valores desconocidos permanecen `unknown`/`null` según el contrato. Un campo ausente no se interpreta como cero.

## D05 — Apertura, rendimiento y recomendación no se sustituyen entre sí

La clasificación de apertura permanece separada de JGB, CABE, RULA, rendimiento y economía.

## D06 — Memoria en capas

El tamaño de pesos, KV cache, overhead del runtime y margen se mantienen como conceptos distintos. La matriz hardware no debe tratar el tamaño de pesos como memoria total de ejecución.

## D07 — Contexto como capacidad y demanda

La longitud de contexto descrita por un modelo y el contexto objetivo de una configuración son conceptos distintos. Una recomendación puede limitarse a la capacidad demostrada; nunca se inventa soporte de contexto.

## D08 — H10 permanece estable

H06 consume la infraestructura H10 ya aceptada. No se modifica H10 como parte de esta auditoría salvo que se demuestre una incompatibilidad contractual.

## D09 — La validación debe ser trazable

Una muestra de datos normalizada debe poder seguirse desde fuente → descubrimiento → identidad → entidad Atlas → evidencia → consumidor. La validación de H06 tendrá que demostrar esa cadena.
