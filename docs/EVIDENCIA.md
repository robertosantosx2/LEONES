# LEONES — Sistema de Evidencia

## Estado

**🟢 Arquitectura funcional cerrada · implementación pendiente**

EVIDENCIA es la capa que conecta afirmaciones, fuentes, mediciones y decisiones. No sustituye al Atlas, al Router ni a la observabilidad.

## Principio

```text
AFIRMACIÓN
    ↓
EVIDENCE RECORD
    ↓
FUENTE / MEDICIÓN / PRUEBA
    ↓
VERIFICACIÓN
    ↓
CONFIANZA
    ↓
ATLAS / ROUTER
```

Una afirmación no se considera verdadera por aparecer en una fuente: debe conservarse qué fuente la respalda, qué se comprobó y cuándo.

## Tipos de evidencia

- `primary_source` — documentación o fuente primaria del proyecto/fabricante;
- `repository` — código y artefactos del repositorio;
- `license` — texto y metadatos de licencia;
- `benchmark` — benchmark reproducible;
- `physical_measurement` — medición real de hardware/modelo;
- `experiment` — experimento reproducible de LEONES;
- `external_report` — informe externo identificable;
- `community_report` — experiencia comunitaria, siempre diferenciada de medición propia;
- `trace` — registro de ejecución;
- `user_report` — aportación de usuario pendiente de validación.

## Registro mínimo

Cada evidencia debe conservar, cuando aplique:

- `evidence_id`;
- afirmación respaldada;
- tipo;
- fuente/origen;
- URL o identificador de origen;
- fecha de publicación si existe;
- fecha de consulta/medición;
- versión del modelo/software;
- hardware y configuración para mediciones;
- procedimiento;
- resultado bruto o referencia al artefacto;
- estado de verificación;
- nivel de confianza;
- observaciones;
- `trace_id`/`run_id` cuando proceda.

## Estados

```text
DISCOVERED
→ COLLECTED
→ NORMALIZED
→ VERIFIED
→ DISPUTED
→ SUPERSEDED
→ REJECTED
```

`UNVERIFIED`/`DISPUTED` no debe presentarse como hecho verificado.

## Verificación

La fuerza de una evidencia depende del tipo de afirmación.

Ejemplos:

- licencia → fuente legal/primaria y texto de licencia;
- contexto máximo → documentación/model card y comprobación del artefacto;
- tok/s → medición reproducible con hardware/configuración;
- benchmark → resultado asociado a versión, configuración y metodología;
- compatibilidad Agentic → evidencia de integración/versiones;
- recomendación → conjunto de evidencias que sustentan la decisión.

## Evidencia física por modelo

LEONES distingue explícitamente entre:

```text
EVIDENCIA GENERAL DE HARDWARE
        ≠
EVIDENCIA FÍSICA DEL MODELO CONCRETO
```

Una estimación basada en tamaño, arquitectura o hardware no se transforma en medición real. Si falta evidencia física por modelo, el dato debe permanecer identificado como estimado/no verificado.

## Jerarquía práctica

Como regla de calidad, LEONES prioriza:

1. medición reproducible propia;
2. fuente primaria reproducible;
3. benchmark externo con metodología y versión claras;
4. informe técnico identificable;
5. evidencia comunitaria trazable;
6. afirmación secundaria sin verificación.

Esta jerarquía orienta la confianza y no permite convertir automáticamente una fuente débil en dato fuerte.

## Contradicciones

Si dos fuentes discrepan:

- no se sobrescribe silenciosamente la evidencia anterior;
- se conservan ambas;
- se registra la discrepancia;
- se prioriza la evidencia más específica, reciente y reproducible;
- si no puede resolverse, el dato permanece disputado/indeterminado.

## Frescura

Las evidencias sensibles al tiempo deben registrar fecha de comprobación y, cuando proceda, fecha de caducidad/revisión. Una copia nueva de un documento antiguo no convierte su contenido en información nueva.

## Relación con Atlas

```text
EVIDENCIA
   ↓
VERIFICACIÓN
   ↓
ATLAS
```

Atlas almacena conocimiento aceptado y trazable; no debe rellenar huecos inventando datos.

## Relación con Router

El Router puede usar evidencia verificada y estados de incertidumbre para decidir. Nunca debe ocultar una limitación relevante de evidencia para producir una recomendación aparentemente precisa.

## Relación con Observabilidad

```text
OBSERVABILIDAD → demuestra qué ocurrió
EVIDENCIA       → sustenta qué puede afirmarse
```

Un trace de una ejecución no demuestra por sí solo la calidad o veracidad de su resultado.

## Relación con Agentic y MANADA

Las salidas de agentes y MANADA se consideran resultados generados hasta que exista evidencia que las verifique. El consenso entre agentes tampoco equivale automáticamente a evidencia.

## Aportaciones de usuarios

Las recomendaciones o mediciones aportadas por usuarios entran como `user_report` y siguen un circuito de validación antes de alimentar Atlas.

## No concurrencia

La recopilación puede producir eventos concurrentes, pero la modificación de registros canónicos y su promoción a Atlas utiliza exclusivamente `leones-main-writers` con `cancel-in-progress: false`.

## Auditoría

Cada dato que llegue a Atlas o afecte materialmente una recomendación debe poder remontarse a sus evidencias y, cuando exista ejecución, a su `trace_id`/`run_id`.

## Criterio de cierre

La arquitectura de EVIDENCIA queda cerrada. La implementación posterior debe priorizar trazabilidad, reproducibilidad, frescura y separación estricta entre dato medido, dato documentado, estimación y afirmación no verificada.
