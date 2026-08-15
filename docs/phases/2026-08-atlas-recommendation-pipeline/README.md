# Fase 2026-08 — Atlas → recomendador diario enriquecido

**Estado: 🟡 PROVISIONAL / EN VALIDACIÓN**

> Esta documentación se publica mientras se espera la validación real del workflow. La fase **no está aceptada todavía**.

## Objetivo

Convertir la generación diaria de recomendaciones del Atlas en un proceso automático que conserve las columnas existentes y añada, de forma trazable, dimensiones técnicas y de evidencia necesarias para el recomendador:

`JGB · CABE · RULA · rendimiento · memoria · KV cache · runtime/backend · incertidumbre · evidencia`

## Alcance

Incluye:

- extensión del `atlas/schema.json`;
- enriquecimiento de CSV de recomendaciones;
- integración del enriquecedor en `.github/workflows/atlas-pipeline.yml`;
- validación automática de columnas críticas;
- publicación de las salidas generadas por el pipeline.

No incluye todavía la demostración de que todos los valores estén medidos experimentalmente. El enriquecedor debe conservar `unknown`, `estimated`, `reported` y otros estados cuando no exista evidencia suficiente.

## Arquitectura

```text
                 PROSPECCIÓN DIARIA
                        │
                        ▼
                 EVIDENCIA EXTERNA
                        │
                        ▼
                    INGESTA
                        │
                        ▼
                 CONTROL CALIDAD
                        │
                        ▼
                    HIPÓTESIS
                        │
                        ▼
                MATRIZ DE HARDWARE
                        │
                        ▼
                  RECOMENDACIONES
                        │
                        ▼
              ENRIQUECIMIENTO MERGE
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
        JGB           CABE           RULA
          │             │              │
          └─────────────┼──────────────┘
                        ▼
            rendimiento / memoria /
            runtime / evidencia /
                incertidumbre
                        │
                        ▼
                    VALIDACIÓN
                        │
                        ▼
                    PUBLICACIÓN
```

## Regla de merge

El enriquecedor **no sustituye el CSV original por una estructura nueva**. Conserva todas las columnas existentes y añade las que falten.

Esto evita que una nueva capa documental o de recomendación destruya información producida por etapas anteriores.

## Reglas e invariantes

### 1. JGB es independiente

`JGB` representa la dimensión de apertura/libertad definida por LEONES. No se calcula a partir de rendimiento, precio o ajuste hardware.

### 2. CABE no implica RULA

```text
CABE = ¿puede caber/ejecutarse con los recursos?
RULA = ¿resulta útil bajo la carga relevante?

CABE = sí  ─────► RULA puede ser sí o no
CABE = no  ─────► configuración inviable
```

### 3. La ausencia de evidencia no se rellena con una estimación silenciosa

Cuando no existe un valor fiable, el pipeline conserva el desconocimiento y su estado.

### 4. El enriquecedor no inventa rendimiento

No se deriva `tokens_per_second` de JGB, tamaño de modelo, precio ni otra dimensión indirecta.

### 5. Evidencia externa no equivale a medición LEONES

Las fuentes externas ayudan a descubrir y contextualizar; no se convierten automáticamente en resultados propios verificados.

## Campos incorporados

El esquema Atlas incorpora, entre otros:

- `parameters_total_b`
- `parameters_active_b`
- `quantization`
- `weight_memory_gb`
- `kv_cache_gb`
- `runtime_overhead_gb`
- `memory_margin_gb`
- `runtime`
- `runtime_version`
- `backend`
- `context_length`
- `jgb`
- `jgb_status`
- `cabe`
- `cabe_status`
- `rula`
- `rula_status`
- `fit_score`
- `performance_score`
- `economic_score`
- `uncertainty`
- `evidence_state`
- `evidence_type`
- `last_verified_at`

## Decisiones

### D1 — El schema debe reflejar dimensiones separadas

**Motivación:** una única puntuación ocultaría qué parte de la recomendación procede de apertura, viabilidad, rendimiento, economía o evidencia.

### D2 — El enriquecedor debe ser no destructivo

**Motivación:** las recomendaciones ya contienen información producida por otras etapas. La nueva fase debe añadir conocimiento, no borrarlo.

### D3 — La incertidumbre forma parte del dato

**Motivación:** el Atlas trabaja con información con distintos niveles de evidencia. El desconocimiento explícito es preferible a una falsa precisión.

### D4 — La validación debe formar parte del workflow

**Motivación:** una columna crítica que desaparezca durante la generación debe hacer fallar el pipeline inmediatamente, no producir una salida aparentemente válida.

## Flujo operativo

El workflow `.github/workflows/atlas-pipeline.yml` ejecuta la fase después de generar las recomendaciones:

```text
atlas_recommend_from_feed.py
            ↓
atlas_recommendation_enrich.py
            ↓
validación de columnas críticas
            ↓
git add / commit / publicación
```

La ejecución manual se puede lanzar mediante `workflow_dispatch`.

## Validación prevista

La aceptación de esta fase exige comprobar:

- el runner arranca correctamente;
- prospección e ingesta completan sus pasos;
- se generan recomendaciones;
- el merge conserva las columnas originales;
- aparecen las nuevas columnas críticas;
- la validación del workflow pasa;
- los resultados se publican sin conflictos;
- no se generan inferencias prohibidas sobre JGB/RULA/rendimiento.

## Estado de la evidencia

Existe una ejecución manual del workflow **Atlas — Pipeline diario completo #4**, identificada por el run `31878387802`, que en el momento de redactar este documento estaba esperando runner.

Por tanto:

**implementación: realizada**  
**integración: realizada**  
**validación real: pendiente**  
**aceptación: pendiente**

## Limitaciones actuales

- La ejecución real todavía debe demostrar el comportamiento extremo a extremo.
- El enriquecedor no convierte datos desconocidos en mediciones.
- CABE/RULA seguirán necesitando mediciones reales para convertirse en evidencia fuerte.
- El pipeline todavía representa una fase de evolución del Atlas, no un sistema final de recomendación multiobjetivo.

## Siguiente paso

Completar el run manual y revisar sus pasos y logs. Si pasa los criterios de aceptación, esta documentación deberá actualizarse de **PROVISIONAL** a **ACEPTADA**, incorporar la evidencia concreta de la ejecución y enlazarse desde los README afectados como cierre formal de fase.

## Trazabilidad

- Workflow: `.github/workflows/atlas-pipeline.yml`
- Enriquecedor: `scripts/atlas_recommendation_enrich.py`
- Esquema: `atlas/schema.json`
- Metodología: `atlas/RECOMMENDER-METHODOLOGY.md`
- Run de validación: `31878387802` — `Atlas — Pipeline diario completo #4`
- Protocolo general: [`../../DOCUMENTATION_PROTOCOL.md`](../../DOCUMENTATION_PROTOCOL.md)
