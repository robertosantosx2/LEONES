# Edge0 — Comparativa con modelos open-source (octubre 2026)

**Fecha**: 2026-10-02  
**Fuente**: investigación local + Artificial Analysis + Hugging Face + model cards oficiales  
**Contexto LEONES**: prospección de runtimes / MoE on-device para ODS y FitLLM.

---

## 1. ¿Qué es Edge0?

**Edge0** es un **framework de inferencia open-source** (Apache 2.0) + dos checkpoints MoE adaptados para correr modelos grandes con memoria activa extremadamente baja.

- **Repositorio**: https://github.com/Edge0-AI/edge0
- **Técnica clave**: SSD expert offloading + Recover-LoRA + prerouter (predicción de routing)
- **Modelos liberados**:
  - `Edge0-35B-A3B-preview` → basado en **Qwen3.6-35B-A3B** (35B total / ~3B activos)
  - `Edge0-8B-A1B-preview` → basado en **Ling 3.0 tiny** (~7.9B total / ~1.2B activos)

**Resultado medido** (Mac mini M4 Pro):
- Edge0-35B → ~2.9 GiB memoria activa · 14.9–17.7 tok/s
- Edge0-8B → ~1.0 GiB memoria activa · 23.9–25.3 tok/s

---

## 2. Tabla comparativa principal

| Modelo | Total / Activos | Memoria activa aprox. | Calidad relativa (vs Edge0-35B) | Velocidad / Eficiencia on-device | Mejor uso | Licencia |
|--------|-----------------|-----------------------|----------------------------------|----------------------------------|-----------|----------|
| **Edge0-35B** | 35B / ~3B | **~2.9 GB** | Base (referencia) | Excelente (15-18 tok/s en Mac) | Edge / móvil / laptop baja RAM | Apache 2.0 |
| **Edge0-8B** | ~8B / ~1.2B | **~1.0 GB** | Inferior | Muy alta (24-25 tok/s) | Ultra-edge / móviles bajos recursos | Apache 2.0 |
| **Qwen3.6-35B-A3B** (base de Edge0) | 35B / ~3B | 15-20+ GB (normal) | Ligeramente superior (+3-4 pts) | Buena (necesita más RAM) | Local / servidor medio | Apache 2.0 |
| **Qwen3.8-27B** | 27B denso | 14-18 GB | Similar / ligeramente superior | Buena | Local fuerte | Apache 2.0 |
| **GLM-5.3-Flash** | 320B / 18B | 40-60+ GB | **Claramente superior** | Media-alta (servidor) | Agentes / coding fuerte | MIT |
| **GLM-5.3** | ~753B / 40B | 80-120+ GB | **Muy superior** | Media (cluster) | Frontier open / agentes complejos | MIT / similar |
| **DeepSeek-V4-Flash** | 284B / 13B | 30-50 GB | **Superior** | Alta | Coding + reasoning eficiente | MIT |
| **DeepSeek-V4-Pro** | 1.6T / 49B | 100+ GB | **Muy superior** | Media | Máxima calidad open actual | MIT |
| **MiMo-V2.6-Flash** | 309B / 15B | 35-55 GB | **Superior** | Alta | Multimodal + agentes | MIT |
| **MiMo-V2.6-Pro** | 1.02T / 42B | 90-130+ GB | **Muy superior** (top open AA Index ~46) | Media | Frontier open multimodal | MIT |

---

## 3. Resumen por categoría (criterio LEONES)

| Categoría | Mejor opción open-source | Comentario vs Edge0 |
|-----------|---------------------------|---------------------|
| **Memoria ultra-baja (1-4 GB)** | **Edge0-35B / Edge0-8B** | Gana por goleada. Ningún otro modelo ~30B+ corre en <3 GB activos |
| **Calidad / Inteligencia** | MiMo-V2.6-Pro > GLM-5.3 > DeepSeek-V4-Pro > Qwen3.8 | Edge0 queda claramente por detrás |
| **Relación calidad/memoria** | **Edge0-35B** | El más eficiente en hardware débil |
| **Coding / Agentes** | GLM-5.3 / DeepSeek-V4 / MiMo-V2.6 | Mucho más fuertes |
| **On-device real (móvil/laptop)** | **Edge0** + Qwen3.8-27B quantizado | Edge0 es el único 30B+ viable en <4 GB |

---

## 4. Benchmarks de calidad Edge0 (OpenCompass – equipo Edge0)

| Benchmark | Edge0-35B (int4) | Base Qwen3.6-35B-A3B (fp16) | Edge0-8B (int4) | Base Ling 3.0 (fp16) |
|-----------|------------------|-----------------------------|-----------------|----------------------|
| AIME 2026 | 86.6 | 92.7 | 63.3 | 73.3 |
| HumanEval | 90.9 | 95.1 | 91.5 | 92.7 |
| GPQA-Diamond | 79.8 | 81.8 | 70.7 | 71.2 |
| MMLU-Pro | 81.0 | 84.6 | **70.1** | 65.8 |
| IFBench | 57.9 | 61.7 | 53.9 | 60.6 |
| **Promedio** | **79.2** | **83.2** | **69.9** | **72.7** |

→ Pérdida de calidad del pipeline Edge0: **~3-4 puntos** respecto al modelo base en fp16 (gracias a Recover-LoRA).

---

## 5. Conclusión para LEONES / ODS / FitLLM

- **Edge0** es el candidato más interesante actual para **perfiles de hardware muy limitados** (móvil, laptop 16 GB, sin GPU potente).
- Su valor no está en la inteligencia absoluta, sino en la **relación calidad / memoria activa**.
- Para stacks ODS con GPU decente o servidor → preferir GLM-5.3, DeepSeek-V4 o MiMo-V2.6.
- Recomendación FitLLM: marcar Edge0 como **ESTIMATED** para perfiles “edge / low-RAM” y exigir MEASURED en ejecución física.

---

## 6. Edge0 vs TensorFold (Qwen3.6-35B-A3B)

**Fecha de actualización**: 2026-10-02  
**Contexto**: prospección de runtimes de alto rendimiento (TensorFold) frente al enfoque ultra-baja memoria de Edge0.

### 6.1 ¿Qué es TensorFold?

- Motor de inferencia open-source (Apache 2.0) centrado en **speculative decoding exacto** (MTP / DFlash2).
- Soporta Apple Silicon (MLX) y NVIDIA GPU (CUDA, CC ≥ 8.9 → RTX 40/50 + Blackwell).
- API compatible OpenAI.
- Kernels escritos a mano por familia de modelos.
- Ya tiene receta oficial para **Qwen3.6-35B-A3B** (el modelo base de Edge0-35B).

Repositorio: https://github.com/ashhart/TensorFold · https://tensorfold.dev

### 6.2 Números medidos — Edge0 nativo

| Métrica | Valor | Hardware |
|---------|-------|----------|
| Decode | **14.9 – 17.7 tok/s** (hasta 20.4 en algunas mediciones) | Mac mini M4 Pro 24 GB |
| Prefill cold / warm | 113 / 140 tok/s | Mismo |
| Peak active memory | **2.9 GiB** | Mismo |
| Vanilla mlx-lm (todo en RAM) | 3.9 tok/s · 18.2 GiB | Mismo |

### 6.3 Números medidos — TensorFold + Qwen3.6-35B-A3B

| Hardware | Decode single-stream | Decode concurrente | Memoria pico | Notas |
|----------|----------------------|--------------------|--------------|-------|
| **DGX Spark (GB10)** | **141 – 179 tok/s** | — | ~22–31 GiB | Oficiales más altos (code 179.4 / chat 141.3) |
| **RTX PRO 6000 Blackwell** | ~140–170 tok/s (est.) | 427 → 1.094 tok/s (1→8 streams) | ~22–23 GiB | Medido concurrente |
| **RTX 5090 32 GB** | **~120–160 tok/s** (est.) | Alto | ~22–25 GiB | Cabe cómodo |
| **RTX 4090 24 GB** | **~80–110 tok/s** (est.) | Medio | ~22 GiB | Justo / contexto limitado |
| Serial (sin drafts) | 86–88 tok/s | — | — | DGX Spark |

**Prefill TensorFold (DGX Spark)**:
- 2k–8k tokens: 7.1k – 7.4k tok/s
- 64k tokens: ~3.7k tok/s

### 6.4 Comparativa directa

| Aspecto | Edge0 nativo (M4 Pro) | TensorFold Qwen3.6-35B (RTX / Spark) | Factor |
|---------|-----------------------|--------------------------------------|--------|
| **Decode** | ~16 tok/s | **80 – 180 tok/s** | **5–11×** |
| **Prefill** | ~120–140 tok/s | **3.7k – 7.4k tok/s** | **30–50×** |
| **Memoria activa** | **2.9 GiB** | **22–31 GiB** | **~8–10× más** |
| **Hardware** | Mac 24 GB + SSD | RTX 4090/5090 o superior | — |
| **Calidad** | Edge0 (Recover-LoRA) ≈ 79.2 | Base Qwen3.6 ≈ 83.2 | Base +4 pts |
| **Soporte RTX** | No (solo MLX) | Sí (CC ≥ 8.9) | — |

### 6.5 Expectativas de integración Edge0 + TensorFold

| Escenario | Resultado esperado | Probabilidad |
|-----------|--------------------|--------------|
| Cargar checkpoint Edge0 tal cual en TensorFold | Falla o corre serial sin drafts | Casi nula |
| Usar solo el base Qwen3.6-35B-A3B | Funciona hoy | Alta |
| Portar prerouter + Recover-LoRA + SSD streaming a TensorFold | Decode 40–80+ tok/s manteniendo ~3–5 GiB | Requiere engineering |
| Edge0 gana soporte CUDA nativo | Posible en roadmap | Media |

**Conclusión técnica**:
- TensorFold gana de forma aplastante en **velocidad** cuando hay VRAM suficiente.
- Edge0 gana de forma aplastante en **memoria activa** (único 35B viable en <4 GB).
- La combinación ideal (baja memoria + alta velocidad) aún no existe; sería un objetivo de investigación interesante para LEONES/ODS.

### 6.6 Recomendación FitLLM / ODS

| Perfil de hardware | Runtime recomendado | Modelo |
|--------------------|---------------------|--------|
| ≤ 16–24 GB RAM, sin GPU fuerte | **Edge0** | Edge0-35B / Edge0-8B |
| RTX 4090 / 5090 o superior | **TensorFold** (o vLLM) | Qwen3.6-35B-A3B / Qwen3.8-27B |
| Mac M4/M5 con ≥ 32 GB | Ambos viables | Edge0 (memoria) o TensorFold (velocidad) |
| Servidor / multi-GPU | TensorFold / vLLM / otros | GLM-5.3, DeepSeek-V4, MiMo-V2.6 |

Marcar siempre como **ESTIMATED** hasta tener medición física (MEASURED) en el hardware real del usuario.

---

## 7. Enlaces útiles

- Framework Edge0: https://github.com/Edge0-AI/edge0
- Edge0-35B: https://huggingface.co/Edge0/Edge0-35B-A3B-preview
- Edge0-8B: https://huggingface.co/Edge0/Edge0-8B-A1B-preview
- Paper Edge0: *The Other Half of the Memory Wall* (arXiv 2026-09)
- TensorFold: https://github.com/ashhart/TensorFold · https://tensorfold.dev
- Receta Qwen3.6-35B en TensorFold: `docs/recipes/qwen3.6-moe.md`

---

*Documento generado para investigación LEONES · 2026-10-02*  
*Actualizado 2026-10-02 con datos TensorFold + RTX*
