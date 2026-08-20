# Decisión arquitectónica — Hermes como Harness de referencia

**Fecha:** 2026-08-20  
**Estado:** CONGELADA

## Decisión

**Hermes Agent (Nous Research) queda fijado como Harness de referencia de LEONES.**

Repositorio oficial: https://github.com/NousResearch/hermes-agent

Documentación oficial: https://hermes-agent.nousresearch.com/docs/

A partir de esta decisión, Hermes es el baseline de la capa de ejecución agéntica para:

- integración de tareas agentivas;
- benchmarks y evaluación reproducible;
- pruebas de herramientas y trayectorias;
- validación de flujos de coding y tareas multietapa;
- documentación de referencia de la arquitectura agentiva.

## Estado del resto de harnesses

Los otros harnesses previamente considerados quedan en **EN DESARROLLO — PAUSADOS HASTA NUEVA ORDEN**:

- **DeepSeek Harness** — https://github.com/deepseek-ai/deepseek-harness
- **Buddy** — https://github.com/juanje/buddy

Se conserva todo el conocimiento y código ya incorporado, pero se detiene temporalmente su evolución como líneas activas de harness y no se utilizarán como referencia por defecto.

## Límites de la decisión

Esta decisión no elimina ni pausa los demás subproyectos de LEONES.

En particular:

- **ODS** mantiene su papel de servidor de stacks IA.
- **Magnitude** mantiene su papel de asistente/instrumentación de coding y hardware.
- Atlas, LLMFit, runtimes, routers, cuantización y benchmarks mantienen sus funciones propias.

ODS y Magnitude no se clasifican como harnesses de referencia.

## Regla de gobierno

La decisión queda congelada. Cualquier cambio de harness de referencia o reactivación de DeepSeek Harness/Buddy como líneas prioritarias requerirá una nueva decisión explícita y documentada.
