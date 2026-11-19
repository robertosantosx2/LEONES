# Investigación: Megakernels en inferencia LLM (estado a noviembre 2026)

**Fecha de elaboración:** 19 de noviembre de 2026  
**Repositorio destino:** robertosantosx2/LEONES  
**Ruta:** `atlas/megakernels-investigacion.md`  
**Autor:** investigación compilada para LEONES (Local Ecosystem of Open Neural Expert Systems)  
**Estado:** ESTIMATED / prospección (sin mediciones físicas propias en hardware LEONES)

---

## 1. Resumen ejecutivo

Un **megakernel** es un único kernel GPU (o un número muy reducido de kernels) **persistente** que fusiona casi todo el decode loop / forward pass de un modelo LLM (atención, matmuls, norms, residuales, a veces el loop de tokens y speculative decoding) en un solo lanzamiento.

Objetivo principal: eliminar el overhead de cientos de lanzamientos de kernels pequeños por token, reducir barreras full-grid, mejorar locality y prefetch de pesos, y mantener datos en cachés/on-chip más tiempo.

Brilla especialmente en **batch size 1 / low-batch y latencia**. El mantenimiento y la generalización a diferentes batch sizes, contextos o hardware son más difíciles que en engines genéricos (vLLM, SGLang).

**Estado 2026:** Sigue siendo relevante para latencia extrema y modelos/hardware fijos. Los agents de coding (Claude, etc.) ya escriben megakernels automáticamente. Al mismo tiempo, enfoques como torch.compile + CUDA Graphs + PDL + compilers de agents están cerrando o superando la brecha en muchos escenarios de producción, con menos mantenimiento.

Together AI construyó megakernels y luego los eliminó a favor de su Together Compiler (agents que superan los hand-written).

---

## 2. Proyectos más relevantes (GitHub)

| Proyecto | Stars (aprox.) | Descripción breve | Notas |
|----------|----------------|-------------------|-------|
| **mirage-project/mirage** | ~2.6k–3k | Mirage Persistent Kernel (MPK). Compilador/runtime que transforma inferencia multi-GPU en megakernel automático. | Uno de los más maduros y visibles. Reduce latencia 1.2–6.7×. |
| **HazyResearch/Megakernels** | ~880 | Trabajo pionero de Stanford (ThunderKittens). Demos low-latency Llama. | Referencia clásica del enfoque. |
| **dangxingyu/megakernel-zoo** | reciente (nov 2026) | Claude + agents escriben un megakernel + engine por modelo (8 modelos, 8B–594B). | 1.13–1.77× vs mejor engine genérico en single-sequence (hasta 2.05× con cambios numéricos). Incluye server OpenAI-compatible y test suite estricto. Blog: dangxingyu.github.io/megakernel |
| **cohere-ai/cohere-megakernel** | ~109 | Serving engine completo con megakernel de decode para North Mini Code. | 1.25–1.41× vs vLLM end-to-end; ~62% del speed-of-light de H100 en BS=1. |
| **Inferact/tpu-megakernels** | ~188–190 | Colección de megakernels para TPU v7 (Kimi K3, Qwen3.8-27B…). | >700 TPS en Kimi K3 con speculative decoding (vs ~452 en GB200); 1.4–2× en decode sin spec. |
| **RightNow-AI/AutoMegaKernel** | ~163 | Agent harness que compila modelos en megakernels correctos (validados estáticamente), self-retargeting y self-tuning. | Supera cuBLAS en algunos casos int8 batch-1. |
| **megabake/megabake** | ~39 | Compilador PyTorch nativo a megakernel (CuTe DSL). | Enfoque automatizado desde PyTorch. |
| **PixelML/luce-megakernel** | bajo | Primer megakernel para modelos híbridos DeltaNet/Attention. Buena eficiencia energética en consumer GPUs (RTX 3090). | Destacable en tok/J. |

Otros: trabajos específicos (Qwen, LlamaGen), Huawei MegaGDN (NPU), etc. Topic GitHub “megakernel” agrupa varios.

---

## 3. Resultados destacados (reportados)

- **megakernel-zoo (Dang et al., nov 2026):** 1.13–1.77× vs mejor engine genérico (vLLM/SGLang) en single-sequence. Hasta 2.05× con cambios de storage/numéricos permitidos. Mejor servicio de trazas de producción (menos stalls).
- **Together AI:** Megakernel hand-written ~990 tok/s (Llama 1B, BS=1, H100). torch.compile + CUDA Graphs + PDL llega a ~975 (98%). Together Compiler (agents) llega a 1.137 (115% del megakernel).
- **Cohere North Mini Code:** 1.25–1.41× vs vLLM end-to-end.
- **TPU (Inferact):** 709 accepted tokens/s en Kimi K3 con speculative decoding.
- **Luce (consumer):** 413 tok/s decode en RTX 3090 @220W (1.87 tok/J), superando eficiencia de Apple M5 Max en algunos escenarios.

**Nota de LEONES:** Todas las cifras anteriores son **ESTIMATED** (reportadas por terceros). No hay mediciones físicas propias en hardware del ecosistema LEONES (RTX 3050 Laptop, etc.).

---

## 4. Ecosistema y conversación (X / Reddit)

- **X (Twitter):** Conversación activa alrededor del post de @xingyudang (Xingyu Dang) sobre “A Megakernel per Model”. Discusiones sobre especialización vs engines genéricos, Together Compiler, trade-offs de mantenimiento. Cuentas visibles: @xingyudang, @togethercompute, ingenieros de inference (@YuvrajInfer, etc.), @lmsysorg.
- **Reddit:** r/LocalLLaMA, r/Qwen_AI, r/LLMDevs, r/AI_Agents. Posts sobre speedups concretos (Qwen en 3090, Luce, TPU) y escepticismo sobre generalización y complejidad.

---

## 5. Relevancia para LEONES

- **FitLLM / runtime selection:** Los megakernels son altamente especializados (por modelo + GPU). Encajan mal en el flujo genérico de LEONES (descubrir → estimar → elegir → medir). Podrían ser candidatos ESTIMATED para casos de uso de latencia extrema en hardware fijo.
- **Benchmarking:** Interesante para futuras campañas MEASURED en hardware consumer (si aparece implementación viable en RTX 30xx/40xx o equivalentes).
- **Atlas / prospection:** Tema de prospección continua. Prioridad media-alta para seguimiento de mirage, megakernel-zoo y compilers de agents.
- **Riesgos:** Alta complejidad de mantenimiento, poca portabilidad, y el hecho de que compilers + Graphs + PDL están cerrando la brecha rápidamente.

---

## 6. Fuentes principales

- Blog “A Megakernel per Model” — dangxingyu.github.io/megakernel + repo megakernel-zoo
- Mirage: github.com/mirage-project/mirage
- HazyResearch/Megakernels
- Together AI / AgentsPulse (megakernel vs CUDA Graphs + PDL)
- Cohere blog / cohere-megakernel
- Inferact tpu-megakernels
- AutoMegaKernel (RightNow-AI)
- Conversaciones X y Reddit (nov 2026)

---

## 7. Próximos pasos sugeridos (para LEONES)

1. Añadir entradas ESTIMATED en el inventario de motores/runtimes si aparece implementación viable en hardware consumer.
2. Seguir prospection de megakernel-zoo y Mirage.
3. Evaluar si algún megakernel concreto (ej. Luce o derivados) merece una campaña de viabilidad en RTX 3050.
4. Actualizar este documento cuando haya nuevos resultados o mediciones propias.

---

*Documento generado a partir de prospección web, GitHub, X y Reddit. No contiene mediciones físicas propias de LEONES.*
