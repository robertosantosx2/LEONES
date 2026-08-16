# H06 — Open LLM Atlas ampliado

**Estado: 🟢 ACEPTADA / OPERATIVA.**

## Objetivo

Ampliar y depurar el Open LLM Atlas como capa estructurada de conocimiento de LEONES, aumentando cobertura, procedencia, calidad y trazabilidad de modelos, familias, organizaciones, variantes, runtimes, benchmarks y evidencia.

H06 se apoya en la infraestructura diaria H10, que ya está aceptada, pero su aceptación es independiente.

## Resultado de la fase

H06 establece la frontera que faltaba entre el feed operativo y el Atlas canónico:

```text
atlas_feed.csv
      ↓
identidad canónica
      ↓
evidencia
      ↓
quality gate
      ↓
verified-only
      ↓
atlas/catalog.json
```

La promoción es **verified-only**, no destructiva y no inventa valores. El workflow `.github/workflows/atlas-h06.yml` automatiza pruebas, auditorías, promoción y validación contra JSON Schema.

## Validación final

La ejecución final auditó:

- **193** filas del feed;
- **193** identidades;
- **193** identidades únicas según el auditor actual;
- **0** grupos duplicados detectados;
- **193** flags de calidad, todos `unverified`;
- **0** filas `verified`;
- **0** registros promovidos al Atlas canónico;
- **0** registros en `atlas/catalog.json`.

Este resultado es correcto: el Atlas no se rellena artificialmente cuando la evidencia no alcanza el estado exigido. El informe completo queda en [`H06_FINAL.md`](H06_FINAL.md).

La publicación automática se ha endurecido frente a ejecuciones concurrentes: el snapshot generado se confirma y después se rebasea sobre `main` antes del `push`.

## Documentación

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — arquitectura canónica.
- [`COVERAGE-AUDIT.md`](COVERAGE-AUDIT.md) — auditoría de cobertura.
- [`IDENTITY-RULES.md`](IDENTITY-RULES.md) — identidad y deduplicación.
- [`EVIDENCE-RULES.md`](EVIDENCE-RULES.md) — reglas de evidencia.
- [`DECISIONS.md`](DECISIONS.md) — decisiones de arquitectura.
- [`VALIDATION.md`](VALIDATION.md) — validación automatizada.
- [`H06_FINAL.md`](H06_FINAL.md) — informe de cierre.

## Reglas de datos

- No inventar valores.
- Mantener `unknown` cuando no exista evidencia.
- Conservar procedencia y fecha siempre que estén disponibles.
- Separar identidad de modelo, variante, familia y organización.
- Separar evidencia externa de medición LEONES.
- No confundir parámetros totales con parámetros activos.
- No confundir tamaño de pesos con memoria total de ejecución.
- No confundir contexto máximo declarado con contexto efectivamente probado.
- No convertir una ausencia de dato en cero.

## Relación con H10

H10 proporciona la automatización diaria. H06 establece la calidad y frontera de conocimiento que puede convertirse en Atlas canónico.

```text
H06 Atlas
   ↓
conocimiento canónico
   ↓
H10 pipeline diario 🟢
   ├── hardware
   ├── recomendador
   └── publicación
```

## Qué NO queda cerrado por H06

H06 no significa que todos los modelos estén verificados, benchmarkeados o medidos físicamente. Tampoco cierra:

- JGB sistemático completo;
- CABE/RULA completo;
- matriz hardware completa;
- benchmarks físicos;
- optimización multiobjetivo.

## Siguiente fase

**H07 — JGB sistemático.**

H07 podrá consumir la identidad y procedencia normalizadas por H06 sin mezclar apertura con rendimiento, precio o viabilidad.
