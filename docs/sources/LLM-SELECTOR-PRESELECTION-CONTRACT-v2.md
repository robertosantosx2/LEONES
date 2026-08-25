# Selector de LLM — contrato de preselección v2

## Principio
El Selector de LLM **no empieza por comparar modelos**. Primero debe conocer el caso de uso del usuario y el perfil real de hardware. Después decide una combinación viable de runtime de inferencia y técnicas de optimización. Solo entonces consulta los estimadores y valora candidatos.

## Orden obligatorio

```text
Caso de uso del usuario
        ↓
Requisitos funcionales
        ↓
Perfil HW real
        ↓
Runtime de inferencia candidato
        ↓
Técnicas de optimización
        ↓
Estimadores Fit / CanIRun
        ↓
6 modelos por categoría y estimador
        ↓
normalización Dense/MoE
        ↓
3 representantes por categoría
        ↓
runtime-selection.v1
        ↓
benchmark / medición LEONES
```

No se permite invertir este orden y seleccionar primero un modelo para decidir después cómo ejecutarlo.

## Caso de uso
El selector debe capturar, como mínimo:
- categoría: `text`, `image`, `video`;
- tarea concreta;
- necesidad de razonamiento/coding/RAG/visión/generación de vídeo, etc.;
- interacción o batch;
- latencia objetivo;
- contexto objetivo;
- calidad mínima;
- concurrencia;
- restricciones de privacidad/offline;
- límites de almacenamiento/energía/tiempo.

El caso de uso condiciona qué modelos son candidatos y qué benchmark será válido.

## Hardware
Debe utilizarse el hardware real o un perfil declarado:
- CPU y arquitectura;
- RAM;
- GPU(s), VRAM y número de dispositivos;
- ancho de banda relevante;
- almacenamiento y rendimiento I/O;
- SO/driver cuando afecten al runtime.

## Runtime antes del modelo
El selector debe determinar primero uno o varios `runtime_plan` compatibles con HW + workload. Ejemplos de familias: llama.cpp, vLLM, SGLang, MLX-LM, TensorRT-LLM, AirLLM, Lemonade u otros runtimes verificados por LEONES.

El runtime no es un atributo decorativo del modelo: cambia memoria, offload, throughput, latencia, compatibilidad y técnicas disponibles.

## Técnicas de optimización
El plan puede incluir, según HW/runtime/modelo:
- cuantización;
- CPU/GPU offload;
- layer-wise loading;
- prefetching;
- paged KV cache;
- tensor/pipeline parallelism;
- speculative decoding;
- MTP/DFlash cuando esté soportado;
- contexto/KV optimizado;
- batching/concurrencia;
- compilación/backend específico.

Cada técnica debe registrarse como `candidate_optimization`, con compatibilidad y evidencia separadas.

## Dense vs MoE
No se puede ordenar Dense y MoE únicamente por parámetros totales.

### Dense
Para un Dense se conserva:
- `total_parameters_m` como magnitud principal;
- memoria de pesos;
- memoria KV/activaciones;
- requisitos del runtime;
- rendimiento estimado/medido.

### MoE
Para un MoE se deben conservar **dos magnitudes distintas**:
- `total_parameters_m` — tamaño total del modelo;
- `active_parameters_m` — parámetros activados por token/forward según la arquitectura y configuración.

Para la **selección por tamaño representativo del Selector**, los MoE se ordenan por `active_parameters_m`, no por `total_parameters_m`, siempre que el dato sea verificable.

`total_parameters_m` permanece visible porque determina almacenamiento, pesos y otros costes, pero no sustituye a `active_parameters_m` para comparar capacidad computacional por token.

Si `active_parameters_m` no está disponible o no es verificable, el candidato MoE queda como `MISSING_ACTIVE_PARAMS` y no debe mezclarse silenciosamente con Dense en la ordenación principal.

## AirLLM y MoE
AirLLM debe considerarse una opción de runtime/optimización **antes de valorar el candidato**, especialmente cuando el hardware tiene memoria limitada y el modelo exige offload/layer-wise execution. La ficha de AirLLM ya establece que es runtime y que los MoE requieren medición específica por los costes de transferencia/routing. fileciteturn59file0

Esto no significa que AirLLM sea automáticamente mejor para todos los MoE. Significa que el selector debe poder evaluar el par:

`modelo + runtime + técnicas`

y no únicamente `modelo`.

## Salida de los estimadores
Cada estimador debe devolver exactamente **6 modelos por cada categoría**:
- 6 texto;
- 6 imagen;
- 6 vídeo.

Con 6 estimadores: `6 × 3 × 6 = 108` candidatos externos.

Cada candidato debe incluir, cuando aplique:
- `category`;
- `model_id`;
- `architecture_class`: `dense` | `moe`;
- `total_parameters_m`;
- `active_parameters_m` para MoE;
- cuantización;
- runtime recomendado/compatible;
- optimizaciones;
- fit;
- memoria estimada;
- throughput estimado;
- fuente y versión/fecha.

## Reducción
Después de fijar **caso de uso + HW + runtime + optimizaciones**, el Selector conserva 3 por categoría:

- menor;
- medio;
- mayor.

La magnitud de ordenación es:
- Dense → `total_parameters_m`;
- MoE → `active_parameters_m`.

No se mezclan ambas métricas en un mismo eje sin marcar la arquitectura.

## Medición
Los 3 representantes por categoría son candidatos. No son recomendaciones finales.

La promoción requiere:

`runtime_plan + optimization_plan + candidate + benchmark válido → measured evidence`

y debe conservar `measured_*` separado de `estimated_*`.

## Resultado
El Selector deja de ser un simple filtro de modelos y pasa a ser un **selector de configuración de inferencia**:

`use case + HW + runtime + optimization + model`.

Este es el objeto que posteriormente debe entregar `runtime-selection.v1` al executor.