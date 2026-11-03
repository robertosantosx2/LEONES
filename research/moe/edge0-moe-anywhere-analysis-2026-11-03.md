# Edge0 y moe-anywhere: análisis técnico y oportunidades de integración

**Fecha:** 2026-11-03  
**Ámbito:** Inferencia local de modelos sparse-MoE, offloading de expertos, predicción de routing y aceleración de TensorFold y runtimes relacionados.  
**Estado:** análisis documental de repositorios y benchmarks publicados; las propuestas de integración son hipótesis que requieren prototipo y medición.

## Resumen ejecutivo

Edge0 y moe-anywhere atacan partes complementarias del cuello de botella de inferencia MoE:

- **Edge0** combina streaming de pesos de expertos desde SSD, un *prerouter* entrenado que predice expertos del siguiente token y **Recover-LoRA** para recuperar calidad perdida por cuantización int4.
- **moe-anywhere** estudia caché de expertos en VRAM, predicción/pre-gating y prefetch, además de una ruta híbrida CPU/GPU para fallos de caché en llama.cpp.
- Para **TensorFold**, lo más transferible no es copiar ninguno de los runtimes, sino incorporar mecanismos desacoplados: índices de expertos, predicción anticipada, caché multinivel, scheduler por coste, admission control y telemetría.
- Para **tandem.cpp**, moe-anywhere aporta políticas y evaluación de caché; Edge0 aporta la idea de anticipar el routing para ocultar latencia de almacenamiento.
- **InferSSD** sigue siendo el candidato más cercano a Edge0 en streaming desde SSD. Edge0 añade una dimensión importante: predicción aprendida del routing y adaptación LoRA de recuperación de calidad.

## 1. Edge0

Repositorio: https://github.com/menonpg/edge0  
Organización: https://github.com/Edge0-AI/Edge0  
Informe técnico: https://arxiv.org/abs/2609.XXXXX (verificar identificador definitivo en el repositorio antes de citar en publicaciones externas)  
Página de investigación: https://edge0.ai/research/edge0

### Qué hace

Edge0 es un framework de inferencia MoE en streaming. Su tesis es que la memoria pico debe depender del conjunto de expertos activos y no del tamaño total de parámetros.

Su receta principal combina:

1. **SSD expert offload.** Los expertos se leen desde almacenamiento cuando se necesitan. El sistema evita tener todos los pesos de expertos residentes en RAM o VRAM.
2. **Prerouter / routing prediction.** Una cabeza entrenada predice el conjunto de expertos del siguiente token. La carga puede comenzar mientras se ejecuta el token actual, solapando lectura y cómputo.
3. **Recover-LoRA.** La base cuantizada int4 permanece congelada. Adaptadores LoRA entrenados por destilación desde un teacher de precisión completa compensan parte de la pérdida de calidad.
4. **Adaptadores no fusionados.** El modelo base de solo lectura puede servir a distintos conjuntos de LoRA sin duplicar ni reescribir los pesos base.
5. **Separación de backend.** En el framework Python, la lógica de modelos, streaming, routing y servidor se abstrae de MLX. CUDA aparece como backend reservado en la arquitectura, pero no debe confundirse con soporte CUDA ya operativo en el framework Python.

### Diseño interno destacado

La arquitectura organiza módulos separados para:

- especificación de modelo, layout y cuantización MoE;
- streaming de expertos por capa;
- acceso mmap a rangos de archivos safetensors;
- caché compartida LRU entre capas;
- prerouter, staging y doble buffer;
- loop de inferencia y adapters LoRA;
- servidor HTTP compatible con OpenAI.

Durante decode, las predicciones del prerouter se colocan en slots doblemente bufferizados. La capa de expertos usa gather cuantizado y actualiza slots sin reconstruir repetidamente grandes estructuras de tensores. Esta implementación está ligada a MLX en la versión Python actual.

### Modelos y benchmarks publicados

Edge0 publica dos pipelines completos con checkpoint base y adapters entrenados:

| Tier | Base | Perfil |
|---|---|---|
| edge0-35b | Qwen3.6-35B-A3B | int4, 40 capas, 256 expertos, K=4 |
| edge0-8b | Ling 3.0 híbrido | int4, 24 capas, 128 expertos, K=8 |

Benchmarks del equipo, en Mac mini M4 Pro de 24 GB:

| Modelo | Decode | Prefill frío / caliente | Memoria activa pico |
|---|---:|---:|---:|
| Edge0-35B-A3B | 14,9–17,7 tok/s | 113 / 140 tok/s | 2,9 GiB |
| Edge0-8B-A1B | 23,9–25,3 tok/s | 500 / 1428 tok/s | 1,0 GiB |

El repositorio reporta hasta **+59% de throughput de decode** por prerouter en determinados escenarios. Es un resultado del autor y no debe extrapolarse a TensorFold, CUDA o la RTX 3050 del MSI sin benchmark propio.

Evaluación de calidad publicada (OpenCompass, escala 0–100):

| Modelo | Edge0 int4 + adapters | Base fp16 | Diferencia media |
|---|---:|---:|---:|
| Edge0-35B | 79,2 | 83,2 | −4,0 |
| Edge0-8B | 69,9 | 72,7 | −2,8 |

### Qué puede aportar a TensorFold

**Prioridad alta — prerouter y prefetch**
- Predecir expertos del siguiente token a partir de estados disponibles del token actual.
- Lanzar lectura/copia asíncrona de expertos en un buffer alternativo.
- Medir recall@K del predictor, tasa de aciertos útiles, bytes precargados que no se usan y latencia oculta.
- Introducir fallback exacto: una predicción incorrecta no debe alterar el routing ni la distribución del modelo target.

**Prioridad alta — doble buffering**
- Separar el buffer de expertos que está consumiendo el kernel del que se prepara para el siguiente paso.
- Evitar sincronizaciones globales; establecer eventos y dependencias por capa.
- Evaluar si la memoria reservada adicional se compensa con menor tiempo ocioso de GPU.

**Prioridad media — arquitectura de streaming**
- Índices por rangos de bytes de tensores expertos, sin duplicar el archivo.
- Caché compartida entre capas con políticas y presupuestos explícitos.
- Lectura de expertos por demanda y manejo de expertos calientes.

**Prioridad media/experimental — Recover-LoRA**
- Investigar si una LoRA destilada puede recuperar calidad de una cuantización agresiva que haga viable un modelo en 4 GB de VRAM.
- Esto requiere entrenamiento, dataset, teacher y evaluación; no es una optimización puramente de runtime.
- No asumir que los adapters Edge0 se pueden reutilizar con otras bases, cuantizaciones, arquitecturas o motores.

### Límites y riesgos

- La ruta Python pública es MLX/Apple Silicon; backend CUDA está reservado, no implementado en ese framework según la arquitectura consultada.
- El prerouter requiere entrenamiento específico por modelo, capa y configuración de routing.
- Un predictor con recall alto puede ser ineficiente si precarga demasiados expertos o consume la VRAM que necesita el modelo.
- La calidad de int4 depende de adapters y checkpoint emparejados.
- Los números publicados proceden de hardware Apple Silicon; no equivalen a rendimiento en NVIDIA.

## 2. moe-anywhere

Repositorio: https://github.com/carl0sfelipe/moe-anywhere  
Experimentos: https://github.com/carl0sfelipe/moe-anywhere/blob/main/research/experiments.md

### Qué hace

moe-anywhere es un laboratorio basado en llama.cpp para ejecutar MoE sparse en GPU de consumo mediante offloading, caché de expertos y prefetch. No intenta inicialmente reemplazar todo el runtime: añade mecanismos experimentales al flujo existente.

### Mecanismos principales

1. **Expert offloading CPU/GPU.** Los expertos pueden residir en RAM y se ejecutan o transfieren según el placement.
2. **Caché de expertos en VRAM.** Conserva expertos frecuentes, con políticas como LRU y caché de tamaño explícito.
3. **Pre-gating.** Ejecuta anticipadamente el router de una capa futura usando activaciones disponibles de la capa anterior, para estimar qué expertos serán necesarios.
4. **Prefetch asíncrono.** Carga candidatos mientras se ejecuta el trabajo actual.
5. **Ruta híbrida de caché.** En su patch de llama.cpp, un miss puede procesarse por CPU mientras GPU continúa con expertos residentes, en vez de serializar todo el paso.
6. **Trazas de routing.** Propone registrar (capa, token, top-k expertos) y construir datasets para evaluar predictores en horizontes de 1, 2 y 3 tokens.

### Resultados publicados

Experimentos con **Sage-A1.5 (Qwen3.6-35B-A3B, 256 expertos por capa, top-8)**:

| Experimento | GPU / RAM | Decode publicado |
|---|---|---:|
| llama.cpp baseline, expertos en CPU | RTX 5050 8 GB + 31 GB RAM | 41,05 tok/s |
| caché VRAM + load-mode none | RTX 5050 8 GB + 31 GB RAM | 52,1 tok/s |
| caché híbrida CPU/GPU | RTX 5050 8 GB + 31 GB RAM | 55,1 tok/s |
| híbrida, sistema distinto | RTX 5050 + Ryzen 7 7800X3D + 30 GB DDR5 | 61,5 tok/s |

La página de experimentos informa:

- El pre-gating de la capa L+1 sobre la salida de L recupera **82%** de los expertos de la siguiente capa (96% con 16 candidatos).
- LRU con 64 de 256 expertos por capa en VRAM (~4,9 GB) captura **79%** de selecciones.
- Los valores son para RTX 5050 de 8 GB y sistema con ~30 GB RAM. No son estimaciones para una RTX 3050 de 4 GB.

### Qué puede aportar a TensorFold

**Prioridad alta — caché y política de placement**
- Comparar LRU, frecuencia, recencia, predicción de siguiente capa y pre-gating.
- Medir recall de caché por capa y por experto, no solo hit-rate global.
- Reservar VRAM después de descontar pesos densos, KV cache, buffers de cómputo y margen de seguridad.
- Un límite configurable en MiB y una política de eviction explícita son preferibles a asignaciones que compiten de forma opaca por VRAM.

**Prioridad alta — ejecución CPU/GPU concurrente**
- En cache miss, decidir si conviene transferir experto a GPU o ejecutarlo en CPU.
- Mantener GPU ocupada con expertos residentes mientras CPU resuelve otros expertos, cuando el grafo y la semántica lo permitan.
- Scheduler basado en coste: latencia CPU del experto vs. transferencia PCIe + ejecución GPU.
- Medir el cuello real: CPU, ancho de banda PCIe, SSD, kernel GPU, sincronizaciones.

**Prioridad alta — routing traces y benchmark**
- Dataset de routing reproducible para modelos, prompts y configuraciones concretas.
- Evaluar predictor en recall@K y horizonte, pero también en bytes leídos, falsos prefetch, ocupación VRAM y tok/s.
- Reproducir baseline y cada patch en la misma revisión de llama.cpp.

**Prioridad media — diseño de caché híbrida**
- Investigar si el miss híbrido de moe-anywhere se puede convertir en un módulo independiente, en vez de un patch invasivo al runtime.
- Integrarlo con el gestor de memoria y las mejoras de admission/reclaim de TensorFold, especialmente PR #1879.

### Qué puede aportar a tandem.cpp

La sinergia es directa: tandem ya plantea expertos en RAM, caché GPU y solapamiento CPU/GPU/PCIe. moe-anywhere puede aportar:

- evaluación sistemática de predictores y políticas;
- routing traces;
- pre-gating;
- métricas hit/miss y recall;
- selección adaptativa de caché;
- una ruta híbrida alternativa de misses.

La integración debe preservar el split adaptativo de tandem y no asumir que los resultados de moe-anywhere en RTX 5050 escalan linealmente a RTX 3050.

### Límites y riesgos

- Es un laboratorio de llama.cpp y algunos resultados requieren aplicar patches a commits específicos.
- Los resultados se miden con RTX 5050 8 GB y mucha más RAM que el MSI.
- Pre-gating puede precargar expertos equivocados; un recall alto no implica necesariamente ganancia de throughput.
- La caché de 4,9–5,1 GiB publicada no cabe en la GPU de 4 GiB del usuario; se deben explorar tamaños inferiores y políticas híbridas.

## 3. Comparación rápida

| Capacidad | Edge0 | moe-anywhere | InferSSD | tandem.cpp |
|---|---|---|---|---|
| SSD streaming | Central | No es su foco principal actual | Central | No central |
| Predicción aprendida del routing | Prerouter entrenado | Pre-gating / predictores experimentales | Scheduler/prefetch | No central |
| Caché VRAM | Buffers y caché streaming | Central | GPU expert cache | Central |
| Expertos CPU | Menos central en el framework Python MLX actual | CPU fallback/híbrido | CPU sink | CPU execution |
| LoRA recuperación cuantización | Recover-LoRA central | No central | No central | No central |
| Dataset de routing | Implícito en entrenamiento del predictor | Roadmap explícita | Telemetría/runtime | Benchmarking posible |
| Backend portable | Diseño modular; engines por plataforma | llama.cpp | runtime propio/fork | patch llama.cpp |
| Portabilidad directa a TensorFold | Algoritmos, no runtime MLX | Algoritmos/patches, no runtime completo | Módulos de IO/cache/scheduler | Ideas de scheduling |

## 4. Propuesta de arquitectura para TensorFold

Una arquitectura experimental modular podría separar:

1. **ExpertStore**: índice de offsets/layout, validación de modelo y lectura SSD/RAM.
2. **ExpertCache**: niveles RAM y VRAM, presupuesto, LRU/frequency/predictive.
3. **RoutingPredictor**: pre-gating heurístico inicial; predictor entrenado como backend opcional.
4. **PrefetchScheduler**: cola asíncrona, doble buffer, cancelación y prioridades.
5. **PlacementScheduler**: CPU vs. GPU según coste medido y disponibilidad.
6. **MemoryAdmission/Reclaimer**: integración con límites y recuperación de memoria del PR #1879.
7. **Telemetry**: hit/miss, recall@K, bytes SSD/PCIe, tiempo CPU/GPU, falsos prefetch, VRAM/RAM pico, tok/s y latencia de primer token.
8. **Speculative interface**: UBTree/otros métodos como módulo separado; el árbol debe incluir el coste adicional de expertos y KV.

### Orden de experimentación recomendado

**Fase A — baseline TensorFold**
- Qwen3-30B-A3B-2507 con PR #1879.
- Medir carga, prefill, TTFT, decode tok/s, RAM/VRAM, errores y estabilidad.

**Fase B — caché/prefetch sin predictor aprendido**
- LRU y frecuencia.
- Pre-gating de siguiente capa.
- Tamaños de caché pequeños compatibles con 4 GiB.
- Métricas de recall y falsos prefetch.

**Fase C — CPU/GPU concurrente**
- Evaluar expertos en CPU en paralelo con expertos GPU.
- Medir cuándo transferir es más lento que ejecutar en CPU.
- Incorporar admission/reclaim.

**Fase D — SSD streaming**
- Si el modelo no cabe en RAM, streaming por rangos y lectura asíncrona.
- Medir latencia del SSD del MSI y rendimiento real; no extrapolar de PCIe 4/5.

**Fase E — predictor entrenado / Recover-LoRA**
- Solo cuando haya traces suficientes y un baseline robusto.
- Entrenamiento y evaluación independiente; conservar fallback exacto.

## 5. Fuentes

- Edge0 README: https://github.com/menonpg/edge0
- Edge0 arquitectura: https://github.com/Edge0-AI/Edge0/blob/main/docs/architecture.md
- Edge0 README en español: https://github.com/Edge0-AI/Edge0/blob/main/README_es.md
- Edge0 artículo técnico: https://edge0.ai/research/edge0
- moe-anywhere README y resultados: https://github.com/carl0sfelipe/moe-anywhere
- moe-anywhere experimentos: https://github.com/carl0sfelipe/moe-anywhere/blob/main/research/experiments.md

## Conclusión

**Edge0** aporta principalmente *anticipación*: predicción aprendida, staging y recuperación de calidad int4.  
**moe-anywhere** aporta principalmente *observabilidad y scheduling*: trazas, pre-gating, caché GPU, evaluación de políticas y misses híbridos.  
**InferSSD** aporta *streaming multinivel SSD/RAM/GPU*.  
**tandem.cpp** aporta *ejecución concurrente CPU/GPU y split adaptativo*.

La oportunidad para TensorFold es combinar estas ideas en módulos propios y medibles, sin convertirlo en un fork de llama.cpp o MLX. En el MSI, el objetivo inicial debe ser demostrar una mejora estable con caché pequeña y uso híbrido, antes de plantear SSD streaming o speculative trees.
