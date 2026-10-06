# Propuesta de integración de cafe-llama.cpp en ODS

**Línea experimental:** `ods-evolution`  
**Proyecto:** LEONES  
**Fecha:** 2026-10-06  
**Estado:** Estudio de arquitectura e integración — listo para PR a ODS tras validación  
**Upstream:** https://github.com/quimmedes/cafe-llama.cpp  
**Licencia:** MIT (fork de llama.cpp)

## 1. Resumen ejecutivo

**cafe-llama.cpp** es un fork de llama.cpp orientado a maximizar la capacidad real de inferencia local sobre hardware modesto y modelos MoE grandes. Aporta flags y kernels específicos para:

- Offload agresivo de expertos MoE a pinned host RAM (`CUDA_Host`), CPU RAM o SSD (mmap on-demand).
- Turbo KV cache de baja bit-depth (turbo4 / turbo3 / turbo2) con flash-attention.
- Optimizaciones PLE / N-gram internas de Qwen 3.8 Flash Next.
- Speculative decoding MTP (Multi-Token Prediction) y n-gram drafts.
- Carga directa de checkpoints safetensors (sin conversión previa a GGUF).
- Binarios precompilados multi-plataforma (CUDA 12/13, Metal, Vulkan, ROCm, Windows, arm64).

El papel adecuado en ODS es:

> **runtime opcional y avanzado compatible con llama.cpp**, seleccionado cuando el perfil de hardware + modelo (especialmente MoE o contextos largos) se beneficie de sus capacidades de offload y speculative decoding.

Debe complementar, no sustituir, al `llama-server` upstream de ODS.

## 2. Por qué encaja en LEONES → ODS

ODS ya tiene `llama-server` como runtime core. cafe-llama.cpp es una evolución natural del mismo stack:

| Aspecto | llama-server (upstream) | cafe-llama.cpp |
|---------|-------------------------|----------------|
| Compatibilidad GGUF | Amplia | Amplia (compatible) |
| API OpenAI | Sí | Sí (`llama-server`) |
| Offload MoE a host/SSD | Limitado / experimental | Flags de primera clase (`-hmoe`, `-cmoe`, `-ssd`) |
| Turbo KV low-bit | No | turbo4/3/2 + FA obligatorio |
| MTP / speculative | Parcial | Draft-MTP + n-gram + PLE |
| Safetensors nativo | No | Sí (streaming in-memory) |
| Binarios listos | Oficiales ggml-org | Releases propias multi-arch |

Encaja directamente con **Inference Configuration Discovery (ICD)**:

```text
hardware + modelo + cuantización + offload + KV + MTP + workload
        ↓
   Inference Profile medido
```

Permite que ODS descubra configuraciones viables que el upstream llama.cpp no ofrece de forma tan completa (especialmente MoE grandes en GPUs de 8–24 GB).

## 3. Capacidades clave de cafe-llama.cpp

### 3.1 Offload de MoE

| Flag | Descripción |
|------|-------------|
| `-hmoe` / `--host-moe` | Todos los expertos MoE en pinned host RAM (CUDA_Host). GPU calcula; caché de expertos calientes en VRAM. |
| `-nhmoe N` | Solo las primeras N capas en host. |
| `-cmoe` / `--cpu-moe` | Expertos en system RAM. |
| `-ncmoe N` | Primeras N capas en CPU RAM. |
| `-ssd` / `--ssd-streaming` | Expertos streameados desde SSD vía mmap (solo los seleccionados por el token). |
| `-nssd N` | Primeras N capas desde SSD. |
| Variantes `*d` | Equivalentes para el modelo draft (speculative). |

### 3.2 Turbo KV Cache

Tipos `turbo4` (~4.1 bits), `turbo3` (~3.5), `turbo2` (~2.5). Requieren flash-attention (`-fa`). Permiten contextos largos con mucho menos VRAM de KV.

Ejemplo: `-ctk turbo4 -ctv turbo4 -fa on`.

### 3.3 PLE / N-gram (Qwen 3.8 Flash Next)

| Flag | Descripción |
|------|-------------|
| `--ngram-ssd` | Tabla N-gram interna en SSD (mmap). |
| `--no-ngram` | Deshabilita completamente la tabla PLE (ahorra ~51B parámetros). |
| `--ngram` | Carga normal (default). |

### 3.4 Speculative / MTP

- `--spec-type draft-mtp`
- `--spec-draft-n-max 4` (recomendado; >6 degrada por kernels matmul)
- Soporte de draft models GGUF MTP (ej. quimmedes/Qwen3.8-Flash-Next-MTP-GGUF)
- Combinable con n-gram drafts

### 3.5 Safetensors directo

`-m` acepta directorio o fichero `.safetensors`. No genera GGUF intermedio. Soporta FP8, NVFP4, Exl3, etc., con opciones de outtype y native.

## 4. Papel dentro de la arquitectura ODS

```text
USUARIO / CARGA
       ↓
PERFIL DEL MODELO (GGUF o safetensors)
       ↓
PERFIL DE HARDWARE + ALMACENAMIENTO
       ↓
REGISTRO DE CAPACIDADES ODS
       ↓
ESTRATEGIA DE EJECUCIÓN (ICD)
       ↓
SELECTOR DE RUNTIME
       ↓
 ┌──────────────────┬────────────────────┬─────────────────┐
 │ llama-server     │ cafe-llama.cpp     │ TensorFold /    │
 │ (baseline)       │ (avanzado MoE/MTP) │ otros           │
 └──────────────────┴────────────────────┴─────────────────┘
       ↓
API ODS UNIFICADA (OpenAI-compatible)
       ↓
validación / evidencia LEONES
```

Cafe no es un runtime de familia cerrada (como TensorFold). Es un **drop-in avanzado de llama-server** con flags extra. Por tanto puede servir la mayoría de modelos GGUF que ya usa ODS, más modelos MoE grandes que de otro modo no cabrían.

## 5. Diseño de integración propuesto en ODS

### 5.1 Servicio opcional

```text
extensions/services/cafe-llama/
├── manifest.yaml
├── docker-compose.yml          # o native binary path
├── Dockerfile                  # opcional, si se prefiere imagen
├── entrypoint.sh
└── README.md
```

### 5.2 Variables / parámetros a exponer en Dashboard y `.env`

Prioridad alta (deben aparecer en el formulario avanzado):

| Parámetro | Flag cafe | Descripción |
|-----------|-----------|-------------|
| GPU layers | `-ngl` | Capas en GPU |
| Host MoE | `-hmoe` / `-nhmoe` | Offload de expertos a pinned RAM |
| CPU MoE | `-cmoe` / `-ncmoe` | Offload a system RAM |
| SSD streaming | `-ssd` / `-nssd` | Expertos desde SSD |
| Context size | `-c` | Ventana de contexto |
| KV cache type | `-ctk` / `-ctv` | q8_0, turbo4, etc. |
| Flash attention | `-fa` | Obligatorio para turbo KV |
| Spec type | `--spec-type` | draft-mtp, ngram-mod, … |
| Spec draft n-max | `--spec-draft-n-max` | Recomendado 4 |
| Draft model | `-md` | Ruta del MTP/draft GGUF |
| N-gram PLE | `--no-ngram` / `--ngram-ssd` | Control de tabla interna |
| Pipeline parallel | `--pipeline-parallel` | Overlap host→device |
| Threads / batch | `-t`, `-b`, `-ub`, `-np` | Rendimiento |

Estos parámetros se mapean de forma natural sobre el sistema existente de `LLAMA_ARG_*` y el Model Switchboard de ODS.

### 5.3 Activación

```bash
ods enable cafe-llama
# o
ODS_INFERENCE_RUNTIME=cafe-llama
```

El instalador/binario puede:
1. Descargar release precompilada de quimmedes/cafe-llama.cpp (recomendado), o
2. Compilar desde fuente cuando se necesite un backend concreto no cubierto por los binaries.

### 5.4 Compatibilidad con el stack actual

- Misma API OpenAI-compatible que llama-server → Portal, Open WebUI, Hermes, LiteLLM, clientes externos siguen funcionando sin cambios.
- Modelos GGUF existentes del catálogo ODS siguen siendo válidos.
- Se puede mantener ambos runtimes instalados y cambiar por perfil / modelo.

## 6. Matriz de evidencia y reglas LEONES

| Clase | Significado |
|-------|-------------|
| **REPORTED** | Cifras publicadas por el proyecto cafe-llama.cpp o usuarios (X, issues). |
| **OBSERVED** | Capacidad verificada en README / releases / código. |
| **ESTIMATED** | Inferencia de viabilidad antes de ejecutar. |
| **MEASURED** | Resultado producido por LEONES en hardware objetivo (única clase válida para afirmar rendimiento local). |

Ejemplo de registro de capacidad:

```yaml
runtime:
  cafe-llama:
    supported: true
    upstream: https://github.com/quimmedes/cafe-llama.cpp
    api:
      openai_compatible: true
      binary: llama-server
    capabilities:
      moe_host_offload: true
      moe_cpu_offload: true
      moe_ssd_streaming: true
      turbo_kv: true
      mtp_speculative: true
      ple_ngram_control: true
      safetensors_native: true
    constraints:
      gguf: true
      family_specific: false   # a diferencia de TensorFold
    evidence_class_default: OBSERVED
```

## 7. Fases de implementación recomendadas

### Fase 1 — Documentación y registro (este PR en LEONES)
- Documento de integración (este archivo).
- Entrada en el registro de capacidades / ROADMAP de integraciones.

### Fase 2 — Runtime opcional en ODS (PR futuro a Osmantic/ODS)
- Servicio `cafe-llama` opt-in.
- Descarga de binario o build controlada.
- Exposición de los parámetros prioritarios en Dashboard → Models (sección avanzada).
- Health check y `ods status`.

### Fase 3 — Perfiles recomendados
- Perfiles predefinidos por envelope de hardware (ej. “MoE 8–12 GB”, “MoE 16–24 GB + MTP”, “long-context turbo-KV”).
- Integración con ICD: candidate generation → local benchmark → best profile.

### Fase 4 — Evidencia medida
- Workloads estandarizados (tok/s + Octopus Invaders u otros).
- Comparativa lado a lado con llama-server upstream bajo las mismas condiciones.
- Persistencia de Inference Profiles medidos.

## 8. Qué no hacer

- No sustituir el `llama-server` por defecto de ODS.
- No presentar cafe como “mejor en todo”; es mejor en escenarios concretos (MoE grandes, contextos largos, speculative agresivo).
- No copiar benchmarks de X/Reddit como `MEASURED`.
- No asumir que todos los flags funcionan igual en Metal / Vulkan / ROCm; validar por backend.
- No mezclar la identidad de salida de cafe con la de TensorFold u otros runtimes.

## 9. Relación con TensorFold, Strata y Bonsai

| Runtime | Fortaleza principal | Tipo de integración |
|---------|---------------------|---------------------|
| llama-server | Baseline amplia, estable | Core |
| **cafe-llama.cpp** | Offload MoE + Turbo KV + MTP genérico | Runtime avanzado compatible |
| TensorFold | Kernels por familia + exact speculative | Runtime especializado family-specific |
| Strata / heterogéneo | Ejecución > VRAM (placement) | Runtime de memoria/placement |
| Bonsai / PTQ kernels | Cuantización extrema + kernel | Evidencia de configuración / kernel |

Cafe y TensorFold son complementarios: Cafe amplía el espacio de configuraciones de llama.cpp; TensorFold ofrece motores de familia cerrada con contrato de exactitud interno.

## 10. Conclusión y siguiente paso

cafe-llama.cpp es el candidato más natural y de menor fricción para el siguiente runtime opcional de ODS después del baseline llama-server:

- Mantiene la API y el formato GGUF.
- Añade dimensiones reales de capacidad (MoE offload, Turbo KV, MTP, PLE).
- Encaja perfectamente en el modelo de Inference Profiles del ICD.
- Permite que ODS deje de rechazar modelos “demasiado grandes” solo por VRAM teórica.

**Acción inmediata:** este documento se incorpora a LEONES.  
**Acción siguiente:** una vez revisado y estabilizado, abrir PR formal contra `Osmantic/ODS` (o el fork de trabajo) con el servicio opt-in y la exposición de parámetros en Dashboard.

## Referencias

- https://github.com/quimmedes/cafe-llama.cpp
- https://github.com/quimmedes/cafe-llama.cpp/releases
- https://huggingface.co/quimmedes/Qwen3.8-Flash-Next-MTP-GGUF
- Documentos relacionados en este repo:
  - `docs/integrations/tensorfold/README.md`
  - `docs/integrations/ODS/INFERENCE-CONFIGURATION-DISCOVERY-2026-10-06.md`
  - `docs/integrations/Bonsai2-Small-GPU-EXTERNAL-EVIDENCE.md`
  - `docs/integrations/cafe-llamacpp-vs-strata-vs-tensorfold-2026-10-06.html`
