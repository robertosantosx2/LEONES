# H09 — CABE / RULA

## Estado

**🟢 Infraestructura del contrato terminada y limpia.**

La clasificación CABE/RULA está implementada como una capa derivada de una medición de `tokens_per_second`. No sustituye al rendimiento observado, no es un `fit_score` y no incorpora por sí misma JGB, precio, hardware ni apertura.

La **cobertura empírica física** sigue siendo una tarea abierta: que el clasificador esté terminado no significa que todos los modelos y equipos hayan sido medidos.

## Regla oficial

```text
< 1 tok/s           → NO_CABE
1 <= tok/s < 10    → CABE
10 <= tok/s <= 100  → RULA
> 100 tok/s        → RULA+
```

Los límites son deliberados:

- `1` pertenece a CABE.
- `10` pertenece a RULA.
- `100` pertenece a RULA.
- `100.01` pertenece a RULA+.

## Principio fundamental

El dato continuo y la etiqueta son dos campos distintos:

```text
TOKENS_PER_SECOND = observación
PERFORMANCE_CLASS = interpretación derivada
```

Nunca se debe sustituir el primer campo por el segundo.

## Arquitectura

```text
medición / fuente
       ↓
normalize_cabe_rula_measurement.py
       ↓
classify_cabe_rula.py
       ↓
classify_performance.py
       ↓
performance_class
```

Cuando la entrada procede del circuito de benchmarks reales:

```text
runtime
  ↓
run_and_record_benchmark.py
  ↓
record_benchmark.py
  ↓
measurement_type = measured
  ↓
enrich_measured_performance.py
  ↓
CABE / RULA
```

## Componentes

### `scripts/normalize_cabe_rula_measurement.py`

Convierte el valor recibido a `float` y rechaza entradas vacías, no numéricas, negativas, `NaN` e infinitas. Su función es validar el dato; no decide la categoría.

### `scripts/classify_cabe_rula.py`

Es el **clasificador canónico**. Contiene las cuatro fronteras oficiales y no realiza estimaciones.

Además, protege el contrato directamente frente a `NaN` e infinito. Esto evita que una llamada directa al clasificador pueda convertir un dato inválido en `RULA+`.

### `scripts/classify_performance.py`

Es el punto de entrada que deben utilizar los pipelines. Primero normaliza y después llama al clasificador canónico. Así las reglas no se copian en cada pipeline.

### `scripts/enrich_measured_performance.py`

Añade la clasificación únicamente a registros cuyo `measurement_type` sea `measured`. Una estimación no puede entrar por este camino.

## Tests

`tests/test_cabe_rula.py` cubre expresamente:

- `0.99 → NO_CABE`;
- `1 → CABE`;
- `9.99 → CABE`;
- `10 → RULA`;
- `100 → RULA`;
- `100.01 → RULA+`;
- valores negativos rechazados;
- `NaN` rechazado;
- infinito rechazado.

El resto del circuito de medición dispone además de tests de normalización, enriquecimiento, promoción, publicación e integración con Atlas.

## Separación respecto de otros criterios

CABE/RULA no sustituye:

- **JGB**, que mide apertura/libertad según su propio contrato;
- **precio**, que pertenece al análisis económico;
- **hardware**, que determina compatibilidad y recursos;
- **fit_score**, que es una decisión de recomendación;
- **T0/T1/T2/T3**, que describe el estado de evidencia técnica.

H10 establece explícitamente como invariante que JGB/CABE/RULA no se sustituyen por un único score y que no se inventa rendimiento. urlDocumentación H10 — VALIDATION.mdhttps://github.com/robertosantosx2/LEONES/blob/main/docs/phases/2026-08-atlas-recommendation-pipeline/VALIDATION.md

## Evidencia real

Una clasificación solo describe el valor que recibe. No convierte una estimación en medición.

El circuito de evidencia distingue:

```text
estimated ≠ measured
```

La infraestructura completa está descrita en [`BENCHMARK-MEASURED-EVIDENCE.md`](BENCHMARK-MEASURED-EVIDENCE.md).

El formato canónico general de resultados también mantiene separados los estados `reported`, `reproducible`, `verified` y `rejected`; que un resultado sea sintácticamente válido no lo convierte automáticamente en verificado. [`RESULT_SCHEMA.md`](../RESULT_SCHEMA.md).

## Criterio de cierre

H09 queda cerrado como **infraestructura de clasificación** porque:

1. existe una única implementación canónica de las fronteras;
2. la normalización está separada de la clasificación;
3. los límites 1, 10 y 100 están probados;
4. los datos imposibles se rechazan;
5. los pipelines tienen un punto de entrada común;
6. una medición real conserva `tokens_per_second`;
7. una estimación no puede promocionarse como medición;
8. JGB, hardware, precio y `fit_score` permanecen independientes;
9. existe documentación pedagógica de mantenimiento.

## Qué queda fuera del cierre

```text
CONTRATO CABE/RULA              🟢
IMPLEMENTACIÓN                  🟢
NORMALIZACIÓN                   🟢
TESTS                           🟢
INTEGRACIÓN CON MEDICIONES      🟢
COBERTURA FÍSICA DE BENCHMARKS  🟡
```

La cobertura física se seguirá ampliando mediante el circuito de benchmarks medidos. No se marcará como evidencia real ningún resultado obtenido únicamente mediante simulaciones o estimaciones.

## Mantenimiento para humanos no especialistas

Si se modifica una frontera:

1. cambiar la regla únicamente en `classify_cabe_rula.py`;
2. no copiar la regla a otros scripts;
3. modificar `tests/test_cabe_rula.py` con el nuevo comportamiento;
4. revisar `classify_performance.py` y el circuito de medición;
5. actualizar este documento;
6. ejecutar la batería de tests;
7. revisar que ningún `fit_score`, JGB o precio haya empezado a depender de la etiqueta.

La documentación de fases establece que una pieza no se considera cerrada solo por tener código: debe implementarse, validarse, aceptarse, documentarse profusamente y enlazarse desde los README. [`docs/phases/README.md`](../phases/README.md).
