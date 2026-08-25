# Local LLM Coding Guide

## Identidad
- **Fuente primaria:** https://github.com/isaacrowntree/local-llm-coding-guide
- **Capa:** metodología / benchmarking.
- **Estado:** `research-candidate`.
- **Revisión:** 2026-08-25.

## Qué es
Guía centrada en la selección de modelos locales para programación. Su valor para LEONES no está tanto en un catálogo concreto como en una disciplina: **no confundir tablas estáticas de throughput con mediciones actuales del hardware y runtime reales**.

## Problema
El rendimiento de un modelo no es una constante universal. Cambia con:

- hardware;
- runtime;
- cuantización;
- contexto;
- prompt/workload;
- versión;
- configuración;
- concurrencia.

Por tanto, una tabla externa puede ser útil para prospección, pero no debe convertirse automáticamente en evidencia de rendimiento de la máquina del usuario.

## Fuente y evidencia
La documentación se conserva como metodología externa. Cualquier cifra concreta que aparezca en la fuente debe mantener su contexto y fecha.

## Estimación
Las recomendaciones de la guía son orientación externa. No constituyen un score LEONES.

## Medición LEONES
La metodología encaja directamente con nuestro executor canónico:

```text
modelo
  ↓
quant + runtime
  ↓
workload coding versionado
  ↓
warmup
  ↓
TTFT / TPOT / tok/s
  ↓
grader funcional
  ↓
evidence
```

## Valor para LEONES
Alto como regla editorial de benchmarks. Refuerza una distinción esencial:

```text
modelo recomendado por conocimiento
             ≠
modelo medido por LEONES
```

## Relación con LLMFit
LLMFit puede generar una primera shortlist. La guía refuerza que esa shortlist debe pasar posteriormente por medición real, especialmente para coding donde pequeñas diferencias de contexto y latencia afectan mucho la experiencia.

## Relación con Dubir
Dubir aporta workload como dimensión de selección. Esta guía aporta la necesidad de convertir ese workload en una medición reproducible.

## Limitaciones
- Es metodología, no benchmark canónico LEONES.
- No sustituye la infraestructura de ejecución.
- Las recomendaciones pueden quedar obsoletas.

## Clasificación
`research-candidate` / metodología.

## Próximo paso
Usar sus principios para revisar el contrato de benchmark coding de LEONES y asegurar que los resultados de diferentes runtimes no se comparan sin normalizar workload y configuración.