# Inference Optimization

## Qué es
Capa de conocimiento para técnicas y runtimes que permiten ejecutar modelos en hardware limitado mediante reducción de memoria, offload, streaming, sparsity, caché, compilación o distribución.

## Familias
- **QUANTIZATION:** GGUF/llama.cpp, GPTQ, AWQ, BitNet.
- **OFFLOAD/STREAMING:** AirLLM, FlexGen, CPU/GPU layer offload, mmap, prefetch.
- **SPARSE/MoE:** expert-aware execution, expert offload, PowerInfer.
- **CACHE/DECODING:** KV-cache quantization/compression, speculative decoding.
- **COMPILED/HARDWARE:** llama.cpp hardware backends/kernels, MLC-LLM.
- **DISTRIBUTED:** Petals, Exo.
- **EXPERIMENTAL:** LowMemoryLLM.

## Cómo lo usará LEONES
La optimización se decide antes de valorar modelos: caso de uso → hardware → runtime → técnicas compatibles → candidatos.

El candidato efectivo es `modelo + cuantización + runtime + offload + cache + decoding + hardware`.

## Dense y MoE
Dense: la selección por tamaño utiliza `total_parameters_m`.
MoE: el criterio computacional utiliza `active_parameters_m`; el total se conserva para memoria/almacenamiento. Sin parámetros activos verificables: `MISSING_ACTIVE_PARAMS`.

## Evidencia
Las mejoras publicadas por terceros son evidencia/estimación externa. Solo el benchmark controlado LEONES produce `measured_tps` y otras mediciones propias.

## Estado
`knowledge-contract-ready`.