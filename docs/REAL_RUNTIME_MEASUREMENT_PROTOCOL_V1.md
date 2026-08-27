# Protocolo de medición real V1

## 1. Objetivo

Medir rendimiento físico de un LLM/runtimes de forma comparable y auditable, sin convertir estimaciones externas en resultados LEONES.

La referencia metodológica de la serie LLM indica que la velocidad depende de memoria, ancho de banda, runtime y forma de carga; distingue prefill de decode y recomienda medir TTFT, TPOT, tokens/s, memoria, hardware, runtime/version y workload. fileciteturn0file0L230-L414

## 2. Regla de congelación

Antes de ejecutar la medición final quedan congelados:

- modelo y revisión;
- artefacto y hash;
- cuantización y formato;
- runtime y versión objetivo;
- backend;
- hardware;
- contexto;
- prompt/protocolo;
- plantilla de chat;
- parámetros de decodificación;
- warm-up;
- número de iteraciones;
- concurrencia;
- métricas;
- método de agregación.

Después de observar los resultados finales no se cambia el protocolo y se sigue llamando a esa misma prueba "limpia". La fuente de referencia exige separar desarrollo y prueba final y congelar el protocolo antes de la medición final. fileciteturn0file0L1172-L1207

## 3. Primera prueba física: single-user decode

Para el primer salto de llama.cpp en Debian:

- concurrencia: `1`;
- prompt estable y versionado;
- contexto fijado;
- salida objetivo fija;
- decodificación fija;
- warm-up: `3` ejecuciones;
- mediciones: `10` ejecuciones;
- agregación principal: mediana;
- conservar también cada muestra individual.

La primera prueba no pretende ser un benchmark universal. Es el **baseline físico LEONES** del host, modelo y runtime exactos.

## 4. Workload

El workload debe separar explícitamente:

### A. Decode-oriented

Prompt relativamente corto + generación larga. Sirve para observar el comportamiento de decodificación y el impacto del ancho de banda.

### B. Prefill-oriented

Prompt largo + generación corta. Sirve para observar TTFT y coste de prellenado.

### C. Context growth

Mismo prompt base con varios tamaños de contexto predefinidos. Solo se ejecuta cuando el primer baseline sea estable.

### D. Serving/concurrency

Se reserva para la fase posterior. No mezclar single-user y serving en una misma métrica.

La distinción prefill/decode es esencial: el prefill es más intensivo en cómputo y condiciona TTFT; el decode genera tokens secuencialmente y suele estar limitado por ancho de banda de memoria. fileciteturn0file0L302-L337

## 5. Métricas obligatorias

### Tiempo

- TTFT: tiempo desde el envío de la solicitud hasta el primer token observado.
- TPOT: tiempo medio por token después del primero.
- tokens/s: tokens de salida / tiempo de generación.
- wall time total.

No sustituir TTFT por tiempo total. No presentar tokens/s sin especificar si incluye prefill.

### Memoria

- RAM inicial y pico si se puede observar.
- VRAM inicial y pico si existe GPU.
- memoria del runtime si el runtime la reporta de forma fiable.

### Sistema

- CPU;
- GPU;
- VRAM;
- RAM;
- OS/kernel;
- backend;
- versión exacta del runtime;
- versión del driver cuando aplique;
- ancho de banda de memoria cuando esté documentado para el hardware.

### Energía

Registrar potencia solo cuando exista un contador fiable. Si no está disponible: `unavailable`, nunca estimar silenciosamente.

## 6. Protocolo de ejecución

### Fase 0 — identidad

1. Crear `execution_id`.
2. Registrar commit de LEONES.
3. Registrar hash de la selección.
4. Registrar modelo/revisión/cuanti/formato.
5. Calcular hash del artefacto.
6. Registrar runtime/version/backend.
7. Registrar fingerprint del host.

### Fase 1 — preflight

Comprobar sin medir:

- runtime disponible;
- versión correcta;
- backend correcto;
- modelo accesible;
- hash correcto;
- memoria disponible;
- dispositivo esperado;
- comando autorizado;
- puerto disponible si es servidor;
- herramientas de medición disponibles.

Si falla un requisito: **no medir**. Crear ejecución `failed`/`aborted` con evidencia del preflight.

### Fase 2 — warm-up

Ejecutar 3 veces con exactamente el mismo workload.

No incluir warm-up en las estadísticas finales.

El objetivo es eliminar la distorsión inicial por carga de modelo, compilación de kernels, cachés y inicialización del runtime.

### Fase 3 — medición

Ejecutar 10 veces con el protocolo congelado.

Conservar cada resultado individual, no solo la mediana.

Para cada muestra:

- timestamp;
- TTFT;
- TPOT;
- tokens/s;
- input/output tokens;
- memoria;
- potencia si existe;
- exit code;
- hashes de stdout/stderr.

### Fase 4 — agregación

Calcular:

- mediana;
- media;
- mínimo/máximo;
- desviación estándar cuando tenga sentido;
- p50/p95/p99 cuando haya suficientes observaciones para que sean informativos.

La métrica publicada como baseline será la mediana de las ejecuciones válidas, acompañada por `n` y por las muestras individuales.

## 7. Reglas de validez

Una muestra es válida solo si:

- el proceso terminó correctamente;
- produjo la salida esperada;
- no hubo OOM;
- no hubo error de backend;
- no hubo cambio de modelo/runtime;
- no se modificó el workload;
- los contadores de tokens son coherentes;
- stdout/stderr fueron conservados.

Un fallo no se elimina del registro: se conserva como muestra fallida y se explica por qué no entra en la agregación.

## 8. Qué NO hacer

- No comparar dos runtimes con modelos/cuants diferentes.
- No cambiar el prompt entre runtimes.
- No medir una vez y publicar ese número como verdad general.
- No mezclar estimaciones de llmfit, Artificial Analysis u otras fuentes con mediciones LEONES.
- No usar screenshots como único soporte.
- No borrar ejecuciones lentas o fallidas.
- No ocultar OOM.
- No cambiar flags después de ver el resultado y reutilizar el mismo protocolo.

La fuente de referencia insiste en que entrenar, ajustar prompts o seleccionar contra una prueba final contamina la comparación; por extensión, el protocolo físico de LEONES debe congelarse antes de la medición final. fileciteturn0file0L1172-L1207

## 9. Artefactos que se conservan

Por cada ejecución:

```text
artifacts/runtime-executions/<execution_id>/
  execution.json
  selection.json
  command.json
  stdout.txt
  stderr.txt
  host.json
  model-manifest.json
  samples.jsonl
```

Opcionalmente:

```text
  power.csv
  gpu-metrics.csv
  profiler.json
```

El `execution.json` debe ser conforme a `runtime-execution.v1`.

## 10. Cadena de evidencia

```text
modelo/revisión/hash
        ↓
selection_plan_hash
        ↓
runtime-execution.v1
        ↓
raw stdout/stderr
        ↓
observed metrics
        ↓
runtime-benchmark.v1
        ↓
evidence
        ↓
recommendation / Atlas
```

Nunca se permite el camino:

```text
benchmark externo → measured_tps
```

Los benchmarks externos son conocimiento/evidencia externa para selección, no observación física de LEONES.

## 11. Criterio de comparación

Dos resultados son directamente comparables solo si coinciden en:

- mismo modelo ID;
- misma revisión;
- mismo artefacto/hash;
- misma cuantización/formato;
- mismo workload;
- mismo contexto;
- mismos parámetros de decodificación;
- misma definición de tokens/s;
- misma clase de medición;
- y hardware suficientemente identificado.

Si cambia el hardware, runtime, versión, cuanti, contexto o workload, se crea una nueva serie de medición.

## 12. Secuencia Debian

Cuando se retome el trabajo físico:

```text
CI verde
  ↓
MERGE #62
  ↓
Debian preflight
  ↓
llama.cpp
  ↓
execution_id
  ↓
warm-up ×3
  ↓
measure ×10
  ↓
execution.json + raw evidence
  ↓
validate schema
  ↓
runtime-benchmark.v1
  ↓
evidence
```

Después de cerrar el baseline de llama.cpp, se reutiliza exactamente el mismo protocolo para los runtimes compatibles. Solo cambia la dimensión que se está comparando; no se rediseña la evidencia.
