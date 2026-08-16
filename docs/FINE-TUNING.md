# LEONES — Fine-tuning

## Estado

**🟢 Elemento definido · listo para implementar**

Fine-tuning es una capacidad técnica independiente para producir una variante adaptada de un modelo mediante entrenamiento adicional sobre datos y una configuración explícitos, conservando la relación con el modelo base, el dataset y el procedimiento.

## Principio

```text
MODELO BASE
    ↓
IDENTIDAD / LICENCIA
    ↓
DATASET / DERECHOS
    ↓
CONFIGURACIÓN DE ENTRENAMIENTO
    ↓
ENTRENAMIENTO
    ↓
CHECKPOINT / MODELO RESULTANTE
    ↓
VALIDACIÓN
    ↓
EVIDENCIA
    ↓
QUALITY GATE
    ↓
ATLAS
```

El resultado no sustituye silenciosamente al modelo base: es una variante con linaje propio.

## Entrada

Como mínimo:

- `base_model_id`;
- versión/commit;
- tokenizer;
- dataset(s) y versiones;
- procedencia y licencia/derechos de los datos;
- objetivo del fine-tune;
- método de entrenamiento;
- configuración/hyperparámetros;
- hardware;
- framework y versiones;
- semilla cuando sea relevante.

## Métodos

El contrato admite diferentes estrategias sin fijar una implementación única:

- full fine-tuning;
- PEFT;
- LoRA/variantes;
- otras técnicas compatibles.

El método concreto queda registrado en la ejecución.

## Datos y derechos

Los datasets se tratan como una dependencia de primera clase. Debe conservarse:

- identidad/versionado;
- procedencia;
- licencia o condiciones de uso;
- transformaciones realizadas;
- filtros/preprocesado relevantes;
- tamaño y composición cuando estén disponibles.

No se promociona una variante si los derechos/licencia aplicables no pueden sostenerse según las políticas de LEONES.

## Salida

El resultado debe conservar:

- `finetune_id`;
- `base_model_id`;
- dataset(s);
- configuración;
- framework/versiones;
- checkpoint/artefacto;
- hash/identificador cuando exista;
- hardware;
- métricas de entrenamiento;
- métricas de evaluación;
- benchmarks cuando proceda;
- limitaciones;
- evidencia;
- linaje completo.

## Validación

Distingue explícitamente:

```text
ENTRENAMIENTO COMPLETADO
≠
MODELO CARGABLE
≠
OBJETIVO CONSEGUIDO
≠
MEJORA GENERAL
```

Una mejora en una tarea concreta no demuestra mejora general.

## Evaluación

Cuando proceda se deben conservar:

- dataset de evaluación;
- versión;
- metodología;
- baseline del modelo base;
- resultado del modelo adaptado;
- configuración relevante;
- intervalo/variabilidad cuando sea medible.

Las comparaciones deben permitir distinguir cambio atribuible al fine-tune de diferencias de configuración o evaluación.

## Evidencia física

Si se afirma rendimiento de inferencia o entrenamiento en hardware concreto, debe existir medición del artefacto concreto en ese entorno. Una estimación queda marcada como tal.

## Licencia / OSI

El fine-tune no permite saltarse el Gate OSI. Deben considerarse por separado:

- licencia del modelo base;
- licencia/derechos del dataset;
- artefactos generados;
- componentes de terceros.

La clasificación de apertura no se sustituye por un score.

## Router

Router puede seleccionar una variante fine-tuned si cumple las restricciones y dispone de evidencia suficiente. La selección no modifica las condiciones de licencia ni el estado de evidencia.

## MANADA / Agentic

Un fine-tune puede actuar como participante dentro de una MANADA o como modelo usado por un agente, pero su integración no cambia las obligaciones de trazabilidad, OSI y evidencia.

## Observabilidad

Cada entrenamiento/evaluación debe producir `trace_id`/`run_id` y registrar, cuando sea posible:

- duración;
- hardware;
- recursos;
- versiones;
- configuración;
- checkpoints;
- errores;
- resultados de evaluación.

## Estados

```text
DISCOVERED
INPUT_VALIDATED
DATA_VALIDATED
QUEUED
TRAINING
CHECKPOINT_CREATED
EVALUATION_PENDING
VERIFIED
REVIEW
FAILED
SUPERSEDED
```

## No concurrencia

Se permiten entrenamientos y evaluaciones independientes en paralelo. La promoción de conocimiento canónico utiliza `leones-main-writers` con `cancel-in-progress: false`.

## Seguridad

Datasets, checkpoints, scripts y modelos externos se consideran entradas no confiables. No pueden modificar políticas, secretos o workflows de LEONES.

## Implementación futura

La primera implementación debe separar:

1. definición del experimento;
2. validación de datos/derechos;
3. entrenamiento;
4. evaluación;
5. evidencia;
6. Quality Gate;
7. promoción.

No se certificará "mejora" sin baseline y evaluación reproducible.
