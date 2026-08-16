# LEONES — Observabilidad y trazabilidad

## Estado

**🟢 Arquitectura funcional cerrada · implementación pendiente**

La observabilidad es la capa común que permite reconstruir qué ocurrió en Router, Agentic y MANADA. No altera Atlas ni decide recomendaciones.

## Principio

```text
EVENTO → TRACE → RUN → RESULTADO
              ↓
        EVIDENCIA / AUDITORÍA
```

Cada ejecución relevante debe poder responder: qué se pidió, qué se decidió, qué se ejecutó, qué herramientas se usaron, qué ocurrió y por qué terminó.

## Identificadores

Toda ejecución debe disponer de:

- `trace_id`: recorrido completo de una petición;
- `run_id`: ejecución concreta;
- `span_id`: unidad de trabajo dentro de una ejecución;
- `parent_span_id`: relación con la operación que la originó;
- `timestamp_start` / `timestamp_end`;
- `component`: Router, Agentic, MANADA, herramienta, etc.;
- `model_id` / `agentic_id` cuando corresponda;
- `status` y `termination_reason`.

## Eventos mínimos

- petición recibida;
- perfil efectivo del Router;
- candidatos considerados;
- candidatos excluidos y motivo;
- selección/composición;
- inicio y fin de agente;
- llamada a herramienta;
- resultado de herramienta;
- error;
- retry/recovery;
- cambio de participante;
- síntesis;
- resultado final;
- persistencia canónica.

## Evidencia

La trazabilidad distingue explícitamente:

```text
LOG / TRACE
    ≠
EVIDENCIA DE RESULTADO
    ≠
MEDICIÓN FÍSICA
    ≠
FUENTE EXTERNA
```

Un trace demuestra que una acción ocurrió; no demuestra por sí solo que la respuesta sea correcta.

## Métricas

Cuando existan datos fiables, se registran:

- latencia total;
- latencia por etapa;
- tokens de entrada/salida;
- tokens/s;
- llamadas a herramientas;
- errores;
- retries;
- tiempo de recuperación;
- coste;
- uso de CPU/RAM/GPU/VRAM cuando esté disponible;
- éxito de tarea;
- resultado de verificación.

CABE y RULA se derivan de mediciones de throughput, no de preferencias del usuario:

- **CABE:** 1–<10 tok/s;
- **RULA:** 10–100 tok/s.

## Privacidad

No se registra contenido sensible innecesario. Los eventos deben admitir redacción/anonimización y separación entre metadatos de ejecución y contenido de usuario.

Las credenciales, tokens, secretos y claves nunca forman parte de los eventos canónicos.

## Niveles

```text
INFO       ciclo normal
WARN       degradación recuperable
ERROR      fallo de operación
SECURITY   evento de seguridad
AUDIT      cambio relevante / decisión trazable
```

## Integración

```text
                  OBSERVABILIDAD
                 /       |       \
             ROUTER   AGENTIC   MANADA
                 \       |       /
                  herramientas
                       ↓
                  TRACE/RUN
                       ↓
                evidencia/auditoría
```

La observabilidad es transversal y no debe duplicarse dentro de cada componente.

## No concurrencia

La observabilidad puede recibir eventos concurrentes durante una ejecución, pero la escritura de artefactos canónicos debe pasar por el único grupo `leones-main-writers`, con `cancel-in-progress: false`.

La concurrencia de ejecución no crea escritores canónicos adicionales.

## Fallos

Un fallo de observabilidad no debe convertir automáticamente una ejecución en éxito ni falsear sus métricas. Si faltan eventos necesarios, el resultado debe marcarse con la correspondiente pérdida de observabilidad.

## Retención y versionado

El esquema de eventos debe versionarse. Los cambios incompatibles requieren nueva versión. Los registros históricos no se reescriben para adaptarlos a esquemas posteriores.

## Integridad

Las decisiones y resultados que alimenten Atlas deben poder relacionarse con su `trace_id`/`run_id` y con la evidencia que los sustenta.

## Criterio de cierre

La arquitectura queda cerrada. La implementación deberá priorizar trazabilidad reproducible, separación entre logs y evidencia, privacidad y compatibilidad futura con una interfaz WebApp.
