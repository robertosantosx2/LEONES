# LEONES V1 — A01 con runtime real

> **Build it. Measure it. Explain it. Preserve the evidence.**

## Propósito

Este documento fija el significado de una ejecución completa de una tarea agentiva A01 utilizando un **runtime real**, un modelo real y una API local real. Su finalidad no es demostrar que cualquier modelo pequeño pueda ejecutar cualquier tarea, sino demostrar que la cadena de decisión de LEONES puede pasar de una selección declarada a una ejecución reproducible y volver con evidencia.

El recorrido validado es:

```text
selección de modelo
      ↓
runtime-selection.v1
      ↓
plan de ejecución autorizado
      ↓
Ollama local
      ↓
Qwen2.5 0.5B Q4_K_M
      ↓
A01
      ↓
lookup_model → write_report
      ↓
grader A01
      ↓
runtime-benchmark.v1 / evidencia canónica
      ↓
evidencia medida
```

## Evidencia H10 de referencia

La validación H10 realizada en Debian produjo una ejecución real que queda preservada como evidencia canónica:

| Campo | Valor |
|---|---|
| Modelo | `qwen2.5:0.5b-instruct-q4_K_M` |
| Runtime | Ollama `0.33.1` |
| Tarea | `A01` |
| Tool calls | `2` |
| Tool errors | `0` |
| Resultado | `success` |
| Grader | `passed` |
| Score | `1.0` |
| **Throughput medido** | **`51.5798 tok/s`** |
| Measurement status | `reported_by_runtime` |
| Evidence type | `measured` |
| Measurement kind | **`real`** |
| Execution ID | `ba58d9dd-15ac-4a43-88d2-2aaf537efe5e` |
| Measured at | `2026-08-27T06:02:24.821349+00:00` |

El registro canónico resumido está en `artifacts/h10-a01-runtime-selection-evidence.v1.json` y conserva el SHA-256 del artefacto completo generado localmente:

`6c99e6bd6c02c5d5d6062c731c4a30cbf380280791259fca93174db411c7d45d`

**51.5798 tok/s pertenece exclusivamente a esta ejecución concreta.** No es una cifra universal del modelo, de Ollama ni del equipo.

## Evidencia frente a afirmaciones

LEONES distingue deliberadamente:

- **Fuente:** lo que declara un proyecto, fabricante o tercero.
- **Observed:** lo que se observa en el entorno.
- **Estimated:** cálculo o predicción.
- **Measured:** resultado obtenido ejecutando el procedimiento de LEONES.
- **Verified:** evidencia que ha pasado el quality gate correspondiente.

Una medición sintética no puede promocionarse a `measured` ni `verified`. El contrato exige `measurement_kind=real` para evidencia medida/verificada, y rechaza explícitamente `measurement_kind=synthetic`.

Por tanto, `51.5798 tok/s` es una **medición de esta ejecución concreta**. No debe presentarse como una propiedad intrínseca de Qwen2.5 0.5B.

Tampoco debe utilizarse esta medición para atribuir rendimiento a otros equipos, otras versiones de Ollama, otros contextos, otras cuantizaciones o GPU.

## Identidad y procedencia

La ejecución H10 quedó identificada por:

- `execution_id`: `ba58d9dd-15ac-4a43-88d2-2aaf537efe5e`;
- `measured_at`: `2026-08-27T06:02:24.821349+00:00`;
- `source_artifact_sha256`: `6c99e6bd6c02c5d5d6062c731c4a30cbf380280791259fca93174db411c7d45d`;
- runtime: `ollama`;
- versión instalada en Debian: `0.33.1`.

La selección declaró explícitamente modelo, runtime y cuantización. El benchmark consume esa selección y no sustituye el plan por una decisión textual independiente.

## El papel de `runtime-selection.v1`

La selección produce un plan que identifica, entre otras cosas:

- `model_id`;
- runtime;
- versión del runtime;
- cuantización;
- estado de selección;
- autorización de ejecución;
- necesidad de medición.

La ejecución H10 recorrió ese plan y obtuvo:

- `execution_authorized=true`;
- `measurement_required=true`;
- `selection_rank=1`;
- ejecución real en Ollama;
- A01 `success`;
- grader `passed`.

Esto evita que la medición física se convierta en un camino paralelo al selector: **la medición debe recorrer el mismo contrato que utilizaría una recomendación real**.

## El adaptador de Ollama

`scripts/ollama_a01_runtime.py` funciona como puente entre Ollama y el contrato canónico A01.

Sus responsabilidades son deliberadamente pequeñas:

1. recibir el modelo seleccionado;
2. enviar el prompt y las herramientas a la API local de Ollama;
3. exigir `lookup_model` como primera herramienta;
4. proporcionar el resultado de la búsqueda al modelo;
5. exigir `write_report` a continuación;
6. normalizar las llamadas a JSON canónico;
7. recoger `eval_count` y `eval_duration` cuando Ollama los proporciona;
8. calcular `measured_tps` únicamente a partir de esos valores;
9. no inventar throughput cuando el runtime no lo reporta.

La evidencia resultante se marca explícitamente `measurement_kind=real`. Si el runtime no proporciona los datos necesarios, LEONES conserva `null` y no convierte una estimación en medición.

## El grader A01

El grader comprueba cinco propiedades esenciales:

1. **tool order** — `lookup_model` antes de `write_report`;
2. **target model** — el modelo solicitado coincide con el seleccionado;
3. **lookup result** — la herramienta recibe una identidad válida;
4. **artifact exists** — se produce `report.txt`;
5. **artifact contains model** — el artefacto conserva la identidad del modelo.

En la ejecución H10 las cinco comprobaciones fueron `true` y el grader obtuvo `score: 1.0`.

Una ejecución rápida no basta: **debe producir el comportamiento correcto**.

## Variabilidad y criterio de referencia

Durante la integración se obtuvieron varias ejecuciones válidas. Deben conservarse como ejecuciones independientes y nunca combinarse para fabricar una cifra única:

| Ejecución | Throughput | Estado |
|---|---:|---|
| histórica 1 | `52.7164 tok/s` | conservada como histórica |
| histórica 2 | `47.9803 tok/s` | conservada como histórica |
| cierre anterior | `40.7666 tok/s` | conservada como histórica |
| **H10 actual** | **`51.5798 tok/s`** | **evidencia real canónica** |

Las cifras no son contradictorias: son ejecuciones distintas. **No se debe escoger la mayor cifra para representar el sistema.** La evidencia canónica actual identifica exactamente la ejecución H10 mediante su `execution_id` y el hash del artefacto.

Para un benchmark comparativo posterior habrá que fijar una metodología específica: repeticiones, calentamiento, contexto, prompt, generación, versión del runtime y condiciones del hardware. Esta prueba A01 no pretende resolver por sí sola esa metodología.

## Reproducibilidad

La ejecución H10 se realizó mediante el camino de selección a A01:

```bash
python3 scripts/run_a01_selected.py \
  --selection artifacts/real-a01-selection.json \
  --runtime-commands artifacts/real-a01-runtime-commands.json \
  --workspace .leones/h10-a01-workspace \
  --prompt 'Execute A01. Return only JSONL tool calls.' \
  --out artifacts/h10-a01-runtime-selection-result.json
```

El servicio Ollama debe estar disponible localmente y el modelo seleccionado debe existir en el host.

La evidencia H10 se validó estructuralmente con:

```bash
python3 -m json.tool artifacts/h10-a01-runtime-selection-result.json >/dev/null
```

y mediante aserciones que exigen simultáneamente:

```text
 evidence_type == measured
 measurement_kind == real
 execution_id presente
 measured_at presente
 measurement_status == reported_by_runtime
 A01 == success
 grader == passed
 score == 1.0
 execution_authorized == true
 measurement_required == true
```

La validación H10 obtuvo además:

```text
177 passed
SCHEMAS: PASS
CANONICAL A01 REAL EVIDENCE: PASS
H10 EVIDENCE CONTRACT: PASS
```

## Qué NO demuestra esta prueba

Esta prueba no demuestra:

- que Ollama sea el runtime óptimo para todos los modelos;
- que Qwen2.5 0.5B sea el mejor modelo para todas las tareas;
- que `51.5798 tok/s` sea un benchmark general del equipo;
- que una ejecución agentiva larga tenga el mismo rendimiento;
- que el modelo mantenga esa velocidad con otro contexto o configuración;
- que la cifra sea comparable sin normalizar metodología con cifras de terceros;
- que los campos de hardware desconocidos deban rellenarse retrospectivamente con suposiciones.

Su alcance es preciso: **A01 funciona de extremo a extremo con el modelo y runtime seleccionados, el grader valida el comportamiento requerido y el runtime real devuelve una medición de throughput utilizable como evidencia LEONES.**

## Fixture frente a runtime real

El fixture sigue siendo necesario para CI porque GitHub Actions no debe depender de una GPU, de una descarga de modelos ni de un servicio externo. Su función es comprobar contratos y regresiones de forma determinista.

El runtime real tiene otra función: demostrar que el mismo camino puede llegar hasta una inferencia física y regresar con medición.

```text
fixture CI  → contrato reproducible y barato
runtime real → evidencia física
```

**No deben mezclarse ni presentarse como si fueran la misma evidencia.**

## Criterio de calidad V1

A partir de aquí, cualquier nuevo runtime debe poder demostrar el mismo contrato:

```text
selección
→ autorización
→ ejecución
→ trayectoria
→ grading
→ artefacto
→ medición real
→ evidencia
```

El objetivo no es acumular scripts de runtimes. El objetivo es que **todos los runtimes entren y salgan por el mismo contrato**, de manera que las recomendaciones posteriores puedan comparar evidencia sin perder procedencia.
