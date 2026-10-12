# INVESTIGACIÓN · MiniCPM-V 4.7 — RTX y umbral ~25 tok/s

**Fecha:** 2026-10-12  
**Tipo:** ESTIMATED (no MEASURED)  
**Fuente primaria:** [OpenBMB / @sudoingX](https://x.com/sudoingX/status/2109722692282917026) + release oficial MiniCPM-V 4.7  
**Contexto LEONES:** atlas de evidencia externa para preselección FitLLM / hardware discovery.  
**Regla de autoridad:** esta nota es **ESTIMATED**. Solo una ejecución física autorizada en hardware real produce **MEASURED**.

---

## Modelos analizados

| Modelo | Arquitectura | Tamaño GGUF relevante | Notas |
|--------|--------------|-----------------------|-------|
| **MiniCPM-V 4.7 35B-A3B** | MoE (~35B total / ~3B activos) + visión | Q4_K_M ≈ **21.2 GB** · mixed 3-bit ≈ **15.5 GB** (+ mmproj ~1 GB) | Primer MoE open-source con LES (Lookahead Expert Scheduling). Corre a 13–17+ tok/s en iPhone/iPad con ~3 GB. |
| **MiniCPM-V 4.7 1B** | Denso ligero + visión | Q4 ≈ **0.67 GB** + mmproj ≈ **1.1 GB** (~1.8–2.5 GB en práctica) | Extremadamente eficiente. |

Soporte day-0 en llama.cpp (upstream merge previo al lanzamiento). Disponibles BF16, FP8, INT4, AWQ, GPTQ y full set GGUF.

---

## Metodología de estimación

- Benchmarks públicos de MoE similares (Qwen3 / 3.5 / 3.6 30B-A3B y 35B-A3B) en llama.cpp Q4_K_M + flash-attn + KV cuantizado cuando posible.
- Los MoE con ~3B activos se comportan mucho más rápido que densos de 30–35B.
- Contexto moderado (4–8K). Visión (mmproj) añade overhead; 16× compression alivia.
- Umbral de referencia: **≥ 25 tok/s** (fluidez aceptable para chat local).
- **No** se reclama MEASURED. Variaciones esperadas por driver, contexto exacto, speculative decoding (DSpark) y quant final.

---

## Tabla estimada (tok/s aproximados)

| GPU RTX | VRAM | 35B-A3B Q4_K_M (21.2 GB) | 35B-A3B 3-bit (15.5 GB) | 1B Q4 (~2 GB) | ¿≥ 25 tok/s? |
|---------|------|---------------------------|--------------------------|---------------|--------------|
| **RTX 5090** | 32 GB | 140–180+ | 160–200+ | 400–600+ | Sí (ambos) |
| **RTX 4090** | 24 GB | 100–140 | 120–160 | 300–450+ | Sí (ambos) |
| **RTX 3090 / 3090 Ti** | 24 GB | 90–130 | 110–150 | 250–400+ | Sí (ambos) |
| **RTX 4080 / 4080 Super** | 16 GB | Offload parcial (~40–70) | ~70–100 | 250–400+ | Sí (1B + 3-bit cómodo; Q4_K_M justo) |
| **RTX 4070 Ti Super / 4070 Ti** | 16 GB | Offload (~30–60) | ~60–90 | 200–350+ | Sí (1B + 3-bit; Q4_K_M borderline) |
| **RTX 4070 / 4070 Super** | 12 GB | Offload pesado (<30) | Offload (~40–70) | 180–300+ | Sí solo 1B (y 3-bit con offload) |
| **RTX 4060 Ti 16GB** | 16 GB | Offload (~25–50) | ~50–80 | 180–300+ | Sí (1B + 3-bit) |
| **RTX 4060 Ti 8GB / 4060** | 8 GB | No práctico | Offload pesado | 150–250+ | Sí solo 1B |
| **RTX 3080 12GB / 3070** | 8–12 GB | No | Offload muy lento | 120–200+ | Sí solo 1B |

---

## Resumen operativo (para FitLLM / preselector)

### MiniCPM-V 4.7 35B-A3B
- **≥ 25 tok/s cómodo:** RTX 4090 / 3090 / 5090 (Q4_K_M o 3-bit).
- **Posible ≥ 25 tok/s:** RTX 4080 / 4070 Ti 16 GB (preferir mixed 3-bit 15.5 GB).
- < 16 GB → offload a RAM/CPU; cae fácilmente bajo 25 tok/s (especialmente con visión).

### MiniCPM-V 4.7 1B
- Corre a **>> 25 tok/s** (fácilmente 150–400+) en **cualquier RTX moderna**, incluso 8 GB.
- Candidato “plug & play” para hardware modesto.

---

## Notas de implementación LEONES

- Marcar siempre como **ESTIMATED** hasta que exista evidencia MEASURED de una ejecución física autorizada.
- Útil para el preselector FitLLM: filtrar candidatos por VRAM observada + umbral de throughput deseado.
- El modelo 35B-A3B destaca por LES + cuantización fina de expertos → memoria real mucho menor que el total de parámetros en dispositivos edge.
- Próximo paso recomendado: cuando se autorice, medir en hardware real (llama.cpp + Q4_K_M / 3-bit) y archivar como evidencia MEASURED en `artifacts/` o atlas empírico.

---

**Autor de la nota:** análisis generado a partir de release OpenBMB + benchmarks públicos de MoE análogos (2026-10).  
**Estado:** ESTIMATED · listo para ingestión en atlas / FitLLM.
