# Propuesta de integración de TensorFold en ODS

**Línea experimental:** `ods-evolution`  
**Proyecto:** LEONES  
**Fecha:** 2026-10-11  
**Estado:** Estudio de arquitectura e integración — alineado con el plan de motores; listo para scaffold en ODS tras validación  
**Upstream:** https://github.com/ashhart/TensorFold — https://tensorfold.dev  
**Licencia:** Apache-2.0 (desde 0.6.0; releases anteriores MIT)  
**Plan maestro:** `docs/integrations/PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md`

---

## 1. Resumen ejecutivo

**TensorFold** es un motor de inferencia local de código abierto orientado a **familias de modelos concretas**. Aporta:

- Kernels escritos por familia (Metal / CUDA).
- Speculative decoding con contrato de **exactitud byte-identical** respecto a la decodificación serial del **mismo** motor, pesos y configuración.
- API compatible con OpenAI (chat/completions, completions, responses) y Anthropic Messages.
- Runtime nativo Zig (1.0.x): serve sin Python ni MLX instalados en el host.
- Checkpoints cualificados (MLX affine y recetas propias); **no** es un loader genérico GGUF.

El papel adecuado en ODS es:

> **runtime opcional y especializado (family-specific)**, seleccionado solo cuando el hardware y la familia/checkpoint están en la matriz cualificada de TensorFold.

Debe **complementar, no sustituir**, al `llama-server` upstream de ODS. Es complementario de **cafe-llama.cpp** (drop-in avanzado de llama.cpp) y de **Strata** (placement extremo para Flash Next en consumer GPU).

---

## 2. Por qué encaja en LEONES → ODS

ODS ya tiene `llama-server` como runtime core y café-llama como candidato avanzado compatible. TensorFold aporta una dimensión distinta:

| Aspecto | llama-server | cafe-llama.cpp | TensorFold |
|---------|--------------|----------------|------------|
| Alcance modelos | Amplio GGUF | Amplio GGUF + safetensors | Lista corta family-specific |
| API OpenAI | Sí | Sí | Sí (+ Anthropic Messages) |
| Speculative | Parcial | MTP / n-gram / PLE | MTP / DFlash + **exact same-engine** |
| Formato checkpoint | GGUF | GGUF + safetensors nativo | MLX affine / TensorFold-owned |
| Kernels | Generales ggml | Extensiones sobre llama.cpp | Por familia (Metal/CUDA) |
| Contrato de salida | No formal | No formal | Drafted == serial (byte-identical) |
| Instalación | Contenedor / native | Binarios multi-arch | Nativo Zig 1.0.x (preferido); Python 0.6 fallback |

Encaja en **Inference Configuration Discovery (ICD)**:

```text
hardware + familia + checkpoint cualificado + draft + workload
        ↓
   Inference Profile medido (solo MEASURED afirma rendimiento local)
```

Permite que ODS ofrezca rutas de alto rendimiento y exactitud reproducible en las combinaciones donde TensorFold está cualificado, sin pretender sustituir el camino genérico GGUF.

---

## 3. Capacidades clave de TensorFold (estado 1.0.x)

### 3.1 Runtime nativo Zig (1.0.x)

- Serve sin Python ni MLX en el proceso de serving.
- Carga de checkpoints, tokenización, chat templates e inferencia en el binario nativo.
- Línea Python 0.6 mantenida para familias/rutas aún no migradas al nativo.

### 3.2 Speculative decoding exacto

- Un drafter propone tokens; el modelo objetivo los verifica en bloque.
- Solo se aceptan tokens que coinciden con lo que produciría la decodificación serial del **mismo** motor.
- Cada release documenta comprobaciones drafted == serial.
- **Importante para LEONES:** esto es contrato *intra-motor*, no equivalencia entre TensorFold y llama.cpp / vLLM / otros.

### 3.3 Matriz cualificada orientativa (1.0.4 — actualizar con cada release)

| Familia / modelo | Formato checkpoint | Plataforma cualificada (documentada) | Draft |
|------------------|--------------------|--------------------------------------|-------|
| Nemotron 3.5 Lightning 30B-A3B | MLX affine 4-bit + MTP head | Metal M1–M5; CUDA GB10 / RTX 3090 | MTP incluido |
| Qwen3.8-27B | MLX affine 4-bit + DFlash2 | Metal M5 Max, M3 Ultra | DFlash2 |
| Qwen3.8 Flash Next | MLX affine 6-bit (u otras recetas) | Metal M5 Ultra (y rutas CUDA documentadas en línea Python/recetas) | MTP |
| GLM-5.3-Flash | MLX affine 4-bit | Metal dos M5 Ultra; CUDA multi-rank en recetas | MTP / DFlash2 |
| Qwen3.5-2B | MLX affine 4-bit | Metal M5 Max | — |

Esta tabla es **OBSERVED** a partir de releases y README de TensorFold. No implica soporte en hardware no listado (p. ej. RTX 3050 4 GB) hasta MEASURED local.

### 3.4 API y operaciones

- OpenAI: `/v1/chat/completions`, `/v1/completions`, `/v1/responses`, `/v1/models`.
- Anthropic Messages.
- Health, metrics, opciones de dashboard según release.
- Comandos: `tensorfold serve`, `pull`, `models`, `info`, `capabilities`.

### 3.5 Instalación típica

```bash
# macOS (Homebrew)
brew install ashhart/tensorfold/tensorfold

# o install script
curl -fsSL https://tensorfold.dev/install.sh | sh

# servir (ejemplo conceptual)
tensorfold serve "$HOME/models/nemotron-lightning" \
  --name local-model --parallel 1 --context 8192 --temperature 0
```

Cliente: `http://127.0.0.1:8080/v1` (puerto por defecto del motor; en ODS irá detrás del proxy unificado).

---

## 4. Papel dentro de la arquitectura ODS

```text
USUARIO / CARGA
       ↓
PERFIL DEL MODELO (familia + checkpoint cualificado)
       ↓
PERFIL DE HARDWARE + ALMACENAMIENTO
       ↓
REGISTRO DE CAPACIDADES ODS (Runtime Registry)
       ↓
ESTRATEGIA DE EJECUCIÓN (ICD)
       ↓
SELECTOR DE RUNTIME
       ↓
 ┌──────────────────┬────────────────────┬─────────────────┬─────────┐
 │ llama-server     │ cafe-llama.cpp     │ TensorFold      │ Strata / │
 │ (baseline)       │ (avanzado MoE)     │ (family-specific│ otros    │
 │                  │                    │  + exact draft) │         │
 └──────────────────┴────────────────────┴─────────────────┴─────────┘
       ↓
API ODS UNIFICADA (OpenAI-compatible)
       ↓
validación / evidencia LEONES
```

TensorFold **no** es un drop-in genérico de llama-server. Solo debe activarse cuando el selector ICD encuentre coincidencia hardware + familia + checkpoint en el registro. En caso contrario, fallback a cafe-llama o llama-server con mensaje claro en Dashboard.

---

## 5. Diseño de integración propuesto en ODS

### 5.1 Servicio opcional

```text
extensions/services/tensorfold/
├── manifest.yaml
├── docker-compose.yml          # opcional (fallback)
├── Dockerfile                  # opcional
├── entrypoint.sh               # preferir ruta native
├── native-install.sh           # Homebrew / release assets / install.sh
└── README.md
```

### 5.2 Variables / parámetros a exponer en Dashboard y `.env`

Prioridad alta (formulario avanzado):

| Parámetro | Flag / interfaz TensorFold | Descripción |
|-----------|----------------------------|-------------|
| Model path / name | `serve PATH --name` | Checkpoint local o tras `tensorfold pull` |
| Context | `--context` | Ventana de contexto |
| Parallel | `--parallel` | Streams (limitado por familia en 1.0.x) |
| Temperature | `--temperature` | Sampling |
| Draft / drafter | draft on-off / `--drafter` | MTP o ruta DFlash2 según familia |
| Keep-warm | `--keep-warm` | Metal idle keepalive |
| No-thinking | `--no-thinking` | Cuando el modelo lo soporte |
| Device / ranks | según backend | CUDA ordinal / multi-rank en recetas |

Parámetros de bajo nivel de kernel no deben inundar el Dashboard; solo lo necesario para perfiles y diagnóstico.

### 5.3 Activación

```bash
ods enable tensorfold
# o
ODS_INFERENCE_RUNTIME=tensorfold
```

El instalador puede:

1. Instalar binario nativo (Homebrew en macOS; assets / install.sh en Linux cualificado) — **recomendado**.
2. Usar contenedor solo como fallback o para recetas CUDA que aún dependan de la línea Python.

### 5.4 Gestión de modelos

- Caché **separada** del catálogo GGUF de ODS.
- Envolver o invocar `tensorfold pull` para checkpoints cualificados.
- Respetar restricciones de hard-links / clones (Sliding Weights y snapshots HF): no reescribir pesos compartidos del cache.

### 5.5 Compatibilidad con el stack actual

- Misma API OpenAI-compatible detrás del proxy ODS → Portal, Open WebUI, agentes, n8n, LiteLLM sin cambios de cliente.
- Los modelos GGUF del catálogo ODS **no** se sirven por TensorFold; solo checkpoints de la matriz cualificada.
- Ambos (o más) runtimes pueden coexistir; el selector elige por perfil.

---

## 6. Matriz de evidencia y reglas LEONES

| Clase | Significado |
|-------|-------------|
| **REPORTED** | Cifras publicadas por TensorFold o terceros (X, blogs, DGX Spark). |
| **OBSERVED** | Capacidad verificada en README / releases / código (p. ej. matriz 1.0.4). |
| **ESTIMATED** | Inferencia de viabilidad antes de ejecutar. |
| **MEASURED** | Resultado producido por LEONES en hardware objetivo (única clase válida para afirmar tok/s, TTFT o memoria local). |

Ejemplo de registro de capacidad:

```yaml
runtime:
  tensorfold:
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
      tensor_streaming: true
    constraints:
      model_family_specific: true
      checkpoint_specific: true
      gguf: false
    evidence_class_default: OBSERVED
```

**Exactitud:** registrar siempre como *same engine + same weights + same config*. No equivaler salida TensorFold con salida de otros runtimes.

**Hardware LEONES de referencia histórica (RTX 3050 Laptop 4 GB):** no hay MEASURED de compatibilidad ni rendimiento con las recetas cualificadas actuales. No afirmar que “cabe” o “es rápido” en esa GPU hasta medición local autorizada.

---

## 7. Fases de implementación recomendadas

Alineadas con `PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md` y con el patrón cafe-llama.

### Fase 1 — Documentación y registro (este documento en LEONES)

- Propuesta de integración actualizada (este archivo).
- Entrada en Runtime Registry / ROADMAP.
- Matriz cualificada versionada (fuente: releases TensorFold).

### Fase 2 — Runtime opcional en ODS (PR a Osmantic/ODS o fork de trabajo)

- Servicio `tensorfold` opt-in (`extensions/services/tensorfold/`).
- Instalación native preferida + health + `ods status`.
- Parámetros prioritarios en Dashboard → Models (avanzado).
- Proxy OpenAI-compatible unificado.

### Fase 3 — Perfiles ICD

- Perfiles predefinidos solo para combinaciones cualificadas (ej. “Nemotron Lightning exact-MTP”, “Qwen3.8-27B DFlash2 Metal”).
- Candidate generation → benchmark local → best profile.
- Fallback explícito a cafe-llama / llama-server.

### Fase 4 — Evidencia MEASURED

- Workloads estandarizados (tok/s, TTFT, memoria peak, verificación drafted==serial).
- Comparativa lado a lado solo cuando el mismo workload sea ejecutable en otro runtime (sin forzar equivalencia de salida).
- Persistencia de Inference Profiles medidos.

---

## 8. Qué no hacer

- No sustituir el `llama-server` por defecto de ODS.
- No presentar TensorFold como backend genérico ni como “mejor en todo”.
- No servir GGUF arbitrarios del catálogo ODS a través de TensorFold.
- No copiar benchmarks de DGX Spark / Macs M5 como `MEASURED` en hardware distinto.
- No interpretar “exact same-engine” como equivalencia entre runtimes.
- No afirmar soporte AMD / Windows nativo / RTX de baja VRAM sin validación MEASURED.
- No mezclar caches de checkpoints TensorFold con el catálogo GGUF.
- No abrir PR de implementación a Osmantic/ODS sin revisión del diseño en LEONES.

---

## 9. Relación con cafe-llama, Strata y AirLLM

| Runtime | Fortaleza principal | Tipo de integración |
|---------|---------------------|---------------------|
| llama-server | Baseline amplia, estable | Core |
| cafe-llama.cpp | Offload MoE + Turbo KV + MTP genérico | Runtime avanzado **compatible** (GGUF) |
| **TensorFold** | Kernels por familia + exact speculative | Runtime **especializado** family-specific |
| Strata | Flash Next en 12–24 GB (placement multi-tier) | Runtime de memoria/placement |
| AirLLM | Layer streaming; VRAM mínima | Experimental; no producción |

Cafe y TensorFold son **complementarios**: Cafe amplía configuraciones de llama.cpp; TensorFold ofrece motores cerrados con contrato de exactitud y velocidad en familias cualificadas. Strata cubre el extremo “Flash Next en gaming PC”. AirLLM solo investigación.

Ver también:

- `docs/integrations/PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md`
- `docs/integrations/cafe-llama.cpp/README.md`
- `docs/integrations/cafe-llamacpp-vs-strata-vs-tensorfold-2026-10-06.html`

---

## 10. Conclusión y siguiente paso

TensorFold es el candidato natural de **runtime especializado de alto rendimiento y exactitud reproducible** en ODS, siempre detrás de admisión estricta por familia/checkpoint/hardware.

- Mantiene la API OpenAI-compatible unificada.
- No compite con el camino GGUF genérico (llama-server / cafe-llama).
- Encaja en ICD y en las reglas de evidencia LEONES.
- Prioridad de implementación: tras (o en paralelo controlado con) el scaffold de cafe-llama, siguiendo el plan maestro de motores.

**Acción inmediata:** este README actualizado como espejo de la propuesta cafe-llama y del plan de motores.  
**Acción siguiente:** scaffold `extensions/services/tensorfold/` en el fork de trabajo de ODS (opt-in, native-first, sin activar por defecto) y primera pasada de registry ICD.

---

## Referencias

- https://tensorfold.dev
- https://github.com/ashhart/TensorFold
- https://github.com/ashhart/TensorFold/releases
- https://github.com/ashhart/TensorFold/blob/main/RUNBOOK.md
- Documentos relacionados en este repo:
  - `docs/integrations/PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md`
  - `docs/integrations/cafe-llama.cpp/README.md`
  - `docs/integrations/ODS/INFERENCE-CONFIGURATION-DISCOVERY-2026-10-06.md` (si existe)
  - `docs/integrations/Bonsai2-Small-GPU-EXTERNAL-EVIDENCE.md`
  - `docs/integrations/cafe-llamacpp-vs-strata-vs-tensorfold-2026-10-06.html`
  - `docs/integrations/tensorfold/README-eng.mkd` (resumen EN; actualizar en seguimiento si hace falta)
