# LEONES — Contrato Atlas ↔ Router ↔ Evidence

## Estado

**🟢 Contrato funcional cerrado · implementación pendiente**

Este documento fija la frontera entre conocimiento canónico (Atlas), evidencia y decisión de recomendación (Router).

## Principio

```text
EVIDENCE
   ↓
QUALITY GATE
   ↓
ATLAS  ← conocimiento canónico
   ↓
ROUTER ← decisión / recomendación
   ↓
RESULTADO EXPLICABLE
```

Router consume Atlas y evidencia asociada; no convierte sus preferencias ni sus cálculos en modificaciones del conocimiento canónico.

## Responsabilidades

### Atlas
Es el **destino canónico del conocimiento aceptado**. Conserva entidades, relaciones, atributos, estados aceptados y referencias a evidencia.

Atlas no debe ser cola de descubrimiento ni almacén de afirmaciones pendientes.

### Evidence
Es la **base de trazabilidad de las afirmaciones**. Conserva procedencia, fecha, método, artefactos, mediciones y estado de verificación.

Evidence puede existir antes de que un dato sea aceptado en Atlas.

### Router
Es el **motor de decisión**. Recibe una petición, restricciones duras y preferencias permitidas; consulta conocimiento y evidencia; produce una recomendación explicable.

Router no escribe directamente en Atlas.

## Lectura canónica

Una lectura de Atlas para Router debe poder identificar:

- `entity_id`;
- versión/estado relevante;
- atributos utilizados;
- fecha/frescura;
- estado de evidencia;
- `evidence_id` asociados;
- restricciones aplicables;
- relaciones relevantes.

## Regla de evidencia

Un atributo usado materialmente para recomendar debe poder clasificarse como:

```text
VERIFIED
ESTIMATED
UNVERIFIED
DISPUTED
STALE
```

El Router debe respetar la política correspondiente a cada estado. No puede convertir `ESTIMATED` en `VERIFIED` por cálculo interno.

## Modelo de dato lógico

```text
Entity
 ├── attributes
 ├── versions
 ├── relationships
 └── evidence_refs[]

Evidence
 ├── type
 ├── source
 ├── observed_at
 ├── collected_at
 ├── verification_state
 ├── methodology
 └── artifact_ref

Recommendation
 ├── recommendation_id
 ├── request
 ├── selected_entities[]
 ├── constraints_applied[]
 ├── preferences_applied[]
 ├── evidence_refs[]
 ├── uncertainty[]
 └── explanation
```

## Contrato de lectura Router

Router puede:

- consultar entidades;
- consultar relaciones;
- consultar estados de evidencia;
- comparar candidatos;
- calcular criterios derivados;
- producir recomendaciones.

Router no puede:

- cambiar licencia/OSI;
- validar físicamente un modelo por inferencia;
- convertir una estimación en medición;
- modificar evidencia histórica;
- promover una entidad a Atlas.

## Contrato de escritura Atlas

Toda modificación canónica debe entrar por un proceso de promoción que incluya, según corresponda:

```text
IDENTIDAD
 → OSI
 → EVIDENCIA
 → QUALITY GATE
 → PROMOTION
 → ATLAS
```

La escritura se serializa mediante `leones-main-writers`.

## Versionado y frescura

Atlas debe conservar versión y fecha relevantes. Cuando un atributo dependa de información volátil, Router debe conocer su frescura antes de utilizarlo.

No se considera nueva evidencia una mera copia nueva de una fuente antigua.

## Contradicciones

Si Evidence contiene fuentes contradictorias, Atlas no debe ocultar la discrepancia. Puede almacenar un estado `DISPUTED` o la resolución documentada.

Router debe tratar una contradicción relevante como incertidumbre, exclusión o condición de revisión según la política aplicable.

## Recomendación

Toda recomendación material debe poder explicar:

1. qué candidatos fueron considerados;
2. cuáles quedaron excluidos y por qué;
3. qué restricciones se aplicaron;
4. qué preferencias se aplicaron;
5. qué evidencia sustentó la decisión;
6. qué incertidumbres permanecen;
7. por qué ganó la opción elegida.

## No confundir score con apertura

La clasificación de apertura/OSI permanece como atributo/política independiente. Un score de rendimiento, coste o utilidad no puede sustituirla.

## Relación con Router Dashboard

La interfaz del usuario puede cambiar preferencias permitidas y valores operativos, pero no puede editar OSI ni evidencia. El dashboard consume este contrato; no define nuevas reglas de conocimiento.

## Relación con cuantización y fine-tuning

Las variantes producidas por cuantización y fine-tuning mantienen linaje hacia el modelo base y referencias a su propia evidencia.

```text
BASE MODEL
   ├── quantized_variant → Evidence → Atlas
   └── finetuned_variant → Evidence → Atlas
```

Una variante no hereda automáticamente todas las afirmaciones físicas del modelo base. Las propiedades específicas de la variante requieren evidencia propia cuando corresponda.

## Observabilidad

Las decisiones del Router deben conservar `trace_id`/`run_id`. La trazabilidad permite reconstruir qué versión de Atlas y qué evidencia se consultaron.

## Errores de contrato

Como mínimo:

- `ENTITY_NOT_FOUND`
- `STALE_EVIDENCE`
- `EVIDENCE_MISSING`
- `EVIDENCE_DISPUTED`
- `POLICY_BLOCKED`
- `OSI_REQUIRED`
- `QUALITY_NOT_PASSED`
- `ATLAS_WRITE_FORBIDDEN`
- `INVALID_VARIANT_LINEAGE`

## Cierre

Atlas es el conocimiento canónico; Evidence sustenta y contextualiza las afirmaciones; Router decide. Ninguna capa puede usurpar la responsabilidad de otra.

El contrato queda listo para implementar adaptadores y APIs sin entrar todavía en código de ejecución.
