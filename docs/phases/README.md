# LEONES — Índice de fases e hitos

Los paquetes de fase son la unidad documental de cierre de las grandes etapas del proyecto. Cada fase aceptada o en desarrollo se identifica además con un **hito estable Hxx**, referencia común para conversaciones, issues, documentación, commits y decisiones.

## Convención de hitos

- **H01, H02, H03...** — identificadores estables y reutilizables.
- Un hito conserva su número aunque evolucione.
- Una fase posterior que sustituya un hito debe mantener la trazabilidad y marcar la relación.
- **No se reutilizan números.**

## Estados

- 🟡 **PROVISIONAL / EN VALIDACIÓN** — implementación existente, pero todavía no aceptada.
- 🟢 **ACEPTADA** — implementación validada, documentada y aceptada explícitamente.
- 🔵 **SIGUIENTE** — siguiente unidad prioritaria de trabajo.
- ⚪ **PLANIFICADA** — todavía no implementada.
- 🔵 **SUSTITUIDA** — reemplazada por una fase posterior, conservando trazabilidad.

## Regla de cierre

```text
IMPLEMENTAR
    ↓
VALIDAR
    ↓
ACEPTAR
    ↓
DOCUMENTAR PROFUSAMENTE
    ↓
ENLAZAR DESDE README
    ↓
CERRAR FASE
```

## Auditoría

[`PHASE_AUDIT_2026-08.md`](PHASE_AUDIT_2026-08.md) — revisión de capacidades y paquetes documentales.

## Fases documentadas

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

### 🔵 H06 — 2026-08 — Open LLM Atlas ampliado — SIGUIENTE

[`atlas/README.md`](../../atlas/README.md)

**Siguiente unidad prioritaria de trabajo.** Objetivo: ampliar y depurar el conocimiento estructurado de modelos, familias, organizaciones, benchmarks y procedencia; consolidar contratos de evidencia; y preparar una base sólida para la evolución sistemática de JGB, hardware y recomendación.

H06 no está aceptado todavía. Su estado se mantiene explícitamente separado del verde de H10.

### 🟡 H07 — 2026-08 — Índice JGB sistemático

Consolidación de cobertura, evidencia y aplicación sistemática del criterio de apertura/libertad al conjunto de modelos.

### 🟡 H08 — 2026-08 — Matriz completa de hardware

Matriz 2/4/8/16/32/64/128 GB, emparejamiento Intel/AMD y cobertura NVIDIA/VRAM.

### 🟡 H09 — 2026-08 — CABE/RULA

Capa sistemática de viabilidad hardware-modelo y utilidad bajo carga.

### 🟢 H10 — 2026-08 — Atlas → recomendador diario enriquecido

[`2026-08-atlas-recommendation-pipeline/`](2026-08-atlas-recommendation-pipeline/)

**ACEPTADA mediante Run #18.** La infraestructura diaria ejecuta prospección → evidencia → ingesta → evidencia técnica → calidad → hipótesis → matriz → recomendador → enriquecimiento → validación → publicación.

**Evidencia:** Run ID `31912695040`, con 32.128 filas de matriz, 59 ficheros de recomendaciones y 859 filas validadas.

## Resultado de la auditoría

Las capacidades aceptadas disponen de referencia Hxx y paquete documental. Las áreas en evolución no se presentan como terminadas.

## Orden de trabajo vigente

```text
H10 CERRADA 🟢
      ↓
H06 ATLAS AMPLIADO 🔵  ← SIGUIENTE
      ↓
H07 JGB SISTEMÁTICO 🟡
      ↓
H08 MATRIZ HARDWARE 🟡
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

## Plantilla conceptual de un paquete

Cada paquete debe cubrir, según proceda:

- `README.md` — contexto, alcance, estado y mapa documental.
- `ARCHITECTURE.md` — arquitectura y esquemas.
- `DECISIONS.md` — decisiones, motivaciones y alternativas.
- `VALIDATION.md` — pruebas, evidencia y aceptación.
- `DIAGRAMS.md` — diagramas mantenidos cuando su complejidad lo justifique.

Norma completa: [`../DOCUMENTATION_PROTOCOL.md`](../DOCUMENTATION_PROTOCOL.md).
