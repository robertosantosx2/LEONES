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


### 4.3 Dossier experimental: Qwen3-30B-A3B-Instruct-2507 IQ3_XXS en el MSI

**Identidad del modelo y del artefacto.** El nombre exacto probado es **Qwen3-30B-A3B-Instruct-2507**, arquitectura Qwen3MoE, aproximadamente **30,53 B parámetros totales**, **8 de 128 expertos activos** por token. Cuantización **GGUF IQ3_XXS, 3,0625 bpw**, archivo de aproximadamente **11,37 GiB**. Artefacto: `Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf`; SHA-256 `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`.

**Plataforma común:** MSI Thin 15 B12UC, Intel Core i7-12650H, 14 GiB de RAM visible, NVIDIA RTX 3050 Laptop 4 GiB (sm_86), Ubuntu, driver 580.178.04, CUDA runtime 13.0. Las campañas usan builds, protocolos y configuraciones diferentes; sus velocidades no se deben combinar como una única clasificación.

#### A. Head-to-head llama.cpp CUDA frente a RustingStrata — 21-10-2026

- llama.cpp: `0.7.0-dev`, build 11740, commit `6fa4f6cd3`.
- RustingStrata: `1.0.1`.
- Prompt: «Responde brevemente en español: ¿qué es la inferencia local?».
- Seis ejecuciones por motor (una inicial + cinco repeticiones); los 12 códigos de salida registrados son 0.
- Configuración llama.cpp: `--n-gpu-layers 14 --fit off --ctx-size 1024 --batch-size 64 --ubatch-size 32 --threads 8 --predict 128 --temp 0 --seed 42`.
- Configuración RustingStrata: `strata generate --gpu --ctx 1024 --threads 8 -n 128 --temp 0`; caché de ejecución aislada con `XDG_CACHE_HOME`.
- El script reproducible y los resultados por repetición están en el directorio de artefactos enlazado abajo.

| Motor | Ejecución | Prefill (tok/s) | Tokens generados | Decode (tok/s) | Observaciones |
|---|---:|---:|---:|---:|---|
| llama.cpp | 1 | 8,56 | 73 | 1,9454 | 24 tokens de prompt; EOS |
| llama.cpp | 2 | 6,79 | 73 | 1,8594 | 24 tokens de prompt; EOS |
| llama.cpp | 3 | 5,04 | 73 | 2,2902 | 24 tokens de prompt; EOS |
| llama.cpp | 4 | 9,08 | 73 | 2,0217 | 24 tokens de prompt; EOS |
| llama.cpp | 5 | 10,97 | 73 | 1,9474 | 24 tokens de prompt; EOS |
| llama.cpp | 6 | 10,83 | 73 | 2,0370 | 24 tokens de prompt; EOS |
| RustingStrata | 1 | 11,71 | 128 | 14,34 | 16 tokens de prompt; 30,8 % hit, 38.272 misses, 128 swaps |
| RustingStrata | 2 | 19,67 | 98 | 29,94 | 16 tokens; 79,0 % hit, 9.178 misses, 16 swaps |
| RustingStrata | 3 | 20,03 | 128 | 30,08 | 16 tokens; 77,9 % hit, 12.194 misses, 1 swap |
| RustingStrata | 4 | 18,91 | 104 | 30,90 | 16 tokens; 80,2 % hit, 9.125 misses, 1 swap |
| RustingStrata | 5 | 18,96 | 128 | 31,89 | 16 tokens; 78,6 % hit, 11.856 misses, 1 swap |
| RustingStrata | 6 | 17,98 | 128 | 29,33 | 16 tokens; 78,8 % hit, 11.716 misses, 1 swap |

**Resumen estadístico:** llama.cpp tuvo mediana de decode **1,985 tok/s**; RustingStrata, mediana **30,01 tok/s** (media aproximada 27,75 tok/s, muy afectada por la primera ejecución de calentamiento, 14,34 tok/s). En Strata, excluyendo esa primera ejecución, el decode se situó entre 29,33 y 31,89 tok/s. La tasa de acierto de expertos de las ejecuciones 2–6 quedó entre 77,9 % y 80,2 %, con 1–16 swaps; la primera ejecución registró solo 30,8 % y 128 swaps. El cálculo de medianas no elimina las diferencias metodológicas: llama.cpp procesó 24 tokens de prompt y terminó por EOS con 73 tokens; Strata procesó 16 tokens y generó longitudes variables (98–128). Por ello es una comparación práctica del comportamiento de los dos motores con ese script, no un benchmark perfectamente equivalente.

#### B. Sweep nativo de llama-bench — 22-10-2026

Campaña separada con `llama-bench`, mismo GGUF y build llama.cpp b11740 / commit `6fa4f6cd3`, ocho hilos, PP128 y TG32, tres repeticiones por ajuste. Se variaron las capas descargadas a GPU: `--n-gpu-layers 0/1/8`. Las nueve ejecuciones finalizaron con código 0.

| N capas GPU | PP128 media | PP128 mediana | PP128 desviación estándar | TG32 media | TG32 mediana |
|---:|---:|---:|---:|---:|---:|
| 0 | 22,553 | 24,420 | 8,093 | 1,487 | 1,450 |
| 1 | **74,473** | **76,250** | 16,377 | 1,660 | 1,440 |
| 8 | 34,957 | 26,380 | 30,746 | **1,827** | **1,880** |

- `ngl=1` obtuvo la mejor mediana de prefill PP128.
- `ngl=8` tuvo una dispersión muy alta en PP128 (9,41–69,08 tok/s); no se debe interpretar su media como rendimiento estable.
- Decode TG32 estuvo aproximadamente entre 1,40 y 2,14 tok/s.
- En logs de carga se observaron capas 35–48 asignadas a CUDA0, buffer de modelo CUDA de 3.290,68 MiB, KV de 26 MiB y compute de 86,25 MiB. Se registró un warning de tamaño del compute buffer CUDA_Host distinto de la expectativa; no fue fatal en esas ejecuciones y no se le atribuye causalidad sin prueba.
- Una instantánea posterior de `nvidia-smi` no representa el pico de VRAM durante la ejecución. En pruebas históricas con llama-server también se comunicó Xid 31; conviene vigilar errores del driver y telemetría durante futuras repeticiones.

Este sweep no es la misma campaña que el head-to-head de seis ejecuciones ni que la prueba de Strata. Su benchmark de generación es TG32, no 73–128 tokens generados en el head-to-head.

#### C. Picchio v0.8.0 — INT4 CPU streaming y caché de expertos — 07/08-11-2026

Esta es otra conversión del mismo modelo base, no el GGUF IQ3_XXS: **Qwen3-30B-A3B INT4 en safetensors**, conversión Picchio local de unos 20,6 GB en 16 shards, 25.013 tensores. La RTX 3050 no participó en la inferencia (rutas GPU desactivadas).

- Primera inferencia end-to-end: contexto 512, 128 tokens, sin reasoning, 4 hilos CPU + 4 hilos I/O, caché experta 2 GiB; carga 2,8 s, generación 128 tokens en 79,1 s, **1,6 tok/s**, RSS final 6,32 GB, cache hit 59,7 %, 21.072 lecturas de disco. Respuesta coherente pero truncada al límite de 128 tokens.
- Campaña posterior con caché de expertos 4 GiB: CPU-only, prompt/contexto y semilla controlados, 128 tokens. En la secuencia 4–8–8–4, medias: **1,220 tok/s con 4 hilos** y **1,196 tok/s con 8 hilos**; 8 hilos tardaron 1,95 % más. Diferencia pequeña, afectada potencialmente por temperatura (se observó 96 °C antes de una ejecución) y variabilidad; no demuestra que 4 hilos sea universalmente mejor.
- La topología SMBIOS mostraba dos módulos DDR4-3200 de 8 GB en controladores/canales distintos, compatible con dual-channel. STREAM Triad alcanzó 34,60 GB/s con 16 hilos y 32,24 GB/s con 4. No se hizo una comparación single-channel controlada: no se puede afirmar que dual-channel duplique el rendimiento ni que la RAM sea el cuello de botella demostrado.
- El hot-store persistente `.picchio_usage` registra/restaura estadísticas de uso; la inspección de código no demostró que estas estadísticas seleccionen o precarguen expertos calientes. No atribuir aceleración a esa función sin una prueba A/B.

#### D. Otros intentos y límites de compatibilidad

- En una prueba CPU de RustingStrata comunicada posteriormente, el modelo se ejecutó con prefill/decode de 128/32 tokens a aproximadamente **0,4 tok/s**; debe mantenerse separada del head-to-head CUDA y no usarse como su cifra representativa.
- En octubre de 2026, TensorFold 1.1.1 no declaraba la familia Qwen3MoE / `qwen3moe`; no se debe presentar el modelo como ejecutado con TensorFold en esa versión.
- Picchio, RustingStrata, llama.cpp y llama-bench representan rutas distintas: GGUF IQ3_XXS frente a conversión INT4 safetensors, CPU-only frente a híbrido CPU/GPU y distintas longitudes de prompt/salida. No comparar directamente sus tok/s como si fueran un único benchmark controlado.

#### E. Evidencias, scripts y logs originales

1. **Head-to-head, paquete bruto limpio:** [directorio de artefactos](../docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/), [README](../docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/README.md), [script reproducible](../docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/benchmark-strata-vs-llamacpp.sh), [CSV por ejecución](../docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/results-summary.csv), [extracto de consola](../docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/extracted-console-evidence.txt), [manifiesto SHA-256](../docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/raw-archive-manifest.md) y [archivo tar.gz de los 36 ficheros originales](../docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/head-to-head-20261021-raw-no-cache.tar.gz). SHA-256 del tar.gz: `95496a42dd5816908d03fc373d8ef2b6f6630f84d2fd4c373287d6dbcdad6fdb` (273.761 bytes). Contiene 12 `rep-*.log`, 12 `time-*.txt` y 12 `rc-*.txt` (seis por motor); todos los códigos de salida son cero.
2. **Copia de logs individuales versionados:** [llama.cpp: seis logs rep, seis time y seis rc](../docs/reports/artifacts/qwen3-30b-a3b-iq3-xxs-head-to-head-20261021/llama/) y [RustingStrata: seis logs rep, seis time y seis rc](../docs/reports/artifacts/qwen3-30b-a3b-iq3-xxs-head-to-head-20261021/strata/), con [manifiesto de checksums](../docs/reports/artifacts/qwen3-30b-a3b-iq3-xxs-head-to-head-20261021/SHA256SUMS.txt). Los logs de llama.cpp incluyen salida verbose extensa; los de Strata registran throughput, hit rate, misses y swaps.
3. **Sweep llama-bench / campaña octubre:** [informe reproducible en español](../docs/reports/report-inferencia-dense_Octubre26.md), [informe en inglés](../docs/reports/report-inference-dense-october-2026.md) y [paquete de evidencias de la campaña](../docs/reports/artifacts/inferencia-rtx3050-4gb-oct26-collection-20261022-123939.tar.gz). El paquete contiene los ficheros recopilados de la campaña; no sustituye los 36 logs head-to-head anteriores.
4. **Picchio / memoria:** [primera ejecución Qwen3-30B-A3B en MSI](../docs/subprojects/REDIL-IA-distribuida/PICCHIO-QWEN3-30B-A3B-MSI-2026-11-07.md) y [estudio de RAM dual-channel y escalado CPU](../docs/reports/picchio-ram-dual-channel-msi-2026-11-08.md). Los logs originales de Picchio siguen descritos en esos informes; no todos los archivos locales están publicados como logs individuales en GitHub.

**Conclusión de LEONES:** el resultado más destacado del GGUF IQ3_XXS en este portátil fue RustingStrata CUDA híbrido, con ~30 tok/s de decode después del calentamiento, frente a ~2 tok/s en el head-to-head llama.cpp con 14 capas GPU. El sweep nativo de llama-bench confirma que una descarga pequeña (`ngl=1`) favoreció el prefill, pero no elevó de forma comparable la generación. Picchio demuestra una ruta CPU streaming viable con INT4, alrededor de 1,2–1,6 tok/s en sus pruebas documentadas. Son resultados válidos para sus protocolos concretos, no una comparación universal entre motores.

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

---

## 10. Investigación académica: semántica, routing y control de expertos (ACL/EMNLP/ICLR 2025–2026)

Esta sección incorpora tres trabajos revisados en noviembre de 2026. Su contribución principal no es acelerar directamente kernels ni demostrar más tokens/s: explican la relación entre contenido, representaciones internas y selección de expertos, y ofrecen métodos para medir o intervenir en el router.

### 10.1 SARA — Semantically Anchored Routing Alignment (Findings of ACL 2026)

**Referencia:** [Dong et al., “SARA: Unlocking Multilingual Knowledge in Mixture-of-Experts via Semantically Anchored Routing Alignment”, ACL Findings 2026, pp. 2830–2846](https://aclanthology.org/2026.findings-acl.136/). [PDF](https://aclanthology.org/2026.findings-acl.136.pdf). [Código](https://github.com/iMoriton/sara).

**Problema:** un MoE puede contener conocimiento útil aprendido con datos de idiomas de alto recurso y, sin embargo, no activarlo cuando recibe una pregunta semánticamente equivalente en un idioma de bajo recurso. El router deriva hacia otros expertos por diferencias léxicas/superficiales. No es necesariamente ausencia de conocimiento en los pesos: puede ser un problema de acceso al conocimiento mediante el routing.

**Técnica SARA, en tres etapas:**

1. **Construcción de pares semánticamente anclados.** Se parte de preguntas y respuestas inglesas verificadas; se traducen a cinco idiomas de bajo recurso (hindi, nepalí, bengalí, telugu y suajili). Se crean dos pistas independientes con inglés y chino como anclas.
2. **Extracción de priors del router.** Se ejecuta el propio MoE sobre la secuencia completa pregunta+respuesta del idioma ancla y se guardan las distribuciones softmax del gate por token y capa. No se guardan solo los IDs top-k: se conservan las probabilidades densas, que contienen información sobre alternativas y son más estables. Se promedian a nivel de secuencia, enmascarando padding.
3. **Alineamiento de routing durante fine-tuning.** Se entrena con una función compuesta:

   `L = L_CE + λ_LB · L_LB + λ_JS · L_JS`

   - `L_CE`: pérdida habitual de predicción del siguiente token.
   - `L_LB`: balanceo de carga para evitar colapso o infrautilización de expertos.
   - `L_JS`: divergencia Jensen–Shannon simétrica entre el perfil de routing del idioma objetivo y el prior del idioma ancla, aplicada solo a capas intermedias.

La divergencia JS se prefiere a KL por su simetría y por ser menos problemática cuando las colas de probabilidades de expertos no seleccionados son muy pequeñas. En Qwen3, los autores alinean las capas 7–34 (índices del artículo). La supervisión se aplica a perfiles agregados de secuencia, no a una obligación rígida de que cada token seleccione exactamente el mismo top-k.

**Resultados y lectura correcta:**

- En Qwen3-30B-A3B, SARA con ancla inglesa obtiene 71,53 en Global-MMLU frente a 70,73 de fine-tuning convencional: **+0,80 puntos**. En BELEBELE obtiene 83,09 frente a 82,95 (+0,14). En MGSM obtiene 87,40 frente a 87,20 (+0,20); frente al modelo vanilla (79,20), la diferencia es mucho mayor porque también incorpora el efecto del fine-tuning supervisado.
- En el resumen del artículo se informa además de una mejora de +1,2 puntos en Global-MMLU para Phi-3.5-MoE-Instruct.
- El artículo compara con fine-tuning convencional, AES y ShifCon. Alinear directamente la distribución interna del router supera de forma más consistente a las alternativas que solo alinean texto o representaciones.
- La ablación es crucial: usar priors externos generados por un modelo distinto, alinear capas aleatorias o forzar todas las capas degrada resultados. La variante de priors propios del modelo y selección de capas intermedias es la más sólida.

**Coste y aplicabilidad local:** no es una optimización que se active simplemente al arrancar un servidor. Los experimentos de fine-tuning usaron 16 NVIDIA H100 de 80 GB, dos épocas y unas 15 horas por sesión. No es viable entrenar SARA en la MSI. Sí es transferible como técnica de diagnóstico: registrar distribuciones de gate, construir priors de secuencia y comparar routing entre idiomas o dominios. Para aplicar SARA propiamente dicha se necesita un pipeline de entrenamiento que pueda acceder a logits del router y actualizar pesos.

### 10.2 Probing Semantic Routing in Large Mixture-of-Expert Models (Findings of EMNLP 2025)

**Referencia:** [Olson et al., “Probing Semantic Routing in Large Mixture-of-Expert Models”, Findings of EMNLP 2025, pp. 18263–18278](https://aclanthology.org/2025.findings-emnlp.991/). [PDF](https://aclanthology.org/2025.findings-emnlp.991.pdf).

**Pregunta:** ¿los expertos responden a semántica contextual o solo a identidad del token? El trabajo diseña dos pruebas controladas para separar ambas explicaciones:

- **WiC (Word-in-Context):** mantiene la misma palabra objetivo y cambia el contexto para que conserve o cambie de sentido.
- **SWORDS (sustitución léxica):** mantiene el contexto y sustituye la palabra objetivo por otra semánticamente equivalente o por una alternativa de significado diferente.

Evalúa seis modelos de tres familias: DeepSeek-R1, DeepSeek-V2-Lite, Mixtral-8x7B, Mixtral-8x22B, Llama-4-Scout y Llama-4-Maverick.

**Métrica reutilizable: solapamiento de expertos corregido por azar.** Si `o` es el número de expertos comunes entre dos entradas, `k` el número de expertos activos y `N` el total de expertos, bajo selección aleatoria uniforme el solapamiento esperado es `E[o] = k²/N`. El score normalizado es:

`overlap_norm = (o - E[o]) / (k - E[o])`

Es análogo a Cohen's κ y evita comparar directamente porcentajes brutos entre modelos con top-k y cantidades de expertos diferentes.

**Hallazgos:**

- Los seis modelos muestran mayor solapamiento de expertos cuando el sentido se conserva que cuando cambia; el resultado es estadísticamente significativo (WiC: p < 0,001; el análisis complementario informa p < 0,0001 para todos los modelos).
- La especialización semántica es más visible en capas intermedias. DeepSeek-R1 muestra una señal especialmente clara y consistente.
- En general, la señal crece con la escala, aunque Llama-4-Scout es una excepción destacada.
- El estudio de CoT con DeepSeek-R1 sugiere que patrones de razonamiento latentes también pueden asociarse con subconjuntos de expertos.

**Implicación para inferencia local:** el routing no es una función estática de la palabra aislada. Depende de contexto, sentido, posición y estado interno. Por tanto, una lista global de “expertos más calientes” puede ser útil como prior, pero no describe todo el working set de una petición. El cache/placement debe considerar la distribución por tarea y por fase de ejecución. El score normalizado permite comprobar si dos prompts semánticamente equivalentes activan rutas parecidas y si una cuantización/backend cambia ese patrón.

### 10.3 Multilingual Routing in Mixture-of-Experts (ICLR 2026)

**Referencia:** [Bandarkar et al., “Multilingual Routing in Mixture-of-Experts”, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/file/1b558190825286a3defcc78d02fa2189-Paper-Conference.pdf).

**Hallazgo estructural:** la divergencia de routing entre inglés y otros idiomas sigue, en general, una curva en U a través de las capas: es alta al principio y al final, y baja en las capas intermedias. Las capas medias comparten más expertos entre idiomas; las capas iniciales y finales conservan mayor especialización lingüística. La alineación en capas intermedias correlaciona fuertemente con la competencia del modelo en cada idioma. El trabajo estudia Qwen3-30B-A3B, Phi-3.5-MoE, GPT-OSS-20B y OLMoE.

**Cómo medirlo:** los autores agregan pesos de routing a nivel de secuencia y comparan distribuciones mediante una Jensen–Shannon normalizada por entropía (DH-JS). Esta normalización es necesaria porque la entropía del router cambia a través de las capas; comparar JS sin corregir ese efecto puede confundir divergencia con concentración. El promedio de toda la secuencia es más estable que observar solo el último token.

**Identificación de expertos especializados:** calculan, para cada experto, la diferencia entre la frecuencia relativa con la que aparece en top-k para un corpus de tarea/idioma y un corpus general de referencia. Con un umbral `τ`, seleccionan expertos cuya activación relativa aumenta de forma marcada. En Qwen3, con τ=0,3, identifican 586 expertos multilingües y 99 expertos matemáticos entre 6.144 posiciones experto-capa; no encuentran intersección entre ambos grupos. Es evidencia de modularidad funcional, no una regla universal de que los expertos no puedan compartir capacidades.

**Intervención en tiempo de inferencia:** interceptan los logits del router antes del softmax:

- *Soft steering:* desplazan el logit de un experto objetivo en una cantidad proporcional a la desviación estándar de los logits: `z'_k = z_k + λ · std(z)`. Valores pequeños, habitualmente |λ| ≤ 1 y λ=0,5 en varios experimentos, son los más seguros.
- *Hard steering:* fuerzan un experto al top-k asignándole el máximo logit (más una perturbación mínima) o lo excluyen con el mínimo. Aunque el método duro solo fuerza uno o dos expertos dentro del top-k, puede alterar mucho el resultado.

La intervención que funciona consiste en promover expertos de tarea identificados con datos ingleses dentro de las capas intermedias. No funciona promover indiscriminadamente expertos multilingües ni intervenir en todas las capas. En Qwen3 el intervalo estudiado es aproximadamente capas 8–35 (numeración del artículo). Salirse de esa zona puede degradar significativamente el rendimiento.

**Resultados:** en MGSM, la media no inglesa pasa de 76,4 a 78,0 (+1,6 puntos) en Qwen3-30B-A3B, de 57,5 a 58,9 (+1,4) en Phi-3.5-MoE y de 68,9 a 71,5 (+2,6) en GPT-OSS-20B. En Global-MMLU médico, las mejoras medias son más modestas: +0,9, +1,0 y +0,7 puntos, respectivamente. Hay idiomas que no mejoran o incluso retroceden; el resultado es una mejora media y estadísticamente significativa, no una garantía para cada idioma o tarea.

**Implicación para LEONES:** este es el trabajo más directamente aplicable a una futura variante experimental de runtime, porque modifica el routing durante el forward sin reentrenar el modelo. Sin embargo, requiere un hook en el punto exacto donde se calculan los logits del gate. Un servidor GGUF que solo expone texto y tokens no ofrece ese control. No debe implementarse como un sesgo global de expertos: primero hay que perfilar expertos de tarea, delimitar las capas medias y validar cada modelo con pruebas de regresión.

### 10.4 Síntesis conjunta de los tres artículos

Los tres trabajos son complementarios:

| Trabajo | Qué demuestra | Técnica reutilizable | Aplicación principal |
|---|---|---|---|
| EMNLP 2025 — Semantic Routing | La selección de expertos contiene señal semántica contextual | WiC/SWORDS, overlap corregido por azar, análisis por capa | Diagnóstico y perfilado |
| ICLR 2026 — Multilingual Routing | Las capas medias son más compartidas; la intervención selectiva puede mejorar tareas | DH-JS, frecuencia diferencial, soft/hard steering pre-softmax | Experimentos de inferencia con router hooks |
| ACL 2026 — SARA | Alinear distribuciones internas puede transferir capacidades entre idiomas | Priors densos de routing, promedio por secuencia, JS + CE + balanceo | Fine-tuning / investigación de modelos |

**Conclusión técnica:** no se debe confundir “experto caliente” con “experto semánticamente correcto”. La frecuencia mide demanda; el overlap y la divergencia miden similitud de rutas; la evaluación de tarea mide utilidad. LEONES debe conservar esas tres dimensiones separadas.

---

## 11. Técnicas clave para motores MoE locales: traducción a ingeniería

### 11.1 Telemetría de routing por capa y token

Cuando el motor o una build instrumentada lo permita, registrar para cada capa MoE:

- logits del gate antes del softmax (si se dispone de ellos);
- probabilidades softmax completas o, como mínimo, top-k IDs y pesos;
- expertos seleccionados y pesos efectivos después de normalización;
- posición del token, fase prefill/decode, secuencia, idioma y categoría de tarea;
- latencia de dispatch, espera, lectura/copia de pesos y ejecución del experto.

La telemetría completa puede ser voluminosa y alterar el rendimiento. Debe ejecutarse como campaña de profiling independiente, no mezclarse con el benchmark de velocidad sin instrumentación. Si solo se registran IDs top-k, no se debe afirmar que se ha reconstruido la distribución densa del router.

### 11.2 Métricas de perfil

LEONES debería calcular por capa y por corpus:

1. **Frecuencia de activación:** proporción de tokens en que cada experto aparece en top-k.
2. **Top-N coverage:** porcentaje de selecciones cubierto por los N expertos más frecuentes.
3. **Entropía del routing:** concentración o dispersión de las probabilidades/picks.
4. **Gini / skew:** desigualdad de la frecuencia de acceso.
5. **Normalized expert overlap:** similitud de rutas entre pares de prompts, corregida por azar y por N/k.
6. **JS / DH-JS:** divergencia entre perfiles de idiomas, tareas, cuantizaciones o motores.
7. **Working-set por ventana:** expertos distintos usados en ventanas temporales de tokens, separando prefill y decode.

Los perfiles deben segmentarse por modelo, hash de checkpoint, cuantización, backend, idioma, tarea y fase. No reutilizar un perfil si cambia la identidad del modelo o el artefacto.

### 11.3 Cache y placement: estático más dinámico

La evidencia semántica obliga a refinar la política de caché ya descrita en este atlas:

- Un perfil global de uso es un prior de colocación, no una predicción exacta del siguiente token.
- Mantener un conjunto base de expertos frecuentes en VRAM si el skew lo justifica.
- Añadir una caché dinámica con política LRU/CLOCK o LFU con decaimiento, actualizada con el tráfico reciente.
- Medir por separado cache hit, misses, bytes transferidos, swaps por token y tiempo de espera.
- Si es posible, usar el perfil de secuencia para prefetch de expertos probables, pero validar que el prefetch no compite con el cómputo ni aumenta el uso de memoria.
- Medir prefill y decode por separado: el patrón de acceso y el paralelismo no son equivalentes.
- Elegir CPU/RAM frente a PCIe/VRAM con medidas bajo carga, no con ancho de banda teórico ni benchmarks de copia aislados.

**Hipótesis nueva para validar, no hecho demostrado por estos artículos:** cuantizaciones agresivas pueden cambiar el orden de logits de expertos cercanos al umbral top-k. Eso podría alterar el routing, además del error numérico de los expertos. Para comprobarlo hay que ejecutar el mismo conjunto de tokens sobre una referencia de mayor precisión y sobre el artefacto cuantizado, comparando top-k overlap, JS de probabilidades y calidad final. No se debe atribuir una diferencia de velocidad a routing distinto sin medirlo.

### 11.4 Intervención selectiva: protocolo de seguridad experimental

Para explorar el método ICLR en un motor propio o fork:

1. Elegir un modelo con soporte de instrumentación y conservar una ejecución baseline sin modificaciones.
2. Obtener un corpus general y otro de tarea/idioma, con hashes y separación train/eval.
3. Medir activación relativa por experto y capa; identificar candidatos con umbrales conservadores.
4. Delimitar las capas intermedias usando la divergencia por capa, no copiar números de otro modelo.
5. Aplicar primero soft steering de magnitud pequeña y solo a un conjunto pequeño de expertos.
6. Comparar hard steering únicamente como experimento separado.
7. Ejecutar pruebas de calidad por idioma/tarea, regresión en inglés, estabilidad numérica, throughput, TTFT y memoria.
8. Revertir cualquier intervención que mejore una media pero cause regresiones severas en idiomas, dominios o prompts no objetivo.

No activar esta técnica por defecto en LEONES. Debe existir un perfil explícito, reproducible y desactivado por defecto.

---

## 12. Auditoría del benchmark de motores — PR #142 y rama research/kinetic-audit-benchmark

**Enlaces de trabajo:**
- [PR #142 — Add extensible inference engine registry, source snapshots and reproducible benchmark framework](https://github.com/robertosantosx2/LEONES/pull/142)
- [Rama research/kinetic-audit-benchmark](https://github.com/robertosantosx2/LEONES/tree/research/kinetic-audit-benchmark)
- [Directorio artifacts/engine-comparison](https://github.com/robertosantosx2/LEONES/tree/research/kinetic-audit-benchmark/artifacts/engine-comparison)
- [Plan del benchmark cruzado, 11-11-2026](../docs/KINETIC-CROSS-ENGINE-BENCHMARK-PLAN-2026-11-11.md)
- [Auditoría estática de Kinetic, 11-11-2026](../docs/KINETIC-SOURCE-AUDIT-2026-11-11.md)
- [Contrato de adaptadores](../docs/ENGINE-ADAPTER-CONTRACT.md)
- [Política de snapshots de código fuente](../docs/ENGINE-SOURCE-VENDORING.md)
- [Runbook de compilación Ubuntu/MSI](../docs/ENGINE-BUILD-RUNBOOK.md)
- [Runner](../scripts/engine_comparison.py) · [validador](../scripts/validate_engine_config.py) · [registro de motores](../configs/engines.registry.json) · [configuración de ejemplo](../configs/engine-comparison.example.json) · [tests](../tests/test_engine_comparison.py)

### 12.1 Estado verificado a 12-11-2026

PR #142 aparece **Draft**, con 113 commits dirigidos a `main` desde `research/kinetic-audit-benchmark`. Su objetivo es añadir un registro extensible de motores, snapshots inmutables, procedencia de builds y un runner secuencial con recuperación de la máquina.

La rama contiene cinco motores principales de comparación:

| Motor | Identidad en registry | Estado de configuración de ejemplo | Observación |
|---|---|---|---|
| Kinetic | `kinetic` | Enabled | Único motor habilitado en el ejemplo; solo perfil CUDA 8 capas |
| TensorFold | `tensorfold` | Disabled | Requiere checkpoint/directorio compatible y build local |
| Tandem.cpp | `tandem-cpp` | Disabled | Requiere patch y base llama.cpp exacta |
| RustingStrata | `rusting-strata` | Disabled | Build y backend CUDA/NVRTC pendientes de evidencia de esa campaña |
| llama.cpp | `llama-cpp` | Disabled | Upstream independiente, no confundir con base Tandem |

Hay dos identidades auxiliares adicionales, no dos motores extra del head-to-head: `llama-cpp-tandem-base` (commit exacto sin parche para comparar Tandem) y `project-maya` (fuente/model-specific engine añadida a la registry como preparación/investigación).

### 12.2 Procedencia y preservación: punto fuerte del PR

El PR registra siete identidades de código fuente como `VENDORED`, con snapshots bajo `third_party/engines/<id>/source/<commit>/`, metadatos `SOURCE.json` y `VENDOR_REPORT.json`. Los commits fijados que aparecen en el informe de vendoring son:

| Identidad | Commit |
|---|---|
| Kinetic | `351554bf8996ffb9ef361796626c8c122d43f2b4` |
| TensorFold | `6b739dd5e14ce213c8d45589e9e15fdabb0ae660` |
| Tandem.cpp | `d67bbcb9453a1e6c9f4b3ba0d29fb63193c57287` |
| llama.cpp upstream | `9e9619d030bbe6b584d826a0a6cf06e38251f52b` |
| RustingStrata | `f47e370cb72e06c9d2c7fc6f618dfe5f1029fed4` |
| llama.cpp base de Tandem | `f5222f25c18da062ab2b8a2dbbfbf4feae398566` |
| Project Maya | `a3582528bfb73175fed1757b485bfcaaf01aaeaa` |

Cada snapshot conserva URL upstream, ref solicitado, commit/tree SHA, estado de submódulos, Git LFS y archivos de licencia/avisos. Los pesos de modelos no se copian dentro del vendoring. Esta separación es correcta y esencial: Tandem.cpp es un conjunto de parches sobre una base concreta, no un fork completo intercambiable con el HEAD actual de llama.cpp. Para una comparación causal de Tandem se necesita compilar también el commit base exacto sin parche.

### 12.3 Contrato de benchmark y runner: capacidades implementadas

El contrato de adaptadores define identidad de motor, commit/tree, build, toolchain, flags, SHA-256 del ejecutable, modelo/tokenizer/plantilla, backend, parámetros efectivos, entorno saneado, logs, respuestas y telemetría. El protocolo v1 acepta comando argv (no shell string) y API OpenAI-compatible; los servidores deben enlazar a `127.0.0.1`. Una API no compatible necesita adaptador dedicado, sin descartar silenciosamente parámetros.

`scripts/engine_comparison.py` implementa:

- ejecución secuencial por motor/perfil;
- health check y tiempo de carga;
- warmup no medido;
- peticiones SSE con captura de respuesta y usage;
- TTFT, prefill aproximado, decode aproximado y wall time;
- hashes de modelo/artefactos, fuente y binario;
- snapshots de máquina, RSS del proceso, RAM/swap y datos de `nvidia-smi`;
- parada del proceso y gate de recuperación antes de cargar el siguiente perfil;
- salida `manifest.json`, `results.jsonl`, `summary.json`, logs, respuestas y snapshots.

`capture_engine_build.py` registra SHA-256 del binario, comando y log de build, toolchain, backend, features y hashes de parches. El validador comprueba paridad registry/config, snapshots, notices, modelo registry y que Tandem apunte a la base exacta con evidencia del patch.

### 12.4 Resultado de la verificación: framework preparado, comparación física aún no demostrada

**No hay base documental para publicar un ranking comparativo MEASURED de los cinco motores a partir del PR #142 en su estado revisado.** El propio plan fechado el 11-11-2026 declara explícitamente que todavía no existen resultados comparativos MEASURED y que la fase pendiente es ejecutar builds y pruebas físicas en la MSI. El runbook también declara que es preparación, no evidencia de builds o ejecuciones ya realizadas. En los ficheros modificados del PR se encuentran el plan, la auditoría, el código, la registry, las configuraciones y los snapshots; no aparece un paquete de resultados de la campaña que demuestre cinco motores ejecutados bajo una matriz común.

La configuración de ejemplo confirma esta limitación:
- solo Kinetic figura como `enabled: true`;
- TensorFold, Tandem.cpp, RustingStrata, llama.cpp, la base Tandem y Maya están deshabilitados;
- los cinco motores comparativos están limitados al perfil `ctx512-cuda8`, aunque el archivo declara perfiles CPU 512/4, CPU 1024/8 y CUDA 512/8;
- las rutas de binarios de los motores deshabilitados siguen siendo placeholders `/ABS/PATH/...`;
- el runner exige `artifacts/engine-builds/<id>/build.json` por defecto. Sin esa evidencia, registra `BUILD_EVIDENCE_REQUIRED` y no mide el motor. El ejemplo no incluye esos manifiestos de build.

Por tanto, el estado correcto es **FRAMEWORK IMPLEMENTED / SOURCE VENDORED / STATIC REVIEW**, no “cinco motores comparados”. Kinetic tiene configuración habilitada, pero no debe considerarse medido por el mero hecho de estar habilitado: debe pasar build-evidence, hash del binario, health check, carga del modelo y ejecución de prompts.

### 12.5 Observaciones metodológicas que deben corregirse o explicitarse antes de publicar resultados

1. **Muestreo de memoria durante la petición.** El plan exige muestras durante cada petición y máximos observados. El runner visible toma snapshots antes, tras cargar y después de cada petición; no implementa un muestreador continuo de alta frecuencia durante toda la generación. Así no puede garantizar el pico real de VRAM/RAM. Añadir un monitor periódico (por ejemplo 100–250 ms configurable) que guarde máximos y series temporales, o declarar que el dato es una muestra puntual.
2. **Prefill.** `prompt_tokens / TTFT` es una aproximación, no el prefill puro: TTFT incluye cola, scheduling, transporte, procesamiento de prompt y generación del primer token. Etiquetar como `approx_prefill_tok_s` y conservar TTFT como métrica primaria de latencia inicial.
3. **Decode SSE.** `(completion_tokens - 1) / (last_chunk_time - first_chunk_time)` es aproximado porque un fragmento SSE puede contener varios tokens y los servidores pueden agrupar fragmentos. No equivale a timestamps por token. Mantenerlo como estimación y contrastarlo con métricas internas del motor o instrumentación token-level.
4. **RSS del árbol de procesos.** La función visible suma el proceso y sus hijos directos; no recorre necesariamente descendientes de varios niveles. Etiquetar como RSS parcial o implementar recorrido recursivo.
5. **API y usage.** El runner solicita `stream_options.include_usage`. Debe verificarse que cada servidor lo soporte y que `prompt_tokens`/`completion_tokens` sean válidos. Si no, no fabricar tokens/s a partir de caracteres; registrar métrica como no disponible y conservar la respuesta bruta.
6. **Paridad de artefactos.** Kinetic, Tandem y llama.cpp pueden consumir el mismo GGUF; TensorFold puede requerir un directorio de checkpoint MLX/EXL3 propio y RustingStrata debe validar su soporte real. Si no se usa el mismo fichero, tokenizer y plantilla, el resultado es comparación de checkpoints/cuants equivalentes, no head-to-head bit a bit. Registrar cada SHA.
7. **Perfiles CPU/GPU.** El plan propone CPU 4/8 hilos y CUDA, pero la configuración actual limita motores principales a CUDA 512/8. Ejecutar CPU y CUDA como matrices separadas y no inferir el comportamiento CPU de una prueba CUDA.
8. **Ablaciones de Kinetic.** El plan describe baseline con aceleraciones y ablaciones separadas. La configuración de ejemplo incluye `--off warm-start`; debe documentarse como un perfil concreto, no presentarse como baseline con todas las aceleraciones activas. Mantener RAD-1, Warm Start, Torque, Zero Wait y Convoy en pruebas A/B separadas.
9. **Tandem causal.** Comparar Tandem parcheado contra llama.cpp master mezcla el efecto del parche con los cambios upstream. La comparación correcta usa `llama-cpp-tandem-base` en el commit `f5222f...` y el mismo toolchain, configuración, modelo y flags.
10. **CI no equivale a ejecución MSI.** El workflow está diseñado para validar sintaxis Python, JSON, paridad de configuración, tests unitarios y wrappers shell en Ubuntu CI. No puede validar CUDA real, NVRTC, memoria disponible, estabilidad del driver ni throughput de la MSI.

### 12.6 Protocolo de cierre recomendado para PR #142

Antes de convertir el PR en ready-for-review o publicar un ranking:

- [ ] Confirmar checks CI verdes y guardar el enlace/commit de la ejecución.
- [ ] Compilar cada motor en Ubuntu/MSI siguiendo el runbook; capturar log y `build.json`.
- [ ] Verificar SHA-256 del ejecutable en el momento de lanzamiento.
- [ ] Confirmar backend CUDA efectivo y descartar fallback silencioso a CPU.
- [ ] Seleccionar un modelo principal realmente soportado por los motores; conservar hash de checkpoint, tokenizer y chat template.
- [ ] Ejecutar smoke test funcional por motor antes de la matriz.
- [ ] Habilitar un motor cada vez, sin placeholders ni procesos residuales.
- [ ] Completar perfiles CPU y CUDA en campañas separadas, con repeticiones y orden controlado.
- [ ] Añadir monitor de picos de memoria o documentar su ausencia.
- [ ] Validar TTFT, tokens de usage, respuesta, errores y recuperación de la máquina.
- [ ] Publicar todos los resultados brutos, logs, manifiestos, respuestas y hashes en `artifacts/engine-comparison/<session-id>/`.
- [ ] Generar resumen con mediana, dispersión y percentiles cuando el tamaño de muestra lo permita; nunca solo best-of-N.
- [ ] Clasificar cada motor como MEASURED, UNSUPPORTED, BUILD_FAILED, API_INCOMPATIBLE o BLOCKED_BASELINE según evidencia real.

---

## 13. Plan experimental derivado para LEONES: unir routing y benchmark de motores

La siguiente fase debería producir dos campañas diferentes, relacionadas pero no mezcladas.

### Campaña A — rendimiento del runtime (sin instrumentación de router)

Objetivo: comparar motores sin que los hooks de diagnóstico alteren tiempos. Usar el protocolo de PR #142 con el mismo modelo/artefacto cuando sea posible, temperatura 0, seed fijo, contexto y prompts versionados, warmup separado, varias repeticiones, ejecución serial y recuperación de host. Publicar TTFT, prefill aproximado, decode aproximado, wall time, load time, RSS, pico RAM/VRAM, swap, energía si está disponible y errores.

### Campaña B — comportamiento del router (instrumentada)

Objetivo: comprender por qué un runtime/cache obtiene determinados resultados y comprobar la estabilidad del routing. Para cada modelo y cuantización compatible:

- recoger top-k IDs y pesos por capa en un corpus corto reproducible;
- separar prefill y decode;
- calcular entropía, top-N coverage, Gini, working-set, overlap normalizado y JS/DH-JS;
- ejecutar pares WiC/SWORDS y pares paralelos español/inglés cuando la familia de modelo lo permita;
- contrastar GGUF/cuants/backends con un artefacto de referencia;
- medir overhead de instrumentación y no usar esos tiempos para el ranking de Campaña A.

### Orden de implementación recomendado

1. Completar primero la auditoría y validación de PR #142, builds y campaña de rendimiento.
2. Añadir un formato versionado `moe-routing-profile.v1` para perfiles por capa/experto, con identidad del modelo y artefacto.
3. Crear un adaptador opcional de telemetría para un motor donde se pueda acceder al router (fork/instrumentación), sin exigirlo a todos los motores.
4. Implementar análisis offline de perfiles y métricas EMNLP/ICLR.
5. Probar políticas de caché estática + dinámica en RustingStrata/Tandem o un fork compatible.
6. Solo después estudiar steering pre-softmax en un fork experimental, con regresión de calidad y desactivado por defecto.

### Encaje con el MSI de referencia

MSI Thin 15 B12UC: i7-12650H, RTX 3050 Laptop 4 GiB, 14 GiB RAM, Ubuntu. Es suficiente para medir runtimes con modelos pequeños y para capturar telemetría limitada, pero no para entrenar SARA ni para ejecutar los grandes modelos de los estudios originales. Para Qwen3-30B-A3B y otros MoE con pesos mayores que VRAM, la pregunta central sigue siendo coste de offload, working-set, cache hit y presión de RAM/swap. La instrumentación debe ser ligera y por campañas; no añadir logs completos del router al benchmark normal.

---

## 14. Referencias directas y artefactos de reproducibilidad

### Papers

- [SARA — ACL Findings 2026, landing page](https://aclanthology.org/2026.findings-acl.136/)
- [SARA — PDF](https://aclanthology.org/2026.findings-acl.136.pdf)
- [SARA — código](https://github.com/iMoriton/sara)
- [Probing Semantic Routing — EMNLP Findings 2025, landing page](https://aclanthology.org/2025.findings-emnlp.991/)
- [Probing Semantic Routing — PDF](https://aclanthology.org/2025.findings-emnlp.991.pdf)
- [Multilingual Routing in MoE — ICLR 2026, PDF](https://proceedings.iclr.cc/paper_files/paper/2026/file/1b558190825286a3defcc78d02fa2189-Paper-Conference.pdf)

### Motores y documentos del PR #142

- [Kinetic](https://github.com/Veloresearch/kinetic)
- [TensorFold](https://github.com/ashhart/TensorFold)
- [Tandem.cpp](https://github.com/ewhacc/tandem.cpp)
- [RustingStrata](https://github.com/RustingStudio/RustingStrata)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [Project Maya](https://github.com/mw00/project-maya)
- [PR #142](https://github.com/robertosantosx2/LEONES/pull/142)
- [Plan de benchmark cruzado](../docs/KINETIC-CROSS-ENGINE-BENCHMARK-PLAN-2026-11-11.md)
- [Auditoría de Kinetic](../docs/KINETIC-SOURCE-AUDIT-2026-11-11.md)
- [Contrato de adaptadores](../docs/ENGINE-ADAPTER-CONTRACT.md)
- [Política de vendoring](../docs/ENGINE-SOURCE-VENDORING.md)
- [Runbook de compilación](../docs/ENGINE-BUILD-RUNBOOK.md)
- [Runner de comparación](../scripts/engine_comparison.py)
- [Registro de motores](../configs/engines.registry.json)
- [Configuración de ejemplo](../configs/engine-comparison.example.json)
- [Tests del runner](../tests/test_engine_comparison.py)
- [Artefactos de sesiones](https://github.com/robertosantosx2/LEONES/tree/research/kinetic-audit-benchmark/artifacts/engine-comparison)

**Estado de esta actualización (12-11-2026):** análisis de los tres artículos incorporado; PR #142 inspeccionado como framework de benchmark y vendoring; no se atribuyen velocidades comparativas MEASURED a una campaña que todavía no ha sido ejecutada/documentada en la MSI.
