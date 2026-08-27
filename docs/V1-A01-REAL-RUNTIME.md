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

La ejecución real realizada en Debian utilizó:

| Campo | Valor |
|---|---|
| Modelo | `qwen2.5:0.5b-instruct-q4_K_M` |
| Cuantización | `Q4_K_M` |
| Runtime | Ollama |
| Versión runtime | `0.33.1` |
| Endpoint | `127.0.0.1:11434` |
| Hardware de inferencia | CPU |
| Tarea | `A01` |
| Tool calls | `2` |
| Resultado | `success` |
| Grader | `passed` |
| Score | `1.0` |
| Tiempo de pared, ejecución 1 | `2.147932 s` |
| Rendimiento, ejecución 1 | `52.7164 tok/s` |
| Tiempo de pared, ejecución 2 | `2.345202 s` |
| Rendimiento, ejecución 2 | `47.9803 tok/s` |

La segunda ejecución es la evidencia final que debe citarse para esta sesión: **47.9803 tok/s**. La primera queda conservada como observación histórica y no debe sobrescribirse.

## Evidencia frente a afirmaciones

LEONES distingue deliberadamente:

- **Fuente:** lo que declara un proyecto, fabricante o tercero.
- **Observed:** lo que se observa en el entorno.
- **Estimated:** cálculo o predicción.
- **Measured:** resultado obtenido ejecutando el procedimiento de LEONES.
- **Verified:** evidencia que ha pasado el quality gate correspondiente.

Por tanto, `47.9803 tok/s` no es una cifra universal de Qwen2.5 0.5B. Es una **medición de esta ejecución concreta**, bajo las condiciones que quedaron registradas.

Tampoco debe utilizarse esta medición para atribuir rendimiento a otros equipos, otras versiones de Ollama, otros contextos, otras cuantizaciones o GPU.

## El papel de `runtime-selection.v1`

La selección no ejecuta directamente el modelo. Produce un plan que identifica, entre otras cosas:

- `model_id`;
- runtime;
- versión del runtime;
- cuantización;
- estado de selección;
- autorización de ejecución;
- necesidad de medición.

El benchmark consume ese plan. Esto es importante porque impide que el benchmark se convierta en un script paralelo al selector: **la medición física debe recorrer el mismo contrato que utilizaría una recomendación real**.

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

Esta última regla es fundamental. En las primeras ejecuciones con el runtime fixture el benchmark podía tener tiempo de pared, pero no tokens por segundo. Eso no autorizaba a rellenar el campo con una estimación.

## El grader A01

El grader comprueba cinco propiedades esenciales:

1. **tool order** — `lookup_model` antes de `write_report`;
2. **target model** — el modelo solicitado coincide con el seleccionado;
3. **lookup result** — la herramienta recibe una identidad válida;
4. **artifact exists** — se produce `report.txt`;
5. **artifact contains model** — el artefacto conserva la identidad del modelo.

Una ejecución rápida no basta: **debe producir el comportamiento correcto**.

## Qué significa `47.9803 tok/s`

La cifra pertenece a `runtime-benchmark.v1` y a la ejecución cuyo identificador fue:

`a757ce94-0a2c-4042-95a2-39c89d8ba67c`

El benchmark también conserva el hash SHA-256 del resultado del ejecutor:

`8b9e14a4f9e6041ce8fed47d4f816df0f500646aa6de4f0297e63e2b02a75f7a`

La existencia del hash permite detectar cambios posteriores en el resultado sin confundir una nueva ejecución con la antigua.

## Reproducibilidad

La ejecución local se realizó con:

```bash
python3 scripts/a01_runtime_benchmark.py \
  --selection artifacts/real-a01-selection.json \
  --runtime-commands artifacts/real-a01-runtime-commands.json \
  --workspace .leones/a01-real-workspace \
  --out artifacts/a01-real-runtime-benchmark.v1.json
```

El servicio Ollama debe estar disponible en `127.0.0.1:11434` y el modelo seleccionado debe existir localmente.

La preparación del modelo fue:

```bash
ollama pull qwen2.5:0.5b-instruct-q4_K_M
```

La verificación del endpoint confirmó que el runtime era alcanzable y que el modelo estaba disponible.

## Qué NO demuestra esta prueba

Esta prueba no demuestra:

- que Ollama sea el runtime óptimo para todos los modelos;
- que Qwen2.5 0.5B sea el mejor modelo para todas las tareas;
- que `47.9803 tok/s` sea un benchmark general del equipo;
- que una ejecución agentiva larga tenga el mismo rendimiento;
- que el modelo mantenga esa velocidad con otro contexto o configuración;
- que la cifra sea comparable sin normalizar metodología con cifras de terceros.

Su alcance es mucho más preciso: **A01 funciona de extremo a extremo con el modelo y runtime seleccionados, y el runtime real devuelve una medición de throughput utilizable como evidencia LEONES.**

## Fixture frente a runtime real

El fixture sigue siendo necesario para CI porque GitHub Actions no debe depender de una GPU, de una descarga de modelos ni de un servicio externo. Su función es comprobar contratos y regresiones de forma determinista.

El runtime real tiene otra función: demostrar que el mismo camino puede llegar hasta una inferencia física y regresar con medición.

Por tanto:

```text
fixture CI  → contrato reproducible y barato
runtime real → evidencia física
```

No deben mezclarse ni presentarse como si fueran la misma evidencia.

## Estado V1

A01 ya tiene las dos capas necesarias:

- **CI:** contrato determinista y sin dependencia de hardware específico.
- **Debian:** ejecución real con Ollama y medición física.

Los gates de CI asociados al commit de corrección quedaron verdes:

- `Agentic A01 contract` — success;
- `LEONES Contract Tests` — success;
- `LEONES V1 Complete Gate` — success.

Esto convierte A01 en una integración funcional, no solamente en una prueba aislada del adaptador.

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
