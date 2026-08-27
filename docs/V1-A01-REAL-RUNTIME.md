# LEONES V1 — A01 con runtime real

> **Build it. Measure it. Explain it. Preserve the evidence.**

## Propósito

Este documento fija el significado de la primera ejecución completa de una tarea agentiva A01 utilizando un **runtime real**, un modelo real y una API local real. Su finalidad no es demostrar que cualquier modelo pequeño pueda ejecutar cualquier tarea, sino demostrar que la cadena de decisión de LEONES puede pasar de una selección declarada a una ejecución reproducible y volver con evidencia.

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
runtime-benchmark.v1
      ↓
evidencia medida
```

## Qué se ha demostrado

La ejecución de cierre realizada en Debian utilizó:

| Campo | Valor |
|---|---|
| Modelo | `qwen2.5:0.5b-instruct-q4_K_M` |
| Cuantización | `Q4_K_M` |
| Runtime | Ollama |
| Versión runtime instalada | `0.33.1` |
| Endpoint | `127.0.0.1:11434` |
| Tarea | `A01` |
| Tool calls | `2` |
| Tool errors | `0` |
| Resultado | `success` |
| Grader | `passed` |
| Score | `1.0` |
| Tiempo de pared, cierre | `5.744973 s` |
| **Throughput medido, cierre** | **40.7666 tok/s** |
| Evidencia | `measured` |

**40.7666 tok/s es la medición de cierre de esta ejecución.** No es una cifra universal del modelo, de Ollama ni del equipo.

## Evidencia frente a afirmaciones

LEONES distingue deliberadamente:

- **Fuente:** lo que declara un proyecto, fabricante o tercero.
- **Observed:** lo que se observa en el entorno.
- **Estimated:** cálculo o predicción.
- **Measured:** resultado obtenido ejecutando el procedimiento de LEONES.
- **Verified:** evidencia que ha pasado el quality gate correspondiente.

Por tanto, `40.7666 tok/s` es una **medición de esta ejecución concreta**. No debe presentarse como una propiedad intrínseca de Qwen2.5 0.5B.

Tampoco debe utilizarse esta medición para atribuir rendimiento a otros equipos, otras versiones de Ollama, otros contextos, otras cuantizaciones o GPU.

## Identidad y procedencia

La ejecución de cierre quedó identificada por:

- `execution_id`: `378854c5-8147-47a3-8e1b-33b078424d00`;
- `executor_result_sha256`: `ae11c085b986ef1c7a88983c4deaeb82cd714e72de36c3bff81e8eff7fa3f02b`;
- runtime: `ollama`;
- versión del runtime en el plan: `local`;
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

El benchmark consume ese plan. Esto evita que la medición física se convierta en un camino paralelo al selector: **la medición debe recorrer el mismo contrato que utilizaría una recomendación real**.

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

Esta última regla es fundamental: si el runtime no proporciona los datos necesarios, LEONES conserva `null` y no convierte una estimación en medición.

## El grader A01

El grader comprueba cinco propiedades esenciales:

1. **tool order** — `lookup_model` antes de `write_report`;
2. **target model** — el modelo solicitado coincide con el seleccionado;
3. **lookup result** — la herramienta recibe una identidad válida;
4. **artifact exists** — se produce `report.txt`;
5. **artifact contains model** — el artefacto conserva la identidad del modelo.

En la ejecución de cierre las cinco comprobaciones fueron `true` y el grader obtuvo `score: 1.0`.

Una ejecución rápida no basta: **debe producir el comportamiento correcto**.

## Medición de cierre

La cifra pertenece a `runtime-benchmark.v1` y a la ejecución cuyo identificador fue:

`378854c5-8147-47a3-8e1b-33b078424d00`

El benchmark conserva el hash SHA-256 del resultado del ejecutor:

`ae11c085b986ef1c7a88983c4deaeb82cd714e72de36c3bff81e8eff7fa3f02b`

El hash permite detectar cambios posteriores en el resultado sin confundir una nueva ejecución con la antigua.

## Variabilidad y criterio de referencia

Durante la integración se obtuvieron varias ejecuciones válidas:

| Ejecución | Wall time | Throughput | Estado |
|---|---:|---:|---|
| histórica 1 | `2.147932 s` | `52.7164 tok/s` | conservada como histórica |
| histórica 2 | `2.345202 s` | `47.9803 tok/s` | conservada como histórica |
| **cierre V1** | **`5.744973 s`** | **`40.7666 tok/s`** | **referencia de cierre** |

Las cifras no son contradictorias: son ejecuciones distintas. **La última ejecución válida es la referencia de cierre de esta validación.** No se debe escoger la mayor cifra para representar el sistema.

Para un benchmark comparativo posterior habrá que fijar una metodología específica: repeticiones, calentamiento, contexto, prompt, generación, versión del runtime y condiciones del hardware. Esta prueba A01 no pretende resolver por sí sola esa metodología.

## Reproducibilidad

La ejecución de cierre se realizó con:

```bash
python3 scripts/a01_runtime_benchmark.py \
  --selection artifacts/real-a01-selection.json \
  --runtime-commands artifacts/real-a01-runtime-commands.json \
  --workspace .leones/a01-real-workspace \
  --prompt 'Execute A01. Return only JSONL tool calls.' \
  --out artifacts/a01-real-runtime-benchmark.v1.json
```

El servicio Ollama debe estar disponible en `127.0.0.1:11434` y el modelo seleccionado debe existir localmente.

La preparación del modelo fue:

```bash
ollama pull qwen2.5:0.5b-instruct-q4_K_M
```

La disponibilidad del servicio y del modelo se verificó con la API local y `ollama list`.

La evidencia generada se valida con:

```bash
python3 -m json.tool artifacts/a01-real-runtime-benchmark.v1.json >/dev/null
cat .leones/a01-real-workspace/report.txt
```

El cierre adicional se validó mediante aserciones estructurales, la suite completa de tests y la validación de todos los esquemas JSON.

## Resultado del cierre técnico

La ejecución de cierre alcanzó simultáneamente:

- A01 `success`;
- grader `passed` con score `1.0`;
- dos tool calls;
- cero errores de herramienta;
- `report.txt` verificado;
- `runtime-benchmark.v1` con estado `measured`;
- `measured_tps` informado por el runtime;
- router `evidence_supported`;
- coincidencia entre modelo y runtime seleccionados y ejecutados.

En la misma revisión local:

- **174 tests pasaron** (`174 passed`);
- **12 esquemas JSON** fueron parseados correctamente.

## Qué NO demuestra esta prueba

Esta prueba no demuestra:

- que Ollama sea el runtime óptimo para todos los modelos;
- que Qwen2.5 0.5B sea el mejor modelo para todas las tareas;
- que `40.7666 tok/s` sea un benchmark general del equipo;
- que una ejecución agentiva larga tenga el mismo rendimiento;
- que el modelo mantenga esa velocidad con otro contexto o configuración;
- que la cifra sea comparable sin normalizar metodología con cifras de terceros;
- que los campos de hardware `unknown` de la evidencia deban rellenarse retrospectivamente con suposiciones.

Su alcance es preciso: **A01 funciona de extremo a extremo con el modelo y runtime seleccionados, el grader valida el comportamiento requerido y el runtime real devuelve una medición de throughput utilizable como evidencia LEONES.**

## Fixture frente a runtime real

El fixture sigue siendo necesario para CI porque GitHub Actions no debe depender de una GPU, de una descarga de modelos ni de un servicio externo. Su función es comprobar contratos y regresiones de forma determinista.

El runtime real tiene otra función: demostrar que el mismo camino puede llegar hasta una inferencia física y regresar con medición.

```text
fixture CI  → contrato reproducible y barato
runtime real → evidencia física
```

No deben mezclarse ni presentarse como si fueran la misma evidencia.

## Próximo criterio de calidad

A partir de aquí, cualquier nuevo runtime debe poder demostrar el mismo contrato:

```text
selección
→ autorización
→ ejecución
→ trayectoria
→ grading
→ artefacto
→ medición
→ evidencia
```

El objetivo no es acumular scripts de runtimes. El objetivo es que **todos los runtimes entren y salgan por el mismo contrato**, de manera que las recomendaciones posteriores puedan comparar evidencia sin perder procedencia.
