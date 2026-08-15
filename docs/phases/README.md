# LEONES — Índice de fases

Los paquetes de fase son la unidad documental de cierre de las grandes etapas del proyecto.

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

## Fases actuales

### 🟡 2026-08 — Atlas → recomendador diario enriquecido

[`2026-08-atlas-recommendation-pipeline/`](2026-08-atlas-recommendation-pipeline/)

Estado actual: **en validación**. El workflow diario ha sido conectado al enriquecedor de recomendaciones y existe una ejecución manual de GitHub Actions pendiente de completar. No se marca como aceptada hasta comprobar el run real.

### Próximas fases

Se añadirán aquí únicamente cuando exista una unidad de trabajo suficientemente definida y trazable.

## Plantilla conceptual de un paquete

Cada paquete debe cubrir, según proceda:

- `README.md` — contexto y mapa documental.
- `ARCHITECTURE.md` — arquitectura y esquemas.
- `DECISIONS.md` — decisiones y alternativas.
- `VALIDATION.md` — pruebas y aceptación.
- `DIAGRAMS.md` — diagramas mantenidos.

Norma completa: [`../DOCUMENTATION_PROTOCOL.md`](../DOCUMENTATION_PROTOCOL.md).
