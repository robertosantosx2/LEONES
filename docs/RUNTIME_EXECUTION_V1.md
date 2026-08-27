# `runtime-execution.v1` — JALÓN 2

## Propósito

`runtime-execution.v1` es el contrato de evidencia de una **ejecución física real** de un runtime. Se sitúa después de `runtime-selection.v1` y antes de `runtime-benchmark.v1` / evidence bridge.

Flujo canónico:

```text
JALÓN 1
  ↓
CI verde
  ↓
MERGE #62
  ↓
JALÓN 2
  ↓
runtime-selection.v1
  ↓
runtime-execution.v1
  ↓
runtime físico
  ↓
llama.cpp
  ↓
benchmark real
  ↓
evidence real
```

El contrato **no ejecuta nada**. Define exactamente qué debe capturarse cuando la ejecución se haga en un host real, empezando por Debian con `llama.cpp`.

## Principios normativos

1. **Declaración ≠ ejecución.** Un registro de selección o un adapter declarativo nunca constituye evidencia de ejecución física.
2. **Estimación ≠ medición.** `estimated_tps` y cualquier predicción quedan fuera de `measurements` y nunca pueden promocionarse a evidencia medida.
3. **Una ejecución tiene identidad única.** `execution_id` debe acompañar al artefacto desde el inicio hasta la evidencia final.
4. **Todo resultado debe ser reproducible.** Modelo, revisión, cuantización, protocolo, runtime, hardware, comando y entorno deben quedar identificados.
5. **Los datos observados son inmutables conceptualmente.** El bridge puede transformar el formato, pero no inventar ni corregir mediciones.
6. **El fallo también es evidencia operacional.** Una ejecución fallida conserva identidad, comando, entorno y stdout/stderr para explicar por qué no produjo evidencia medida.
7. **Sin secretos.** No se almacenan tokens, credenciales, claves ni variables de entorno completas. Los prompts pueden referenciarse por hash o ID de protocolo en lugar de contener contenido sensible.
8. **No hay evidencia real sin host real.** CI puede validar el contrato, pero no puede sustituir una ejecución física.

## Estados

- `planned`: registro preparado, todavía no ejecutado.
- `running`: ejecución física iniciada.
- `completed`: proceso terminó correctamente y existe al menos una medición observada.
- `failed`: proceso terminó con error o no produjo una medición válida.
- `aborted`: ejecución detenida antes de completar el protocolo.

Solo `completed` puede entrar en `runtime-benchmark.v1` como medición y solo un benchmark completado y medido puede cruzar el evidence bridge existente.

## Identidad de ejecución

Obligatorios:

- `schema_version`
- `execution_id`
- `status`
- `created_at`
- `runtime.name`
- `runtime.adapter`
- `runtime.version`
- `model.id`
- `model.revision`
- `model.quantization`
- `hardware`
- `workload`
- `protocol`
- `command`
- `environment`

El `execution_id` debe ser UUID y no debe reutilizarse para otra ejecución.

## Modelo

La identidad del modelo debe separar:

- identificador lógico (`model.id`);
- revisión exacta (`model.revision`);
- artefacto utilizado (`model.artifact`);
- hash del artefacto cuando sea posible (`model.artifact_sha256`);
- cuantización (`model.quantization`).

Para GGUF, por ejemplo, el nombre del archivo no sustituye al hash del artefacto.

## Hardware y entorno

Se registra el hardware que realmente ejecutó la prueba:

- sistema operativo y versión;
- kernel;
- CPU y número de hilos disponibles;
- GPU(s), VRAM y driver cuando existan;
- RAM total/disponible al comenzar;
- backend utilizado por el runtime;
- versión exacta de llama.cpp u otro runtime;
- Python/Node/etc. solo si forman parte de la ruta de ejecución.

No se debe convertir una especificación declarada del hardware en una medición: las capacidades se identifican, las métricas de uso se observan.

## Comando

`command.argv` conserva los argumentos efectivos ejecutados, en orden.

Debe registrarse además:

- directorio de trabajo;
- código de salida;
- hash del comando serializado si se desea una identidad compacta;
- referencia a stdout/stderr y sus hashes cuando estén disponibles.

Los secretos deben eliminarse o redactarse antes de persistir el registro.

## Protocolo de benchmark

`protocol` debe identificar el protocolo congelado antes de la ejecución. Como mínimo:

- nombre/versión del protocolo;
- warm-up;
- número de iteraciones medidas;
- contexto;
- longitud objetivo de entrada/salida;
- concurrencia;
- batch si aplica;
- política de decoding y seed si aplica;
- identificador/hash del prompt o corpus utilizado;
- reglas de descarte y agregación.

El contenido completo del prompt no es obligatorio en el registro si existe una referencia reproducible por hash/ID.

## Mediciones observadas

`measurements` contiene exclusivamente valores obtenidos de la ejecución física. Entre las métricas previstas:

- `ttft_ms` — time to first token;
- `tpot_ms` — time per output token;
- `tokens_per_second` — velocidad observada;
- `output_tokens`;
- `total_latency_ms`;
- `peak_ram_mb`;
- `peak_vram_mb`;
- `avg_power_w` y/o `energy_wh` cuando exista instrumentación fiable;
- percentiles (`p50`, `p95`, `p99`) cuando el protocolo los calcule sobre observaciones válidas.

Las métricas no disponibles se omiten; no se rellenan con `null` como si hubieran sido medidas ni se sustituyen por estimaciones.

## Proveniencia

El registro debe permitir responder:

> ¿Qué se ejecutó, dónde, cuándo, con qué código, contra qué artefacto y bajo qué protocolo?

Por ello `provenance` incluye:

- commit/revisión de LEONES;
- timestamp de inicio y fin;
- host/runtime identity no sensible;
- hashes de artefactos relevantes;
- referencia al log bruto;
- `execution_id`.

## Reglas de promoción a evidencia

Una ejecución puede considerarse `measured` únicamente cuando:

- `status == completed`;
- el proceso terminó con código `0`;
- existe al menos una medición numérica observada;
- no hay `estimated_tps` dentro de `measurements`;
- runtime, adapter, modelo, revisión y cuantización están identificados;
- existe `execution_id` y timestamps;
- el comando y el entorno están registrados;
- el resultado puede vincularse a stdout/stderr o a una referencia equivalente de observación.

Estas reglas son deliberadamente más estrictas que «el programa arrancó».

## Relación con los contratos existentes

### `runtime-selection.v1`

Produce el plan autorizado: runtime + adapter + modelo + cuantización + hardware/workload compatibles. No produce evidencia física.

### `runtime-execution.v1`

Captura la ejecución física del plan autorizado y su observabilidad. Es la frontera entre **plan** y **hecho observado**.

### `runtime-benchmark.v1`

Consume la ejecución completada y organiza las mediciones para el benchmark. El contrato existente rechaza convertir `estimated_tps` en medición.

### Evidence bridge

Solo transforma un benchmark completado y medido en evidencia con procedencia. El bridge existente exige `measurement_status == measured`, `execution_id`, `finished_at`, identidad de runtime/adapter/modelo y una medición numérica.

## Primera ejecución: Debian + llama.cpp

El primer caso físico de JALÓN 2 será:

```text
runtime-selection.v1
        ↓
plan autorizado para llama.cpp
        ↓
runtime-execution.v1
        ↓
llama.cpp real en Debian
        ↓
observación de stdout/stderr + exit code
        ↓
TTFT / TPOT / tokens/s / memoria disponible
        ↓
runtime-benchmark.v1
        ↓
evidence bridge
```

No se considera completado JALÓN 2 por disponer del adapter, del comando esperado o de una estimación. Se completa cuando exista el primer `execution_id` con resultado físico verificable.

## No objetivos

- No descarga modelos automáticamente.
- No ejecuta runtimes.
- No inventa valores ausentes.
- No convierte especificaciones de hardware en rendimiento.
- No mezcla resultados estimados con mediciones.
- No permite que CI se presente como evidencia física.
- No obliga todavía a ejecutar vLLM, SGLang, MLX, ExLlama, OpenVINO, ONNX Runtime GenAI o TensorRT-LLM; esos quedan para la expansión física posterior.
