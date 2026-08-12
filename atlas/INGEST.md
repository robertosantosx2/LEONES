# Atlas ingestion v0.1

El catálogo de LEONES permanece vacío hasta incorporar datos con procedencia.

## Fuente mínima de un registro

Cada registro debe cumplir `atlas/schema.json` y contener:

- `id`, `kind`, `name`.
- Estado de evidencia: `reported`, `reproducible`, `verified` o `rejected`.
- Fuentes y fecha de recuperación cuando estén disponibles.
- Clasificación de apertura separada de cualquier puntuación.

## Flujo

Prospección → extracción → normalización → revisión → Atlas.

Los datos descubiertos automáticamente no se consideran verificados por el mero hecho de aparecer en una fuente.
