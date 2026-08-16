# H06.1 — Auditoría inicial del Open LLM Atlas

**Fecha:** 16/08/2026  
**Estado:** 🟡 auditoría inicial completada; inventario oficial todavía vacío.

## 1. Resultado ejecutivo

La revisión directa del repositorio confirma un hecho importante: **el catálogo oficial del Atlas todavía no contiene registros**.

`atlas/catalog.json` declara `atlas_version: 0.2` y `records: []`. fileciteturn126file0L2-L2

`atlas/seed.json` también está deliberadamente vacío y explica que no se incorporan modelos sin evidencia. fileciteturn127file0L2-L2

Por tanto, H06.1 no debe tratarse como una auditoría de "calidad de 209 modelos dentro del Atlas oficial". Los **209 modelos observados en H10 pertenecen al pipeline de recomendación/ingesta de esa ejecución**, y no deben presentarse como 209 registros ya aceptados dentro de `atlas/catalog.json`.

Esta distinción es crítica para mantener la trazabilidad.

## 2. Base estructural

El Atlas sí dispone de una base de contrato sólida:

- `atlas/schema.json` define registros estructurados.
- La ingesta exige `id`, `kind`, `name` y estado de evidencia.
- Existen categorías para modelo, familia, organización, runtime, backend, cuantización, herramienta, benchmark, hardware, conocimiento y experimento.
- El contrato contempla evidencia externa, experimentos, evaluación y flags de calidad.
- `atlas/INGEST.md` establece procedencia, privacidad y compatibilidad de ejecución.

El sistema está preparado para recibir conocimiento, pero **todavía no tiene conocimiento oficial cargado**.

## 3. Inventario comprobado

| Elemento | Estado actual | Conclusión H06.1 |
|---|---|---|
| `atlas/catalog.json` | `records: []` | 🟡 Vacío |
| `atlas/seed.json` | `records: []` | 🟡 Vacío deliberadamente |
| `atlas/schema.json` | Existe | 🟢 Contrato disponible |
| `atlas/INGEST.md` | Existe | 🟢 Reglas disponibles |
| Fuentes empíricas | Catalogadas | 🟢 Base de investigación |
| Pipeline H10 | Operativo/aceptado | 🟢 Genera conocimiento intermedio |
| Atlas oficial poblado | No | 🔴 Pendiente H06 |

## 4. Consecuencia arquitectónica

No vamos a copiar automáticamente el output de H10 dentro del Atlas oficial.

El flujo correcto debe ser:

```text
PROSPECCIÓN / H10
       ↓
DATOS INTERMEDIOS
       ↓
IDENTIDAD
       ↓
NORMALIZACIÓN
       ↓
EVIDENCIA
       ↓
QUALITY GATE
       ↓
REVISIÓN / ACEPTACIÓN
       ↓
ATLAS OFICIAL
```

Esto evita que "aparece en el pipeline" se convierta accidentalmente en "conocimiento aceptado".

## 5. Auditoría de identidad

No existen todavía registros oficiales suficientes para ejecutar una deduplicación sobre el catálogo: con `records: []`, el número de duplicados oficiales es **0 por ausencia de registros**, no porque se haya demostrado que 209 modelos sean únicos.

**Resultado:** H06.2 debe diseñar y ejecutar la deduplicación sobre el feed intermedio real antes de su promoción al Atlas.

## 6. Auditoría de procedencia

El contrato y la documentación de ingesta exigen procedencia y estados de evidencia. Las fuentes externas sirven para descubrimiento y contraste y no convierten automáticamente una afirmación en medición LEONES ni en `verified`. fileciteturn119file0L2-L2

**Resultado:** 🟢 regla definida; 🟡 cobertura de procedencia del feed intermedio pendiente de medir.

## 7. Auditoría de calidad

El esquema contempla flags para `missing`, `unverified`, `stale`, `contradictory`, `duplicate`, `invalid_value`, `unsupported_claim`, `source_missing`, `identity_collision` e `inconsistent_units`.

**Resultado:** 🟢 contrato preparado; 🟡 auditoría automática pendiente.

## 8. Riesgos principales

### R1 — Confundir pipeline con Atlas oficial

Es el riesgo más importante detectado.

**Solución:** mantener explícita la frontera entre feed/intermedio y catálogo oficial.

### R2 — Promocionar datos sin evidencia suficiente

**Solución:** quality gate obligatorio antes de escribir en `catalog.json`.

### R3 — Duplicar modelos por variantes, cuantizaciones o artefactos

**Solución:** identidad canónica antes de promoción.

### R4 — Confundir puntuaciones con dimensiones independientes

La apertura/JGB debe permanecer separada de rendimiento, precio, hardware, CABE y RULA.

### R5 — Incorporar datos de hardware sin semántica suficiente

El Atlas exige distinguir compute/FLOPS, memoria, almacenamiento, bandwidth e interconnect cuando estén disponibles.

## 9. Próxima tarea: H06.2

La siguiente unidad debe ser **identidad y deduplicación del feed intermedio real**, no rellenar manualmente `catalog.json`.

Debe producir como mínimo:

```text
canonical_id
organization
family
model
variant
artifact
quantization
runtime
source
source_record_id
identity_confidence
identity_collision
```

Y debe separar:

```text
modelo ≠ variante ≠ checkpoint ≠ cuantización ≠ runtime
```

## 10. Criterio de cierre H06.1

H06.1 queda **cerrada como auditoría inicial documental y de inventario del catálogo oficial**, pero no como cierre de H06.

### Resultado

**Atlas oficial: 0 registros aceptados.**

Esto no es un fallo: es el comportamiento deliberado del diseño actual, que evita incorporar conocimiento sin evidencia. fileciteturn126file0L2-L2

> El siguiente objetivo no es "llenar el Atlas". Es construir un proceso seguro que permita llenarlo sin perder identidad, procedencia ni calidad.
