# Atlas — metodología de recomendación v0.2

## Objetivo

Transformar la información del Atlas en recomendaciones reproducibles sin colapsar todas las dimensiones en una única puntuación opaca.

## Principio

Una recomendación Atlas debe responder separadamente a cinco preguntas:

1. **¿Es libre/abierto?** → JGB.
2. **¿CABE en el hardware?** → memoria, cuantización, contexto y margen.
3. **¿Puede RULAR con el stack elegido?** → runtime/backend/formato.
4. **¿Qué rendimiento se observa?** → medición propia o evidencia externa claramente etiquetada.
5. **¿Qué coste tiene?** → precios observados, nunca precios inventados.

La decisión final puede ordenar candidatos, pero debe conservar todas las dimensiones originales.

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
- `RULA`: existe una ruta de ejecución compatible.
- `RULA_INCIERTO`: la compatibilidad no ha sido verificada en la configuración exacta.
- `NO_RULA`: no existe actualmente una ruta compatible documentada.

**CABE no implica RULA. RULA no implica buen rendimiento.**

## Memoria

Para una primera aproximación:

`memoria_pesos_GB ≈ parámetros_B × bits_efectivos / 8`

Después deben añadirse KV cache, activaciones, overhead del runtime y margen de seguridad. Para cuantizaciones GGUF se pueden usar los factores documentados en `LLM-SYSTEMS-2026.md` como aproximación inicial, pero la medición real prevalece.

Para MoE se deben conservar por separado `parameters_total` y `parameters_active`.

## Runtime

El formato del modelo no determina por sí solo el runtime óptimo. La recomendación debe registrar al menos:

- formato;
- backend/runtime;
- versión o commit cuando esté disponible;
- acelerador;
- offloading;
- contexto;
- parámetros relevantes de ejecución.

## Evidencia

Jerarquía:

1. **LEONES measured** — hardware y configuración reproducibles.
2. **External reproducible** — tercero con configuración suficientemente documentada.
3. **External reported** — dato publicado pero sin protocolo completo.
4. **Estimated** — cálculo derivado; nunca presentarlo como benchmark.

Los datos externos no se convierten en `tokens_per_second` oficiales LEONES.

## Ranking

El ranking económico/performance puede utilizar una función auxiliar para ordenar candidatos, pero no reemplaza los campos originales. En particular, **JGB nunca se reduce a una consecuencia del rendimiento**.

La visualización debe mostrar, como mínimo:

- JGB;
- CABE;
- RULA;
- rendimiento;
- coste/precio;
- nivel de evidencia;
- advertencias de incertidumbre.

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

El siguiente paso del Atlas es incorporar campos explícitos de:

- memoria estimada de pesos;
- memoria KV estimada;
- margen de memoria;
- CABE;
- RULA;
- runtime recomendado;
- nivel de evidencia;
- fuente de rendimiento;
- fuente de precio;
- incertidumbre.

Esto permite que el recomendador sea explicable y evita que una única puntuación o benchmark sustituya la clasificación de apertura JGB.
