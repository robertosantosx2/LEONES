# LEONES — Estado de los harnesses

**Decisión vigente: 20 de agosto de 2026**

## Harness de referencia

### Hermes Agent — FIJADO

Hermes Agent, de Nous Research, queda fijado como **Harness de referencia de LEONES** para la ejecución y evaluación agéntica.

Repositorio oficial: https://github.com/NousResearch/hermes-agent

Documentación: https://hermes-agent.nousresearch.com/docs/

Esta decisión significa que, a partir de ahora, las integraciones, benchmarks agentivos, protocolos de ejecución y pruebas de referencia de LEONES deben tomar Hermes como baseline salvo que una decisión posterior lo cambie explícitamente.

Hermes no sustituye a Atlas, LLMFit, los runtimes ni la infraestructura de inferencia: ocupa la posición de harness de referencia en la capa agéntica.

## Harnesses en desarrollo — PAUSADOS

Los siguientes harnesses permanecen reconocidos por LEONES, pero quedan **en desarrollo y pausados hasta nueva orden**:

- **DeepSeek Harness** — https://github.com/deepseek-ai/deepseek-harness
- **Buddy** — https://github.com/juanje/buddy

No se continuará, por ahora, con nuevas integraciones, optimizaciones, benchmarks específicos ni ampliaciones de estos dos harnesses como líneas prioritarias de LEONES.

Su código, documentación y conocimiento acumulado se conservan. Pausar no significa descartar.

## Separación de responsabilidades

| Componente | Estado | Papel |
|---|---|---|
| **Hermes Agent** | **Referencia fijada** | Harness agéntico de referencia |
| **DeepSeek Harness** | **En desarrollo / pausado** | Harness candidato |
| **Buddy** | **En desarrollo / pausado** | Harness candidato |
| **ODS** | Activo en su línea | Servidor de stacks IA |
| **Magnitude** | Activo en su línea | Asistente / infraestructura de coding y estimación |

ODS y Magnitude **no forman parte de la lista de harnesses de referencia**. Mantienen sus funciones propias dentro de la arquitectura LEONES.

## Regla de cambio

Esta decisión queda congelada como decisión de arquitectura. Para cambiar el harness de referencia, reactivar DeepSeek Harness o Buddy, o sustituir Hermes, será necesaria una nueva decisión explícita y documentada en `LEONES_DECISION_LOG.md`.
