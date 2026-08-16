# LEONES — Contrato común de datos y estados

## Estado

**🟢 Contrato funcional cerrado · implementación pendiente**

Este documento define el vocabulario mínimo común entre ADIVINO, OSI, EVIDENCIA, QUALITY GATE, ROUTER, MANADA, OBSERVABILIDAD, ALERTAS, CI/CD y ATLAS.

## Regla

Los componentes pueden evolucionar internamente, pero las interfaces canónicas solo cambian mediante versionado explícito.

## Entidades principales

```text
Candidate       descubrimiento pendiente
Entity          entidad identificada
Evidence        evidencia asociada
Evaluation      evaluación / Quality Gate
Recommendation  decisión del Router
Run             ejecución
Alert           evento notificable
Promotion       cambio hacia conocimiento canónico
```

## Identificadores

Cuando corresponda:

- `candidate_id`
- `entity_id`
- `evidence_id`
- `evaluation_id`
- `recommendation_id`
- `trace_id`
- `run_id`
- `span_id`
- `alert_id`
- `promotion_id`

Los identificadores son estables y no se reutilizan para otra entidad.

## Estado de candidato

```text
DISCOVERED
IDENTITY_PENDING
OSI_PENDING
EVIDENCE_PENDING
QUALITY_PENDING
REVIEW
ACCEPTED
REJECTED
SUPERSEDED
```

No todos los candidatos recorren todos los estados; el flujo aplicable depende del tipo de entidad y de las políticas obligatorias.

## Estado de evidencia

```text
DISCOVERED
COLLECTED
VERIFIED
DISPUTED
SUPERSEDED
REJECTED
```

`VERIFIED` describe la evidencia respecto al criterio aplicado; no convierte automáticamente la afirmación respaldada en una verdad universal.

## Estado de evaluación

```text
PENDING
PASS
REVIEW
FAIL
DISPUTED
SUPERSEDED
```

`PASS` no es un score. Significa que se cumplen los requisitos definidos para esa evaluación.

## Estado de ejecución

```text
QUEUED
RUNNING
SUCCESS
PARTIAL
RETRYING
FAILED
BLOCKED
CANCELLED
```

`PARTIAL` nunca equivale a éxito completo para una promoción canónica.

## Estado de alerta

```text
NEW
SENT
ACKNOWLEDGED
SNOOZED
RESOLVED
```

Un error de envío no resuelve una alerta.

## Promoción

```text
PROPOSED
ELIGIBLE
PROMOTING
PROMOTED
BLOCKED
REJECTED
```

Solo `PROMOTED` significa que el cambio canónico se completó.

## Reglas de transición

Una transición debe registrar:

- estado anterior;
- estado nuevo;
- timestamp;
- actor/workflow;
- motivo;
- referencias de evidencia;
- `trace_id`/`run_id` cuando proceda.

No se permiten saltos silenciosos ni mutaciones históricas.

## Contrato de evidencia

Todo dato relevante que llegue a Atlas debe poder relacionarse con una o más evidencias, salvo campos explícitamente definidos como metadatos derivados.

La ausencia de evidencia no se representa como evidencia positiva.

## Contrato Router

El Router recibe restricciones y preferencias y devuelve una recomendación trazable. No puede alterar:

- estado OSI;
- evidencia;
- Quality Gate;
- conocimiento canónico de Atlas.

## Contrato MANADA

MANADA recibe una composición autorizada y produce resultados de ejecución. Los resultados intermedios son no canónicos hasta superar el proceso de evidencia/evaluación que corresponda.

## Contrato Observabilidad

Cada operación relevante debe poder relacionarse con `trace_id` y/o `run_id`. La observabilidad describe la ejecución; no decide la validez del conocimiento.

## Contrato Alertas

Una alerta referencia un evento origen y, cuando exista, la evidencia/evaluación correspondiente. La notificación nunca modifica por sí sola el estado canónico.

## Contrato CI/CD

Los workflows consumen y producen estados del contrato. Deben ser idempotentes y no pueden promover directamente datos que no hayan superado los controles obligatorios.

## Contrato Atlas

Atlas es el destino del conocimiento canónico aceptado. No debe utilizarse como cola de candidatos ni como almacén de datos pendientes de verificación.

## Versionado

El contrato se identifica mediante una versión semántica conceptual:

```text
MAJOR.MINOR
```

- `MAJOR`: cambio incompatible;
- `MINOR`: extensión compatible.

Los registros deben conservar la versión del contrato con la que fueron producidos cuando sea necesario para reconstrucción histórica.

## Errores

Los errores de interfaz deben ser estructurados y no ambiguos. Como mínimo:

- `INVALID_STATE_TRANSITION`
- `MISSING_REQUIRED_EVIDENCE`
- `POLICY_BLOCKED`
- `IDENTITY_CONFLICT`
- `DUPLICATE_ENTITY`
- `STALE_DATA`
- `CONCURRENCY_BLOCKED`
- `AUTHENTICATION_ERROR`
- `EXTERNAL_SOURCE_UNAVAILABLE`
- `VALIDATION_FAILED`

## No concurrencia

La ejecución interna puede ser concurrente. Las modificaciones de conocimiento canónico se serializan mediante `leones-main-writers`.

```text
procesos paralelos
       ↓
resultados aislados
       ↓
writer canónico único
       ↓
Atlas
```

## Regla de oro

```text
DESCUBRIR ≠ ACEPTAR
EVIDENCIA ≠ VERDAD ABSOLUTA
TRACE ≠ EVIDENCIA
ESTIMADO ≠ MEDIDO
PASS ≠ SCORE
NOTIFICAR ≠ PROMOVER
```

Estas distinciones forman parte del contrato y no deben perderse en las implementaciones.

## Cierre

Este contrato es la interfaz semántica común de LEONES. Antes de implementar integraciones definitivas, cada componente deberá mapear explícitamente sus entradas, salidas y transiciones a estos estados y entidades.
