# Selector de LLM — contrato de preselección v2

## Principio
El Selector de LLM no empieza por comparar modelos. Primero debe conocer el caso de uso del usuario y el perfil real de hardware. Después decide una combinación viable de runtime de inferencia y técnicas de optimización. Solo entonces consulta los estimadores y valora candidatos.

## Orden obligatorio

```text
Caso de uso del usuario
        ↓
Requisitos funcionales
        ↓
Perfil HW real
        ↓
Runtime de inferencia
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
- necesidad de razonamiento/coding/RAG/visión/generación de vídeo;
- interacción o batch;
- latencia objetivo;
- contexto objetivo;
- calidad mínima;
- concurrencia;
- privacidad/offline;
- límites de almacenamiento, energía y tiempo.

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
El selector debe determinar primero un `runtime_plan` compatible con HW + workload. El runtime no es un atributo decorativo del modelo: cambia memoria, offload, throughput, latencia, compatibilidad y técnicas disponibles.

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
Se conserva `total_parameters_m` como magnitud principal, además de memoria, KV/activaciones, requisitos del runtime y rendimiento estimado/medido.

### MoE
Se conservan dos magnitudes:
- `total_parameters_m`: tamaño total del modelo, memoria y almacenamiento;
- `active_parameters_m`: parámetros activados por token/forward según arquitectura y configuración.

Para la selección por tamaño representativo, los MoE se ordenan por `active_parameters_m`, siempre que el dato sea verificable. Si falta, el candidato queda como `MISSING_ACTIVE_PARAMS` y no se sustituye silenciosamente por el total.

## AirLLM y MoE
AirLLM debe poder aparecer como runtime/optimización antes de valorar el candidato, especialmente cuando la memoria es limitada y se necesita ejecución por capas/offload. No se presupone que sea mejor para todos los MoE: LEONES debe comparar la configuración completa y medir transferencia, routing, memoria y rendimiento.

## Salida de los estimadores
Cada uno de los seis estimadores debe devolver exactamente:
- 6 modelos de texto;
- 6 modelos de imagen;
- 6 modelos de vídeo.

Con seis estimadores: `6 × 3 × 6 = 108` observaciones externas.

Cada candidato debe incluir, cuando aplique:
- `category`;
- `model_id`;
- `architecture_class`: `dense` | `moe`;
- `total_parameters_m`;
- `active_parameters_m` para MoE;
- cuantización;
- runtime compatible;
- optimizaciones;
- fit;
- memoria estimada;
- throughput estimado;
- fuente y versión/fecha.

Una salida incompleta de un estimador no se rellena artificialmente.

## Reducción
Después de fijar caso de uso + HW + runtime + optimizaciones, el Selector toma la unión de los candidatos válidos de cada categoría, elimina duplicados por identidad y conserva:

- menor;
- medio: elemento central inferior si el conjunto es par;
- mayor.

Resultado normal: **3 texto + 3 imagen + 3 vídeo = 9 candidatos**.

Magnitud de ordenación:
- Dense → `total_parameters_m`;
- MoE → `active_parameters_m`.

## Medición
Los nueve representantes son candidatos, no recomendaciones finales. La promoción requiere:

`runtime_plan + optimization_plan + candidate + benchmark válido → measured evidence`

Los `estimated_*` externos permanecen separados de `measured_*` de LEONES.

## Resultado
El Selector pasa de ser un simple filtro de modelos a un **selector de configuración de inferencia**:

`use case + HW + runtime + optimization + model`.

Este objeto es el que debe entregar `runtime-selection.v1` al executor.