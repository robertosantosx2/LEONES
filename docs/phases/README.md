# LEONES — Índice de fases e hitos

Los paquetes de fase son la unidad documental de cierre de las grandes etapas del proyecto. Cada fase aceptada o en validación se identifica además con un **hito estable Hxx**, que es la referencia común para conversaciones, issues, documentación, commits y decisiones.

## Convención de hitos

- **H01, H02, H03...** — identificadores estables y reutilizables.
- Un hito conserva su número aunque evolucione.
- Una fase posterior que sustituya un hito debe mantener la trazabilidad y marcar la relación.
- **No se reutilizan números.**

## Estados

- 🟡 **PROVISIONAL / EN VALIDACIÓN** — implementación existente, pero todavía no aceptada.
- 🟢 **ACEPTADA** — implementación validada, documentada y aceptada explícitamente.
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

[`PHASE_AUDIT_2026-08.md`](PHASE_AUDIT_2026-08.md) — revisión de todas las capacidades que el estado actual del proyecto identifica como terminadas/operativas.

## Fases documentadas

### 🟢 H01 — 2026-08 — Bot mensual de precios de hardware

[`2026-08-hardware-pricing/`](2026-08-hardware-pricing/)

Infraestructura operativa de observación mensual de precios, normalización, calidad, histórico, resumen y publicación. La cobertura de mercado y la inteligencia avanzada siguen en desarrollo.

### 🟢 H02 — 2026-08 — Integración precios → perfiles hardware → Atlas/recomendador

[`2026-08-hardware-pricing/`](2026-08-hardware-pricing/)

Integración validada de las observaciones de precios con perfiles de hardware y el recomendador.

### 🟢 H03 — 2026-08 — Ranking económico V1

[`2026-08-economic-ranking-v1/`](2026-08-economic-ranking-v1/)

Primera versión validada del ranking que combina rendimiento, JGB, hardware fit y coste observado, con viabilidad antes de economía y cobertura explícita.

### 🟢 H04 — 2026-08 — Prospección diaria automatizada

[`2026-08-daily-prospection/`](2026-08-daily-prospection/)

Automatización diaria de descubrimiento, filtro OSI, prioridad Copyleft, enriquecimiento, informes e integración con Atlas/web.

### 🟢 H05 — 2026-08 — Protocolo y sistema de documentación de fases

[`DOCUMENTATION_PROTOCOL.md`](../DOCUMENTATION_PROTOCOL.md)

Establece la documentación como condición de cierre y define arquitectura, decisiones, validación, trazabilidad, estados y enlaces obligatorios.

### 🟡 H06 — 2026-08 — Open LLM Atlas ampliado

[`atlas/README.md`](../../atlas/README.md)

Ampliación y depuración continua de modelos, familias, organizaciones, benchmarks y procedencia. Sigue en evolución y no se considera una fase aceptada globalmente.

### 🟡 H07 — 2026-08 — Índice JGB sistemático

Consolidación de cobertura, evidencia y aplicación sistemática del criterio de apertura/libertad al conjunto de modelos.

### 🟡 H08 — 2026-08 — Matriz completa de hardware

Matriz 2/4/8/16/32/64/128 GB, emparejamiento Intel/AMD y cobertura NVIDIA/VRAM.

### 🟡 H09 — 2026-08 — CABE/RULA

Capa sistemática de viabilidad hardware-modelo y utilidad bajo carga.

### 🟡 H10 — 2026-08 — Atlas → recomendador diario enriquecido

[`2026-08-atlas-recommendation-pipeline/`](2026-08-atlas-recommendation-pipeline/)

Estado actual: **en validación**. El workflow diario ha sido conectado al enriquecedor de recomendaciones y existe una ejecución manual de GitHub Actions en curso. No se marca como aceptada hasta comprobar el run real y sus resultados.

## Resultado de la auditoría

La revisión del repositorio ha comparado las capacidades que el roadmap identifica como terminadas con los paquetes documentales. Las capacidades actualmente marcadas como operativas/validadas disponen ahora de una referencia Hxx y de paquete documental cuando corresponde.

Durante la revisión se detectó y corrigió una discrepancia documental: el documento antiguo del bot de precios describía Amazon España como fuente activa, mientras la configuración efectiva del repositorio mantiene cuatro fuentes activas y Amazon fuera de cobertura. La documentación ahora refleja la configuración efectiva.

Las áreas que el roadmap marca como **en evolución o en desarrollo** no se han falsificado como fases terminadas: Atlas, JGB, matriz hardware, CABE/RULA, benchmarks reales, agentic, router, web/app y Manada siguen fuera del estado ACEPTADA cuando la evidencia disponible no permite cerrarlas.

## Próximas fases

Los siguientes hitos se numerarán cuando exista una unidad de trabajo suficientemente definida. **No se reutilizan Hxx ya asignados.**

## Plantilla conceptual de un paquete

Cada paquete debe cubrir, según proceda:

- `README.md` — contexto, alcance, estado y mapa documental.
- `ARCHITECTURE.md` — arquitectura y esquemas.
- `DECISIONS.md` — decisiones, motivaciones y alternativas.
- `VALIDATION.md` — pruebas, evidencia y aceptación.
- `DIAGRAMS.md` — diagramas mantenidos cuando su complejidad lo justifique.

Norma completa: [`../DOCUMENTATION_PROTOCOL.md`](../DOCUMENTATION_PROTOCOL.md).
