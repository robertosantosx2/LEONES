# Optimización de inferencia para hardware modesto

**Contrato:** `KNOWLEDGE-FICHA-CONTRACT.v1`  
**Papel:** capa previa al Selector de LLM  
**Estado:** `knowledge-contract-ready`

## 1. Qué es

Conjunto de runtimes y técnicas que pueden cambiar la viabilidad de un modelo cuando el hardware tiene memoria, VRAM, ancho de banda o capacidad de cómputo limitados.

LEONES no selecciona primero un modelo y después busca cómo ejecutarlo. El orden canónico es:

```text
caso de uso
→ requisitos funcionales
→ hardware real
→ runtime candidato
→ optimizaciones compatibles
→ Dense / MoE
→ estimadores
→ candidatos
→ selección
→ runtime-selection.v1
→ benchmark
→ medición LEONES
```

## 2. Familias

### QUANTIZATION
Reducir memoria y tráfico de memoria mediante menor precisión.

- GGUF / cuantizaciones de llama.cpp
- GPTQ
- AWQ
- BitNet / enfoques 1-bit

**Uso LEONES:** evaluar siempre junto con modelo, runtime, hardware y calidad; una cuantización no es intercambiable automáticamente entre runtimes.

### OFFLOAD / STREAMING
Evitar que todo el modelo deba residir simultáneamente en VRAM.

- AirLLM
- FlexGen
- CPU/GPU layer offload
- `mmap`
- layer streaming
- prefetch

**Uso LEONES:** especialmente relevante cuando el modelo supera la VRAM disponible pero existe RAM/almacenamiento y ancho de banda suficientes.

### SPARSE / MoE
Explotar sparsity, routing y localidad para reducir el trabajo efectivo.

- PowerInfer
- expert-aware execution
- expert offload

**Uso LEONES:** distinguir siempre parámetros totales de parámetros activos.

### CACHE / DECODING
Reducir memoria de contexto o aumentar throughput sin cambiar necesariamente el modelo objetivo.

- KV-cache quantization/compression
- speculative decoding

**Uso LEONES:** debe evaluarse según contexto, draft model, tasa de aceptación y workload.

### COMPILED / HARDWARE-SPECIFIC
Adaptar kernels, compilación y backend al dispositivo.

- llama.cpp backends
- MLC-LLM
- AVX2 / AVX512 / AMX
- CUDA / Vulkan / SYCL / Metal

**Uso LEONES:** el mismo modelo y cuantización pueden tener comportamientos radicalmente distintos según backend y kernels.

### DISTRIBUTED
Repartir modelo o inferencia entre varios dispositivos.

- Petals
- Exo

**Uso LEONES:** red, latencia, ancho de banda y sincronización forman parte de la configuración y del benchmark.

### EXPERIMENTAL
Proyectos o técnicas prometedoras que necesitan validación específica.

- LowMemoryLLM

**Uso LEONES:** fuente de descubrimiento; no elevar a evidencia fuerte por el mero hecho de existir.

## 3. Fuentes principales

| Fuente | Familia principal | Papel |
|---|---|---|
| AirLLM | OFFLOAD / STREAMING | runtime candidato para memoria limitada y modelos grandes |
| llama.cpp | QUANTIZATION / OFFLOAD / HARDWARE | baseline local y referencia de backends |
| PowerInfer | SPARSE / MoE | ejecución consciente de activación/sparsity |
| FlexGen | OFFLOAD / STREAMING | planificación de memoria y offload |
| Petals | DISTRIBUTED | modelos repartidos entre máquinas |
| BitNet | QUANTIZATION | baja precisión extrema, experimental según modelo/runtime |
| MLC-LLM | COMPILED / HARDWARE | compilación específica de dispositivo |
| Exo | DISTRIBUTED | agregación de dispositivos locales |
| LowMemoryLLM | EXPERIMENTAL | descubrimiento de técnicas de baja memoria |

Las URLs primarias y fichas individuales se mantienen en `web/data/inference-optimization.json` y en las fichas específicas de `docs/sources/`.

## 4. Dense frente a MoE

### Dense
Para la escala de selección:

`selection_parameters_m = total_parameters_m`

### MoE
Registrar simultáneamente:

- `total_parameters_m`: tamaño total, memoria y almacenamiento.
- `active_parameters_m`: parámetros activos por token, referencia del coste computacional.
- expertos activos, cuando la fuente/runtime los exponga.

Para la selección por escala computacional:

`selection_parameters_m = active_parameters_m`

Si no existe un valor activo verificable:

`MISSING_ACTIVE_PARAMS`

No se sustituye silenciosamente por el total.

## 5. La unidad real de selección

El candidato no es solamente `model_id`.

```text
modelo
+ arquitectura
+ total_parameters_m
+ active_parameters_m si MoE
+ cuantización
+ runtime
+ offload
+ estrategia KV/cache
+ decoding optimization
+ hardware
+ workload
```

Por eso AirLLM, llama.cpp, PowerInfer y las demás técnicas no son un apéndice posterior: pueden cambiar el conjunto de modelos que merece la pena evaluar.

## 6. Las cuatro capas de conocimiento

### FUENTE / DESCUBRIMIENTO
El proyecto, runtime o técnica existe y se identifica mediante su fuente primaria.

### EVIDENCIA
La fuente documenta mecanismos, compatibilidades o resultados. Se conserva el contexto y la versión cuando sea posible.

### ESTIMACIÓN
Predicciones externas de memoria, throughput, fit o speedup. Nunca se presentan como mediciones LEONES.

### MEDICIÓN LEONES
Solo procede de una ejecución controlada con el runtime seleccionado, executor, grader y benchmark.

En particular:

`estimated_tps != measured_tps`

## 7. Quality gates

Antes de promocionar una técnica o configuración:

1. identificar fuente primaria;
2. identificar modelo/versión y runtime;
3. registrar supuestos de hardware;
4. separar Dense/MoE;
5. registrar cuantización y contexto;
6. conservar claims externos como evidencia/estimación;
7. ejecutar la configuración en el pipeline controlado cuando proceda;
8. registrar `measured_*` solo tras ejecución real.

## 8. Integración con Selector de LLM

La capa de optimización debe producir restricciones y configuraciones compatibles; **no debe elegir por sí sola el modelo final**.

El selector recibe después las salidas de los seis estimadores y aplica su regla de candidatos por categoría:

- 6 modelos por estimador y categoría;
- texto, imagen y vídeo;
- 108 candidatos externos como máximo cuando los seis estimadores estén completos;
- tres representantes por categoría: menor, medio y mayor;
- Dense ordenado por `total_parameters_m`;
- MoE ordenado por `active_parameters_m`.

El resultado pasa a `runtime-selection.v1` para la decisión ejecutable y posteriormente a benchmark.
