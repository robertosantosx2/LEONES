# Atlas — metodología de recomendación v0.3

## Objetivo

Transformar la información del Atlas en recomendaciones reproducibles sin colapsar todas las dimensiones en una única puntuación opaca.

## Capas de conocimiento y evidencia

LEONES mantiene cuatro capas que no deben mezclarse:

1. **Fuente** — el proyecto, documentación o servicio que aporta información.
2. **Evidencia** — lo que esa fuente afirma o demuestra, con su procedencia y fecha.
3. **Estimación** — cálculo derivado de datos disponibles; no es una medición.
4. **Medición LEONES** — resultado obtenido por LEONES ejecutando una prueba reproducible sobre hardware/runtime concretos.

LLMFit entra en las capas de **Fuente/Evidencia** y puede producir **Estimaciones** de ajuste. Nunca convierte por sí mismo una estimación de rendimiento o compatibilidad en `LEONES measured`.

## Principio

Una recomendación Atlas debe responder separadamente a cinco preguntas:

1. **¿Es libre/abierto?** → JGB.
2. **¿CABE en el hardware?** → memoria, cuantización, contexto y margen.
3. **¿Puede RULAR con el stack elegido?** → runtime/backend/formato.
4. **¿Qué rendimiento se observa?** → medición propia o evidencia externa claramente etiquetada.
5. **¿Qué coste tiene?** → precios observados, nunca precios inventados.

La decisión final puede ordenar candidatos, pero debe conservar todas las dimensiones originales.

## LLMFit → runtime-selection.v1

El adaptador `atlas/llmfit_adapter.py` normaliza candidatos LLMFit al contrato del Atlas y puede producir un candidato `runtime-selection.v1`.

La regla de seguridad es deliberada:

```text
LLMFit
  │
  ▼
Fuente / Evidencia externa
  │
  ▼
Estimación CABE / ajuste
  │
  ▼
runtime-selection.v1
  │
  ├── sin RULA verificado → NO autorizar ejecución
  └── RULA verificado + comando confiable → autorizar
```

Por tanto, que LLMFit estime que un modelo cabe en memoria **no autoriza** su ejecución. La autorización necesita una ruta de runtime confiable y `RULA` verificado. La posterior ejecución A01 es la que puede generar medición LEONES.

## Pipeline

```text
MODELO
  │
  ├── JGB ────────────────┐
  ├── tamaño/cuanti ──────┤
  ├── contexto/KV ────────┤
  ├── runtime/backend ────┤
  ├── evidencia rendimiento ┤
  └── precio hardware ────┘
              │
              ▼
        FILTRO CABE
              │
              ▼
        FILTRO RULA
              │
              ▼
     COMPARACIÓN EXPERIMENTAL
              │
              ▼
       RANKING EXPLICABLE
```

## Estados

- `CABE`: el modelo entra en memoria con margen suficiente según la estimación disponible.
- `NO_CABE`: la estimación supera la memoria disponible o deja un margen inseguro.
- `CABE_INCIERTO`: faltan datos relevantes (por ejemplo KV/contexto/runtime).
- `RULA`: existe una ruta de ejecución compatible y verificada.
- `RULA_INCIERTO`: la compatibilidad no ha sido verificada en la configuración exacta.
- `NO_RULA`: no existe actualmente una ruta compatible documentada.

**CABE no implica RULA. RULA no implica buen rendimiento. Una estimación tampoco implica medición.**

## Evidencia

Jerarquía:

1. **LEONES measured** — hardware y configuración reproducibles.
2. **External reproducible** — tercero con configuración suficientemente documentada.
3. **External reported** — dato publicado pero sin protocolo completo.
4. **Estimated** — cálculo derivado; nunca presentarlo como benchmark.

Los datos externos no se convierten en `tokens_per_second` oficiales LEONES.

## Ranking

El ranking puede ordenar candidatos, pero no reemplaza los campos originales. En particular, **JGB nunca se reduce a una consecuencia del rendimiento**.

La visualización debe mostrar, como mínimo: JGB, CABE, RULA, rendimiento, coste/precio, nivel de evidencia y advertencias de incertidumbre.

## Recomendación por hardware

Para cada perfil de hardware, el Atlas debe producir:

1. candidatos que CABE;
2. candidatos que además RULA;
3. candidatos con evidencia de rendimiento;
4. candidatos con precio documentado;
5. ranking final explicable;
6. lista de datos que faltan para mejorar la recomendación.

## Regla de selección

La recomendación preferida no es necesariamente el modelo con mayor puntuación. Es el candidato que ofrece el mejor equilibrio para la carga concreta **sin violar las restricciones de CABE, RULA y libertad**, y con evidencia suficiente.

Cuando dos candidatos son equivalentes, debe preferirse el que tenga menor incertidumbre y mejor trazabilidad.

## Próxima implementación

El siguiente paso es alimentar el selector con candidatos de LLMFit y, tras `runtime-selection.v1`, ejecutar el mismo camino A01 que ya está preparado para producir evidencia `measured`. Los valores de LLMFit deben conservarse como estimaciones hasta que una prueba LEONES los sustituya o complemente.
