# Integraciones LEONES: LLMFit, ODS, Magnitude y runtimes de inferencia

Estas integraciones y prospecciones convierten herramientas externas en **perfiles medibles y documentados** sin convertirlas en dependencias estructurales de LEONES.

## Integraciones principales

- **LLMFit — preselector hardware-aware**.
- **ODS — Servidor de Stacks IA**.
- **Magnitude — asistente personal IA**.
- **WARP — runtime experimental para MoE grandes mediante paging desde NVMe**.

## Prospección de runtimes para ODS

### P1 — prioridad alta

| Proyecto | Perfil | Informe |
|---|---|---|
| MoE-Infinity | MoE CUDA + RAM/SSD offload + serving | [MoE-Infinity](moe-infinity/README.md) |
| ramvamp | CPU/NVMe MoE streaming | [ramvamp](ramvamp/README.md) |
| Edge0 | SSD streaming + routing prediction | [Edge0](edge0/README.md) |
| BigMoeLLM | MoE > VRAM, mmap/paging | [BigMoeLLM](bigmoellm/README.md) |
| FrankenMoE-CUDA | NVMe→RAM→VRAM expert tiers | [FrankenMoE-CUDA](frankenmoe-cuda/README.md) |
| llama.cpp expert paging PoC | posible evolución upstream | [llama.cpp expert paging](llama-cpp-expert-paging/README.md) |
| LocalAI | arquitectura multi-backend | [LocalAI](localai/README.md) |
| llama-cpp-studio | control plane multi-runtime | [llama-cpp-studio](llama-cpp-studio/README.md) |

### P2 — candidatos / investigación

| Proyecto | Perfil | Informe |
|---|---|---|
| SSD MoE | SSD streaming | [ssdmoe](ssdmoe/README.md) |
| ExpertFlow | predictive expert caching | [ExpertFlow](expertflow/README.md) |
| moe-hotcache | hot-expert cache sobre llama.cpp | [moe-hotcache](moe-hotcache/README.md) |
| vllm-moe | CPU offload + GPU prefetch | [vllm-moe](vllm-moe/README.md) |
| vLLM RFC | diseño de MoE CPU offload | [RFC](vllm-cpu-offload-rfc/README.md) |
| DynaExQ | precisión/residencia dinámica | [DynaExQ](dynae-xq/README.md) |
| MoE CPU/GPU Collaborative Inference | caching CPU/GPU | [CPU/GPU](moe-cpu-gpu-collaborative-inference/README.md) |
| local-llm-npu | Intel NPU/OpenVINO | [NPU](local-llm-npu/README.md) |
| Atomic-Chat | multi-engine local | [Atomic-Chat](atomic-chat/README.md) |
| llama.cpp.35B.moe | optimizaciones MoE CUDA | [fork](llama-cpp-35b-moe/README.md) |
| moe-ssd-streaming-windows | SSD streaming Windows/NVIDIA | [Windows](moe-ssd-streaming-windows/README.md) |
| expert-streaming-engine | expert streaming | [engine](expert-streaming-engine/README.md) |
| ds4-ssd | SSD/weight streaming | [ds4-ssd](ds4-ssd/README.md) |
| moe-edge-inference | MoE edge | [edge](moe-edge-inference/README.md) |
| moe-stream | MoE streaming | [stream](moe-stream/README.md) |

### P3 — radar

| Proyecto | Perfil | Informe |
|---|---|---|
| oBeaver | toolkit local/platform-aware | [oBeaver](obeaver/README.md) |
| Forge | runtime Rust/CUDA general | [Forge](forge/README.md) |
| BaseRT | runtime Apple/NVIDIA específico | [BaseRT](basert/README.md) |
| ES-MoE | offload para entrenamiento | [ES-MoE](es-moe/README.md) |
| weight-streaming | streaming de pesos | [weight-streaming](weight-streaming/README.md) |

## Regla de frontera

Las herramientas externas siguen siendo responsables de su instalación, runtime y comportamiento interno. LEONES se ocupa de preflight, consentimiento, instalación reproducible cuando corresponda, captura de configuración, validación independiente, benchmark y separación `estimated` / `reported` / `observed` / `measured`.

**Importante:** las cifras publicadas por los proyectos no son mediciones LEONES hasta reproducirlas.

## Flujo común

```text
PREFLIGHT → CONSENTIMIENTO → INSTALACIÓN CONTROLADA
→ HEALTH/STATUS → CONFIGURACIÓN → BENCHMARK
→ ESTIMATED ≠ REPORTED ≠ OBSERVED ≠ MEASURED
→ EVIDENCIA
```
