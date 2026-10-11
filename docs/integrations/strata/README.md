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

**Strata** es un motor de inferencia MIT orientado a **un modelo y una clase de hardware**: ejecutar **Qwen3.8-Flash-Next** (MoE ~125B parámetros totales; ~6B activos por token; 24576 expertos, ~10 por token) en un PC de consumo con **GPU NVIDIA o AMD >= 12 GB VRAM** y **32-64 GB de RAM**, mediante placement multi-tier (VRAM / RAM / SSD), speculative decoding documentado y API **OpenAI- y Anthropic-compatibles** en localhost (chat, messages, responses; imagen opcional).

No es un runtime genérico. Ocupa el nicho "Flash Next en hardware modesto" junto a cafe-llama (offload MoE genérico) y TensorFold (familia Flash Next cualificada), con un contrato distinto: **producto one-model**, instalador one-click (`START-HERE.bat` / `setup.sh` / Docker) y stack C++/CUDA/HIP + servidor Python.

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

**Claves i18n propuestas:**

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

### 3.1 Cómo funciona

- **24576 expertos**; cada token usa ~10.
- **GPU:** expertos más usados.
- **RAM:** conjunto de expertos (shard 1); primer arranque puede "congelar" el PC 1–3 min (documentado).
- **SSD:** tabla de lookup (shard 2, ~29 GB) vía mmap.
- **Guess-and-check:** draft + verify (~1.6–1.8× — REPORTED).
- Prefill en bloques grandes (hasta 8192 tokens).

### 3.2 Envelope de hardware

| Recurso | Requisito documentado |
|---------|------------------------|
| GPU | NVIDIA RTX 20/30/40/50 o AMD listada; **>= 12 GB VRAM** |
| RAM | **>= 32 GB**; **64 GB** para todos los sizes principales |
| Disco | **~80 GB libres**; SSD/NVMe recomendado |
| OS | Windows 10/11 o Linux |
| Multi-GPU | 2–3 tarjetas (`docs/MULTI_GPU.md`) |
| AMD HIP | Lista de GPUs; vision AMD Linux vía CPU |
| Experimental | GPUs antiguas, Intel Arc, Strix Halo — no default ODS |

### 3.3 Sizes y versiones

| Size | RAM+VRAM approx. | Velocidad | Calidad |
|------|------------------:|-----------|---------|
| **Q2_0** | 37.6 GB | Más rápida | Buena |
| **IQ2_XS** | 39.2 GB | Rápida | Mejor (**recomendada**) |
| **IQ3_XXS** | 47.0 GB | Más lenta | Muy buena |
| **IQ3_S** | 54.8 GB | Más lenta | Mejor |

Descarga 66–76 GB (+ MTP ~6 GB; +1 GB vision).

| RAM del PC | Recomendación |
|------------|---------------|
| 32 GB | **Coder**; con GPU 24 GB también Q2_0/IQ2_XS (low-RAM) |
| 48 GB | **IQ2_XS** o **Q2_0** |
| 64 GB | **IQ2_XS** (default); IQ3_* posibles |
| >= 96 GB | **IQ3_S** o Unsloth UD-IQ4_XS |

| Familia | Notas |
|---------|--------|
| Flash Next | Default; vision; speed projection experimental |
| Coder | 256/512 expertos; cabe ~32 GB RAM; fuerte código; débil fuera/CJK |
| Swift 1.5 | Fine-tune; menos thinking |
| Unsloth UD-IQ4_XS | ~94 GB download; >= 48 GB RAM |
| Unsloth UD-Q4_K_XL | Experimental; lento si sale del SSD |
| OrcaRouter Uncensored | Manual |

### 3.4 Rendimiento publicado (solo REPORTED)

RTX 5070 12 GB + 64 GB RAM (upstream): Q2_0 ~94 tok/s generate / ~2650 prefill; IQ2_XS ~79 / ~2090; etc. AMD RX 9070 XT cifras menores. **No transferir como MEASURED.**

### 3.5 API

| Superficie | URL |
|------------|-----|
| App web | `http://127.0.0.1:8080` |
| OpenAI | `http://127.0.0.1:8080/v1` |
| Anthropic | `.../v1/messages` |
| Responses | `.../v1/responses` |

Default: una petición a la vez; parallel opcional (más lento en 12 GB). LAN: host 0.0.0.0 **solo con API key**.

### 3.6 Low-RAM mode

Si la RAM no sostiene todos los expertos, Strata mapea desde disco (mucho más lento). Setup puede activarlo. ODS debe advertir (i18n `runtime.strata.lowRam`).

---

## 4. Papel en la arquitectura ODS

```text
USUARIO / CARGA
       ↓
PERFIL DEL MODELO (¿Flash Next?)
       ↓
PERFIL DE HARDWARE (VRAM / RAM / disco)
       ↓
REGISTRO DE CAPACIDADES
       ↓
ICD → Inference Profile
       ↓
SELECTOR DE RUNTIME
       ↓
 llama-server | cafe-llama | TensorFold | Strata
       ↓
API ODS UNIFICADA
       ↓
evidencia LEONES
```

**Reglas de selección:**

1. Modelo no Flash Next (ni variante) → Strata fuera.
2. Envelope incumplido → `notQualified` + fallback cafe/llama/TensorFold.
3. Flash Next + envelope OK → Strata candidato prioritario para "máximo modelo en consumer GPU".

---

## 5. Diseño de integración en ODS

### 5.1 Servicio

```text
extensions/services/strata/
├── manifest.yaml          # versión pineada, puertos, health
├── docker-compose.yml     # NVIDIA preferido en Linux ODS
├── Dockerfile             # adaptar upstream
├── entrypoint.sh
├── native-install.sh      # setup no interactivo cuando exista
└── README.md
```

- **Linux + NVIDIA:** Docker alineado con ODS, o native.
- **Windows:** según política ODS (native / WSL2).
- **AMD HIP:** experimental; default off.

### 5.2 Parámetros Dashboard

| UI (i18n) | Env / flag típica | Descripción |
|-----------|-------------------|-------------|
| modelSize | MODEL | Q2_0, IQ2_XS, IQ3_XXS, IQ3_S, … |
| family | FAMILY | flash-next, coder, swift, unsloth |
| context | CONTEXT | Ventana de contexto |
| vision | VISION | no / yes / cpu |
| kvCache | KV | int8, q4_0, k8v4, … |
| gpu | GPU / GPUS | Dispositivo(s) |
| lowRam | low-ram on/off | Modo low-RAM |
| apiKey | si bind no loopback | Seguridad |

### 5.3 Activación

```bash
ods enable strata
# o
ODS_INFERENCE_RUNTIME=strata
```

Precondiciones: comprobar VRAM/RAM/disco; consentimiento descarga (~70–80 GB); pull/setup; health antes de Ready; aviso first-start (1–3 min posible lentitud del host).

### 5.4 Modelos y datos

- Catálogo **aparte** del GGUF ODS: `data/strata/` o volumen dedicado.
- No mezclar selector GGUF con sizes Strata.
- Pin de versión de motor en `manifest.yaml`.

### 5.5 Proxy API

- Strata en puerto interno; ODS unifica el endpoint que ya usan Portal / Open WebUI / agentes.
- Alias de modelo estable en `/v1/models`.

### 5.6 Registro YAML

```yaml
runtime:
  strata:
    supported: conditional
    upstream: https://github.com/Niko1221/Strata
    license: MIT
    api:
      openai_compatible: true
      anthropic_messages: true
      responses_api: true
    backends:
      - cuda
      - hip   # experimental
    capabilities:
      flash_next_only: true
      multi_tier_placement: true
      optional_vision: true
      speculative_decoding: true
      one_click_install: true
      low_ram_mode: true
    constraints:
      model_family_specific: true
      family: Qwen3.8-Flash-Next
      min_vram_gb: 12
      min_ram_gb: 32
      recommended_ram_gb: 64
      disk_gb_approx: 80
      gguf_generic: false
    evidence_class_default: OBSERVED
```

### 5.7 Perfiles ICD de ejemplo

| Profile id | Condiciones | Size sugerido |
|------------|-------------|---------------|
| `strata-flash-next-32gb-coder` | RAM ~32 GB, VRAM >= 12 | Coder |
| `strata-flash-next-48gb-iq2` | RAM ~48 GB | IQ2_XS o Q2_0 |
| `strata-flash-next-64gb-iq2` | RAM >= 64 GB | IQ2_XS (default) |
| `strata-flash-next-64gb-iq3s` | RAM >= 64 GB, calidad | IQ3_S |
| `strata-flash-next-vision` | vision=yes + envelope | según RAM |

Fallback: Strata → cafe-llama (si GGUF Flash Next) → llama-server → TensorFold (si cualificado).

---

## 6. Flujos operativos ODS

### 6.1 Enable feliz

1. Usuario/ICD elige Strata + size.
2. Dashboard muestra requisitos (i18n) y pide consentimiento de descarga.
3. `ods enable strata` → install/pull → start → health.
4. Proxy apunta a Strata; `/v1/models` refleja alias.
5. Clientes existentes siguen igual.

### 6.2 No cualificado

Envelope fallido → mensaje `notQualified` + hint + fallback (cafe/llama). No iniciar descarga.

### 6.3 Fallos frecuentes

| Síntoma upstream | Acción ODS |
|------------------|------------|
| PC "congelado" 1–3 min al primer start | Aviso `firstStart.warn`; no matar el proceso |
| Disco/RAM insuficiente | failed; sugerir size menor o low-RAM |
| Puerto en uso | `portInUse`; reasignar en compose ODS |
| Descarga interrumpida | Reanudar (upstream lo soporta) |
| HIP/AMD no validado | No ofrecer como default |

### 6.4 Seguridad

Default bind loopback. Si LAN: API key obligatoria. No exponer sin revisión de red ODS.

---

## 7. Relación con otros runtimes

| Runtime | Cuándo para Flash Next |
|---------|------------------------|
| **Strata** | Consumer GPU 12–24 GB + RAM generosa; one-click; vision |
| **cafe-llama** | GGUF + flags MoE/Turbo/MTP genéricos |
| **TensorFold** | Matriz cualificada TF + exact same-engine |
| **llama-server** | Fallback amplio |
| **AirLLM** | Solo experimental |

---

## 8. Evidencia LEONES

| Clase | Uso |
|-------|-----|
| REPORTED | tok/s y tablas del README Strata |
| OBSERVED | API, installer, Docker, sizes, requisitos en docs |
| ESTIMATED | Cabe en esta máquina (antes de instalar) |
| MEASURED | Solo tras enable + workload en hardware objetivo |

---

## 9. Fases de implementación

### Fase 0 — Prerrequisitos

| Ítem | Estado |
|------|--------|
| Scaffold cafe-llama | En curso |
| i18n Dashboard | Pendiente merge |
| Plan motores | Existe |
| Este README | LEONES ods-evolution |

### Fase 1 — Docs y registry (LEONES)

- [x] README detallado
- [ ] ROADMAP / registry experimental
- [ ] Claves i18n cerradas en/es/zh-CN

### Fase 2 — Servicio MVP (ODS)

- [ ] `extensions/services/strata/`
- [ ] Docker NVIDIA mínimo
- [ ] enable / disable / status / health
- [ ] Proxy unificado
- [ ] Envelope checks + consentimiento disco
- [ ] Humo: health → models → chat corto

### Fase 3 — Dashboard + i18n

- [ ] Formulario avanzado (size, family, context, vision, KV, GPU, lowRam)
- [ ] Estados ready/downloading/failed/notQualified
- [ ] Diccionarios en/es/zh-CN

### Fase 4 — ICD

- [ ] Candidatos solo Flash Next + envelope
- [ ] Perfiles de ejemplo (§5.7)
- [ ] Fallback ordenado
- [ ] Persistencia MEASURED

### Fase 5 — MEASURED

- [ ] Workload estándar LEONES
- [ ] Matriz size × GPU de lab (sin extrapolar)
- [ ] Registrar fallos de admisión

### Fase 6 — Hardening

- [ ] API key si no loopback
- [ ] Multi-GPU documentado, no default
- [ ] HIP experimental flag
- [ ] Pin de versión en manifest

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| ~80 GB disco | Consentimiento + check espacio |
| Solo Flash Next | Admisión estricta + UI clara |
| Duplicar abstracciones | Reutilizar café; un solo plugin path |
| i18n no mergeado | Esperar o incluir diccionarios en el PR |
| Primer start "congela" host | Aviso i18n; timeouts de health generosos |
| AMD HIP | Default off |
| Benchmarks mal usados | Clases de evidencia obligatorias |

---

## 11. Qué no hacer

- No sustituir llama-server ni cafe-llama.
- No presentar Strata como multi-modelo genérico.
- No activar por defecto.
- No mezclar catálogo GGUF con pesos Strata.
- No hardcodear strings de UI.
- No traducir nombres de size/modelo/flags.
- No copiar tok/s de RTX 5070 como MEASURED ajeno.
- No abrir PR upstream sin revisión en LEONES.

---

## 12. Conclusión y siguientes pasos

Strata es el especialista **Qwen3.8-Flash-Next en GPU de consumo** dentro de los motores opcionales de ODS. Integración **delgada**: mismo armazón que cafe-llama + misma capa i18n.

**Inmediato (LEONES):** revisión de este README; registry/ROADMAP; cerrar textos i18n.  
**Siguiente (ODS):** tras café + i18n → scaffold servicio → envelope + proxy → Dashboard → ICD → primer MEASURED.

---

## Referencias

- https://github.com/Niko1221/Strata
- https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md
- https://github.com/Niko1221/Strata/blob/main/docs/INSTALL.md
- `docs/integrations/cafe-llama.cpp/README.md`
- `docs/integrations/tensorfold/README.md`
- `docs/integrations/PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md`
- `docs/ODS-DASHBOARD-I18N-PR.md`
- `docs/integrations/cafe-llamacpp-vs-strata-vs-tensorfold-2026-10-06.html`
