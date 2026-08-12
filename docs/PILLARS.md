# LEONES · 9 pilares oficiales

La arquitectura canónica de LEONES se organiza en nueve pilares. Esta lista es la referencia conceptual; la página web `web/pilares.html` contiene los esquemas, propósito, evolución y estado actual de cada uno.

| # | Pilar | Verbo | Función |
|---|---|---|---|
| 1 | Leones Atlas | Conoce | Conserva conocimiento estructurado y evidencia. |
| 2 | Leones Router | Decide | Selecciona la combinación apropiada para una tarea y entorno. |
| 3 | Leones Agents | Actúa | Convierte modelos en sistemas que usan herramientas, skills, memoria y verificación. |
| 4 | Leones Runtime | Ejecuta | Abstrae y ejecuta los backends locales. |
| 5 | Leones Quant | Reduce coste | Gestiona cuantizaciones y su impacto en memoria, velocidad y calidad. |
| 6 | Leones Fine-Tuning | Adapta | Asiste en adaptación local mediante herramientas Open. |
| 7 | Benchmark & Evaluation | Mide | Produce evidencia reproducible sobre rendimiento y utilidad. |
| 8 | Task Intelligence | Entiende | Convierte la petición en un contrato de capacidades y restricciones. |
| 9 | Leones Prospector | Descubre | Explora diariamente el ecosistema Open y detecta cambios relevantes. |

## Principio de separación

```text
Prospector → descubre
Atlas      → conoce
Task       → entiende
Router     → decide
Quant      → optimiza representación
Fine-Tuning→ adapta
Agents     → actúa
Runtime    → ejecuta
Benchmark  → mide
```

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
