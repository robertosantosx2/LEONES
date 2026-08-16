# LEONES — CI/CD y automatización

## Estado

**🟢 Arquitectura funcional cerrada · implementación progresiva**

Esta capa convierte los procesos definidos por LEONES en ciclos automáticos, reproducibles y observables. La automatización ejecuta políticas existentes; no las modifica.

## Objetivo

Eliminar la necesidad de lanzar manualmente cada incorporación:

```text
SCHEDULE / EVENT / MANUAL
          ↓
       WORKFLOW
          ↓
   DESCUBRIMIENTO
          ↓
    ACTUALIZACIÓN
          ↓
       EVIDENCIA
          ↓
    QUALITY GATE
          ↓
     ALERTA / REVIEW
          ↓
     PROMOCIÓN
          ↓
        ATLAS
```

## Familias de workflows

### `discovery`
Ejecuta ADIVINO y recoge nuevos candidatos.

### `refresh`
Comprueba cambios en fuentes y entidades conocidas.

### `evidence`
Recolecta o actualiza evidencias pendientes.

### `quality`
Ejecuta Quality Gate sobre elementos preparados para evaluación.

### `alerts`
Genera y entrega notificaciones de eventos relevantes.

### `promotion`
Promueve únicamente elementos que hayan superado los requisitos correspondientes.

### `physical-validation`
Ejecuta pruebas reales cuando exista infraestructura y protocolo; sus resultados quedan separados de estimaciones.

## Triggers

Los workflows pueden iniciarse por:

- horario programado;
- cambios en repositorio;
- nuevas releases;
- eventos externos admitidos;
- cola de trabajo;
- solicitud explícita de revisión;
- ejecución manual de emergencia.

El trigger no implica aceptación de datos.

## Cadencia

La frecuencia se adapta al tipo de información:

```text
volátil       → frecuente
moderada      → periódica
estable       → espaciada
bajo demanda  → evento/revisión
```

Los datos de precio, disponibilidad, versiones y actividad requieren mayor frescura que información histórica estable.

## Idempotencia

Cada workflow debe poder ejecutarse de nuevo sin duplicar entidades ni corromper estados.

Se utilizan identificadores estables, deduplicación y estados transaccionales.

## Concurrencia

La ejecución de tareas independientes puede ser paralela.

Los writers canónicos no:

```text
workers ─┐
workers ─┼→ resultados aislados → leones-main-writers → Atlas
workers ─┘
```

Todos los workflows que escriban datos canónicos deben respetar:

```yaml
concurrency:
  group: leones-main-writers
  cancel-in-progress: false
```

La paralelización interna no crea writers adicionales.

## Artefactos

Cada ciclo relevante conserva artefactos suficientes para auditarlo:

- resultados de descubrimiento;
- evidencias recolectadas;
- informes de Quality Gate;
- logs sanitizados;
- métricas;
- errores;
- referencias `trace_id`/`run_id`.

Los artefactos temporales no deben convertirse automáticamente en conocimiento canónico.

## Fallos y reintentos

Los errores recuperables pueden reintentarse con límites explícitos. Los fallos permanentes pasan a estado de revisión o error.

Un retry nunca debe duplicar una promoción canónica.

```text
FAIL → RETRY → SUCCESS
       ↓
      FAIL → REVIEW / ERROR
```

## Dependencias

Los pasos deben declarar dependencias de forma explícita. Un workflow no puede asumir que otro terminó correctamente solo porque fue lanzado previamente.

Cuando una dependencia es necesaria:

```text
A → B → C
```

y el resultado de A/B debe quedar disponible como artefacto o estado verificable.

## Secretos

Las credenciales se inyectan exclusivamente desde el mecanismo seguro definido en `SECRETOS-Y-CREDENCIALES.md`.

No se almacenan secretos en workflows, scripts, commits, artefactos ni logs.

## Email y validación

El workflow de alertas podrá utilizar `mananadaleones.ia@gmail.com` como remitente una vez configurada la credencial segura.

La respuesta humana `OK LEONES` pertenece al circuito de validación y no debe permitir saltarse OSI o Quality Gate.

## Observabilidad

Cada workflow debe generar trazabilidad suficiente para saber:

- qué lo inició;
- qué versión del workflow se ejecutó;
- qué entradas recibió;
- qué pasos ejecutó;
- qué produjo;
- qué falló;
- qué fue promovido;
- qué alerta generó.

## Seguridad de la automatización

Los contenidos descubiertos se consideran datos no confiables. Un documento externo no puede modificar el workflow, las políticas, los secretos ni las instrucciones de LEONES.

Los permisos de cada workflow deben ser mínimos y explícitos.

## Promoción canónica

La promoción sigue siempre el circuito correspondiente:

```text
DESCUBRIMIENTO
     ↓
IDENTIDAD
     ↓
OSI (si aplica)
     ↓
EVIDENCIA
     ↓
QUALITY GATE
     ↓
PROMOTION
     ↓
ATLAS
```

No existe un workflow de "importación directa" que salte estos controles.

## Estado operativo

Se recomienda mantener estados explícitos por workflow:

```text
QUEUED
RUNNING
SUCCESS
PARTIAL
RETRYING
FAILED
BLOCKED
```

`PARTIAL` no equivale a `SUCCESS` para promociones canónicas.

## Criterio de cierre

La arquitectura de CI/CD queda cerrada. La implementación debe automatizar el ciclo completo sin convertir la automatización en una vía para saltarse políticas, evidencia, OSI o trazabilidad.
