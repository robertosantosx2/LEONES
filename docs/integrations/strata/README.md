# Propuesta de integración de Strata en ODS

**Línea experimental:** `ods-evolution`  
**Proyecto:** LEONES  
**Fecha:** 2026-10-11 (detalle ampliado)  
**Estado:** Estudio de arquitectura e integración detallado — depende de la infraestructura cafe-llama.cpp y del i18n del Dashboard (pendiente de merge)  
**Upstream:** https://github.com/Niko1221/Strata  
**Licencia:** MIT  
**Plan maestro:** `docs/integrations/PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md`  
**Patrón de referencia:** `docs/integrations/cafe-llama.cpp/README.md`  
**i18n Dashboard:** `docs/ODS-DASHBOARD-I18N-PR.md` (en / es / zh-CN; pendiente de merge upstream)

---

## 1. Resumen ejecutivo

**Strata** es un motor de inferencia MIT orientado a **un modelo y una clase de hardware**: ejecutar **Qwen3.8-Flash-Next** (MoE ~125B parámetros totales; ~6B activos por token; 24 576 expertos, ~10 por token) en un PC de consumo con **GPU NVIDIA o AMD ≥ 12 GB VRAM** y **32–64 GB de RAM**, mediante placement multi-tier (VRAM / RAM / SSD), speculative decoding documentado y API **OpenAI- y Anthropic-compatibles** en localhost (chat, messages, responses; imagen opcional).

No es un runtime genérico. Ocupa el nicho “Flash Next en hardware modesto” junto a cafe-llama (offload MoE genérico) y TensorFold (familia Flash Next cualificada), con un contrato distinto: **producto one-model**, instalador one-click (`START-HERE.bat` / `setup.sh` / Docker) y stack C++/CUDA/HIP + servidor Python.

**Papel en ODS:**

> Runtime **opcional y altamente especializado**, seleccionado solo cuando el modelo es Flash Next (o variante admitida: Coder, Swift 1.5, Unsloth, etc.) **y** el hardware cumple el envelope documentado por Strata.

Debe **complementar, no sustituir**, a `llama-server`. Debe **reutilizar** el armazón de cafe-llama (servicio opt-in, Runtime Registry, ICD, Dashboard avanzado, evidencia LEONES) y la **capa i18n** del Dashboard para toda UI nueva.

---

## 2. Infraestructura a reutilizar (cafe-llama + i18n)

### 2.1 Cafe-llama como camino estándar de runtime opcional

| Pieza | Cafe-llama aporta | Strata reutiliza |
|-------|-------------------|------------------|
| Layout de servicio | `extensions/services/<runtime>/` | `extensions/services/strata/` |
| Activación | `ods enable` / `ODS_INFERENCE_RUNTIME` | `ods enable strata` |
| Runtime Registry | capacidades + constraints + evidence_class | `flash_next_only`, min VRAM/RAM/disco |
| ICD | hardware + modelo → perfil medido | Solo si familia Flash Next + envelope |
| Dashboard avanzado | params prioritarios | size, context, vision, KV, GPU, family |
| Proxy API | OpenAI-compatible unificado | Clientes ODS agnósticos al runtime |
| Evidencia | REPORTED / OBSERVED / ESTIMATED / MEASURED | Benchmarks públicos Strata = REPORTED |
| Coexistencia | No sustituye baseline | Selector elige; varios runtimes instalados OK |

**Secuencia:** estabilizar scaffold cafe-llama (servicio + registry + hooks Dashboard) antes o en paralelo controlado con Strata.

### 2.2 i18n del Dashboard (pendiente de merge)

Referencia: `docs/ODS-DASHBOARD-I18N-PR.md`.

- Locales: `en` (default + fallback), `es`, `zh-CN`.
- Persistencia: `ods.language.v1`.
- Claves planas; resolución locale → en → clave literal.
- **Regla Strata:** ninguna cadena de UI hardcodeada; identificadores técnicos sin traducir (`Strata`, `Q2_0`, `IQ2_XS`, flags, rutas, env).

**Claves i18n propuestas (completas):**

```text
runtime.strata.title
runtime.strata.description
runtime.strata.enable
runtime.strata.disable
runtime.strata.status.ready
runtime.strata.status.downloading
runtime.strata.status.starting
runtime.strata.status.failed
runtime.strata.status.notInstalled
runtime.strata.modelSize
runtime.strata.modelSize.help
runtime.strata.family
runtime.strata.family.flashNext
runtime.strata.family.coder
runtime.strata.family.swift
runtime.strata.family.unsloth
runtime.strata.context
runtime.strata.vision
runtime.strata.vision.no
runtime.strata.vision.yes
runtime.strata.vision.cpu
runtime.strata.kvCache
runtime.strata.gpu
runtime.strata.lowRam
runtime.strata.requirements.title
runtime.strata.requirements.vram
runtime.strata.requirements.ram
runtime.strata.requirements.disk
runtime.strata.requirements.os
runtime.strata.notQualified
runtime.strata.notQualified.hint
runtime.strata.consent.download
runtime.strata.consent.download.size
runtime.strata.fallbackCafe
runtime.strata.fallbackLlama
runtime.strata.fallbackTensorfold
runtime.strata.healthOk
runtime.strata.healthFail
runtime.strata.firstStart.warn
runtime.strata.portInUse
```

Preferible merge del PR i18n antes del PR de servicio Strata; si no, incluir diccionarios en el mismo tren.

---

## 3. Capacidades upstream (OBSERVED / REPORTED)

### 3.1 Cómo funciona (resumen técnico)

Según documentación de Strata (HOW_IT_WORKS / README):

- El modelo es un equipo de **24 576 expertos**; cada token usa ~10.
- **GPU:** guarda los expertos más usados.
- **RAM:** mantiene el conjunto de expertos (shard 1); el sistema puede quedar bajo presión al primer arranque (1–3 min “congelado” es comportamiento documentado).
- **SSD:** tabla de lookup grande (shard 2, ~29 GB) vía mmap.
- **Guess-and-check:** un ayudante propone tokens; el modelo grande verifica en bloque (~1.6–1.8× — **REPORTED**).
- Prefill en bloques grandes (hasta 8 192 tokens) a >1 000 tok/s en hardware de referencia upstream.

### 3.2 Envelope de hardware (documentación Strata)

| Recurso | Requisito documentado |
|---------|------------------------|
| GPU | NVIDIA RTX 20/30/40/50 **o** AMD Radeon listada; **≥ 12 GB VRAM** |
| RAM | **≥ 32 GB** (elige size); **64 GB** para todos los sizes principales |
| Disco | **~80 GB libres**; SSD/NVMe recomendado |
| OS | Windows 10/11 o Linux; driver actual |
| Multi-GPU | 2–3 tarjetas documentado (`docs/MULTI_GPU.md`) |
| AMD HIP | Soportado en lista de GPUs; vision en AMD Linux vía CPU; Windows vision limitado |
| Experimental | GPUs antiguas, Intel Arc, Strix Halo, CPUs sin AVX2 — docs aparte; no default ODS |

### 3.3 Sizes y versiones de modelo

**Sizes principales (familia original) — requisitos RAM+VRAM y carácter (upstream MODELS.md):**

| Size | RAM+VRAM approx. | Velocidad relativa | Calidad relativa |
|------|------------------:|--------------------|------------------|
| **Q2_0** | 37.6 GB | Más rápida | Buena |
| **IQ2_XS** | 39.2 GB | Rápida | Mejor (**recomendada**) |
| **IQ3_XXS** | 47.0 GB | Más lenta | Muy buena |
| **IQ3_S** | 54.8 GB | Más lenta | Mejor (cerca del full en tests publicados) |

Descarga típica 66–76 GB (+ capa MTP draft ~6 GB; +1 GB con imágenes). Primer arranque puede cargar 35–55 GB en RAM.

**Elección por RAM del sistema (upstream):**

| RAM del PC | Recomendación Strata |
|------------|----------------------|
| 32 GB | **Coder** (cabe); con GPU 24 GB también Q2_0 / IQ2_XS en low-RAM |
| 48 GB | **IQ2_XS** o **Q2_0** |
| 64 GB | **IQ2_XS** (default); IQ3_XXS / IQ3_S posibles |
| ≥ 96 GB | **IQ3_S** o Unsloth UD-IQ4_XS |

**Versiones / familias adicionales:**

| Familia | Notas |
|---------|--------|
| **Flash Next** (default) | Todos los sizes; vision; speed projection experimental |
| **Coder** (ISTA-DASLab) | 256/512 expertos; IQ1_M; cabe en ~32 GB RAM; fuerte en código; más débil fuera de código / CJK |
| **Swift 1.5** | Fine-tune; menos “thinking”; calidad similar; misma RAM aprox. |
| **Unsloth UD-IQ4_XS** | ~4-bit; descarga ~94 GB; ≥ 48 GB RAM; parte desde SSD si RAM < ~80 GB |
| **Unsloth UD-Q4_K_XL** | Experimental; más cerca del full; muy lento si expertos salen del SSD |
| **OrcaRouter Uncensored** | Setup manual; no menú del installer |

### 3.4 Rendimiento publicado (solo REPORTED)

Ejemplo NVIDIA RTX 5070 12 GB + 64 GB RAM (upstream):

| Size | Generate (chat corto) | Prefill (prompt largo) |
|------|----------------------:|------------------------:|
| Q2_0 | ~94 tok/s | ~2 650 tok/s |
| IQ2_XS | ~79 tok/s | ~2 090 tok/s |
| IQ3_XXS | ~62 tok/s | ~1 750 tok/s |
| IQ3_S | ~53 tok/s | ~1 620 tok/s |
| Coder | ~55 tok/s | ~2 180 tok/s |

AMD RX 9070 XT (ejemplo upstream): cifras menores (p. ej. Q2_0 ~60 tok/s generate). **Prohibido** usar estas cifras como MEASURED en otro hardware.

### 3.5 API y uso

| Superficie | URL / nota |
|------------|------------|
| App web Strata | `http://127.0.0.1:8080` (Chat, Monitor, About) |
| OpenAI-compatible | `http://127.0.0.1:8080/v1` |
| Anthropic Messages | `http://127.0.0.1:8080/v1/messages` |
| OpenAI Responses | `/v1/responses` |
| Reasoning effort | off / low / medium / high |
| Parallel | default 1 request; `