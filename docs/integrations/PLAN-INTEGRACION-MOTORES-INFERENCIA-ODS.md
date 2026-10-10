# Plan de integración de motores de inferencia en ODS

**Línea experimental:** `ods-evolution`  
**Proyecto:** LEONES  
**Fecha:** 2026-10-10  
**Estado:** Plan de arquitectura e integración — listo para revisión y scaffold en ODS  
**Alcance:** TensorFold, cafe-llama.cpp, Strata, AirLLM (y relación con llama-server baseline)

---

## 1. Resumen ejecutivo

ODS (Osmantic Deployment System) tiene hoy **llama-server** (llama.cpp) como runtime de inferencia core. Para maximizar capacidad real sobre hardware heterogéneo sin fragmentar la experiencia de usuario, se proponen **runtimes opcionales y complementarios**, no sustitutivos.

| Runtime | Rol propuesto | Tipo |
|---------|---------------|------|
| **llama-server** | Baseline / core | Amplio, estable, multi-backend |
| **cafe-llama.cpp** | Opcional avanzado compatible | Drop-in de llama.cpp con MoE offload, Turbo KV, MTP/PLE |
| **TensorFold** | Especializado family-specific | Kernels por familia + speculative decoding **byte-exact** |
| **Strata** | Especializado MoE grande en consumer GPU | Placement multi-tier (VRAM/RAM/SSD) para Qwen3.8 Flash Next |
| **AirLLM** | Experimental / accesibilidad | Layer streaming; no producción |

El patrón de referencia ya validado en LEONES es la propuesta de **cafe-llama.cpp** (`docs/integrations/cafe-llama.cpp/`). Este plan lo generaliza a un **Runtime Registry + ICD** común para que añadir TensorFold, Strata o AirLLM sea barato y consistente.

**Principio rector LEONES:** solo evidencia **MEASURED** (ejecución física autorizada en hardware objetivo) puede afirmar rendimiento local. REPORTED / OBSERVED / ESTIMATED son informativos.

---

## 2. Roles y fortalezas (matriz de decisión)

| Runtime | Fortaleza principal | Formato checkpoints | API | Cuándo elegirlo |
|---------|---------------------|---------------------|-----|-----------------|
| llama-server | Amplia, estable, multi-backend (CUDA/Metal/Vulkan/SYCL) | GGUF | OpenAI | Default; siempre disponible |
| cafe-llama.cpp | MoE offload (host/CPU/SSD), Turbo KV, MTP/PLE genérico, safetensors nativo | GGUF + safetensors | OpenAI | MoE grandes en 8–24 GB; contextos largos; flags que upstream no expone igual |
| TensorFold | Kernels por familia + speculative **exacto** (drafted == serial del mismo motor) | MLX affine / TensorFold-owned (no GGUF genérico) | OpenAI + Anthropic | Familias cualificadas (Nemotron 3.5 Lightning, Qwen3.8-27B+DFlash2, Flash Next, GLM-5.3-Flash, Qwen3.5-2B) en Metal/CUDA cualificado |
| Strata | Qwen3.8 Flash Next en 12–24 GB VRAM + 32–64 GB RAM | Propio | OpenAI + Anthropic | Flash Next en gaming PC; placement multi-tier |
| AirLLM | Modelos enormes en VRAM mínima (layer streaming) | HF safetensors sharded | Transformers-like | Solo investigación / “cabe aunque sea lento”; no producción |

**Complementariedad clave:**

- Cafe amplía el espacio de configuraciones de llama.cpp.
- TensorFold ofrece motores cerrados por familia con contrato de exactitud y velocidad superior en combinaciones cualificadas.
- Strata es el especialista extremo en Flash Next sobre hardware modesto.
- AirLLM es el extremo de accesibilidad a costa de throughput.

No se sustituye llama-server. No se presenta ningún runtime como “mejor en todo”.

---

## 3. Qué se aprovecha de la integración cafe-llama.cpp

La propuesta de cafe (`docs/integrations/cafe-llama.cpp/README.md`) es el **patrón de referencia**. Reutilizar:

1. **Servicio opt-in** bajo `extensions/services/<runtime>/` (manifest, entrypoint, compose o native path, README).
2. **Activación:** `ods enable <runtime>` o `ODS_INFERENCE_RUNTIME=<runtime>` / selector por perfil o modelo.
3. **Registro de capacidades** en ICD / capability registry con clases REPORTED | OBSERVED | ESTIMATED | MEASURED.
4. **Dashboard:** parámetros prioritarios en sección avanzada; clientes (Portal, Open WebUI, agentes, n8n) solo ven la API OpenAI-compatible unificada.
5. **Fases:** docs → servicio opt-in → perfiles ICD → evidencia MEASURED.
6. **Reglas de “qué no hacer”:** no sustituir baseline, no copiar benchmarks externos como MEASURED, validar por backend/hardware, no mezclar identidades de salida entre runtimes.

**Diferencias que hay que diseñar desde el día 1 para TensorFold (y análogas para Strata/AirLLM):**

| Aspecto | cafe-llama | TensorFold |
|---------|------------|------------|
| Alcance modelos | Genérico GGUF (+ safetensors) | Lista corta family-specific |
| Checkpoints | Compatible con catálogo ODS GGUF | MLX / TensorFold-owned; `tensorfold pull` |
| Binario | Precompilados multi-arch o build | Preferir nativo Zig 1.0.x; Python 0.6 como fallback |
| Exactitud | No contrato formal | Drafted == serial (byte-identical) |
| Hardware inicial | CUDA/Metal/Vulkan según binario | Metal (Apple Silicon) + CUDA cualificado |

---

## 4. Arquitectura común: Runtime Registry + ICD

Objetivo: un solo camino de descubrimiento, selección, arranque y evidencia.

```text
USUARIO / CARGA / HARDWARE
        ↓
PERFIL DEL MODELO (familia, cuantización, formato)
        ↓
PERFIL DE HARDWARE + ALMACENAMIENTO
        ↓
REGISTRO DE CAPACIDADES ODS (Runtime Registry)
        ↓
ESTRATEGIA DE EJECUCIÓN (ICD — Inference Configuration Discovery)
        ↓
SELECTOR DE RUNTIME + Inference Profile
        ↓
┌──────────────┬─────────────────┬──────────────┬─────────┬─────────┐
│ llama-server │ cafe-llama.cpp  │ TensorFold   │ Strata  │ AirLLM  │
│ (baseline)   │ (avanzado MoE)  │ (family)     │ (MoE)   │ (exp.)  │
└──────────────┴─────────────────┴──────────────┴─────────┴─────────┘
        ↓
API ODS UNIFICADA (OpenAI-compatible / proxy)
        ↓
validación / evidencia LEONES (MEASURED)
```

### 4.1 Runtime Registry (esquema orientativo)

```yaml
runtime:
  id: tensorfold
  supported: conditional
  upstream: https://github.com/ashhart/TensorFold
  license: Apache-2.0
  api:
    openai_compatible: true
    anthropic_messages: true
    binary: tensorfold / tensorfold-native
  backends:
    - metal
    - cuda
  capabilities:
    exact_speculative_decoding: true
    family_specific_kernels: true
    mtp_draft: true
    dflash_draft: true
  constraints:
    model_family_specific: true
    checkpoint_specific: true
    gguf: false
  qualified_models:   # actualizar con releases TensorFold
    - family: Nemotron-3.5-Lightning
      platforms: [metal-m1-m5, cuda-gb10, cuda-rtx3090]
    - family: Qwen3.8-27B
      platforms: [metal-m5-max, metal-m3-ultra]
      drafter: DFlash2
    - family: Qwen3.8-Flash-Next
      platforms: [metal-m5-ultra]
    - family: GLM-5.3-Flash
      platforms: [metal-2x-m5-ultra]
    - family: Qwen3.5-2B
      platforms: [metal-m5-max]
  evidence_class_default: OBSERVED
```

Análogo para cafe-llama (ya esbozado en su README), Strata y AirLLM (`experimental: true`).

### 4.2 Capas a introducir o reforzar en ODS

1. **Runtime Registry** — extensión del capability-profile / ICD.
2. **Model Catalog ampliado** — entradas con runtime preferido + fallback ordenado.
3. **Unified Serve Adapter** — `start_runtime(runtime_id, model_id, profile)` genera comando/compose; health y `/v1/models` normalizados.
4. **Dashboard unificado** — selector de runtime + parámetros comunes + sección avanzada por runtime.
5. **ICD / Inference Profiles** — candidatos → benchmark local (tok/s, TTFT, memoria, exactitud si aplica) → perfil MEASURED persistido.
6. **Evidencia LEONES** — mismo esquema de clases para todos los runtimes.

---

## 5. Detalle por runtime

### 5.1 TensorFold

**Upstream:** https://tensorfold.dev / https://github.com/ashhart/TensorFold  
**Licencia:** Apache-2.0 (desde 0.6.0)  
**Estado relevante:** 1.0.x nativo Zig (sin Python/MLX en runtime de serve); línea Python 0.6 mantenida.

**Instalación propuesta:**

- macOS: Homebrew `ashhart/tensorfold/tensorfold` o release arm64 + install.sh.
- Linux CUDA cualificado: release / install.sh / binario nativo cuando exista para la plataforma.
- Docker: opcional (fallback); preferir native en Metal y en hosts CUDA cualificados.

**Parámetros prioritarios Dashboard / `.env`:**

| Parámetro | Flag / env TensorFold | Descripción |
|-----------|----------------------|-------------|
| Model path / name | `serve PATH --name` | Checkpoint local o tras `tensorfold pull` |
| Context | `--context` | Ventana de contexto |
| Parallel | `--parallel` | Streams concurrentes (limitado por familia) |
| Temperature | `--temperature` | Sampling |
| Draft | draft on/off / `--drafter` | MTP o DFlash2 según familia |
| Keep-warm | `--keep-warm` | Metal idle keepalive |
| No-thinking | `--no-thinking` | Cuando aplique |

**Gestión de modelos:**

- Integrar o envolver `tensorfold pull`.
- Caché separada del catálogo GGUF de ODS.
- Respetar restricciones de hard-links / Sliding Weights (no reescribir snapshots compartidos del cache HF).

**Health / API:**

- Endpoint detrás del proxy unificado de ODS (mismo puerto lógico que llama-server desde el punto de vista de clientes).
- `/health`, `/v1/models`, chat completions, streaming.

### 5.2 cafe-llama.cpp

Ya documentado en `docs/integrations/cafe-llama.cpp/`. Resumen de reutilización:

- Flags prioritarios: `-hmoe`/`-cmoe`/`-ssd`, Turbo KV (`-ctk`/`-ctv` turbo*), `-fa`, `--spec-type draft-mtp`, `--spec-draft-n-max`, PLE/ngram, pipeline-parallel.
- Mismo GGUF del catálogo ODS cuando sea posible.
- No sustituir llama-server.

### 5.3 Strata

- Especialista en Qwen3.8 Flash Next en 12–24 GB VRAM + RAM sistema.
- Mismo patrón opt-in + registry.
- Activación condicionada a detección de hardware + modelo Flash Next.
- Evidencia MEASURED obligatoria antes de recomendar en LEONES.

### 5.4 AirLLM

- Marcar `experimental: true` / `production: false`.
- No activar por defecto ni en perfiles de producción.
- Útil solo para “¿cabe este modelo en esta VRAM?” con throughput muy bajo.
- Registry + documentación; sin promesa de rendimiento.

---

## 6. Estructura de servicio propuesta (TensorFold ejemplo)

```text
extensions/services/tensorfold/
├── manifest.yaml
├── docker-compose.yml          # opcional
├── Dockerfile                  # opcional
├── entrypoint.sh               # preferir native
├── native-install.sh           # Homebrew / release assets
└── README.md
```

**Activación:**

```bash
ods enable tensorfold
# o
ODS_INFERENCE_RUNTIME=tensorfold
```

El selector ICD puede forzar TensorFold solo cuando hardware + familia estén en la matriz cualificada; en caso contrario fallback a cafe-llama o llama-server con mensaje claro en Dashboard.

---

## 7. Fases priorizadas de implementación

### Prioridad 1 — Fundación (1–2 semanas)

- [x] Este plan en LEONES.
- [ ] Documento espejo TensorFold alineado con estilo cafe-llama (`docs/integrations/tensorfold/` — completar si hace falta).
- [ ] Entrada en Runtime Registry / ROADMAP de integraciones.
- [ ] Matriz modelos cualificados × plataforma (fuente: releases TensorFold 1.0.x).
- [ ] Política de instalación del binario (Homebrew / install.sh / assets) y de caché de pesos.

### Prioridad 2 — Servicio opt-in MVP (2–4 semanas)

- [ ] `extensions/services/tensorfold/` (manifest, entrypoint native, health).
- [ ] Variables y parámetros Dashboard prioritarios.
- [ ] `ods enable tensorfold` + exposición detrás del proxy OpenAI-compatible.
- [ ] Soporte inicial: Apple Silicon (Metal) + NVIDIA CUDA cualificado.
- [ ] Tests de humo: start → `/v1/models` → chat completion.
- [ ] Scaffold análogo ya iniciado para cafe-llama; mantener paridad de interfaz.

### Prioridad 3 — ICD + perfiles (3–6 semanas)

- [ ] Candidate generation que incluya TensorFold / cafe / Strata según hardware+familia.
- [ ] Perfiles predefinidos (ej. “Nemotron Lightning high-speed”, “Flash Next exact-MTP”, “MoE 8–12 GB cafe”).
- [ ] Benchmarks estandarizados: tok/s, TTFT, memoria peak, verificación exactitud (TensorFold).
- [ ] Persistencia de Inference Profiles **MEASURED**.
- [ ] Fallback automático documentado.

### Prioridad 4 — UX y operaciones

- [ ] Integración de `tensorfold pull` / gestión de modelos no-GGUF.
- [ ] Métricas unificadas (Prometheus / Dashboard).
- [ ] Documentación de usuario: cuándo elegir cada runtime.
- [ ] Concurrency / multi-usuario (limitaciones por familia en TensorFold).

### Prioridad 5 — Strata y AirLLM

- [ ] Strata: mismo patrón opt-in + perfiles Flash Next en consumer GPU.
- [ ] AirLLM: solo experimental en registry; sin activación por defecto.

---

## 8. Reglas de evidencia LEONES (obligatorias)

| Clase | Significado | Uso permitido |
|-------|------------|---------------|
| **REPORTED** | Cifras publicadas por upstream o terceros | Contexto, nunca como rendimiento local garantizado |
| **OBSERVED** | Capacidad verificada en README/releases/código | Registro de capacidades |
| **ESTIMATED** | Inferencia de viabilidad antes de ejecutar | FitLLM / preselección |
| **MEASURED** | Resultado de ejecución física autorizada en hardware objetivo | Única clase válida para afirmar tok/s, TTFT, memoria en LEONES/ODS |

No reutilizar resultados de otras máquinas como MEASURED. No copiar benchmarks de X/Reddit como MEASURED.

---

## 9. Qué no hacer

- No sustituir el `llama-server` por defecto de ODS.
- No presentar TensorFold, cafe, Strata o AirLLM como “mejor en todo”.
- No mezclar identidades de salida ni caches de checkpoints entre runtimes.
- No asumir que todos los flags/backends de cafe o TensorFold funcionan igual en Metal / CUDA / Vulkan / ROCm sin validación.
- No activar AirLLM en perfiles de producción.
- No afirmar soporte AMD/Windows nativo para TensorFold hasta validación MEASURED.
- No abrir PRs de implementación a Osmantic/ODS sin revisión humana del diseño en LEONES.

---

## 10. Relación con documentos existentes en LEONES

- `docs/integrations/cafe-llama.cpp/README.md` — patrón de referencia.
- `docs/integrations/tensorfold/` — propuesta TensorFold (completar alineación con este plan).
- `docs/integrations/airllm/` — base experimental.
- `docs/integrations/cafe-llamacpp-vs-strata-vs-tensorfold-2026-10-06.html` — comparación.
- `docs/integrations/ODS/INFERENCE-CONFIGURATION-DISCOVERY-*.md` — ICD.
- `docs/integrations/Bonsai2-Small-GPU-EXTERNAL-EVIDENCE.md` — evidencia externa de referencia.
- Arquitectura ODS-LEONES completa (docs/integrations/ODS-LEONES-COMPLETE-ARCHITECTURE*.md).

---

## 11. Siguiente paso inmediato

1. Revisión humana de este plan en LEONES (`ods-evolution`).
2. Completar/actualizar `docs/integrations/tensorfold/README.md` si el borrador existente no cubre registry + fases de este documento.
3. Scaffold de servicio TensorFold en el fork de trabajo de ODS (espejo del scaffold cafe-llama), sin activar por defecto.
4. Definir 2–3 perfiles ICD mínimos y un workload de benchmark común para generar la primera evidencia MEASURED en hardware disponible.

---

## Referencias

- TensorFold: https://tensorfold.dev — https://github.com/ashhart/TensorFold
- cafe-llama.cpp: https://github.com/quimmedes/cafe-llama.cpp
- ODS: https://github.com/Osmantic/ODS — https://osmantic.com
- LEONES (este repo): rama `ods-evolution`, `docs/integrations/`
- MTP GGUF (cafe): https://huggingface.co/quimmedes/Qwen3.8-Flash-Next-MTP-GGUF

---

*Documento generado como plan de investigación LEONES → ODS. No constituye implementación en producción ni promesa de soporte hasta completar las fases y evidencia MEASURED correspondientes.*
