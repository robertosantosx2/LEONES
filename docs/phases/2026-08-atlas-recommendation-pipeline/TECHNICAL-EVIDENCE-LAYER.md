# H10 — Capa de evidencia técnica de modelos

**Estado: 🟡 En desarrollo**

## 1. Motivo

El Run #10 demostró que la primera capa de evidencia técnica encontraba información para 39/209 modelos, pero clasificaba 0/209 como preparados para recomendación porque exigía simultáneamente runtime, cuantización, memoria y contexto. Ese criterio mezclaba tres niveles diferentes de conocimiento.

Se adopta ahora una separación explícita T1/T2/T3.

## 2. Niveles

### T0 — Sin perfil técnico suficiente
No hay evidencia estructurada suficiente para describir o evaluar el modelo.

### T1 — Identidad técnica
Permite describir el modelo y su ruta de ejecución: runtime, contexto y arquitectura o parámetros.

### T2 — Viabilidad calculable
Añade tamaño observado de los pesos, contexto y runtime suficientes para evaluar una primera condición de viabilidad hardware. La cuantización declarada no es obligatoria si el tamaño real del fichero de pesos ha sido observado; nunca se inventa una cuantización.

### T3 — Rendimiento observado
Añade una observación de rendimiento con hardware y runtime identificables. El extractor no fabrica T3.

```text
T0 → T1 → T2 → T3
│     │     │     │
│     │     │     └─ rendimiento reproducible/identificado
│     │     └─────── viabilidad calculable
│     └───────────── identidad técnica
└────────────────── insuficiente
```

## 3. Regla de recomendación

La matriz puede consumir perfiles **T2 o T3**. No necesita que exista previamente un campo `estimated_memory_gb` artificialmente calculado ni una etiqueta de cuantización si existe tamaño observado de pesos.

La memoria observada de pesos se conserva en `weight_memory_gb`. No se presenta como memoria total de ejecución.

## 4. Límites

La viabilidad T2 es una primera evaluación, no una garantía de ejecución. El tamaño de pesos no incluye automáticamente KV cache, overhead del runtime u otros consumos dinámicos. Por eso las recomendaciones deben conservar incertidumbre y no convertir T2 en una afirmación de rendimiento.

## 5. Reglas permanentes

- No inventar datos.
- `unknown` cuando no haya evidencia.
- Procedencia y fecha cuando sea posible.
- CABE independiente de `fit_score`.
- JGB independiente del rendimiento.
- Rendimiento externo no equivale a medición LEONES.
- T3 solo con evidencia de rendimiento identificable.
- La matriz vacía debe provocar fallo explícito.

## 6. Próxima validación

El siguiente run debe mostrar la distribución T0/T1/T2/T3 y demostrar que al menos algunos T2/T3 llegan a la matriz. Si la matriz sigue vacía, el log debe permitir identificar si el bloqueo está en evidencia, compatibilidad de hardware o filtros de recomendación.
