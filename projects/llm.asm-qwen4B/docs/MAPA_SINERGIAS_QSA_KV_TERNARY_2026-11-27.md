# Mapa de sinergias: QSA, atención dispersa, KV-cache y cuantización extrema

**Fecha de prospección:** 2026-11-27  
**Ámbito:** LEONES / `projects/llm.asm-qwen4B` / investigación transversal para llm.asm  
**Estado:** investigación documental; no implica código integrado, compatibilidad implementada ni benchmark físico.  
**Plataforma de referencia:** MSI Thin 15 B12UC, i7-12650H, RTX 3050 Laptop 4 GiB, 14 GiB RAM, Ubuntu, CUDA SM86.

## 1. Resumen ejecutivo

La oportunidad no consiste en portar un único kernel QSA. Hay cinco palancas distintas que conviene mantener separadas y después combinar:

1. **Reducir cómputo/lecturas de atención:** QSA, Quest, MInference, DuoAttention.
2. **Reducir memoria persistente KV:** KIVI, TurboQuant+, SnapKV y políticas de cache eviction/streaming.
3. **Reducir bytes de pesos y coste de GEMM:** Ternary Bonsai/PTQ1_0, BitNet.cpp, OpenBonsai, ik_llama.cpp.
4. **Aprovechar arquitecturas híbridas:** Gated DeltaNet / Flash Linear Attention más capas de atención selectiva.
5. **Acelerar generación:** MTP y speculative decoding; no confundir este efecto con ahorro de memoria o mejora de prefill.

**Hallazgo crítico para el diseño:** QSA, por sí sola, no elimina las entradas de la KV-cache ni reduce necesariamente su asignación. Su selector reduce los bloques que se leen/atienden en cada paso. En Bonsai-QSA, la huella de KV también se beneficia de que 48 capas son Gated DeltaNet recurrentes y solo 16 capas mantienen KV de atención completa. Por tanto, QSA (menos tráfico/cómputo) y KV quantization/offload (menos memoria residente) son técnicas complementarias, no intercambiables.

En el MSI, CUDA SM86 permite estudiar kernels compatibles, pero 4 GiB VRAM descarta reproducir los perfiles de 27B QSA a 128K–256K publicados para GPUs de 16–24 GiB. La ruta útil para el MSI es validar piezas aisladas con modelos pequeños, CPU y contextos cortos; los perfiles grandes quedan como diseño escalable para hardware futuro.

## 2. Proyectos principales y líneas de sinergia

### A. QSA y adaptaciones Qwen 3.8 / Bonsai

| Proyecto | Qué aporta | Sinergia propuesta | Estado para MSI |
|---|---|---|---|
| [PrismML-Eng/llama.cpp](https://github.com/PrismML-Eng/llama.cpp) | Runtime Prism para cuantizaciones Bonsai/PTQ1_0; base de integración del parche QSA citado por la publicación original. | Referencia primaria para estudiar formato, kernels y ABI; fijar commit y comparar cambios frente a upstream. | Compilar SM86 solo como gate documental/build; no asumir que el GGUF cabe en VRAM. |
| [Qwen3.8-27B-QSA-llama.cpp](https://github.com/kuraneko1/Qwen3.8-27B-QSA-llama.cpp) | Runtime específico QSA con indexers, MTP, multimodalidad y reutilización de prefijo. | Comparar arquitectura del kernel con el parche QSA original; extraer solo las abstracciones útiles, no adoptar el fork completo. | Referencia de código; sus perfiles GPU publicados no son transferibles a 4 GiB. |
| [Qwen3.8-27B-QSA GGUF](https://huggingface.co/higa2515/Qwen3.8-27B-QSA-GGUF) | Modelo QSA y runtime capturado; incluye indexers y metadatos. | Fuente de referencia para estructura de tensores/indexers y validación de compatibilidad de GGUF. | No descargar el artefacto de 27B al MSI sin gate de espacio; no ejecutable en TensorFold estándar por defecto. |
| [Ternary Bonsai 2.5 27B QSA (sahenjp)](https://huggingface.co/sahenjp/Ternary-Bonsai-2.5-27B-QSA-GGUF) | Pesos ternarios 1,75 bpw más indexers QSA destilados; requiere motor modificado. | Caso de estudio de co-diseño: pesos compactos + selector entrenado + kernel block-sparse. | Objetivo de investigación, no target de ejecución MSI. |
| [GSQ-RCO QSA GGUF (pentacoxian-dev)](https://huggingface.co/pentacoxian-dev/Qwen3.8-27B-QSA-GSQ-RCO-GGUF) | Variante QSA con cuantización GSQ-RCO y MTP/DFlash2 asociados. Su propia ficha reporta degradación de recall en contextos muy largos incluso tras reentrenar indexers. | Comparar cuantización de pesos, indexer y calidad como ejes separados; incorporar pruebas de recuperación profunda y decoys. | Solo referencia documental hasta tener un runtime/artefacto pequeño compatible. |
| [bonsai2-small-gpu](https://github.com/matt-fell-ai/bonsai2-small-gpu) | Scripts por niveles de VRAM, kernels PTQ1_0 y recuperación de cabeza MTP; sweeps y resultados. | Plantillas de matriz de memoria, launch scripts y pruebas de identidad numérica; especialmente útil para diseño de perfiles de 8/12/16 GB. | Sus perfiles de 8 GB ya exceden la VRAM del MSI; reutilizar metodología, no parámetros. |
| [local-ai-on-your-gaming-gpu](https://github.com/sudoingX/local-ai-on-your-gaming-gpu) | Recetas y patches de kernel para GPUs de consumo, PTQ1_0 y MTP. | Contrastar optimizaciones de GEMV/MVQ y batch pequeño con las restricciones de llm.asm. | Referencia de optimización; no demuestra viabilidad en 4 GB. |

**Precaución QSA:** en una adaptación QSA consultada, todas las entradas KV siguen asignadas; el ahorro está en lecturas/cómputo de atención. El modelo híbrido y la cuantización/offload son los que atacan la huella de memoria. Medir por separado bytes KV reservados, bytes leídos por token y operaciones de atención.

### B. Atención dispersa, selección y poda de KV

| Proyecto | Mecanismo | Sinergia con QSA / llm.asm | Limitación |
|---|---|---|---|
| [Microsoft MInference](https://github.com/microsoft/MInference) | Patrones dinámicos por cabeza para acelerar especialmente el prefill; integra métodos de atención, compresión, recuperación y carga KV. | Baseline para prefill sparse; comparar patrones vertical/slash, A-shape y Tri-shape con selector QSA por bloques. | Implementación principal Python/Triton/HF/vLLM/SGLang; no es un port directo NASM/CUDA minimalista. |
| [MIT Quest](https://github.com/mit-han-lab/quest) | Estima importancia de páginas KV usando min/max de claves y el vector query; carga solo top-K páginas. Conserva la KV completa. | Complemento natural para decode: indexación por página sin descartar datos. Comparar coste de índice y recall con QSA indexer. | No reduce la memoria de KV; reduce tráfico. |
| [MIT DuoAttention](https://github.com/mit-han-lab/duo-attention) | Clasifica cabezas Retrieval (KV completa) y Streaming (ventana/sink compactos). | Puede reducir memoria además de tráfico; estudiar si una clasificación por cabeza/capa puede combinarse con QSA solo en las cabezas de retrieval. | Requiere identificar/calibrar cabezas; no es equivalente a la arquitectura de 48 Gated DeltaNet + 16 QSA. |
| [SnapKV](https://github.com/FasterDecoding/SnapKV) | Selección de posiciones importantes a partir de una ventana de observación; comprime cache durante prompt. | Baseline para compresión de prompt/cache y comparación con selección learned/indexer. | Su repositorio indica compatibilidad de Transformers antigua que debe verificarse; poda puede perder tokens relevantes futuros. |
| [StreamingLLM](https://github.com/EIT-NLP/StreamingLLM) | Mantiene attention sinks y ventana reciente para streaming estable. | Política de fallback de memoria constante cuando el usuario no exige recuperación arbitraria del contexto. | No conserva todo el historial semántico; no sustituye QSA/Quest para retrieval profundo. |
| [SCBench](https://huggingface.co/datasets/MInference/SCBench) | Benchmark centrado en ciclo de vida KV: generación, compresión, recuperación y carga; incluye repo QA, multi-turn y retrieval. | Candidato a benchmark común de LEONES; adaptar subset pequeño y reproducible para comparar QSA/Quest/KIVI/TurboQuant. | Dataset/runner original enfocado a HF/vLLM; adaptar harness a inferencia C/ASM. |

### C. Compresión y cuantización de KV-cache

| Proyecto | Qué aporta | Sinergia propuesta | Estado para MSI |
|---|---|---|---|
| [KIVI](https://github.com/jy-yuan/KIVI) | Cuantización asimétrica de KV a 2 bits; tratamiento distinto de K y V y buffer residual. | Baseline de cuantización de cache; medir K/V por separado y validar errores de logits. | Concepto útil; integración original es Python/CUDA, no runtime bare-metal. |
| [TurboQuant+](https://github.com/TheTom/turboquant_plus) | Rotación Hadamard/WHT, codebooks polares, cache K/V asimétrica, políticas por capa y dequantización V guiada por atención. | Muy alta: comparte Hadamard con el ecosistema Bonsai; combinar KV compacta con selector QSA para reducir memoria y bytes leídos. | Port de kernels CUDA requiere medir ocupación, registros y coste en SM86. |
| [llama.cpp + TurboQuant](https://github.com/naveenduggal/llama-cpp-turboquant) | Integración runtime de TurboQuant+ en llama.cpp con backends CUDA/ROCm/Vulkan/Metal/CPU. | Referencia de integración práctica y API de cache quant; comparar su arquitectura con TensorFold y llm.asm. | Fork grande y dependiente de llama.cpp; no copiarlo íntegro. |
| [Shard](https://github.com/krish1905/shard) | Investigación comunitaria de compresión K/V diferenciada (PCA+int4 para K, Hadamard + vector quantization para V). | Explorar separación K/V y compresión de V sin reconstrucción completa. | Afirmaciones de compresión y calidad proceden de autor comunitario; exigir reproducción y benchmarks propios. |
| [DifferentialKV (DKV)](https://github.com/) | En Reddit se describe como compresión KV con anchors, low-rank conjunto, residuales exactos y sparse routed attention; CUDA aún en validación. | Línea de investigación para combinar compresión de estado con enrutamiento disperso. | URL exacta del repositorio no quedó verificada en la prospección; no citar como dependencia hasta localizarla. |
| [TurboQuant Reddit benchmark](https://www.reddit.com/r/LocalLLaMA/comments/1sz9v9z/qwen_3635ba3b_kv_cache_part_2_ppl_kl_divergence/) | Discusión con PPL/KL/top-1 para F16, Q8 y Turbo3/4. | Fuente de hipótesis para pruebas asimétricas K/V y métricas de calidad. | Hardware M5 Max; no extrapolar a CUDA. |

### D. Cuantización ternaria y kernels de pesos

| Proyecto | Qué aporta | Sinergia propuesta | Relevancia MSI |
|---|---|---|---|
| [Microsoft BitNet.cpp](https://github.com/microsoft/BitNet) | Runtime de inferencia ternaria; mpGEMM, Ternary Lookup y formatos Int2+Scale. | Estudiar representación ternaria, empaquetado y kernels de multiplicación; comparar con PTQ1_0 de Prism. | Especialmente interesante para CPU AVX2/VNNI y el i7-12650H; verificar ISA efectiva. |
| [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) | Amplio soporte de cuantizaciones; PTQ1_0/PQ2_0 y repack R8; documentación de estado CPU/GPU por tipo. | Benchmark cruzado para pesos ternarios; estudiar repack de pesos y ruta CPU/GPU. | Su README indica PTQ1_0 y variantes R8 CPU-only, mientras Q2/PQ2 tienen CUDA; confirmar estado al commit fijado. |
| [OpenBonsai](https://github.com/esokullu/openbonsai) | Pipeline experimental de rotación Hadamard, GPTQ secuencial ternario y destilación de escalas; exporta PTQ1_0. | Reutilizar ideas y metodología para convertir/calibrar modelos pequeños y medir el coste real de cuantización. | El pipeline medido usa GPU grande; sus propios resultados reconocen gap frente al Bonsai oficial. |
| [BitTern / CAT-Q discussion](https://www.reddit.com/r/unsloth/comments/1ulllm8/bittern_catq_costefficient_and_accurate_ternary/) | Debate sobre cuantización ternaria entrenable con reconstrucción por capa y modulación de escala/centro/umbral. | Estudiar distilación de pesos y calibración por capa, sin asumir que CAT-Q supera GPTQ + destilación. | Investigación, no runtime directo. |
| [LlamAmpere](https://www.reddit.com/r/LocalLLaMA/comments/1wjuohn/llamampere_v031_updated_with_support_for_exl/) | Proyecto comunitario reporta kernels propios para formatos ternarios y MTP. | Observar estrategias de kernel especializado y speculative decode. | Repositorio exacto no verificado en esta búsqueda; no usar como dependencia. |

### E. Arquitecturas recurrentes/híbridas y kernels de secuencia

| Proyecto | Qué aporta | Sinergia propuesta |
|---|---|---|
| [Flash Linear Attention (FLA)](https://github.com/fla-org/flash-linear-attention) | Implementaciones eficientes de arquitecturas lineales, incluyendo Gated DeltaNet y variantes. | Referencia matemática y de kernels para estado recurrente; estudiar cómo expresar estado, scan y update en llm.asm. |
| [NVlabs GatedDeltaNet-2](https://github.com/NVlabs/GatedDeltaNet-2) | Implementación oficial de una evolución de Gated DeltaNet. | Seguir avances en memoria recurrente y separación erase/write; no asumir compatibilidad directa con el Gated DeltaNet del modelo QSA. |
| [MInference](https://github.com/microsoft/MInference) | Incluye patrones sparse para prefill y referencia de kernels Triton/CUDA. | Posible fuente para kernels de prefilling en capas densas, mientras QSA se usa en decode. |

## 3. Evidencia comunitaria localizada en Reddit

Estas publicaciones son útiles para descubrir problemas y casos límite, no equivalen a validación independiente ni a benchmarks normalizados.

- [QSA indexer y recall a 32K–1M (25 nov 2026)](https://www.reddit.com/r/LocalLLaMA/comments/1y50iam/testing_a_new_kvcache_index_for_longcontext/): comparación comunitaria de Quest, un índice tipo RetroInfer y top-K exacto. Subraya que el recall y el error del output de atención deben medirse, no solo tokens/s.
- [TurboQuant: evitar dequant de V cuando la atención es despreciable](https://www.reddit.com/r/LocalLLaMA/comments/1s56g07/skipping_90_of_kv_dequant_work_228_decode_at_32k/): afirma +22,8% decode a 32K en M5 Max mediante dequantización de V condicionada por atención. Hipótesis complementaria para QSA: no cargar ni dequantizar valores que el kernel no vaya a usar.
- [Shard: compresión de KV](https://www.reddit.com/r/LocalLLaMA/comments/1tnvo7r/shard_getting_to_10_kv_cache_compression/): K y V reciben tratamientos distintos; interesante para estudiar codecs asimétricos.
- [Ternary Bonsai 27B en 8 GB](https://www.reddit.com/r/LocalLLaMA/comments/1v1ya97/i_ran_ternarybonsai27b_2bit_and_bonsai27b_1bit_on/): reporte de Terminal-Bench con RTX 5070 Laptop 8 GB; el autor señala que el modelo ternario 27B obtuvo menor score que Qwen3.5-9B en su harness. Recordatorio de que caber en VRAM no equivale a ser mejor.
- [Project Zero C99, CPU-only](https://www.reddit.com/r/LocalLLaMA/comments/1xdj98z/a_few_months_after_my_earlier_post_project_zero/): afirma soporte de Bonsai 27B, BitNet, dense, MoE y Mamba en un motor C; buen ejemplo de runtime mínimo, pendiente de auditoría independiente.
- [BitNet CPU y validación de corrección](https://www.reddit.com/r/LocalLLaMA/comments/1xa3yqk/i_checked_bitnet_and_bonsai_on_cpu_against/): reporta diferencias de corrección entre runtimes/formatos y subraya la necesidad de comparar contra logits/PPL de referencia.
- [TurboQuant K/V y PPL/KL](https://www.reddit.com/r/LocalLLaMA/comments/1suur3s/qwen36_27bs_surprising_kv_cache_quantization_test/): muestra por qué la cuantización simétrica K/V puede fallar mientras K8 + V comprimida puede ser viable.

## 4. Síntesis: arquitectura de sinergia recomendada

No combinar todas las técnicas en un único cambio. Mantener módulos y métricas separadas:

```text
Modelo / pesos
  └── PTQ1_0 / ternario / GPTQ + distillation
        └── GEMV/GEMM especializado (CPU SIMD / CUDA)

Arquitectura por capa
  ├── capas recurrentes: Gated DeltaNet / estado acotado
  └── capas de atención:
        ├── indexer (QSA / Quest-like)
        ├── selector de bloques/páginas
        ├── cache KV (Q8 / KIVI / TurboQuant+)
        └── kernel sparse attention (CUDA / CPU fallback)

Decode
  ├── MTP / speculative decoding
  └── reutilización de prefijo y estado recurrente

Validación
  ├── paridad logits / KL / PPL
  ├── recall por profundidad / needle / decoys / multi-turn
  ├── prefill y decode separados
  └── VRAM, RAM, swap, bytes KV reservados/leídos
```

### Sinergias con mayor potencial

1. **QSA + KV quantization:** el indexer reduce qué bloques se leen; el codec reduce bytes por bloque. Es la combinación más directa para reducir tráfico de memoria en decode.
2. **QSA + attention-gated V dequant (TurboQuant+):** el selector puede evitar lecturas de bloques y el kernel puede evitar dequantizar valores con peso de atención despreciable. Evitar doble selección redundante; diseñar una interfaz común de índices.
3. **Gated DeltaNet + QSA:** arquitectura híbrida que limita el número de capas con KV creciente y aplica selección dispersa donde la atención completa sigue siendo necesaria.
4. **DuoAttention + QSA:** posible clasificación de cabezas retrieval/streaming dentro de capas de atención; QSA para retrieval heads, ventana/sink para streaming heads. Requiere calibración y validación de calidad.
5. **Ternary Bonsai + kernel de pesos + MTP:** compactar pesos no basta; los formatos ternarios necesitan kernels optimizados y MTP debe medirse como aceleración de decode, sin mezclarlo con el ahorro KV.
6. **MInference + QSA:** MInference como baseline de prefill y QSA como selector de decode; medir si un selector distinto por fase ofrece una relación coste/beneficio mejor.
7. **Quest + SCBench:** Quest aporta retrieval query-aware con KV íntegra; SCBench aporta una matriz de evaluación para no confundir velocidad con retención de información.

## 5. Aplicabilidad y límites en el MSI

| Línea | GPU RTX 3050 4 GiB | CPU i7-12650H / RAM 14 GiB | Decisión |
|---|---|---|---|
| QSA kernel SM86 | Arquitectura CUDA compatible en principio; memoria muy limitada | Puede existir fallback CPU según implementación | Inspeccionar/build aislado; no prometer 27B |
| Ternary GEMV | Posible si el kernel soporta SM86 y el modelo pequeño cabe | Interesante para AVX2/VNNI y offload | Prioridad de pruebas |
| KV Q8 / TurboQuant | Reduce memoria/tráfico, pero no elimina coste de pesos | Puede ampliar capacidad a costa de latencia | Probar en modelos pequeños |
| Quest/QSA selector | Reduce lecturas, no reserva KV | Posible prototipo CPU | Prioridad de prototipo algorítmico |
| DuoAttention / streaming | Requiere clasificación de cabezas y cambios de arquitectura | Puede reducir memoria persistente | Investigación posterior |
| Bonsai QSA 27B 128K–256K | No cabe con los perfiles publicados | Offload masivo no equivale a velocidad publicada | No intentar en MSI |
| MTP | Puede subir throughput de decode si hay memoria y draft head compatibles | Beneficio variable | Solo después de baseline correcto |

**No usar swap como sustituto de VRAM.** Cualquier prueba en MSI debe tener umbrales de parada para RAM disponible, swap, temperatura, tiempo y espacio en disco. No descargar pesos grandes hasta calcular el presupuesto completo.

## 6. Plan de trabajo propuesto para llm.asm

### Fase 0 — Registro y trazabilidad
- Guardar esta matriz como mapa de investigación, sin integrar dependencias.
- Fijar commit/tag y licencia de cada repo antes de copiar código o adaptar kernels.
- Distinguir implementaciones oficiales, forks, demos y afirmaciones de Reddit.
- Mantener referencias externas fuera del clon upstream de llm.asm.

### Fase 1 — Baselines pequeños y CPU-first
- Elegir un modelo pequeño soportado por el motor y un corpus fijo.
- Registrar logits de referencia, PPL, top-1 agreement, latencia, RSS y bytes leídos.
- Evaluar ternary/BitNet frente a Q8/Q4 y validar exactitud de formato.
- Prototipar selector Quest-like sobre matrices KV sintéticas y luego trazas reales pequeñas.

### Fase 2 — Cache y atención como interfaces separadas
- Definir interfaz de cache: append, page/block metadata, quantize/dequantize, gather.
- Definir interfaz de selector: query → lista de bloques, presupuesto K, causal tail y fallback dense.
- Implementar fallback denso obligatorio para A/B y para entradas fuera de distribución.
- Añadir contadores de bytes reservados, bytes leídos, bloques seleccionados y tiempo del selector.

### Fase 3 — Kernels y CUDA SM86
- Evaluar kernel block-sparse con tamaños de bloque pequeños y alineados con el hardware.
- Medir register pressure, occupancy, coalescing y coste de construir índices.
- Comparar Q8 KV frente a una variante comprimida; K y V deben poder configurarse independientemente.
- Mantener implementación CPU de referencia para validar resultados del kernel CUDA.

### Fase 4 — Modelo híbrido
- Estudiar si el formato/runtime puede representar capas recurrentes y de atención distintas.
- No implementar Gated DeltaNet en llm.asm hasta disponer de un perfil de arquitectura, ecuaciones, tensores, test de referencia y gate específica.
- Evaluar QSA solo en capas/head donde la memoria y el tráfico lo justifiquen.

### Fase 5 — Evaluación y escalado
- Subset reproducible de SCBench: retrieval de cadenas, semantic retrieval, RepoQA, multi-turn y needles con decoys.
- Contextos incrementales: 1K, 2K, 4K y 8K en MSI; más grandes solo en hardware apropiado.
- A/B dense vs sparse con mismo modelo, prompt, seed, cache y build.
- Reportar prefill, decode, TTFT, tokens/s, PPL/KL, recall por profundidad, VRAM/RAM/swap y energía si está disponible.

## 7. Criterios de aceptación antes de integrar

- [ ] Fuente y revisión inmutable identificadas.
- [ ] Licencia compatible revisada; preservar avisos y atribución.
- [ ] Formato de tensores y contrato del kernel documentados.
- [ ] Test CPU de referencia y tests de límites.
- [ ] A/B dense/sparse con igualdad de entradas.
- [ ] Recall y calidad evaluados más allá de Needle-in-a-Haystack.
- [ ] Presupuesto de memoria medido; no inferido del tamaño GGUF.
- [ ] Rendimiento medido en hardware objetivo; separar prefill/decode.
- [ ] Fallback denso y comportamiento ante selector vacío/overflow.
- [ ] Sin regresiones en el baseline Qwen3-0.6B de llm.asm.
- [ ] Gate aprobada por el índice maestro antes de implementar cambios sustanciales.

## 8. Referencias académicas y técnicas

- MInference: https://arxiv.org/abs/2407.02490
- Quest: https://arxiv.org/abs/2406.10774
- DuoAttention: https://arxiv.org/abs/2410.10819
- SnapKV: https://arxiv.org/abs/2404.14469
- KIVI: https://arxiv.org/abs/2402.02750
- TurboQuant: https://arxiv.org/abs/2406.03482
- BitNet.cpp: https://arxiv.org/abs/2502.11880
- SCBench: disponible desde https://github.com/microsoft/MInference y https://huggingface.co/datasets/MInference/SCBench
- Flash Linear Attention: https://github.com/fla-org/flash-linear-attention

## 9. Límites de esta prospección

- La búsqueda cubre GitHub y Reddit, pero no es una auditoría completa de cada repositorio ni de cada commit.
- Las cifras de rendimiento de READMEs y posts son afirmaciones de sus autores; no se comparan entre sí si hardware, contexto, batch, cuantización o protocolo difieren.
- Algunas referencias comunitarias (Shard, DKV, LlamAmpere, Project Zero) necesitan revisión de código, commit, licencia y reproducibilidad antes de considerarse candidatas de integración.
- La documentación no declara soporte QSA, ternary Bonsai, Gated DeltaNet ni TurboQuant en llm.asm o TensorFold.
- No se ha ejecutado ningún benchmark físico en el MSI como parte de esta prospección.

---
**Conclusión:** la línea con mejor relación entre valor estratégico y coste inicial es estudiar el contrato selector–KV–kernel con baselines pequeños, y en paralelo evaluar kernels ternarios CPU-first. QSA, KV quantization y Gated DeltaNet deben mantenerse como componentes independientes hasta demostrar una sinergia medible.
