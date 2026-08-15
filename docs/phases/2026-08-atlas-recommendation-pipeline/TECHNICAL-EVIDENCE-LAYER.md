# H10 — Capa de evidencia técnica de modelos

**Estado: 🟡 En desarrollo**

## 1. Motivo

El Run #10 demostró que la primera capa de evidencia técnica encontraba información para 39/209 modelos, pero clasificaba 0/209 como preparados para recomendación porque mezclaba en una sola condición los requisitos de identidad técnica, viabilidad y contexto de una solicitud concreta.

Se adopta una separación explícita T0/T1/T2/T3.

## 2. Niveles

### T0 — Sin perfil técnico suficiente
No hay evidencia estructurada suficiente para describir o evaluar el modelo.

### T1 — Identidad técnica
Existe al menos una señal técnica estructurada útil para identificar o describir la ruta de ejecución del modelo, por ejemplo arquitectura, parámetros, contexto, runtime o backend. T1 no implica viabilidad hardware.

### T2 — Viabilidad calculable
Añade un tamaño observado de los pesos y un runtime conocido, de forma que puede iniciarse una evaluación de viabilidad hardware. El contexto no es obligatorio para alcanzar T2 porque puede faltar en la fuente y es una propiedad distinta de la viabilidad básica de memoria/runtime.

La cuantización declarada no es obligatoria si el tamaño real del fichero de pesos ha sido observado; nunca se inventa una cuantización.

### T3 — Rendimiento observado
Añade una observación de rendimiento con hardware y runtime identificables. El extractor no fabrica T3.

```text
T0 → T1 → T2 → T3
│     │     │     │
│     │     │     └─ rendimiento reproducible/identificado
│     │     └─────── viabilidad preliminar calculable
│     └───────────── identidad técnica
└────────────────── insuficiente
```

## 3. Regla de recomendación

La matriz puede consumir perfiles **T2 o T3**. Una recomendación concreta debe comprobar memoria disponible, runtime, compatibilidad hardware y, cuando exista, el contexto soportado.

Un T2 sin contexto conocido puede producir una **recomendación preliminar de hardware**, pero el resultado debe marcar explícitamente que el contexto está `unknown` y no debe fabricar un valor de contexto.

No se exige que exista previamente un campo `estimated_memory_gb` artificialmente calculado ni una etiqueta de cuantización si existe tamaño observado de pesos.

La memoria observada de pesos se conserva en `weight_memory_gb`. No se presenta como memoria total de ejecución.

## 4. Semántica de contexto

El contexto es una **capacidad del modelo** y una **demanda de la configuración**, no una propiedad que deba crecer obligatoriamente con la RAM disponible.

Se distinguen tres conceptos:

```text
context_supported
    = máximo contexto demostrado por la evidencia del modelo

context_target
    = contexto objetivo del perfil hardware/uso

context_recommended
    = min(context_supported, context_target)
```

Por tanto, un modelo que demuestra 8K no se descarta de un equipo de 128 GB simplemente porque el perfil de hardware tenga como objetivo 16K. Se recomienda a 8K, no se afirma que soporte 16K.

Ejemplo:

```text
modelo: 8K demostrado
hardware: 128 GB
objetivo del perfil: 16K

resultado:
  soportado = 8K
  recomendado = 8K
  NO se afirma soporte de 16K
```

Cuando el contexto no está demostrado:

```text
modelo: T2
contexto: unknown
hardware: compatible por memoria/runtime

resultado:
  recomendación preliminar = SÍ
  contexto recomendado = unknown
  confianza = reducida
```

La ausencia de contexto no se convierte en un número inventado. Si una decisión concreta exige necesariamente un límite de contexto demostrado, esa decisión puede excluir el modelo, pero esa exclusión debe ser explícita y trazable.

## 5. Límites

La viabilidad T2 es una primera evaluación, no una garantía de ejecución. El tamaño de pesos no incluye automáticamente KV cache, overhead del runtime u otros consumos dinámicos. Por eso las recomendaciones deben conservar incertidumbre y no convertir T2 en una afirmación de rendimiento.

El hecho de que un modelo sea T2 no implica que pueda recomendarse para cualquier contexto o hardware.

## 6. Reglas permanentes

- No inventar datos.
- `unknown` cuando no haya evidencia.
- Procedencia y fecha cuando sea posible.
- CABE independiente de `fit_score`.
- JGB independiente del rendimiento.
- Rendimiento externo no equivale a medición LEONES.
- T3 solo con evidencia de rendimiento identificable.
- La matriz vacía debe provocar fallo explícito.
- T1 no debe bloquear por sí mismo el enriquecimiento posterior hacia T2.
- La capacidad de contexto del modelo no se confunde con el objetivo de contexto del hardware.
- Un T2 sin contexto puede ser preliminarmente recomendable, pero nunca con contexto inventado.

## 7. Validación H10

El siguiente run debe mostrar la distribución T0/T1/T2/T3 y demostrar que los perfiles T2/T3 llegan al filtro de recomendación cuando cumplen memoria/runtime/hardware. Los T2 sin contexto deberán aparecer, si caben, como recomendaciones preliminares con contexto `unknown`, no como falsos soportes de contexto.

Si la matriz sigue vacía, el log debe permitir identificar si el bloqueo está en evidencia, memoria, compatibilidad de hardware, runtime o filtros de recomendación.
