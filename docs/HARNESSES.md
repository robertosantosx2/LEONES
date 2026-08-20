# LEONES — Harnesses agénticos

**Estado de la decisión:** CONGELADA  
**Fecha:** 2026-08-20  
**Decisión:** Hermes Agent es el Harness de referencia de LEONES.

## Estado actual

| Componente | Rol | Estado |
|---|---|---|
| **Hermes Agent** | Harness agéntico de referencia | **Referencia fijada** |
| DeepSeek Harness | Harness candidato | **En desarrollo — pausado** |
| Buddy | Harness/agente candidato | **En desarrollo — pausado** |
| ODS | Servidor de stacks IA | Activo en su rol propio |
| Magnitude | Asistente/instrumentación de coding | Activo en su rol propio |

## Regla fijada

Hermes es, hasta nueva decisión explícita, el único **Harness de referencia** de LEONES.

DeepSeek Harness y Buddy no se eliminan ni se descartan. Quedan conservados como líneas de desarrollo, pero su integración y evolución como harnesses de referencia queda **pausada hasta nueva orden**.

ODS y Magnitude no forman parte de la competencia entre harnesses: mantienen sus funciones arquitectónicas específicas.

## Criterio de cambio

Esta decisión solo se modifica mediante una nueva decisión documentada. Una nueva tecnología puede estudiarse sin convertirse por ello en nuevo harness de referencia.

## Arquitectura de referencia

```text
                 LEONES
                    │
                    ▼
          HERMES — HARNESS
              DE REFERENCIA
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   tareas reales             tools
        │                       │
        └───────────┬───────────┘
                    ▼
          benchmark agentic
                    │
                    ▼
          evidencia LEONES

  DeepSeek Harness ──► en desarrollo / pausado
  Buddy             ──► en desarrollo / pausado
  ODS               ──► servidor de stacks IA
  Magnitude         ──► asistente de coding
```

## Consecuencia operativa

Las nuevas pruebas, adaptadores, documentación de evaluación y benchmarks agentivos de LEONES deben tomar **Hermes** como baseline de harness, salvo que una tarea concreta requiera explícitamente otro componente.

La existencia de un baseline no convierte sus resultados en hechos universales: cada resultado conserva modelo, runtime, hardware, configuración, versión/commit y procedencia.
