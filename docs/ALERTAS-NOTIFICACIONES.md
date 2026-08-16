# LEONES — Alertas y notificaciones

## Estado

**🟢 Arquitectura funcional cerrada · implementación pendiente**

Esta capa convierte eventos relevantes de ADIVINO, actualización, evidencia y ejecución en avisos accionables. No modifica Atlas por sí misma.

## Flujo

```text
EVENTO
  ↓
CLASIFICACIÓN
  ↓
REGLAS DE ALERTA
  ↓
DEDUPLICACIÓN / AGRUPACIÓN
  ↓
NOTIFICACIÓN
  ↓
ACCIÓN HUMANA O AUTOMÁTICA
```

## Tipos de alerta

- `NEW_DISCOVERY` — nuevo candidato relevante;
- `SOURCE_CHANGE` — cambio en una fuente conocida;
- `MODEL_UPDATE` — nueva versión relevante;
- `LICENSE_CHANGE` — cambio de licencia/apertura;
- `BENCHMARK_UPDATE` — nueva evidencia de benchmark;
- `PHYSICAL_EVIDENCE` — nueva medición física;
- `REGRESSION` — posible regresión;
- `CONTRADICTION` — evidencias incompatibles;
- `SOURCE_LOST` — fuente o artefacto ya no disponible;
- `REVIEW_REQUIRED` — necesita decisión humana;
- `PIPELINE_ERROR` — fallo del proceso;
- `SECURITY_EVENT` — evento de seguridad.

## Severidad

```text
INFO
NOTICE
WARNING
CRITICAL
```

La severidad representa impacto operativo o de conocimiento, no calidad del modelo.

## Reglas

Una alerta debe incluir:

- `alert_id`;
- tipo;
- severidad;
- fecha/hora;
- origen;
- entidad afectada;
- explicación;
- evidencia relacionada;
- `trace_id`/`run_id` cuando exista;
- acción recomendada;
- estado de resolución.

## Deduplificación

El mismo evento no debe producir una tormenta de correos. Las alertas equivalentes se agrupan por entidad, tipo y ventana temporal definida.

Una nueva evidencia material o un cambio de estado sí puede reabrir una alerta agrupada.

## Canales

La arquitectura permite varios canales sin acoplarlos al descubridor:

- email;
- WebApp / centro de notificaciones;
- webhook;
- otros canales futuros.

El canal no cambia el contenido ni el estado canónico de la alerta.

## Validación humana

Para descubrimientos que requieran validación, la alerta puede ofrecer una acción explícita:

**OK LEONES** → registrar confirmación y continuar el flujo configurado.

La confirmación humana no sustituye OSI, evidencia ni Quality Gate. Solo expresa la decisión humana solicitada por ese circuito.

## Email

El mensaje debe ser breve y accionable:

```text
LEONES — Nuevo descubrimiento

Qué: [candidato]
Por qué: [relevancia]
Fuente: [origen]
Estado: [pendiente]

Acción: responder "OK LEONES" para validar
```

No se incluyen secretos, tokens ni datos sensibles innecesarios.

## Estado de alerta

```text
NEW → SENT → ACKNOWLEDGED → RESOLVED
                 ↓
               SNOOZED
```

Un fallo de envío no equivale a una alerta resuelta. Se registra el error y se conserva el evento.

## Preferencias del usuario

El usuario puede configurar canal, frecuencia de agrupación y tipos de aviso que desea recibir cuando la política de LEONES lo permita. No puede desactivar avisos críticos de integridad, seguridad o fallos que comprometan la fiabilidad del sistema.

## No concurrencia

Los detectores y canales pueden procesar eventos concurrentemente. La creación/modificación de estados canónicos de alertas utiliza exclusivamente `leones-main-writers` con `cancel-in-progress: false`.

Enviar un email no crea un writer adicional sobre Atlas.

## Observabilidad

Cada alerta debe ser trazable hasta el evento origen y, cuando corresponda, hasta `trace_id`/`run_id`. Los envíos, errores y confirmaciones también quedan registrados.

## Integración

```text
ADIVINO / ACTUALIZACIÓN / EVIDENCIA / PIPELINES
                         ↓
                      EVENTOS
                         ↓
                   ALERTAS
                    ↙     ↘
                 EMAIL   WEBAPP
                    \     /
                  VALIDACIÓN
                       ↓
                 OSI / EVIDENCIA
                       ↓
                 QUALITY GATE
                       ↓
                     ATLAS
```

## Criterio de cierre

La arquitectura queda cerrada. Las alertas notifican y solicitan acciones; los gates siguen siendo quienes determinan la aceptación del conocimiento.
