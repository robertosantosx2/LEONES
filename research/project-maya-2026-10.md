# Project Maya — Investigación para LEONES (octubre 2026)

**Fecha**: 2026-10-20  
**Fuente**: GitHub oficial mw00/project-maya, releases v1.1.16, README, CHANGELOG, X (@PeasantSmith), mediciones de usuarios y documentación interna  
**Contexto LEONES**: prospección de runtimes de inferencia MoE locales con expert offloading (VRAM → RAM → NVMe), cuantizaciones de alta fidelidad y soporte multi-GPU / multi-vendor para FitLLM, ODS y perfiles de hardware reales.

---

## 1. ¿Qué es Project Maya?

**Project Maya** es un motor de inferencia open-source (MIT) creado y liderado por **Peasant Smith** (@mw00 / @PeasantSmith), co-mantenido con @needmorevram.

Objetivo: ejecutar **modelos MoE de tamaño datacenter** de forma **privada y local** en el hardware que el usuario ya tiene (incluyendo hardware antiguo o modesto).

- **Repositorio**: https://github.com/mw00/project-maya
- **Primera release**: ~2026-10-07 (v1.0.0)
- **Versión actual analizada**: **v1.1.16** (19 oct 2026)
- **Enfoque técnico clave**:
  - Expertos en tiers (VRAM → RAM → SSD NVMe)
  - Cuantizaciones propias de alta fidelidad (Maya-S / Maya-M / Maya-L)
  - Soporte NVIDIA (principal) + AMD experimental
  - Linux + Windows (experimental)
  - API OpenAI + Anthropic compatible
  - Chat web + monitor de hardware en tiempo real
  - Soporte de visión, tool calling y varias peticiones en paralelo

Nada sale de la máquina.

---

## 2. Modelos soportados

### 2.1 GLM-5.3-Flash (zai-org, MIT)

- **321B parámetros totales**, ~18B activos por token
- Contexto hasta **1M tokens**
- Cuantizaciones oficiales de Project Maya (hechas desde el FP8 original):

| Variante          | Tamaño en disco | Orientado a                          | Fidelidad vs FP8 (zero-shot / next-token) |
|-------------------|-----------------|--------------------------------------|-------------------------------------------|
| **Maya-S** (default) | 96.5 GB        | Pools de memoria más pequeños       | 97.9 % / ~83 %                           |
| **Maya-S24**      | 94.7 GB        | Tarjetas de **24 GB o menos**       | 97.7 % / ~83 % (+14 % decode en 24 GB)   |
| **Maya-M**        | 116 GB         | Más memoria / tool calls / código   | 97.9 % / ~86 %                           |
| **Maya-M-Derisked** | 116 GB       | Maya-M + edit anti-refusals (experimental) | No medido aún                         |
| **Maya-L**        | 156.3 GB       | Máxima fidelidad                    | **99.2 %** / ~90 %                       |

También acepta EXL3 comunitarios (3.05 bpw ~125 GB y 4.05 bpw ~165 GB) de forma experimental.

### 2.2 DeepSeek-V4.1-Flash-1017 (DeepSeek, MIT) — nuevo en v1.1.16

- **748B parámetros** (552B backbone + Engram)
- Activa ~8B (prefill) / ~16B (decode)
- Contexto 1M tokens
- Motor propio (`maya-ds4`)

| Variante                  | Tamaño en disco                  | Hardware mínimo / notas                          |
|---------------------------|----------------------------------|--------------------------------------------------|
| **Maya-S** (recomendado)  | 178 GB + Engram tables (~203 GB) → **~380-390 GB total** | NVIDIA Volta+ y AMD. Cualquier cantidad de memoria (offload a RAM/SSD) |
| unsloth GGUF Q8           | ~508 GB                         | Mismo soporte                                    |
| unsloth GGUF Q4           | ~501 GB                         | Menos VRAM en la parte densa                     |
| LibertAIDAI EXL3 2.9 bpw  | ~414 GB                         | Solo NVIDIA RTX 30 / A100 o más nuevas           |

Fidelidad Maya-S: **92.6 % same next-token** vs original (KL 0.12).

---

## 3. Requisitos de hardware (oficiales + comportamiento real)

### Requisitos generales
- **GPU**: NVIDIA compute capability ≥ 7.0 (V100, RTX 20+). Hasta 16 GPUs.  
  AMD experimental: RX 7900 XT/XTX, Radeon AI PRO R9700 / RX 9070, Strix Halo / Gorgon Halo.
- **RAM**: mínimo **32 GB** (más = más expertos cerca = más velocidad).
- **Disco**: **SSD NVMe rápido** obligatorio (no HDD).
- **Sistema**: Linux (recomendado). Windows 10/11 experimental. CUDA 12.x / ROCm 7.

### Comportamiento de memoria (clave para LEONES)
Maya **no necesita** que el modelo quepa entero en VRAM.  
Los expertos más usados van a GPU, los siguientes a RAM y el resto se leen del SSD bajo demanda.  
Por eso puede correr modelos de cientos de GB en tarjetas de 12-24 GB (más lento, pero funcional).

**Espacio en disco aproximado**:
- GLM Maya-S / S24 → ~100 GB
- GLM Maya-L → ~160 GB
- DeepSeek Maya-S → ~390 GB
- DeepSeek GGUF → ~500-520 GB

---

## 4. Velocidades reales reportadas (usuarios + mantenedor)

| Hardware                                      | Modelo          | Decode (tok/s) | Prefill 8K (tok/s) | Notas                  |
|-----------------------------------------------|-----------------|----------------|--------------------|------------------------|
| 4× RTX 4090 24 GB                             | Maya-S24        | **118**        | 4129               | Mejor resultado actual |
| 1× RTX PRO 6000 Blackwell 96 GB               | Maya-M          | **81**         | 3102               |                        |
| 2× CMP 170HX 64 GB                            | Maya-M (full VRAM) | 61.3        | 514                |                        |
| 2× RTX 3090                                   | Maya-S24        | 53             | 885                |                        |
| 2× Tesla V100 32 GB                           | Maya-S / S24    | 40-54.5        | 542-670            |                        |
| 1× RTX 5090 32 GB                             | Maya-M          | 30+            | ~2000              |                        |
| 1× Tesla V100 32 GB + ~64 GB RAM              | Maya-S          | ~19-27         | hasta 620          |                        |
| AMD Radeon 8065S (Strix Halo, 160 GB unified) | Maya-S          | hasta 29.6     | 278                | Windows                |

DeepSeek Maya-S en hardware limitado (1× RTX 3090 + 64 GB RAM) baja a ~4-5 tok/s de respuesta (aceptable para pruebas, lento para uso intensivo).

---

## 5. Relevancia para LEONES / FitLLM / ODS

### Puntos fuertes para LEONES
- **Expert offloading real** (VRAM → RAM → NVMe) → perfil perfecto para hardware-aware recommendation.
- Cuantizaciones de alta fidelidad documentadas (97.7-99.2 % zero-shot en GLM).
- Soporte multi-GPU hasta 16 cards + AMD experimental.
- API OpenAI/Anthropic + tool calling → fácil de integrar en stacks ODS / agentes.
- Monitor de hardware en tiempo real (dónde viven los expertos).
- Instalación one-command (`./setup.sh` / `START-MAYA.bat`) que detecta hardware y recomienda variante.

### Posición en el mapa LEONES

| Perfil de hardware                  | Recomendación estimada                          | Comentario |
|-------------------------------------|--------------------------------------------------|------------|
| GPU débil / poca VRAM (12-24 GB) + SSD NVMe | Maya-S / Maya-S24 (GLM)                         | Viable y usable |
| 1-2× RTX 3090/4090 + 64-128 GB RAM  | Maya-M o Maya-L (GLM) / Maya-S (DeepSeek)       | Buen rendimiento |
| Multi-GPU potente (4× 4090+)        | Maya-S24 / Maya-L                               | 50-118+ tok/s |
| Hardware muy limitado (≤ 32 GB RAM total) | Mejor Edge0 u otros edge runtimes               | Maya necesita ≥ 32 GB RAM mínimo |
| Solo AMD (Strix Halo / 7900)        | Experimental (Maya-S)                           | Funciona, menos maduro |

**Regla LEONES**: marcar siempre como **ESTIMATED** hasta tener ejecución física y benchmark A01 → **MEASURED** en el hardware real del usuario.

### Posibles integraciones futuras
1. Añadir Project Maya como runtime candidato en el catálogo de ODS.
2. Perfil FitLLM para GLM-5.3-Flash (Maya-S/S24/M/L) y DeepSeek-V4.1-Flash-1017 Maya-S.
3. Captura de configuración (cuántos expertos en VRAM/RAM/SSD, split de capas, etc.).
4. Benchmark LEONES estandarizado contra los números publicados por usuarios.

---

## 6. Enlaces útiles

- Repositorio: https://github.com/mw00/project-maya
- Release v1.1.16: https://github.com/mw00/project-maya/releases/tag/v1.1.16
- Hugging Face (cuants Maya): https://huggingface.co/peasantsmith
- Autor: https://x.com/PeasantSmith
- Documentación de setup: `docs/SETUP.md`
- Documentación AMD: `docs/AMD_MAYA.md`
- Documentación Windows: `docs/WINDOWS.md`

---

## 7. Conclusión para LEONES

**Project Maya** es actualmente uno de los runtimes más interesantes para **MoE grandes en hardware de consumo** con offloading real a SSD.  
Complementa muy bien a Edge0 (ultra-baja memoria) y a TensorFold / vLLM (alta velocidad con mucha VRAM).

- Para **GLM-5.3-Flash** ya es maduro y usable.
- Para **DeepSeek-V4.1-Flash-1017** es muy reciente (v1.1.16) y todavía experimental en velocidad/calidad en hardware limitado.

Recomendación: incluirlo en el atlas de runtimes de LEONES como candidato **ESTIMATED** para perfiles “MoE grande + SSD NVMe + ≥ 32 GB RAM”, y priorizar mediciones físicas (MEASURED) en las siguientes olas de beta.

---

*Documento generado para investigación LEONES · 2026-10-20*  
*Basado en datos oficiales de Project Maya v1.1.16 y reportes de usuarios*