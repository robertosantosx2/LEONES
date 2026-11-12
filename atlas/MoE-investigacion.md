# Investigación: Modelos LLM de tipo Mixture-of-Experts (MoE) — Inferencia local 2025-2026

**Fecha de elaboración original:** 21 de octubre de 2026  
**Última reescritura exhaustiva:** 12 de noviembre de 2026  
**Repositorio destino:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES)  
**Ruta:** `atlas/MoE-investigacion.md`  
**Autor:** investigación compilada y actualizada para LEONES (Local Ecosystem of Open Neural Expert Systems)

---

## 1. Resumen ejecutivo (noviembre 2026)

Entre octubre de 2025 y noviembre de 2026 la arquitectura **Mixture-of-Experts (MoE)** se consolidó como el estándar de facto para modelos open-weight de frontera (>50 B parámetros totales). Aproximadamente el 70 % de los lanzamientos de ese rango usan MoE (frente a ~25 % en 2024).

**Patrón dominante 2026:**
- Ratios de sparsidad 10×–30× (total / activos).
- Expertos finos (cientos por capa) + routing top-k (normalmente 6–10) + 1 experto compartido.
- Contextos nativos de 128 K–1 M tokens.
- Soporte creciente a multimodalidad y modos “thinking” / agentic.
- Inferencia: los pesos totales deben residir en algún nivel de la jerarquía de memoria (VRAM / RAM / NVMe), aunque solo una fracción se activa por token.

**Cambio de paradigma clave (noviembre 2026):**  
MoE ya no es solo “más capacidad con menos FLOPs activos”. Es un problema de **jerarquía de memoria + skew de routing + live working-set**. La evidencia empírica más sólida proviene del estudio de 4 meses de Alexey Fateev (@superalesha) sobre DeepSeek-V4.1-Flash, Qwen3.8-Flash-Next, GLM-5.3-Flash y MiniMax-M3.1-Flash en 4× RTX 3090 (96 GB VRAM), combinada con las mediciones reales de LEONES en hardware constrained (MSI Thin 15 B12UC · RTX 3050 Laptop 4 GiB · 14 GiB RAM).

**Modelo mental central:**

```text
tiempo por token ≈ constante (denso + atención + kernels) + misses_por_token × coste_de_un_miss
```

Un *miss* es un experto elegido por el router que no está en VRAM. El coste del miss depende de dónde se sirve (CPU desde RAM, PCIe → VRAM o disco).

---

## 2. Conceptos clave de MoE para despliegue local

| Concepto | Explicación práctica |
|----------|----------------------|
| **Total parameters** | Tamaño del checkpoint que hay que almacenar/cargar. |
| **Active parameters** | Parámetros realmente usados por token → coste de FLOPs y latencia. |
| **Sparsity ratio** | Total / Active (ej. 18× en DeepSeek-V3/V4). |
| **Memoria teórica llama.cpp (Q4_K_M)** | ≈ (total_params × 4.5–5 bits) + overhead KV-cache + buffers. En la práctica se necesita RAM/VRAM ≈ 0.55–0.65 × tamaño del archivo GGUF. |
| **Offloading** | Dejar expertos en CPU/RAM o NVMe mientras la GPU mantiene capas densas + hot experts + KV. |
| **Routing / Skew** | Distribución de picks del router. Skew fuerte → hot-set estático útil. Skew débil → live cache obligatorio. |
| **Live cache** | Movimiento dinámico de expertos RAM ↔ VRAM según el working-set de la request actual. |
| **Expert profile** | Contadores de picks por experto y capa sobre tráfico representativo del dominio. |

**Nota de memoria:** Aunque solo se activen ~3–50 B parámetros, **todos los expertos deben residir en algún nivel de memoria** (o ser streameados). Un modelo 671 B / 37 B activos puede requerir >300 GB de RAM a Q4 si no se usa offloading agresivo + live cache.

---

## 3. Evidencia empírica primaria: estudio @superalesha (4× RTX 3090)

Fuente: [hilo completo](https://x.com/superalesha/status/2120840758223688028) (12 Nov 2026). Hardware: 4× RTX 3090 (PCIe 3.0 x16, sin NVLink), AMD EPYC 7642, DDR4 variable (2→4→8 canales).

### 3.1 Skew de routing real

| Modelo | Comportamiento del router | Utilidad de hot-set estático |
|--------|---------------------------|------------------------------|
| **DeepSeek V4.1 Flash** | Top-100/384 → 70 %; top-200 → 89 %. Skew fuerte | Alta |
| **Qwen3.8 Flash Next** | 24 % expertos en VRAM (1 GPU) → 74-79 % hits; 53 % (2 GPU) → 92-95 % | Alta |
| **GLM-5.3 Flash** | Mitad “fría” aún recibe 41 % de picks. Cero expertos muertos en 42 capas | Casi nula (solo –10 % misses) |
| **MiniMax M3.1 Flash** | Random ~61 % hits; profile 64-69 % | Baja |

**Regla de oro:** Si el profile bate al random por < ~10 puntos, no construyas el sistema alrededor de un hot-set estático. Construye un **live cache**.

### 3.2 Live cache vs colocación estática (MiniMax, ~64 slots/capa)

| Política | Hits aproximados |
|----------|------------------|
| Random | 61 % |
| Estático por profile de uso | 64-69 % |
| Live cache (1 swap/token) | 72-83 % |
| Live cache (hasta 8 swaps/token) | 87-93 % (servicio real 85 % en agent sessions) |
| LFU con decay / LRU / Belady | 89-99 % |

Implementaciones de referencia: Maya (heat + decay), MiniMax engine (counters half-life ~230 tokens), exllamav3/GLM (CLOCK).

### 3.3 Coste real de un miss

- DeepSeek expert (~11 MB) en CPU AVX2: **0.42-0.46 ms**
- GLM expert 9.4 MB por PCIe 3.0: ~0.75 ms
- MiniMax ~18 MB por PCIe: 1.4-1.5 ms
- 1 capa decode MiniMax completa: 0.4-0.7 ms

En DeepSeek y MiniMax el path CPU ganó (incluso con 2 canales RAM). En GLM el path PCIe fue mejor bajo carga.  
**Claves:** coste real del build de CPU (flag `GGML_IQ1_NO_PDEP` dio 3.6× en Zen 2) y calibración **bajo carga**, no en idle.

### 3.4 Parallelismo

- **Offloaded experts → layer-split** (Strata / Maya forks).
- **Todo en VRAM → Tensor Parallel**.
- Expert Parallel puro en decode es malo; en prefill con offloading es excelente.

### 3.5 Speculative decoding y agentes

Ganancias típicas 1.2–1.5× (mucho más modestas que en densos). Con skew débil las ventanas largas dan poco.  
En sesiones reales de agentes (DeepSeek, 295 turns, hasta 279 K): **77 % del tiempo es generación**, solo 23 % lectura. Median new prompt tokens/turn ≈ 243.

### 3.6 Política de quants y corte de expertos

Más bits → menos expertos en VRAM → más misses.  
Calidad se degrada a ritmos muy distintos (GLM es mucho más sensible que Qwen).  
**Recomendación fuerte:** preferir bajar bits a cortar expertos. Cortar por frecuencia es casi siempre peor que perder 1 bit en todos. REAP (router weight × norm) es mucho mejor selector, pero incluso así mantener todos los expertos en RAM es preferible mientras quepa.

---

## 4. Estado MEASURED en LEONES (hardware de referencia)

**Equipo de referencia:** MSI Thin 15 B12UC · Intel Core i7-12650H · 14 GiB RAM · NVIDIA RTX 3050 Laptop 4 GiB (sm_86) · Ubuntu · driver 580.178.04 · CUDA 13.0.

Fuente canónica: [`docs/benchmarks/INVENTARIO_MODELOS_Y_MOTORES.md`](../docs/benchmarks/INVENTARIO_MODELOS_Y_MOTORES.md) (última consolidación 2026-11-12).

### 4.1 Modelos MoE ejecutados o medidos

| Modelo | Motor | Estado | Notas / métricas clave | Informe / artefacto |
|--------|-------|--------|------------------------|---------------------|
| **Qwen3-30B-A3B** (IQ3_XXS y variantes) | llama.cpp CUDA, RustingStrata | Ejecutado y medido | Sweeps ngl=0/1/8; ngl=1 mejor mediana PP128. RustingStrata híbrido CPU/GPU experts. | Informes de 2026-10 y artefactos en `docs/reports/` |
| **Qwen3.5-35B-A3B** IQ2_XXS | Tandem / llama.cpp CPU-MoE | Ejecutado y medido | Decode ~35,6 tok/s (prueba no-thinking). Evidencia bruta pendiente de consolidación completa. | Inventario §1 y §3 |
| **Clover-35B-A3B-Preview** IQ2_S | llama.cpp CUDA | Ejecutado (experimental) | MoE + difusión por bloques. No cabe íntegramente en 4 GB. | [`research/clover-35b-a3b-preview-experimental-2026-10.md`](../research/clover-35b-a3b-preview-experimental-2026-10.md) |
| **Qwen3.6-35B-A3B** UD-Q2_K_XL | RustingStrata | Evaluado documentalmente; prueba MSI pendiente | Motor admite Ampere sm_80+. Referencia publicada en RTX 3060 12 GiB. | Inventario §3.6 |
| **LFM3-1.7B** y LFM2.5-8B-A1B | Kinetic, Pithos, llama.cpp | Ejecutado y medido | Kinetic: PP512 4.371 tok/s, TG128 137,56 tok/s (MSI). | Inventario y logs locales |
| **MiniCPM5-2B** Q4_K_M | llama.cpp CUDA | Ejecutado y medido | CUDA ctx 2048: ~817 / 85,5 tok/s. | Informe 11-11-2026 |

### 4.2 Motores con soporte MoE relevante en LEONES

| Motor | Estado en MSI | Capacidades MoE destacadas | Notas |
|-------|---------------|----------------------------|-------|
| **llama.cpp CUDA** | Ejecutado y medido | `--n-cpu-moe`, offload de expertos, sweeps ngl | Base sólida. Builds locales disponibles. |
| **RustingStrata** | Ejecutado en otros modelos; Qwen3.6 pendiente | Hybrid CPU/GPU experts, placement adaptativo, NVRTC, MTP | Alineado con las conclusiones de @superalesha. |
| **Tandem / CPU-MoE** | Ejecutado | Offload agresivo a CPU | 35,6 tok/s en Qwen3.5-35B-A3B. |
| **Project Maya / Strata** | Investigación documental ampliada; no ejecutado | Engines especializados por familia, live cache, expert profiles | Requiere ≥32 GB RAM física. No viable en el MSI actual (14 GiB). Ver Inventario §3.7 y PR #142. |
| **Colibri (fork)** | Desarrollo; pruebas MSI pendientes | Presupuesto de expertos CUDA, chain planner | Rama `research/qwen36-cuda-chain-planner`. |
| **Kinetic / Pithos** | Ejecutado | Backends CUDA / OpenCL / Vulkan | Útiles para modelos más pequeños y validación multi-backend. |
| **TensorFold** | Ejecutado en densos; estudios MoE | MLX → CUDA, offload | Compilación adicional fallida en lote 11-11. |

**Regla LEONES:** Solo una ejecución física autorizada produce **MEASURED**. Todo lo demás es ESTIMATED o RESEARCH_ONLY.

---

## 5. Tabla de lanzamientos MoE relevantes (oct 2025 – nov 2026)

Ordenados por fecha aproximada (más recientes primero). Memorias teóricas para Q4_K_M en llama.cpp.

| Fecha (aprox.) | Modelo | Laboratorio | Total / Activos | Contexto | Memoria teórica Q4 | Características y usos preferidos | Estado LEONES |
|----------------|--------|-------------|-----------------|----------|--------------------|-----------------------------------|---------------|
| Oct–Nov 2026 | **Mellum2.1** (12B-A2.5B) | JetBrains | 12 B / 2.5 B | 131 K | ~7–8 GB | Código / agentes. Apache-2.0. Ideal local. | Candidato prioritario |
| Oct 2026 | **Clover-35B-A3B-Preview** | DiffuSpace | 35 B / ~3 B | 128 K | ~19–21 GB | MoE + difusión. Experimental. | Ejecutado (experimental) |
| Oct 2026 | **Beam** (501B-A23B) | Reflection AI | 501 B / 23 B | 1 M | ~280–300 GB | Razonamiento + coding agentic. | ESTIMATED |
| Sep–Oct 2026 | **Ling-3.1-flash** | inclusionAI | 560 B / ~25 B | 256 K–1 M | ~310–330 GB | Reasoning / agentes. | ESTIMATED |
| Sep 2026 | **MiMo-V2.6-Pro / Flash** | Xiaomi | 1.02 T / 42 B · 309 B / 15 B | 1 M | 170–600 GB | Líder open-weight multimodal. | ESTIMATED |
| Ago 2026 | **DeepSeek-V4-Pro / V4.1-Flash** | DeepSeek | 1.65 T / 49 B · 284–552 B / 8–16 B | 1 M | 160–900+ GB | Flagship coding + agentic. DSpark. | ESTIMATED (Maya) |
| Ago 2026 | **Qwen3.8-2.4T-A95B / Flash-Next** | Alibaba | Hasta 2.4 T / 95 B | 256 K–1 M | Variable | Familia Qwen máxima. | ESTIMATED / RustingStrata |
| Jun–2026 | **GLM-5.2 / 5.3** | Z.ai | ~753 B | 1 M | ~420 GB | Coding + agentic. | ESTIMATED (Maya) |
| 2026 | **Qwen3-VL / 30B-A3B / 35B-A3B / 235B-A22B** | Alibaba | 30 B-A3B … 235 B-A22B | 256 K–1 M | 18–130 GB | Multimodal, GUI agents, thinking. | **MEASURED** (30B/35B) |
| 2025–2026 | **Llama 4 Maverick / Scout**, **Kimi K2/K3**, **MiniMax-M***, etc. | Varios | 100 B–2.8 T | 128 K–1 M | Variable | General, reasoning, coding. | ESTIMATED |

> Las cifras de “activos” varían según fuente (prefill vs decode, shared experts). Las memorias son estimaciones; la medición real es la única evidencia válida.

---

## 6. Características técnicas destacadas 2026

### 6.1 Arquitectura
- Fine-grained MoE: cientos de expertos pequeños (256–512) + top-6/8/10 + 1 shared.
- Atención híbrida: MLA, CSA/HCA, Sparse Attention, a veces Mamba/SSM o Gated DeltaNet (Clover, Qwen3.6).
- Contextos largos nativos con KV-cache comprimido.
- Modos duales: thinking / non-thinking, tool-calling nativo, speculative decoding (DSpark, MTP, DFlash2).

### 6.2 Multimodalidad
- Texto + imagen nativa (DeepSeek-V4.1-Flash, MiMo, Qwen3-VL, MiniCPM-V).
- Vision encoder separado + backbone MoE.
- Vídeo/audio todavía experimental en la mayoría.

### 6.3 Usos preferidos

| Tipo de uso | Modelos más adecuados (2026) | Notas LEONES |
|-------------|------------------------------|--------------|
| **Razonador / Thinking** | DeepSeek-V4-Pro, Kimi K3, GLM-5.3, MiMo-V2.6-Pro, Beam | Offload + live cache obligatorios |
| **Código / Agentes** | Mellum2.1, DeepSeek-V4, GLM-5.x, MiniMax-M*, Qwen3-Coder | Sweet-spot consumer: Mellum2.1 y Qwen3-30B/35B-A3B |
| **Imagen / VLM** | Qwen3-VL, DeepSeek-V4.1-Flash, MiMo-V2.6, MiniCPM-V 4.7 | MiniCPM5 ya medido en MSI |
| **Local / Consumer (≤24 GB)** | Mellum2.1, Qwen3-30B-A3B / 35B-A3B, EMO, LFM*, Clover (experimental) | Prioridad de medición LEONES |

---

## 7. Consideraciones prácticas para LEONES / FitLLM / motores

1. **Memoria real vs teórica**  
   Un 30 B-A3B a Q4 cabe en 24 GB. Modelos >100 B necesitan offloading + live cache o multi-GPU + mucha RAM.

2. **Recomendación de selección por hardware**
   - ≤ 8–12 GB VRAM + 16–32 GB RAM → Qwen3-30B-A3B / 35B-A3B (IQ2/IQ3), Mellum2.1, LFM*, MiniCPM.
   - 24–48 GB VRAM → hasta ~100–150 B total con offload moderado.
   - ≥ 64–96 GB VRAM + 128–256 GB RAM → DeepSeek-V4-Flash / GLM-5.3-Flash / Qwen3.8-Flash-Next con Maya/Strata o RustingStrata.

3. **Evidencia vs estimación**  
   LEONES distingue estrictamente ESTIMATED (FitLLM / HF cards / estudios externos) de MEASURED (ejecución física en hardware documentado). Este documento combina ambos; las cifras de @superalesha son MEASURED en su rig; las del MSI son MEASURED en el equipo de referencia de LEONES.

4. **Licencias**  
   MIT / Apache-2.0 dominan (DeepSeek, Xiaomi, JetBrains, Reflection, Aleph Alpha, Z.ai, Clover). Algunas familias Qwen tienen restricciones comerciales según variante.

5. **Checklist de despliegue MoE (adaptado de @superalesha + experiencia LEONES)**
   1. Medir Triad, H2D copy y P2P del equipo.
   2. Dump de router picks (prefill y decode separados) en 5–10 K tokens de tráfico real o sintético representativo.
   3. Calcular curva top-N coverage y simular hits estático vs random.
   4. Construir y validar expert-profile de dominio (split temporal).
   5. Añadir live cache con decay encima del placement estático.
   6. Decidir CPU vs PCIe bajo carga real (no en idle).
   7. Layer-split si hay offload; TP si cabe todo en VRAM.
   8. Añadir drafter + cutoff de confianza + vocabulario adecuado al idioma.
   9. Medir en replay de sesiones reales + generación libre (umbrales escritos antes).
   10. No cortar expertos mientras quepan en RAM; preferir ajustar bits.

---

## 8. Conclusiones y recomendaciones para el ecosistema LEONES

- **MoE es el camino dominante** para escalar capacidad manteniendo coste de inferencia razonable.
- La **calidad por parámetro activo** ha mejorado drásticamente.
- El cuello de botella real en hardware local es la **jerarquía de memoria y el skew del router**, no solo los FLOPs activos.
- Para LEONES el foco debe ser:
  1. Detectar hardware real (VRAM + RAM + anchos de banda).
  2. Filtrar por memoria estimada + ratio de sparsidad + soporte de offload/live-cache del motor.
  3. Preferir modelos con GGUF / formatos listos para llama.cpp, RustingStrata, TensorFold o Maya.
  4. Medir tokens/s y calidad en el hardware del usuario (MEASURED) antes de recomendar.
  5. Incorporar expert-profiles y live-cache como técnicas de primera clase.

**Próximos pasos sugeridos para el atlas y el Inventario:**
- Añadir campos `total_params`, `active_params`, `sparsity`, `moe_experts`, `moe_topk`, `observed_skew`, `live_cache_support` al schema de recomendaciones.
- Priorizar medición de Mellum2.1 y Qwen3.6-35B-A3B en el MSI.
- Validar Clover-35B-A3B-Preview como caso de estudio de MoE + difusión (ya iniciado).
- Documentar y archivar completamente la evidencia bruta de Tandem CPU-MoE y los logs de Kinetic.
- Evaluar integración opcional de técnicas de live-cache / expert-profile en los motores que LEONES ya usa (especialmente RustingStrata y futuros forks de Maya/Strata).
- Mantener Project Maya como RESEARCH_ONLY hasta que exista hardware con ≥32 GB RAM física en el laboratorio.

---

## 9. Fuentes principales

### Evidencia empírica primaria
- Alexey Fateev (@superalesha) — hilo completo del 12 Nov 2026: https://x.com/superalesha/status/2120840758223688028
- Inventario maestro LEONES: [`docs/benchmarks/INVENTARIO_MODELOS_Y_MOTORES.md`](../docs/benchmarks/INVENTARIO_MODELOS_Y_MOTORES.md) (2026-11-12)
- Informes de ejecución Qwen3-30B-A3B, Clover-35B, MiniCPM5-2B, Kinetic LFM3, Pithos, Tandem CPU-MoE (carpeta `docs/reports/` y `docs/experimental/`)

### Fuentes de lanzamientos y arquitectura
- llm-releases.com / changelog
- Hugging Face model cards (DeepSeek, Qwen, Xiaomi MiMo, JetBrains, DiffuSpace/Clover, AllenAI/EMO…)
- Documentación de RustingStrata, Project Maya / Strata, llama.cpp, Colibri
- Papers y surveys: EMO (AllenAI), LatentMoE, Marco-MoE, Dist-MoE, surveys 2024-2026 sobre sparse expert models

### Motores y técnicas
- RustingStrata (hybrid experts, adaptive placement)
- Project Maya / Strata (live cache, expert profiles, layer-split)
- llama.cpp (`--n-cpu-moe`, offload)
- Técnicas relacionadas: REAP, CLOCK, LFU con decay, DSpark / MTP / DFlash2

---

*Documento generado y mantenido para el ecosistema LEONES.  
Toda cifra de memoria teórica es ESTIMATED.  
La medición real en hardware documentado es la única evidencia válida (MEASURED).  
La distinción ESTIMATED ≠ MEASURED es sagrada.*
