# H06.1 — Auditoría inicial del Open LLM Atlas

**Fecha:** 16/08/2026  
**Estado:** 🟡 auditoría inicial completada; correcciones pendientes.

## 1. Resultado ejecutivo

La auditoría documental confirma que LEONES ya tiene una **base de contrato sólida** para H06:

- `atlas/schema.json` define un registro estructurado y exige `id`, `kind`, `name` y `evidence`.
- El catálogo de tipos distingue modelo, familia, organización, runtime, backend, cuantización, herramienta, benchmark, hardware, conocimiento y experimento.
- Existe separación explícita entre apertura/JGB, recomendación, sistema del modelo, hardware, evidencia externa, experimentos, evaluación y flags de calidad.
- `atlas/INGEST.md` establece procedencia, estados de evidencia, compatibilidad de ejecución, requisitos de medición y reglas de privacidad.
- `atlas/README.md` establece la relación del Atlas con H10, Router, MANADA, CABE y RULA.

Por tanto, **el problema principal de H06 no es la ausencia de arquitectura**, sino demostrar y automatizar la cobertura y calidad del conocimiento que entra en esa arquitectura.

## 2. Contrato estructural observado

El esquema actual obliga a que cada registro tenga:

```text
id
kind
name
evidence
```

`kind` está restringido a diez categorías funcionales principales: model, family, organization, runtime, backend, quantization, tool, benchmark, hardware, knowledge y experiment. fileciteturn116file0L2-L2

El esquema dispone además de estructuras para:

- arquitectura y artefactos;
- ejecución;
- recomendación;
- parámetros y memoria del sistema de modelo;
- hardware;
- evidencia externa;
- experimentos y evaluación;
- quality flags;
- evidencia y ciclo de vida.

Esto es suficiente para iniciar la auditoría de datos sin cambiar todavía el contrato principal.

## 3. Evidencia

El contrato reconoce cuatro estados:

```text
reported
   ↓
reproducible
   ↓
verified

rejected = fuera de agregados oficiales
```

También distingue `external`, `manada`, `leones_measurement`, `documentary` y `unknown` como tipos de evidencia. fileciteturn116file0L2-L2

La documentación de ingesta confirma que las fuentes externas sirven para descubrimiento/contraste y no convierten automáticamente un dato en medición LEONES ni en `verified`. fileciteturn119file0L2-L2

## 4. Calidad

El esquema ya prevé estos flags:

- `missing`
- `unverified`
- `stale`
- `contradictory`
- `duplicate`
- `invalid_value`
- `unsupported_claim`
- `source_missing`
- `identity_collision`
- `inconsistent_units`

Esto permite que H06.4 construya una auditoría automática sin tener que inventar un nuevo sistema de incidencias. fileciteturn116file0L2-L2

## 5. Riesgos identificados

### R1 — Cobertura cuantitativa

El contrato está definido, pero esta auditoría documental no demuestra por sí sola cuántos registros reales existen ni qué porcentaje de campos está cubierto.

**Acción:** localizar y auditar los datasets/feed reales utilizados por los workflows Atlas.

### R2 — Identidad

El esquema separa `family`, `organization`, `name` y `version`, pero la auditoría documental no demuestra todavía que no existan colisiones entre nombres, variantes, cuantizaciones o artefactos.

**Acción:** H06.2 debe generar claves canónicas y detección de duplicados/colisiones.

### R3 — Procedencia

El contrato permite `external_evidence` con `source_type`, `url`, `retrieved_at`, `claim` y `source_record_id`, además del bloque general `evidence`. fileciteturn116file0L2-L2

**Acción:** medir cuántos registros relevantes tienen realmente procedencia suficiente.

### R4 — Datos externos frente a mediciones

La separación conceptual está documentada correctamente, pero debe comprobarse automáticamente en los feeds y recomendaciones para evitar promociones indebidas.

**Acción:** auditoría de consistencia H06.4/H06.5.

### R5 — Recomendación

El esquema permite `jgb`, `cabe`, `rula`, `fit_score`, `performance_score`, `economic_score` y `uncertainty` por separado. Esto es correcto y debe mantenerse.

**Acción:** impedir que un score agregado sustituya a JGB, CABE, RULA o evidencia.

## 6. Qué NO se cambia ahora

No se cambia todavía:

- el contrato de JGB;
- la clasificación de apertura;
- CABE/RULA;
- el modelo de hardware;
- el ranking económico;
- el pipeline H10 ya aceptado.

H06 debe mejorar primero la capa de conocimiento y su calidad.

## 7. Próxima auditoría técnica

La siguiente tarea debe ejecutarse sobre los archivos de datos reales:

```text
1. localizar feeds Atlas
2. contar registros por kind
3. detectar IDs repetidos
4. detectar nombres/identidades potencialmente duplicados
5. medir campos vacíos
6. medir procedencia
7. medir estados de evidencia
8. medir quality_flags
9. detectar valores inválidos
10. generar H06.1 coverage report
```

## 8. Conclusión

**H06.1 no está cerrada como fase completa.** La auditoría documental sí queda cerrada como primera revisión del contrato: el esquema actual es suficientemente expresivo para continuar sin rediseño mayor.

La prioridad pasa ahora de **diseño** a **medición del inventario real**.

> **No añadimos datos hasta saber exactamente qué tenemos, qué falta y qué calidad tiene lo que ya tenemos.**
