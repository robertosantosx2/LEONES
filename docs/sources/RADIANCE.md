# Radiance — fuente de conocimiento para LEONES

- **Proyecto:** Radiance
- **Repositorio primario:** https://codeberg.org/StillDeadcode/radiance
- **Organización / autor:** StillDeadcode
- **Tipo:** runtime / motor de inferencia LLM modular (C++ + HIP), servidor HTTP OpenAI-compatible.
- **Estado LEONES:** 🟢 fuente activa · 🟡 `runtime-candidate` · ⏳ pendiente de adapter y benchmark propio.
- **Fecha de revisión documental:** 2026-10-09

> **Regla de evidencia:** las cifras, compatibilidades y afirmaciones de rendimiento procedentes de Radiance o de su documentación son evidencia externa hasta que LEONES las reproduzca. Radiance no convierte por sí mismo un resultado en `measured`.

## 1. Qué es

Radiance es un **motor de inferencia LLM** escrito en C++ y HIP, orientado a maximizar el aprovechamiento de hardware AMD, especialmente **RDNA4** (`gfx1200`, `gfx1201`, p. ej. Radeon AI PRO R9700). Expone una API HTTP compatible con:

- OpenAI Chat / Completions / Responses
- Anthropic Messages
- llama-server (nativo)

Arquitecturas de modelo, bibliotecas de kernels y cuantizadores se cargan como plugins `.so`. Los kernels empaquetados (`libr4d`) están optimizados para RDNA4; el motor arranca en otras familias AMD si se suministra la biblioteca de kernels correspondiente.

Incluye soporte de cuantización avanzada (FP8, MXFP4 / Quark AWQ, experts 4-bit, int8 trunk), speculative decoding (DFlash2, MTP), tensor parallelism flexible (tp 2/3/4), placement de expertos (VRAM + host pool + disk), prefix-cache y un scheduler que evita que un prefill largo starve a las filas de decode.

**Qué no es:** no es un stack de despliegue completo (como ODS), ni un preselector hardware-aware (como LLMFit), ni un workspace agentivo. Es un **runtime de inferencia** de bajo nivel, análogo conceptualmente a vLLM, SGLang, ExLlama o llama.cpp, pero especializado en AMD discrete RDNA4.

## 2. Fuente primaria y procedencia

| Campo | Valor |
|---|---|
| Repositorio | https://codeberg.org/StillDeadcode/radiance |
| Imagen Docker | `stilldeadcode/radiance` (kernels `gfx1201`) |
| Modelos / contenedores `.rad` | Hugging Face (StillDeadcode/*) |
| Licencia (motor) | Apache-2.0 (verificar en LICENSE del tree) |
| Versión revisada | ~1.3.0 (octubre 2026) |
| Predecesor | vllm-radiance (deprecado; el autor migró a este motor standalone por menor overhead de CPU y coste energético) |

## 3. Mecanismos relevantes para LEONES

### Kernels HIP y RDNA4

Los kernels de dispositivo (`libr4d`) están escritos para RDNA4. El motor puede arrancar en otras GPUs AMD, pero sin la biblioteca de kernels adecuada no sirve modelos a velocidad útil. Existe backend host (CPU) para tests, no para serving productivo.

### Plugins `.so`

Arquitecturas, cuantizadores y bibliotecas de kernels se cargan dinámicamente. Esto permite extensibilidad sin recompilar el núcleo, pero exige que cualquier adapter LEONES declare y valide las capacidades del plugin cargado.

### Cuantización y formatos

- FP8, MXFP4 (AMD Quark AWQ), experts 4-bit + trunk int8, bf16 de referencia.
- Contenedores `.rad` empaquetan pesos + tokeniser + chat template + drafter.
- KV cache en FP8; placement de expertos en VRAM / host pinned / disk.

### Speculative decoding y scheduling

DFlash2 / MTP y un scheduler que reserva presupuesto de tokens para decode y admisiones durante prefills largos (`--busy-prefill-chunk`). Relevante para workloads agentivos multi-turno y para no confundir TTFT con throughput de decode.

### API y despliegue

API OpenAI-compatible + Anthropic + llama-server. Imagen Docker oficial + compose files por modelo. No requiere ROCm en el host (solo driver `amdgpu` compatible con ROCm 7.2).

## 4. Encaje con ODS (Osmantic Deployment System)

ODS es la capa de **despliegue/instalación** que LEONES ya trata como subproyecto de integración (`docs/sources/ODS.md`). Su matriz de soporte actual clasifica:

- **Tier A:** Linux + AMD Strix Halo (memoria unificada, Vulkan / ROCm opcional).
- **Tier B:** NVIDIA CUDA, Windows/WSL2, macOS Apple Silicon.
- **Tier C (experimental):** GPUs AMD **discretas** e Intel Arc.

Radiance cubre precisamente el hueco de **AMD discrete RDNA4**. Una integración natural sería:

1. ODS detecta RDNA4 / gfx1201.
2. Elige Radiance como backend de inferencia en lugar de (o además de) llama-server/Vulkan.
3. Arranca el contenedor `stilldeadcode/radiance` + modelo `.rad` vía compose.
4. Expone el endpoint OpenAI-compatible al resto del stack ODS (Dashboard, LiteLLM, agentes, etc.).
5. LEONES recibe el handoff de instalación/estado y realiza la medición propia.

Hoy **no existe integración prevista documentada** ni en el repo de LEONES ni, por la revisión pública, en ODS. El encaje técnico (API, Docker, hardware objetivo) es alto.

## 5. Encaje arquitectónico en LEONES

Radiance es un **runtime**, no una propiedad del modelo y no sustituye al preselector ni al benchmark canónico.

```text
Perfil hardware (AMD RDNA4 / gfx120x)
      ↓
LLMFit / Atlas — preselección / candidatos
      ↓
Router LEONES — tarea + restricciones + evidencia
      ↓
runtime-selection.v1
      ├── llama.cpp / Ollama / vLLM / SGLang / …
      └── Radiance — cuando el hardware sea RDNA4 discrete y se busque eficiencia AMD nativa
      ↓
Adapter confiable (entrypoint Docker o binario, capacidades, validación)
      ↓
Executor + runtime-benchmark.v1
      ↓
Evidence / Atlas / recomendador
```

### Relación con el roadmap V1.1 de runtimes (issue #61)

El issue «V1.1 — ampliar runtimes y conectarlos a runtime-selection.v1» enumera:

llama.cpp (referencia), Ollama, FreeToken, AirLLM, vLLM/SGLang, MLX, ExLlamaV2/V3, OpenVINO/ONNX, TensorRT-LLM.

**Radiance no figura aún.** Puede añadirse como runtime candidato en la misma oleada o en una posterior, siguiendo el contrato de registry + capability match + adapter confiable + `runtime-benchmark.v1`.

### Contrato conceptual del recomendador

Mantener separados, como mínimo:

- `model_id` / contenedor `.rad`
- `runtime_id = radiance`
- `runtime_version`
- `hardware_profile` (familia AMD, gfx target, VRAM, P2P)
- `quantization` / recipe
- `tp` / placement / host-pool
- `kv_cache_dtype`
- `num_speculative_tokens`
- `measured_ttft`
- `measured_prefill_tps` / `measured_decode_tps`
- `peak_vram` / `peak_host_pinned`
- `result_quality`

Así se evita atribuir al modelo el comportamiento específico del runtime HIP.

## 6. Benchmark mínimo LEONES

Antes de promocionar Radiance a una recomendación basada en evidencia medida, registrar:

1. instalación reproducible (Docker oficial o build desde source) en Debian/Ubuntu con driver `amdgpu` + RDNA4;
2. versión exacta de Radiance / imagen / commit;
3. modelo/contenedor `.rad`, recipe y revisión;
4. flags de serve (tp, placement, host-pool, kv-cache, speculative tokens, max-num-seqs, etc.);
5. TTFT y tok/s de prefill y decode bajo workload controlado;
6. VRAM y host pinned pico;
7. comportamiento con contexto largo y concurrent sequences;
8. estabilidad del scheduler bajo prefill largo + decode;
9. calidad frente al mismo modelo en otro runtime comparable (p. ej. vLLM ROCm o llama.cpp Vulkan) cuando exista;
10. artefactos y provenance completos para `runtime-benchmark.v1`.

## 7. Clasificación de evidencia

| Estado | Significado |
|---|---|
| `external` | Afirmación procedente de la documentación / README / releases de Radiance. |
| `verified-primary` | Identidad y procedencia del proyecto comprobadas por LEONES (Codeberg, Docker Hub, HF). |
| `measured` | Resultado reproducido mediante benchmark LEONES en un perfil hardware concreto. |

La ficha actual queda en **fuente activa + runtime-candidate**; no aporta todavía mediciones `measured`.

## 8. Valor estratégico

Radiance permite a LEONES:

- cubrir **AMD discrete RDNA4**, hoy Tier C en ODS y ausente del roadmap V1.1 de runtimes;
- separar claramente «¿cabe en AMD?» de «¿rula con kernels nativos HIP?»;
- generar evidencia MEASURED de eficiencia energética y overhead de CPU (el propio autor destaca menor coste energético frente a vLLM);
- alimentar el adapter de ODS como backend especializado cuando el hardware lo permita.

No sustituye a ODS (capa de despliegue), ni a LLMFit (preselector), ni a la medición canónica de LEONES.

## 9. Integración propuesta (próximos pasos)

1. **Documental (esta ficha):** cerrada como `research-candidate` / `runtime-candidate`.
2. **Registry V1.1:** añadir entrada Radiance con capacidades (arquitecturas AMD, formatos `.rad`/HF, cuantizaciones, TP, speculative decoding, requisitos de driver).
3. **Adapter confiable:** entrypoint Docker o binario, validación de GPU target, healthcheck, extracción de métricas.
4. **Handoff ODS (opcional, paralelo):** proponer a Osmantic que Radiance sea backend oficial para RDNA4; LEONES solo haría handoff de instalación/estado.
5. **Benchmark físico:** al menos una ejecución MEASURED en hardware RDNA4 real bajo el protocolo A01 / runtime-benchmark.v1.
6. **Actualizar** `KNOWLEDGE-REGISTRY.md` y, si procede, la vista web de runtimes.

## 10. Limitaciones

- Optimizado prioritariamente para RDNA4; otras GPUs AMD requieren kernels propios.
- No soporta NVIDIA.
- Contenedores `.rad` y recipes son específicos del ecosistema Radiance.
- Proyecto de un desarrollador principal (StillDeadcode); gobernanza y roadmap dependen de ese mantenimiento.
- No hay todavía mediciones LEONES ni adapter en el árbol.

## 11. Fuente primaria y trazabilidad

- Repositorio: https://codeberg.org/StillDeadcode/radiance
- Imagen: https://hub.docker.com/r/stilldeadcode/radiance
- Modelos de ejemplo: https://huggingface.co/StillDeadcode

Esta ficha fue redactada el **2026-10-09** a partir de la revisión del README, compose files, documentación de plugins/kernels y del estado de integración de ODS y del roadmap de runtimes V1.1 en LEONES. Las afirmaciones externas se mantienen separadas de las mediciones LEONES y deben revisarse cuando cambien el repositorio, los targets GPU o el stack de despliegue.
