# Odysseus — workspace local-first para LEONES

**Nombre de referencia LEONES:** Odysseus  
**Fuente primaria:** https://github.com/odysseus-dev/odysseus  
**Sitio:** https://odysseus-dev.github.io/odysseus/  
**Licencia declarada:** AGPL-3.0-or-later  
**Revisión LEONES:** 2026-08-24  
**Clasificación principal:** `workspace-reference`

## 1. FUENTE / DESCUBRIMIENTO

Odysseus es un **self-hosted AI workspace** para chat, agentes, herramientas, MCP, ficheros, shell, memoria, investigación, documentos, correo, notas, tareas, calendario y workflows de modelos locales/API. El repositorio separa core, companion, integraciones, rutas, servidores MCP, Docker y documentación. La rama `dev` es la de desarrollo más reciente y `main` la rama curada que el proyecto presenta como más estable.

El proyecto incluye un Cookbook de recomendaciones hardware-aware, descarga y serving de modelos, investigación profunda y comparación de modelos. También documenta despliegue Docker y configuración de hosts LLM, Ollama, LM Studio y endpoints compatibles.

## 2. EVIDENCIA

### `evidence-primary`

- El propio repositorio define Odysseus como workspace self-hosted y enumera chat/agents, tools/MCP, memoria, investigación, documentos y otras funciones de aplicación.
- El Cookbook forma parte del producto y ofrece recomendaciones hardware-aware.
- La configuración permite conectar servicios LLM locales o remotos mediante hosts/endpoints.
- La documentación de seguridad exige autenticación en despliegues accesibles por red y desaconseja exponer directamente puertos de modelos/servicios.

### `verification-leones`

LEONES ha verificado documentalmente la existencia, estructura y procedencia del proyecto. Esto **no** equivale a una medición funcional de Odysseus.

### No demostrado

La fuente no demuestra que Odysseus sea el mejor workspace, que sus recomendaciones sean superiores a LLMFit/Magnitude/ODS, ni que un runtime concreto conectado a Odysseus tenga un rendimiento determinado. Tampoco convierte sus comparaciones o workloads en benchmarks canónicos de LEONES.

## 3. ESTIMACIÓN

Odysseus no es principalmente un estimador, pero su Cookbook puede producir **señales externas de recomendación**. LEONES las conservará como:

```text
estimator_source = odysseus
estimation_type = hardware-aware workspace recommendation
status = unverified
```

No se sumarán estas recomendaciones a scores LEONES ni se convertirán en `measured`. Tampoco se mezclarán con las estimaciones de LLMFit o Magnitude como si procedieran del mismo modelo de estimación.

## 4. MEDICIÓN LEONES

**Estado:** `no disponible`.

Cuando Odysseus entre en un benchmark reproducible, la unidad medida será **modelo + runtime + endpoint + workspace + workload**, no el workspace aislado.

Mínimos: commit/version de Odysseus; runtime y versión; modelo/cuanti; hardware/SO; configuración; workload; TTFT; TPOT/tok/s cuando proceda; latencia extremo a extremo; memoria; tool calls; éxito funcional; grader/score; evidence ID y artefactos.

## 5. VALOR PARA LEONES

Odysseus permite estudiar si una recomendación que funciona en generación aislada sigue siendo adecuada cuando aparecen memoria conversacional, herramientas, MCP, recuperación, múltiples turnos, investigación y tareas largas.

Arquitectura correcta:

```text
modelo
   ↓
runtime
   ↓
endpoint
   ↓
Odysseus
   ↓
workload / tools / MCP / memory
   ↓
grader
   ↓
benchmark LEONES
   ↓
medición LEONES
```

Hipótesis FreeToken + Odysseus:

```text
FreeToken → endpoint → Odysseus → workload → grader → evidencia/medición
```

Esta combinación es una **hipótesis de integración** que debe medirse.

## 6. VARIABLES DE SELECCIÓN Y MEDICIÓN

Además de las variables de inferencia: número de turnos, herramientas disponibles, tool calls, tamaño de contexto, memoria persistente, RAG, MCP, duración total, éxito de tarea, fallos/reintentos, coste de tokens y controles de seguridad.

## 7. LIMITACIONES

El proyecto evoluciona rápidamente y `dev` puede ser inestable. Sus propias guías de seguridad consideran que dispone de capacidades locales privilegiadas. La compatibilidad y estabilidad en LEONES deben comprobarse mediante ejecución reproducible.

## 8. INTEGRACIÓN LEONES

Odysseus **no entra en `runtime-selection.v1` como runtime**. Entra como workspace/harness superior después de seleccionar runtime y endpoint.

```text
selector
   ↓
runtime-selection.v1
   ↓
executor/runtime
   ↓
endpoint
   ↓
Odysseus workload
   ↓
grader
   ↓
benchmark
   ↓
evidence
   ↓
Router / Atlas
```

**Próximo gate:** ejecutar un workload agentivo reproducible con un runtime local canónico y después repetirlo con FreeToken cuando exista un endpoint compatible.
