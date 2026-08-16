# H04 — Prospección diaria automatizada

## 1. Qué problema resuelve

El ecosistema cambia demasiado deprisa para mantener un catálogo manual. H04 crea un proceso diario que busca nuevos modelos, runtimes, agentes, herramientas, benchmarks y hardware relevantes.

La palabra clave es **descubrimiento**. Encontrar un proyecto no significa que LEONES lo recomiende ni que haya verificado sus prestaciones.

## 2. Flujo completo

```text
REGISTRO DE FUENTES
       ↓
PLAN DE CONSULTAS
       ↓
DESCUBRIMIENTO
       ↓
MERGE
       ↓
ENRIQUECIMIENTO
       ↓
LICENCIA / CLASIFICACIÓN
       ↓
INGESTA ATLAS
       ↓
PUBLICACIÓN WEB
       ↓
INFORME DIARIO
```

## 3. Workflow

`.github/workflows/daily-prospection.yml` se ejecuta diariamente y también permite ejecución manual.

El orden actual es importante: primero se inventaría la cobertura; después se descubren instancias federadas; luego se ejecutan las fuentes y categorías de modelos, runtimes, agentes, skills, harnesses y hardware; después se enriquecen y clasifican los resultados.

## 4. Script de planificación

`scripts/prospection/run_daily_prospection.py` no hace por sí solo toda la prospección en Internet. Su función es preparar un **plan de consultas** a partir del registro de fuentes y de las familias de búsqueda.

Esto evita mezclar tres conceptos:

- una fuente que sabemos que existe;
- una consulta que queremos ejecutar;
- un hallazgo que realmente hemos descubierto.

El script escribe `source_discovery_plan.ndjson` y un pequeño informe de planificación.

## 5. Categorías

El plan contempla:

- modelos;
- runtimes;
- agentes;
- skills;
- harnesses;
- hardware.

Cada familia tiene consultas específicas que se combinan con las consultas propias del plan.

## 6. Licencias

La política del proyecto utiliza OSI como puerta de entrada del conjunto principal. GPL, AGPL y LGPL tienen prioridad analítica dentro de ese conjunto.

Pero **Copyleft prioritario no significa recomendado**. La licencia declarada por una plataforma es evidencia de descubrimiento; no sustituye una revisión jurídica del proyecto y sus componentes.

## 7. Estados

Un hallazgo debe poder distinguirse de una validación. La arquitectura mantiene estados de descubrimiento, licencia, publicación y evidencia para evitar que una simple aparición en un buscador se convierta en una afirmación fuerte sobre el proyecto.

## 8. Qué debe hacer un mantenedor

Si añades una nueva fuente:

1. regístrala en `sources_registry.json`;
2. define su familia/adaptador;
3. comprueba la política de licencia;
4. ejecuta el flujo de prueba correspondiente;
5. comprueba que la fuente no duplica hallazgos existentes;
6. revisa la trazabilidad de la URL y fecha;
7. actualiza la documentación si cambia la arquitectura.

No conviene introducir una fuente directamente en el workflow sin pasar por el registro: el registro es el inventario que permite saber qué cubre realmente LEONES.

## 9. Enlaces

- Fase: [`docs/phases/2026-08-daily-prospection/`](../phases/2026-08-daily-prospection/)
- Workflow: [`.github/workflows/daily-prospection.yml`](../../.github/workflows/daily-prospection.yml)
- Script de planificación: [`scripts/prospection/run_daily_prospection.py`](../../scripts/prospection/run_daily_prospection.py)
- Política de licencias: [`docs/PROSPECTION_LICENSE_POLICY.md`](../PROSPECTION_LICENSE_POLICY.md)
- Procedimiento de fuentes: [`scripts/prospection/PROCEDIMIENTO_DESCUBRIMIENTO_NUEVAS_FUENTES.md`](../../scripts/prospection/PROCEDIMIENTO_DESCUBRIMIENTO_NUEVAS_FUENTES.md)
