# H06 — Open LLM Atlas ampliado

**Estado: 🟡 IMPLEMENTACIÓN COMPLETA / ACEPTACIÓN CI PENDIENTE.**

## Objetivo

Ampliar y depurar el Open LLM Atlas como capa estructurada de conocimiento de LEONES, aumentando cobertura, procedencia, calidad y trazabilidad de modelos, familias, organizaciones, variantes, runtimes, benchmarks y evidencia.

H06 se apoya en la infraestructura diaria H10, que ya está aceptada, pero su aceptación es independiente.

## Principio rector

```text
DESCUBRIR
   ↓
IDENTIFICAR
   ↓
NORMALIZAR
   ↓
RELACIONAR
   ↓
DOCUMENTAR PROCEDENCIA
   ↓
CLASIFICAR EVIDENCIA
   ↓
VALIDAR
   ↓
PUBLICAR
```

## Resultado de la fase

H06 ya dispone de la capa que faltaba entre el feed operativo y el Atlas canónico:

```text
atlas_feed.csv
      ↓
atlas_identity_audit.py
      ↓
atlas_quality_audit.py
      ↓
atlas_promote_verified.py
      ↓
atlas/catalog.json
```

La promoción es **verified-only**, no destructiva y no inventa valores. El workflow `.github/workflows/atlas-h06.yml` automatiza pruebas, auditorías, promoción y validación contra JSON Schema.

## Documentación

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — arquitectura canónica.
- [`COVERAGE-AUDIT.md`](COVERAGE-AUDIT.md) — auditoría de cobertura.
- [`IDENTITY-RULES.md`](IDENTITY-RULES.md) — identidad y deduplicación.
- [`EVIDENCE-RULES.md`](EVIDENCE-RULES.md) — reglas de evidencia.
- [`DECISIONS.md`](DECISIONS.md) — decisiones de arquitectura.
- [`VALIDATION.md`](VALIDATION.md) — validación automatizada.
- [`H06_FINAL.md`](H06_FINAL.md) — informe de cierre técnico.

## Alcance

1. Modelos y variantes.
2. Familias y organizaciones.
3. Repositorios y procedencia.
4. Arquitectura, parámetros, contexto, pesos y formatos cuando exista evidencia.
5. Runtimes, backends y formatos de ejecución.
6. Benchmarks y resultados con fuente y fecha.
7. Estados de evidencia.
8. Integración con JGB sin sustituir la clasificación de apertura por un score de rendimiento.
9. Contratos de datos para alimentar hardware y recomendación.

## Fuera de alcance de H06

- Declarar que un modelo está benchmarkeado si solo existe información externa.
- Convertir automáticamente datos externos en `verified`.
- Sustituir la clasificación de apertura por una puntuación económica o de rendimiento.
- Cerrar CABE/RULA empíricamente: eso pertenece a H09 y a benchmarks posteriores.

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

## Criterio de aceptación

La fase queda preparada para aceptación cuando el workflow H06 termina en verde y deja publicados los outputs definidos en [`VALIDATION.md`](VALIDATION.md). Si no existen filas verificadas, el catálogo puede permanecer vacío: eso es un resultado válido y preferible a introducir datos ficticios.

## Próximo paso después de H06

Una vez aceptado H06, la siguiente fase es **H07 — JGB sistemático**, consumiendo la identidad y procedencia ya normalizadas sin mezclar apertura con rendimiento, precio o viabilidad.
