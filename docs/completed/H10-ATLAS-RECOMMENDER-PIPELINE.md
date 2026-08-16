# H10 — Pipeline Atlas → recomendador diario

## 1. Qué problema resuelve

H10 conecta las piezas de conocimiento y recomendación en un proceso diario reproducible. La idea es que el resultado de hoy pueda generarse mañana sin que una persona tenga que copiar datos manualmente.

## 2. Flujo

```text
PROSPECCIÓN
   ↓
EVIDENCIA EXTERNA
   ↓
INGESTA
   ↓
EVIDENCIA TÉCNICA
   ↓
CALIDAD
   ↓
HIPÓTESIS
   ↓
MATRIZ HARDWARE
   ↓
RECOMENDADOR
   ↓
ENRIQUECIMIENTO
   ↓
VALIDACIÓN
   ↓
PUBLICACIÓN
```

## 3. El concepto más importante: evidencia

H10 no supone que todos los datos estén medidos físicamente. Por eso conserva estados T0, T1, T2 y T3 y estados de evidencia como `unknown`, `reported`, `reproducible` y `verified`.

La ausencia de un dato no se rellena con una cifra inventada.

## 4. Scripts principales

### `atlas_hardware_matrix.py`

Construye combinaciones de CPU, RAM y GPU NVIDIA y ejecuta el recomendador para cada perfil. Separa RAM del sistema y VRAM. También impone un objetivo de contexto que no convierte automáticamente la RAM en capacidad del modelo.

### `atlas_recommend_from_feed.py`

Es la pieza que decide qué modelos del feed pasan los filtros técnicos de un perfil. Comprueba nivel técnico, memoria, runtime, cuantización/peso observado y compatibilidad del hardware. Después calcula un `fit_score` y conserva las razones de la decisión.

### `atlas_economic_rank.py`

Añade la dimensión económica usando precios observados. Es una capa separada: no cambia JGB ni convierte el precio en evidencia de rendimiento.

## 5. Cómo entender T0–T3

```text
T0 → todavía no hay evidencia técnica estructurada suficiente
T1 → existe identidad/información técnica útil
T2 → existe evidencia suficiente para empezar a evaluar viabilidad
T3 → T2 + rendimiento observado identificable
```

La escalera no es una puntuación de calidad. Es un nivel de evidencia.

## 6. CABE y RULA

- **CABE** responde a si la configuración puede caber técnicamente.
- **RULA** responde a si puede resultar útil bajo la carga considerada.

Que algo quepa no implica que funcione bien. Por eso se mantienen separados.

## 7. Contexto

El sistema distingue tres conceptos:

- `context_supported`: capacidad demostrada por el modelo.
- `context_target`: objetivo del perfil.
- `context_recommended`: el mínimo entre lo demostrado y el objetivo.

Si el modelo no demuestra su contexto, se conserva `unknown`.

## 8. Evidencia de aceptación

H10 fue aceptada mediante Run #18 del pipeline diario. La ejecución de referencia procesó 209 modelos, produjo 32.128 filas de matriz, 59 ficheros de recomendaciones y 859 filas validadas.

Esos números demuestran que el pipeline funciona de extremo a extremo; no significan que cada modelo tenga benchmark físico propio.

## 9. Publicación

El workflow usa una estrategia de `fetch + rebase + retry` para reducir carreras entre ejecuciones que intentan publicar simultáneamente en `main`.

Esta parte es crítica: un pipeline que calcula correctamente pero pierde su publicación no está completo.

## 10. Mantenimiento para principiantes

Cuando una recomendación desaparezca, no empieces modificando el score. Sigue el flujo hacia atrás:

```text
¿está en la salida?
   ↓ no
¿está en la matriz?
   ↓ no
¿pasa el recomendador?
   ↓ no
¿tiene T2/T3?
   ↓ no
¿tiene memoria/runtime/evidencia suficiente?
   ↓ no
¿está bien ingerido?
```

Esto permite encontrar el motivo real en vez de taparlo con una excepción.

## 11. Qué sigue fuera de H10

H10 no cierra JGB sistemático, CABE/RULA con medición real, benchmarks físicos, evaluación agentiva, router dinámico, TCO ni optimización multiobjetivo. Esos elementos siguen en fases posteriores.

## Enlaces

- Fase: [`docs/phases/2026-08-atlas-recommendation-pipeline/`](../phases/2026-08-atlas-recommendation-pipeline/)
- Workflow: [`.github/workflows/atlas-pipeline.yml`](../../.github/workflows/atlas-pipeline.yml)
- Matriz: [`scripts/atlas_hardware_matrix.py`](../../scripts/atlas_hardware_matrix.py)
- Recomendador: [`scripts/atlas_recommend_from_feed.py`](../../scripts/atlas_recommend_from_feed.py)
- Ranking: [`scripts/atlas_economic_rank.py`](../../scripts/atlas_economic_rank.py)
- Contrato de resultados: [`docs/RESULT_SCHEMA.md`](../RESULT_SCHEMA.md)
