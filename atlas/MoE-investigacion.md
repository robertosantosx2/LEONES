# Investigación: Modelos LLM de tipo Mixture-of-Experts (MoE) — últimos 12 meses

**Fecha de elaboración:** 21 de octubre de 2026  
**Repositorio destino:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES)  
**Ruta:** `atlas/MoE-investigacion.md`  
**Autor:** investigación compilada para LEONES (Local Ecosystem of Open Neural Expert Systems)

---

## 1. Resumen ejecutivo

Entre octubre de 2025 y octubre de 2026, la arquitectura **Mixture-of-Experts (MoE)** se consolidó como el estándar de facto para modelos open-weight de frontera (>50 B parámetros totales). Aproximadamente el 70 % de los lanzamientos open-weight de ese rango usan MoE, frente a ~25 % en 2024.

**Patrón dominante 2026:**
- Ratios de sparsidad 10×–30× (total / activos).
- Expertos finos (cientos por capa) + routing top-k (normalmente 6–10) + 1 experto compartido.
- Contextos nativos de 128 K–1 M tokens.
- Soporte creciente a multimodalidad (imagen/vídeo) y modos “thinking” / agentic.
- Inferencia con llama.cpp / vLLM / SGLang: los pesos totales deben cargarse (o streamarse), aunque solo una fracción se activa por token.

---

## 2. Conceptos clave de MoE para despliegue local

| Concepto | Explicación práctica |
|----------|----------------------|
| **Total parameters** | Tamaño del checkpoint que hay que almacenar/cargar. |
| **Active parameters** | Parámetros realmente usados por token → coste de FLOPs y latencia. |
| **Sparsity ratio** | Total / Active (ej. 18× en DeepSeek-V3/V4). |
| **Memoria teórica llama.cpp (Q4_K_M)** | ≈ (total_params × 4.5–5 bits) + overhead KV-cache + buffers. En la práctica se necesita RAM/VRAM ≈ 0.55–0.65 × tamaño del archivo GGUF. |
| **Offloading** | `--n-cpu-moe N` permite dejar expertos en CPU/RAM mientras la GPU solo tiene los activos + capas densas. |
| **Routing** | Top-k de expertos + 1 shared expert es el patrón actual (DeepSeek-style). |

**Nota de memoria:** Aunque solo se activen ~3–50 B parámetros, **todos los expertos deben residir en memoria** (o ser streameados desde NVMe). Por eso un modelo 671 B / 37 B activos puede requerir >300 GB de RAM a Q4 si no se usa offloading agresivo.

---

## 3. Tabla de lanzamientos MoE relevantes (oct 2025 – oct 2026)

Ordenados por fecha aproximada de lanzamiento (más recientes primero). Datos de total/activos, contexto y licencia según anuncios oficiales y model cards de Hugging Face a fecha de esta investigación. Las estimaciones de memoria son teóricas para **Q4_K_M** en llama.cpp (aprox. 0.55–0.6 bytes/param + overhead).

| Fecha (aprox.) | Modelo | Laboratorio | Total / Activos | Contexto | Memoria teórica Q4_K_M (llama.cpp) | HF / descarga | Características y usos preferidos |
|----------------|--------|-------------|-----------------|----------|------------------------------------|---------------|-----------------------------------|
| Oct 2026 | **Mellum2.1** (12B-A2.5B) | JetBrains | 12 B / 2.5 B | 131 K | ~7–8 GB | [HF](https://huggingface.co/JetBrains) (GGUF próximo) | **Código / agentes de coding**. Thinking + RL en sandboxes reales. Apache-2.0. Ideal local. |
| Oct 2026 | **Beam** (501B-A23B) | Reflection AI | 501 B / 23 B | 1 M (API 262 K) | ~280–300 GB | Pesos Apache-2.0 prometidos | Razonamiento + coding agentic. Paridad con GLM-5.x a 3–4× menos compute. |
| Oct 2026 | **Kolibri-1** | Aleph Alpha | 78 B / ~3.5 B | 262 K → 1 M | ~45–50 GB | HF (Apache-2.0) | Soberano DE/EN. Texto puro. |
| Sep–Oct 2026 | **Ling-3.1-flash** | inclusionAI (Ant Group) | 560 B / ~25 B | 256 K (1 M target) | ~310–330 GB | Trial API | Reasoning / agentes / office. Thinking mode. |
| Sep 2026 | **MiMo-V2.6-Pro** | Xiaomi | 1.02 T / 42 B | 1 M | ~570–600 GB | HF (MIT) | **Líder open-weight** (AA Index ~46). Omnimodal. |
| Sep 2026 | **MiMo-V2.6-Flash** | Xiaomi | 309 B / 15 B | 1 M | ~170–180 GB | HF (MIT) | Multimodal barato, alto volumen. |
| Ago 2026 | **DeepSeek-V4-Pro-0813** | DeepSeek | 1.65 T / 49 B | 1 M | ~900+ GB | HF (MIT) | Flagship coding + agentic. CSA+HCA attention. DSpark speculative. |
| Ago 2026 | **Qwen3.8-2.4T-A95B** | Alibaba Qwen | 2.4 T / 95 B | 256 K | ~1.3 TB | HF (licencia Max) | Máximo de la familia Qwen open. |
| Jul–Ago 2026 | **DeepSeek-V4-Flash** / V4.1-Flash | DeepSeek | 284–552 B / 8–16 B | 1 M | 160–310 GB | HF (MIT) | Multimodal, alto throughput. Prefill 8 B / decode 16 B. |
| Jun 2026 | **GLM-5.2 / 5.3** | Z.ai (Zhipu) | 753 B / ~? | 1 M | ~420 GB | HF (MIT) | Coding + agentic fuerte. |
| 2026 (varios) | **Qwen3-VL / Qwen3.x-A3B / A22B** | Alibaba | 30 B-A3B … 235 B-A22B | 256 K–1 M | 18–130 GB | HF | Multimodal (imagen/vídeo), GUI agents, thinking. |
| 2025–2026 | **Llama 4 Maverick / Scout** | Meta | ~400 B / 17 B · 109 B / 17 B | — | 220 / 60 GB | — | General + multimodal. |
| 2025 | **Kimi K2 / K3** | Moonshot | 1 T–2.8 T / 32–104 B | 1 M | 550–1.5 TB | — | Flagship open reasoning/agentic. |
| May 2026 | **EMO** (14B-A1B) | AllenAI | 14 B / 1 B | — | ~8 GB | HF | Investigación modularidad emergente. Selectivo de expertos. |
| Oct 2025–2026 | **MiniMax-M2 / M3**, **openPangu-2.0-Pro**, **Command A+**, **Nemotron 3 Super**, etc. | Varios | 100–500 B / 6–25 B | 128 K–1 M | Variable | HF | Coding, agentic, multimodal. |

> **Nota:** Las cifras de “activos” varían ligeramente según fuente (prefill vs decode, shared experts). Las memorias son estimaciones Q4_K_M; en práctica se recomienda medir con `llama-bench` o `tensorfold` / FitLLM.

---

## 4. Características técnicas destacadas 2026

### 4.1 Arquitectura
- **Fine-grained MoE**: cientos de expertos pequeños por capa (256–512) + top-6/8/10 + 1 shared.
- **Atención híbrida**: MLA (Multi-head Latent Attention), CSA/HCA, Sparse Attention, a veces Mamba/SSM híbrido.
- **Contextos largos nativos**: 256 K–1 M tokens con KV-cache comprimido (hasta 400× más pequeño que V1 en algunos DeepSeek).
- **Modos duales**: “thinking” / non-thinking, tool-calling nativo, speculative decoding (DSpark, MTP).

### 4.2 Multimodalidad
- Texto + imagen nativa (DeepSeek-V4.1-Flash, MiMo, Qwen3-VL, Mistral Large 4).
- Vídeo y audio en previews (algunos inclusionAI / Qwen).
- Vision encoder separado (~1–2 B) + backbone MoE.

### 4.3 Usos preferidos (resumen)

| Tipo de uso | Modelos más adecuados (2026) |
|-------------|------------------------------|
| **Razonador / Thinking** | DeepSeek-V4-Pro, Kimi K3, GLM-5.3, MiMo-V2.6-Pro, Beam |
| **Código / Agentes** | Mellum2.1, DeepSeek-V4, GLM-5.x, MiniMax-M*, Qwen3-Coder |
| **Imagen / VLM** | Qwen3-VL series, DeepSeek-V4.1-Flash, MiMo-V2.6, Mistral Large 4 |
| **Sonido / Vídeo** | Todavía experimental; algunos previews de inclusionAI y Qwen |
| **Local / Consumer** | Mellum2.1 (2.5 B activos), Qwen3-30B-A3B / 35B-A3B, EMO, MobileMoE, LFM2-24B-A2B |

---

## 5. Consideraciones para LEONES / FitLLM / llama.cpp

1. **Memoria real vs teórica**  
   Un modelo 30 B-A3B a Q4 cabe cómodamente en 24 GB VRAM. Un 671 B / 37 B necesita offloading (`--n-cpu-moe`) o multi-GPU / RAM system alta.

2. **Recomendación de selección**  
   - Hardware ≤ 24 GB → priorizar ≤ 35 B total con ≤ 4 B activos (Qwen3-A3B, Mellum2.1, Trinity-Mini style).  
   - 48–80 GB → hasta ~100–150 B total.  
   - ≥ 200 GB RAM + offload → DeepSeek-V4-Flash / MiMo-Flash.

3. **Evidencia vs estimación**  
   LEONES distingue ESTIMATED (FitLLM / HF cards) de MEASURED (ejecución real). Esta investigación es ESTIMATED; las mediciones deben hacerse en la máquina del usuario.

4. **Licencias**  
   MIT / Apache-2.0 dominan (DeepSeek, Xiaomi, JetBrains, Reflection, Aleph Alpha, Z.ai). Algunas (Qwen Max, Muse) tienen restricciones comerciales.

---

## 6. Conclusiones y recomendaciones

- **MoE es el camino dominante** para escalar capacidad manteniendo coste de inferencia razonable.
- La **calidad por parámetro activo** ha mejorado drásticamente: un 37 B activos (DeepSeek-V4) rivaliza con densos de 400 B de generaciones anteriores.
- Para **LEONES** el foco debe seguir siendo:
  1. Detectar hardware real.
  2. Filtrar por memoria estimada + ratio de sparsidad.
  3. Preferir modelos con GGUF / MLX / TensorFold listos.
  4. Medir tokens/s y calidad offline antes de recomendar.

**Próximos pasos sugeridos para el atlas:**
- Añadir campos `total_params`, `active_params`, `sparsity`, `moe_experts`, `moe_topk` al schema de recomendaciones.
- Integrar fuentes vivas (llm-releases.com, models.moe, HF trending MoE).
- Benchmark local de Mellum2.1 y Qwen3-35B-A3B como “sweet spot” consumer.

---

## 7. Fuentes principales (octubre 2026)

- llm-releases.com/changelog
- Hugging Face model cards y collections (DeepSeek, Qwen, XiaomiMiMo, JetBrains, AllenAI/EMO…)
- Presenc AI – Mixture of Experts Open-Weight Adoption 2026
- InsiderLLM, BenchLM, Artificial Analysis Index
- Papers: EMO (AllenAI), LatentMoE, Marco-MoE, Dist-MoE (Meta)
- Anuncios oficiales: DeepSeek, Alibaba Qwen, Xiaomi, JetBrains, Reflection AI, Aleph Alpha, Z.ai, Mistral, Microsoft MAI-Base-2

---

*Documento generado para el ecosistema LEONES. Toda cifra de memoria es teórica; la medición real es la única evidencia válida (MEASURED).*
