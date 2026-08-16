# LEONES — Actualización y descubrimiento continuo

## Estado

**🟢 Arquitectura funcional cerrada · implementación pendiente**

Esta capa mantiene LEONES actualizado sin introducir automáticamente conocimiento no verificado en Atlas.

## Flujo

```text
FUENTES CONOCIDAS
      ↓
DESCUBRIMIENTO
      ↓
ADIVINO / RADAR
      ↓
CANDIDATOS
      ↓
IDENTIDAD
      ↓
OSI (cuando corresponda)
      ↓
EVIDENCIA
      ↓
QUALITY GATE
      ↓
ATLAS
```

## Dos funciones separadas

### 1. Actualización
Comprueba cambios en fuentes ya conocidas: versiones, licencias, benchmarks, precios, hardware, documentación, compatibilidad y estado de proyectos.

### 2. Descubrimiento
Busca fuentes, proyectos, modelos, agentes, harnesses, frameworks, benchmarks, software y otras señales que LEONES todavía no conozca.

Descubrir **no significa aceptar**.

## Adivino

ADIVINO es el radar de descubrimiento futuro. Produce candidatos y razones para investigarlos; no modifica Atlas directamente.

Cada descubrimiento debe conservar:

- `discovery_id`;
- fecha;
- fuente que lo originó;
- URL/identificador;
- tipo de candidato;
- nombre detectado;
- motivo de relevancia;
- confianza del descubrimiento;
- estado de revisión.

## Fuentes

El sistema admite familias de fuentes, por ejemplo:

- repositorios;
- documentación oficial;
- registros de modelos/datasets;
- benchmarks;
- publicaciones técnicas;
- blogs técnicos;
- comunidades;
- newsletters;
- feeds/RSS/APIs;
- fuentes descubiertas por otros candidatos.

Una fuente nueva no se convierte automáticamente en fuente de confianza. Debe pasar el circuito de validación correspondiente.

## Priorización

Los candidatos se priorizan por señales como:

- novedad;
- relevancia para LEONES;
- actividad reciente;
- impacto potencial;
- evidencia disponible;
- probabilidad de duplicado;
- relación con conocimiento existente.

La prioridad organiza trabajo; no decide aceptación.

## Deduplificación

Antes de crear una entidad nueva se intenta resolver identidad y relaciones con entidades existentes. Los posibles duplicados se conservan para revisión y no generan entradas canónicas duplicadas.

## Cambios y regresiones

Una actualización puede:

- crear una nueva versión;
- actualizar evidencia;
- invalidar una evidencia anterior;
- marcar un dato como obsoleto;
- generar una alerta de revisión.

No se reescribe silenciosamente el histórico.

## Cadencia

La frecuencia de comprobación será configurable por familia de fuente y sensibilidad del dato. Datos volátiles requieren mayor frecuencia; datos estables pueden revisarse con menor frecuencia.

La cadencia no altera los criterios de aceptación.

## Alertas

Los eventos relevantes pueden generar alertas para revisión humana:

- nuevo modelo/proyecto;
- nueva versión relevante;
- cambio de licencia;
- cambio de disponibilidad;
- nuevo benchmark;
- regresión detectada;
- fuente desaparecida;
- evidencia contradictoria;
- candidato de alta relevancia.

## Validación humana

Cuando el flujo requiera decisión humana, el candidato queda pendiente. La respuesta **OK LEONES** puede actuar como confirmación en los circuitos que LEONES haya configurado para ello; nunca sustituye la evidencia técnica que corresponda.

## Seguridad

Las fuentes externas se tratan como datos no confiables. El contenido descubierto no debe ejecutarse como código ni modificar instrucciones/políticas del sistema. URLs, documentos y artefactos se procesan como entradas de datos.

## No concurrencia

Los descubridores y recolectores pueden trabajar en paralelo siempre que sus resultados sean aislados. La escritura de candidatos/estados canónicos utiliza exclusivamente `leones-main-writers` con `cancel-in-progress: false`.

```text
DESCUBRIDORES ─┐
RECOLECTORES  ─┼→ RESULTADOS AISLADOS → UN WRITER → CANÓNICO
VALIDADORES   ─┘
```

## Observabilidad

Cada ciclo debe conservar `trace_id`/`run_id` cuando corresponda, fuente, timestamps, resultados y errores. Un descubrimiento debe poder rastrearse hasta su origen.

## Integración

```text
ADIVINO
  ↓
CATÁLOGO DE CANDIDATOS
  ↓
IDENTIDAD
  ↓
OSI
  ↓
EVIDENCIA
  ↓
QUALITY GATE
  ↓
ATLAS
```

El sistema nunca usa el descubrimiento como atajo para saltarse OSI, evidencia o Quality Gate.

## Cierre

La arquitectura queda cerrada. La implementación debe permitir crecer el radar de fuentes sin contaminar Atlas y debe mantener separados descubrimiento, actualización, validación y promoción.
