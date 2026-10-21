# AMD BC-250: Características técnicas, inferencia LLM y clusters de IA locales

**Ficha de prospección / investigación** — LEONES · Fuentes de conocimiento  
Fecha de captura: 2026-10-21  
Estado: ESTIMATED + evidencia comunitaria (no medición LEONES propia)

---

## Resumen ejecutivo

La **AMD BC-250** es una placa de minería excedentaria basada en un APU semi-custom de la familia PS5 (“Oberon” / “Cyan Skillfish”, gfx1013). Combina CPU Zen 2 + GPU RDNA 2 con **16 GB GDDR6 unificada**. La comunidad la ha convertido en una plataforma barata y viable para **inferencia local de LLMs** (Vulkan + llama.cpp / Ollama) y **clusters** mediante RPC de llama.cpp.

Es especialmente atractiva por el ratio precio / memoria / ancho de banda y por la madurez de los unlocks comunitarios (8 núcleos CPU + hasta 40 CUs GPU).

---

## Características técnicas

| Componente | Especificación |
|------------|----------------|
| **CPU** | Zen 2 (“Oberon”), 6c/12t de fábrica (~3,5 GHz). Desbloqueable a 8c/16t (hasta ~3,9-4,0 GHz) |
| **GPU** | RDNA 2 / “RDNA 1.5” (gfx1013 / Cyan Skillfish). 24 CUs de fábrica; hasta 40 CUs desbloqueables |
| **Memoria** | 16 GB GDDR6 UMA, bus 256-bit, ~14 Gbps → ~448 GB/s teóricos (medidos ~350-410 GB/s) |
| **Almacenamiento** | 1× M.2 2280 (PCIe 2.0 ×2 o SATA III, ~1 GB/s máx.) |
| **I/O** | 1× DisplayPort 1.4, 2× USB 3.0, 2× USB 2.0, 1× GbE |
| **Alimentación** | 1× PCIe 8-pin (12 V). TDP ~220 W; real 50-85 W idle, 160-235 W carga |
| **Formato** | Placa de minería personalizada (~310-340 × 115 mm) |
| **OS** | Linux (Mesa/RADV Vulkan). Windows sin drivers GPU oficiales |

**Notas importantes**:
- FPU recortada (similar a PS5) → ~15 % menos rendimiento en cargas AVX2 pesadas.
- VCN (video encode/decode) bloqueado.
- Requiere refrigeración activa y buena PSU en el rail de 12 V (≥300 W recomendado).
- Kernel y TTM (`ttm.pages_limit`) deben ajustarse para aprovechar los 16 GB unificados.

---

## Inferencia de LLMs

**Backend principal**: Vulkan (llama.cpp + Mesa/RADV). ROCm/HIP experimental.

**Rendimientos típicos comunitarios** (llama.cpp Vulkan, quant Q4/IQ2-IQ4, 24-40 CUs):

- 7-9B densos: ~50-80+ tok/s
- 14B densos: ~20-35 tok/s
- MoE Qwen3.x 30-35B-A3B (~3B activos): **55-80+ tok/s**
- GPT-OSS 20B / similares: 45-87 tok/s
- Híbridos Mamba (Granite 4.0-H Tiny): 100-130 tok/s
- Densos 27-32B: 10-20 tok/s
- Contexto largo: muchos modelos llegan a 64K-100K+

El unlock a 40 CUs aporta ~1,3× en generación y ~1,5× en prefill de media.

**Motores recomendados**:
- llama.cpp (Vulkan) — principal
- Ollama (capa fácil sobre Vulkan)
- llmtune (control de flotas y perfiles por arquitectura)
- forks optimizados para gfx1013
- stable-diffusion.cpp para imagen

**Modelos ideales**: MoE de pocos parámetros activos (Qwen 3.x A3B), 7-14B densos de calidad, híbridos Mamba para contexto largo.

---

## Clusters de IA

Viable y económico. Cada placa es un nodo completo (CPU + GPU + 16 GB).

- Método: **llama.cpp RPC** (layer / model parallelism) sobre Ethernet (1 GbE de serie; se recomienda 2,5 GbE).
- Ejemplos comunitarios:
  - 2 placas → Qwen3.6-35B-A3B Q4 ~60 tok/s @ 64K
  - 4 placas (~500 USD) → Next Flash IQ3_XXS ~60-70 tok/s @ 100K; o 2 instancias 35B-A3B ~145 tok/s
  - 6 placas → combinaciones Flash + 35B
- Herramientas: **llmtune** (netboot PXE, control de modelos, clustering).

Limitaciones: latencia de red, generación no escala linealmente, gestión de calor y potencia.

---

## Enlaces a repositorios, documentación y hilos relevantes

### Documentación y guías principales
- [AMD BC250 Documentation (elektricM)](https://elektricm.github.io/amd-bc250-docs/) — documentación canónica comunitaria
- [SkillFishOS – Hardware BC-250](https://skillfishos.com/en/docs/hardware-bc250/)
- [akandr/bc250](https://github.com/akandr/bc250) — guía completa Ollama + Vulkan + benchmarks + Signal bot
- [oldrigrevive – Guía AMD BC-250](https://oldrigrevive.com/guides/amd-bc-250/) (también [versión ES](https://oldrigrevive.com/es/tutoriales/tarjeta-amd-bc-250/))
- [katzzero/bc250-unofficial-community-guide](https://github.com/katzzero/bc250-unofficial-community-guide)
- [mothenjoyer69/bc250-documentation](https://github.com/mothenjoyer69/bc250-documentation)
- [bc-250.com Wiki – AI Inference](https://bc-250.com/wiki?article=linux%2F12-ai-inference)

### Unlocks y herramientas de hardware
- [bc250-40cu-unlock](https://github.com/duggasco/bc250-40cu-unlock) (y variantes comunitarias)
- cyan-skillfish-governor (SMU)
- bc250_memcfg (ajuste de split UMA)

### Inferencia y clustering
- [cachenetics/llmtune](https://github.com/cachenetics/llmtune) — motor de inferencia + control plane de flotas para BC-250
- [TechMakesArt/llama.cpp-bc250](https://github.com/TechMakesArt/llama.cpp-bc250) — fork con optimizaciones Vulkan gfx1013
- [TobiaszJ/qw6](https://github.com/TobiaszJ/qw6) — motor nativo para Qwen 3.6-35B-A3B en BC-250
- [akandr/bc250-rocm](https://github.com/akandr/bc250-rocm) — investigación ROCm/HIP vs Vulkan

### Artículos y reseñas
- [Tom’s Hardware – Benchmarking AMD’s BC-250](https://www.tomshardware.com/pc-components/cpus/benchmarking-amds-bc-250-offering-steam-machine-like-performance-at-half-the-price-unlocking-40-cus-eight-zen-2-cores-on-the-repurposed-ps5-apu)
- [Hackaday – Re-Enable All Compute Units](https://hackaday.com/2026/06/09/re-enable-all-compute-units-on-the-ps5-like-bc-250-cryptomining-card/)
- [Aftermath – Bless The BC250](https://aftermath.site/bc250-steam-machine-budget-computer/)
- [VideoCardz – 40 CU unlock](https://videocardz.com/newz/amd-bc-250-ps5-apu-unlock-exposes-all-40-gpu-cus-for-budget-steam-machine-alternative)

### Hilos de comunidad (Reddit / LocalLLaMA)
- [Running Next Flash IQ3_XXS at ~70 tok/s… 4× BC-250](https://www.reddit.com/r/LocalLLaMA/comments/1x2yv1b/running_next_flash_iq3_xxs_at_70_toks_with_100k/)
- [Two BC-250 running Qwen3.6-35B-A3B at 60 tok/s](https://www.reddit.com/r/LocalLLaMA/comments/1wou3gr/my_foray_into_local_ai_two_bc250_ex_mining_apus/)
- [Update on the “Monstrosity” – 6 BC-250 cluster](https://www.reddit.com/r/LocalLLaMA/comments/1wviphh/update_on_the_monstrosity_6_bc250_board_cluster/)
- [r/BC250Gaming](https://www.reddit.com/r/BC250Gaming/)

### X / Twitter (actividad reciente)
Búsquedas útiles: `BC-250 (LLM OR llama.cpp OR Ollama OR cluster OR tok/s)`. Hay posts de clusters de 4-6 placas, comparaciones con P100 y anuncios de AliExpress.

### Otras referencias
- [llama.cpp Vulkan performance discussion](https://github.com/ggml-org/llama.cpp/discussions/10879) (incluye entradas BC-250)
- BIOS community: [gitlab.com/TuxThePenguin0/bc250-bios](https://gitlab.com/TuxThePenguin0/bc250-bios/)

---

## Relevancia para LEONES

- **Hardware de bajo coste** con 16 GB UMA de alto ancho de banda → candidato interesante para perfiles “memory-constrained / bandwidth-friendly” en LLMFit y matrices de hardware.
- Excelente para **MoE de pocos parámetros activos** y modelos híbridos.
- Permite clusters baratos → posible entrada en prospección de “flotas de nodos económicos”.
- Stack actual maduro en Vulkan; ROCm aún experimental → clasificar como runtime Vulkan-first.

**Clasificación LEONES**:
- Tipo: fuente de conocimiento / prospección de hardware
- Nivel de evidencia: comunitaria (benchmarks públicos + repos) — **no** medición física LEONES propia
- Acción sugerida: valorar inclusión en matriz de hardware y en candidatos de runtime locales 2026

---

*Documento generado a partir de investigación web + repositorios comunitarios (2026-10-21). Actualizar cuando aparezcan nuevas mediciones o cambios de driver/Mesa.*
