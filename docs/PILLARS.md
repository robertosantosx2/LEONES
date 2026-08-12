# LEONES · 9 pilares oficiales

La arquitectura canónica de LEONES se organiza en nueve pilares. El orden importa: **Leones Prospector es la Capa 1**, porque mantiene permanentemente actualizado el conocimiento disponible sobre el ecosistema Open. La página web `web/pilares.html` contiene los esquemas, propósito, evolución y estado actual de cada uno.

| # | Capa / Pilar | Verbo | Función |
|---|---|---|---|
| 1 | **Leones Prospector** | Descubre | Explora diariamente el ecosistema Open y detecta novedades, cambios y oportunidades. |
| 2 | **Leones Atlas** | Conoce | Conserva conocimiento estructurado y evidencia. |
| 3 | **Leones Task Intelligence** | Entiende | Convierte la petición en un contrato de capacidades y restricciones. |
| 4 | **Leones Router** | Decide | Selecciona la combinación apropiada para una tarea y entorno. |
| 5 | **Leones Quant** | Reduce coste | Gestiona cuantizaciones y su impacto en memoria, velocidad y calidad. |
| 6 | **Leones Fine-Tuning** | Adapta | Asiste en adaptación local mediante herramientas Open. |
| 7 | **Leones Agents** | Actúa | Convierte modelos en sistemas que usan herramientas, skills, memoria y verificación. |
| 8 | **Leones Runtime** | Ejecuta | Abstrae y ejecuta los backends locales. |
| 9 | **Leones Benchmark & Evaluation** | Mide | Produce evidencia reproducible sobre rendimiento y utilidad. |

## Flujo conceptual

```text
CAPA 1 · LEONES PROSPECTOR
        ↓
CAPA 2 · LEONES ATLAS
        ↓
CAPA 3 · LEONES TASK INTELLIGENCE
        ↓
CAPA 4 · LEONES ROUTER
        ↓
┌───────┼──────────────┐
↓       ↓              ↓
QUANT   FINE-TUNING    AGENTS
└───────┼──────────────┘
        ↓
LEONES RUNTIME
        ↓
LEONES BENCHMARK & EVALUATION
        ↓
evidencia → retroalimentación
```

## Principio de separación

Prospector → descubre

Atlas → conoce

Task Intelligence → entiende

Router → decide

Quant → optimiza representación

Fine-Tuning → adapta

Agents → actúa

Runtime → ejecuta

Benchmark & Evaluation → mide

Ningún pilar debe absorber silenciosamente la responsabilidad de otro. La implementación puede ser inicialmente pequeña, pero la frontera conceptual debe mantenerse clara.

## Estado

La arquitectura está definida. No todos los pilares están igualmente implementados. La documentación pública debe distinguir siempre entre `activo`, `primera versión`, `en desarrollo` y `arquitectura definida / implementación pendiente`.

## Transparencia transversal

La evidencia no es un décimo pilar. Es una regla transversal. Una fuente externa puede permanecer como `external-unvalidated`; solamente una revisión explícita puede convertirla en `atlas-evidence`. Incluso entonces se conserva si el dato es `measured`, `reported`, `estimated`, `calculated` o `anecdotal`.

## Documentación

- Arquitectura canónica: `web/pilares.html`
- Arquitectura operativa: `web/arquitectura.html`
- Guía de operación: `web/operacion.html`
- Política de descubrimiento: `docs/DISCOVERY_POLICY.md`
- Prospección: `docs/PROSPECTION.md`
- Evidencia: `docs/EVIDENCE.md`
