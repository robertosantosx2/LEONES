# LEONES — Índice de fases e hitos

Los paquetes de fase son la unidad documental de cierre de las grandes etapas del proyecto. Cada fase aceptada o en desarrollo se identifica con un hito estable Hxx.

## Estados

- 🟡 **PROVISIONAL / EN VALIDACIÓN** — implementación existente, todavía no aceptada.
- 🟢 **ACEPTADA / CERRADA** — implementación validada, documentada y aceptada.
- 🔵 **SIGUIENTE** — siguiente unidad prioritaria.
- ⚪ **PLANIFICADA** — todavía no implementada.

## Regla de cierre

```text
IMPLEMENTAR → VALIDAR → ACEPTAR → DOCUMENTAR PROFUSAMENTE → ENLAZAR → CERRAR
```

## Guías pedagógicas de mantenimiento

- [H01/H02 — precios e integración](../completed/H01-H02-HARDWARE-PRICES.md)
- [H03 — ranking económico](../completed/H03-ECONOMIC-RANKING.md)
- [H04 — prospección diaria](../completed/H04-DAILY-PROSPECTION.md)
- [H05 — sistema documental](../completed/H05-DOCUMENTATION-SYSTEM.md)
- [H08 — matriz de hardware](../completed/H08-HARDWARE-MATRIX.md)
- [H09 — CABE/RULA](../completed/H09-CABE-RULA.md)
- [Benchmarks medidos — evidencia empírica](../completed/BENCHMARK-MEASURED-EVIDENCE.md)
- [H10 — pipeline Atlas → recomendador](../completed/H10-ATLAS-RECOMMENDER-PIPELINE.md)

## Fases

### 🟢 H01 — 2026-08 — Bot mensual de precios de hardware

[`2026-08-hardware-pricing/`](2026-08-hardware-pricing/)

Infraestructura operativa de observación mensual de precios, normalización, calidad, histórico, resumen y publicación.

### 🟢 H02 — 2026-08 — Integración precios → perfiles hardware → Atlas/recomendador

[`2026-08-hardware-pricing/`](2026-08-hardware-pricing/)

Integración validada de observaciones de precios con perfiles hardware y recomendador.

### 🟢 H03 — 2026-08 — Ranking económico V1

[`2026-08-economic-ranking-v1/`](2026-08-economic-ranking-v1/)

Primera versión validada del ranking económico.

### 🟢 H04 — 2026-08 — Prospección diaria automatizada

[`2026-08-daily-prospection/`](2026-08-daily-prospection/)

Automatización diaria de descubrimiento, filtro OSI, prioridad Copyleft, enriquecimiento, informes e integración con Atlas/web.

### 🟢 H05 — 2026-08 — Protocolo y sistema de documentación de fases

[`DOCUMENTATION_PROTOCOL.md`](../DOCUMENTATION_PROTOCOL.md)

Establece la documentación como condición de cierre y define arquitectura, decisiones, validación, trazabilidad, estados y enlaces obligatorios.

### 🟢 H06 — 2026-08 — Open LLM Atlas ampliado

[`2026-08-atlas-expanded/`](2026-08-atlas-expanded/)

**ACEPTADA / OPERATIVA.** Identidad → evidencia → quality gate → promoción `verified-only`. La auditoría mantiene `unknown`/`unverified` cuando falta evidencia.

### 🟢 H07 — 2026-08 — Índice JGB sistemático

[`2026-08-jgb-systematic/`](2026-08-jgb-systematic/)

**Infraestructura, procedimiento, integración y validación cerrados.** Falta evidencia primaria real por modelo para publicar clasificaciones factuales como `verified`; la ausencia permanece `unknown`/`provisional`.

### 🟡 H08 — 2026-08 — Matriz completa de hardware — SIGUIENTE

[`../completed/H08-HARDWARE-MATRIX.md`](../completed/H08-HARDWARE-MATRIX.md)

Infraestructura de matriz cerrada y documentada. Genera perfiles CPU × RAM × GPU y reutiliza el recomendador oficial. La matriz representa compatibilidad/recomendación, no benchmark físico. La validación empírica sobre hardware real permanece abierta.

### 🟡 H09 — 2026-08 — CABE/RULA

[`../completed/H09-CABE-RULA.md`](../completed/H09-CABE-RULA.md)

Infraestructura del contrato documentada. La cobertura empírica física permanece abierta.

### 🟢 H10 — 2026-08 — Atlas → recomendador diario enriquecido

[`2026-08-atlas-recommendation-pipeline/`](2026-08-atlas-recommendation-pipeline/)

**ACEPTADA mediante Run #18.** Prospección → evidencia → ingesta → evidencia técnica → calidad → hipótesis → matriz → recomendador → enriquecimiento → validación → publicación.

## Resultado de la auditoría

Las capacidades aceptadas disponen de referencia Hxx y documentación. Las áreas en evolución no se presentan como terminadas. H08 y H09 mantienen abierto únicamente el trabajo empírico físico; H07 mantiene abierta la evidencia primaria real por modelo.

## Orden de trabajo vigente

```text
H10 CERRADA 🟢
      ↓
H06 CERRADA 🟢
      ↓
H07 CERRADA 🟢
      ↓
H08 MATRIZ HARDWARE 🟡 ← SIGUIENTE
      ↓
H09 CABE / RULA 🟡
      ↓
BENCHMARKS REALES
      ↓
AGENTIC / LB
      ↓
ROUTER
      ↓
WEB / APP
      ↓
MANADA
      ↓
TCO
      ↓
OPTIMIZACIÓN MULTIOBJETIVO
```

## Mantenimiento

Cada paquete debe mantener contexto, arquitectura, decisiones, validación y navegación suficientes para que una persona con conocimientos básicos pueda mantenerlo. Todo workflow que escriba en artefactos canónicos debe respetar la regla global de no concurrencia de LEONES.
