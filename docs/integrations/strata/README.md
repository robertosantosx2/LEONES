# Propuesta de integración de Strata en ODS

**Línea experimental:** `ods-evolution`  
**Proyecto:** LEONES  
**Fecha:** 2026-10-11  
**Estado:** Esquema de arquitectura e integración — depende de la infraestructura que aporta cafe-llama.cpp y del i18n del Dashboard (pendiente de merge)  
**Upstream:** https://github.com/Niko1221/Strata  
**Licencia:** MIT  
**Plan maestro:** `docs/integrations/PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md`  
**Patrón de referencia:** `docs/integrations/cafe-llama.cpp/README.md`  
**i18n Dashboard:** `docs/ODS-DASHBOARD-I18N-PR.md` (en / es / zh-CN; pendiente de merge upstream)

---

## 1. Resumen ejecutivo

**Strata** es un motor de inferencia de código abierto orientado a **un modelo y una clase de hardware**: ejecutar **Qwen3.8-Flash-Next** (MoE ~125B parámetros totales, ~6B activos por token) en un PC de consumo con **una GPU NVIDIA o AMD ≥ 12 GB VRAM** y **32–64 GB de RAM de sistema**, vía placement multi-tier (VRAM / RAM / SSD) y API OpenAI- y Anthropic-compatibles en localhost.

No es un runtime genérico. Compite en el mismo espacio de “Flash Next en hardware modesto” que partes de cafe-llama (offload MoE) y TensorFold (familia Flash Next cualificada), pero con un contrato distinto: **un modelo, un instalador one-click, un stack C++/CUDA/HIP + servidor Python**.

El papel adecuado en ODS es:

> **runtime opcional y altamente especializado**, seleccionado solo cuando el usuario (o el ICD) elige Qwen3.8-Flash-Next (o variantes Coder / cuantizaciones documentadas) y el hardware cumple el envelope mínimo documentado por Strata.

Debe **complementar, no sustituir**, a `llama-server`. Debe **reutilizar toda la infraestructura** que introduce la integración de cafe-llama.cpp (servicio opt-in, Runtime Registry, ICD, Dashboard avanzado, evidencia LEONES) y la **capa i18n del Dashboard** para cualquier superficie de UI nueva.

---

## 2. Qué aporta cafe-llama.cpp (infraestructura a reutilizar)

La integración de cafe-llama define el **camino estándar** de un runtime opcional en ODS. Strata no debe inventar otro.

| Pieza | Qué aporta cafe-llama | Cómo la usa Strata |
|-------|----------------------|--------------------|
| Servicio opt-in | `extensions/services/<runtime>/` (manifest, entrypoint, compose/native) | Mismo layout: `extensions/services/strata/` |
| Activación | `ods enable <runtime>` / `ODS_INFERENCE_RUNTIME` | `ods enable strata` |
| Runtime Registry | YAML de capacidades + constraints + evidence_class | Entrada `strata` con `model_family_specific: true` (Flash Next only) |
| ICD / Inference Profiles | hardware + modelo + offload → perfil medido | Candidatos solo si familia = Flash Next + envelope RAM/VRAM/SSD |
| Dashboard avanzado | Parámetros prioritarios en Models | Selector de size (Q2_0, IQ2_XS, …), context, vision, KV, GPU ids |
| API unificada | Proxy OpenAI-compatible | Clientes ODS no saben que hay Strata detrás |
| Evidencia LEONES | REPORTED / OBSERVED / ESTIMATED / MEASURED | Misma disciplina; benchmarks públicos de Strata = REPORTED |
| Coexistencia | No sustituye llama-server | Strata y cafe/llama-server pueden instalarse; el selector elige |

**Dependencia de secuencia recomendada:** estabilizar el scaffold de cafe-llama (servicio + registry + Dashboard hooks) **antes** o en paralelo muy controlado con Strata, para no duplicar abstracciones.

---

## 3. Qué aporta el i18n del Dashboard (pendiente de merge)

Documento de referencia: `docs/ODS-DASHBOARD-I18N-PR.md`.

### 3.1 Capacidades disponibles

- Capa nativa sin dependencia extra: `ods/extensions/services/dashboard/src/i18n/`.
- Locales: `en` (default + fallback), `es`, `zh-CN`.
- Persistencia: `ods.language.v1`.
- Superficies ya cableadas: FirstBoot + Settings → Profile.
- Claves planas (`firstBoot.welcome.title`, `profile.save`, …).
- Resolución: locale seleccionado → inglés → clave literal.

### 3.2 Implicaciones para Strata

Cualquier **UI nueva** relacionada con Strata en el Dashboard debe:

1. Añadir claves a `en.js`, `es.js` y `zh-CN.js` (nunca hardcodear strings en JSX).
2. Usar el helper de traducción existente (mismo patrón que FirstBoot/Profile).
3. Mantener identificadores técnicos sin traducir: `Strata`, `Qwen3.8-Flash-Next`, `Q2_0`, `IQ2_XS`, nombres de flags, rutas, variables de entorno.
4. No traducir payloads de API, nombres de modelos en `/v1/models`, ni mensajes generados por el binario de Strata (fuera de alcance del i18n del Dashboard, igual que el resto de servicios).

**Claves sugeridas (ejemplos):**

```text
runtime.strata.title
runtime.strata.description
runtime.strata.enable
runtime.strata.disable
runtime.strata.modelSize
runtime.strata.context
runtime.strata.vision
runtime.strata.kvCache
runtime.strata.requirements.vram
runtime.strata.requirements.ram
runtime.strata.requirements.disk
runtime.strata.notQualified
runtime.strata.fallbackCafe
runtime.strata.healthOk
runtime.strata.healthFail
```

Hasta que el PR de i18n esté mergeado en ODS, el scaffold de Strata puede dejar las claves en inglés en el código y añadir los tres diccionarios en el mismo PR de servicio, o depender del merge previo del i18n (preferible).

---

## 4. Capacidades clave de Strata (OBSERVED desde upstream)

### 4.1 Alcance del modelo

- **Familia principal:** Qwen3.8-Flash-Next (MoE, PLE/n-gram, contexto largo documentado hasta 128K–262K según size/RAM).
- **Variantes:** tamaños de cuantización (Q2_0, IQ2_XS, IQ3_XXS, IQ3_S, …), versión Coder, builds comunitarios (p. ej. Unsloth / OrcaRouter) cuando el loader los admite.
- **No es genérico:** no sustituye el catálogo GGUF amplio de ODS.

### 4.2 Hardware envelope (documentación upstream — REPORTED/OBSERVED)

| Recurso | Mínimo típico documentado | Recomendado |
|---------|---------------------------|-------------|
| GPU | NVIDIA o AMD ≥ 12 GB VRAM | 12–24 GB+ |
| RAM sistema | ~32 GB (algunos sizes/low-RAM) | 64 GB |
| Disco | ~70–80 GB libres (pesos) | SSD NVMe |
| OS | Windows 10/11, Linux | — |
| AMD | HIP experimental (device IDs limitados) | Validar por dispositivo |

Multi-GPU documentado en upstream (`docs/MULTI_GPU.md`). Docker disponible para NVIDIA.

### 4.3 Mecanismo

- Placement multi-tier: expertos frecuentes en VRAM; resto en RAM; tablas/lookups en SSD (mmap).
- Speculative decoding / draft documentado (p. ej. 1.6–1.8× en materiales del proyecto — **REPORTED**).
- API: OpenAI + Anthropic en localhost; entrada de imagen opcional.
- Instalador one-click: `START-HERE.bat` / `setup.sh` / Docker.

### 4.4 Rendimiento publicado (REPORTED, no MEASURED LEONES)

Ejemplos públicos (RTX 5070 12 GB + 64 GB RAM, sizes varios): decenas de tok/s en generate y miles de tok/s en prefill según size. **No transferir a otra GPU/RAM como MEASURED.**

---

## 5. Papel en la arquitectura ODS (con Runtime Registry)

```text
USUARIO / CARGA
       ↓
PERFIL DEL MODELO (¿Flash Next u otra familia?)
       ↓
PERFIL DE HARDWARE (VRAM ≥ 12 GB? RAM ≥ 32–64 GB? disco?)
       ↓
REGISTRO DE CAPACIDADES ODS
       ↓
ICD → Inference Profile
       ↓
SELECTOR DE RUNTIME
       ↓
 ┌────────────────┬─────────────────┬──────────────┬─────────┐
 │ llama-server   │ cafe-llama.cpp  │ TensorFold   │ Strata  │
 │ (baseline)     │ (MoE genérico)  │ (family+)    │ (Flash  │
 │                │                 │              │  Next)  │
 └────────────────┴─────────────────┴──────────────┴─────────┘
       ↓
API ODS UNIFICADA
       ↓
evidencia LEONES
```

**Regla de selección orientativa:**

1. Si el modelo **no** es Flash Next (ni variante admitida) → Strata no es candidato.
2. Si hardware **no** cumple envelope → Strata no es candidato; mensaje i18n `runtime.strata.notQualified`; ofrecer cafe-llama / llama-server / TensorFold si aplica.
3. Si Flash Next + envelope OK → Strata puede ser preferido para “máximo modelo en consumer GPU”; cafe-llama o TensorFold siguen siendo alternativas según perfil (exactitud TensorFold, flags genéricos cafe).

---

## 6. Diseño de integración en ODS

### 6.1 Servicio opcional

```text
extensions/services/strata/
├── manifest.yaml
├── docker-compose.yml          # ruta NVIDIA documentada por upstream
├── Dockerfile                  # opcional; reutilizar/adaptar el de Niko1221/Strata
├── entrypoint.sh
├── native-install.sh           # setup.sh / START-HERE no interactivo cuando sea posible
└── README.md
```

**Preferencia de despliegue en ODS:**

- Linux + NVIDIA: Docker (compose) alineado con el resto del stack ODS, **o** native si el operario lo prefiere y el installer lo permite de forma no interactiva.
- Windows: native / WSL2 según política ODS existente; documentar límites.
- AMD HIP: marcar experimental; no activar por defecto hasta MEASURED en hardware de referencia.

### 6.2 Parámetros prioritarios (Dashboard avanzado)

| Parámetro UI (i18n key) | Variable / flag Strata típica | Descripción |
|-------------------------|-------------------------------|-------------|
| modelSize | `MODEL` / size (Q2_0, IQ2_XS, …) | Cuantización / footprint |
| context | `CONTEXT` | Ventana de contexto |
| vision | `VISION` (no / yes / cpu) | Entrada de imagen |
| kvCache | `KV` (int8, q4_0, k8v4, …) | Tipo de KV |
| gpu | `GPU` / `GPUS` | Dispositivo(s) |
| apiKey | si se expone fuera de loopback | Seguridad |
| family/version | FAMILY / variante Coder | Variante de pesos |

Estos parámetros se registran en el mismo patrón que `LLAMA_ARG_*` / formulario avanzado de cafe-llama, sin mezclar flags de Strata con los de llama-server.

### 6.3 Activación

```bash
ods enable strata
# o
ODS_INFERENCE_RUNTIME=strata
```

Requisitos previos del enable:

- Comprobación de VRAM/RAM/disco (o degradación a ESTIMATED + aviso).
- Descarga de pesos solo tras consentimiento explícito (tamaño ~70 GB).
- Health check antes de marcar el servicio Ready.

### 6.4 Gestión de modelos

- Catálogo **aparte** del GGUF genérico de ODS.
- Paths bajo `data/strata/` o volumen dedicado.
- No reutilizar el selector de GGUF para Strata; el Dashboard muestra “Strata model sizes” solo cuando el runtime está habilitado o el perfil lo pide.

### 6.5 API y proxy

- Strata escucha OpenAI/Anthropic en su puerto; ODS termina el proxy unificado (mismo patrón que llama-server / cafe-llama).
- Identidad de modelo en `/v1/models` debe ser estable y documentada (alias ODS vs id interno Strata).

### 6.6 Registro de capacidades (YAML orientativo)

```yaml
runtime:
  strata:
    supported: conditional
    upstream: https://github.com/Niko1221/Strata
    license: MIT
    api:
      openai_compatible: true
      anthropic_messages: true
    backends:
      - cuda
      - hip   # experimental
    capabilities:
      flash_next_only: true
      multi_tier_placement: true
      optional_vision: true
      speculative_decoding: true   # según release; clase OBSERVED/REPORTED
      one_click_install: true
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

---

## 7. Relación con cafe-llama, TensorFold y AirLLM

| Runtime | Cuándo preferirlo para Flash Next |
|---------|-----------------------------------|
| **Strata** | Objetivo = Flash Next en 12–24 GB VRAM + RAM generosa; instalador dedicado; vision opcional |
| **cafe-llama.cpp** | Mismo o similar modelo en GGUF con flags MoE/Turbo/MTP genéricos; menos “one-model product” |
| **TensorFold** | Familia Flash Next en matriz cualificada TensorFold (p. ej. Metal M5 Ultra / CUDA recetas); contrato exact same-engine |
| **llama-server** | Fallback amplio; posible offload limitado |
| **AirLLM** | Solo experimental; no producción |

Cafe-llama y Strata pueden coexistir: cafe cubre muchos MoE/GGUF; Strata maximiza el caso Flash Next consumer. El ICD debe poder explicar la elección en UI (claves i18n).

---

## 8. Matriz de evidencia LEONES

| Clase | Uso con Strata |
|-------|----------------|
| REPORTED | tok/s y envelopes de README/blog/X de Niko1221/Strata |
| OBSERVED | Existencia de API OpenAI/Anthropic, installer, Docker, sizes de modelo, requisitos en docs upstream |
| ESTIMATED | “Cabe en esta máquina” antes de instalar (~80 GB disco, RAM, VRAM) |
| MEASURED | Solo tras enable + serve + workload LEONES en hardware objetivo |

**Prohibido:** copiar 94 tok/s (RTX 5070) como rendimiento de otra GPU.

---

## 9. Fases de implementación (detalladas)

### Fase 0 — Prerrequisitos (bloqueantes / paralelos)

| Ítem | Estado |
|------|--------|
| Scaffold cafe-llama (servicio + registry hooks) | En curso / PR de trabajo |
| i18n Dashboard (en/es/zh-CN) | Aportado; **pendiente de merge** |
| Plan motores | `PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md` |
| Este documento | LEONES `ods-evolution` |

**No abrir PR de implementación Strata a Osmantic/ODS hasta:** diseño revisado en LEONES + (idealmente) i18n mergeado o incluido en el mismo tren de PRs + patrón de servicio cafe estable.

### Fase 1 — Documentación y registry (LEONES)

- [x] Este README de integración.
- [ ] Entrada en Runtime Registry / ROADMAP de integraciones.
- [ ] Actualizar comparación cafe vs strata vs tensorfold si hace falta.
- [ ] Lista de claves i18n Strata acordada (en/es/zh-CN).

### Fase 2 — Servicio opt-in MVP en ODS

- [ ] `extensions/services/strata/` (manifest, entrypoint, health).
- [ ] Ruta Docker NVIDIA mínima reproducible.
- [ ] `ods enable strata` / disable / status.
- [ ] Proxy OpenAI-compatible unificado.
- [ ] Comprobación de envelope hardware (VRAM/RAM/disco) con mensajes i18n.
- [ ] Consentimiento de descarga de pesos (~70 GB).
- [ ] Tests de humo: health → `/v1/models` → chat completion corto.

### Fase 3 — Dashboard + i18n

- [ ] Sección avanzada Models cuando runtime = strata (sizes, context, vision, KV, GPU).
- [ ] Todas las cadenas nuevas en `en` / `es` / `zh-CN`.
- [ ] Estados: not qualified, downloading, ready, failed (claves dedicadas).
- [ ] No modificar SettingsModal si el i18n PR lo evita; reutilizar Profile/FirstBoot patterns.

### Fase 4 — ICD y perfiles

- [ ] Candidato Strata solo si familia Flash Next + envelope.
- [ ] Perfiles: p. ej. `flash-next-consumer-12gb-q2`, `flash-next-64gb-iq2xs`, `flash-next-coder`.
- [ ] Fallback ordenado: Strata → cafe-llama (si GGUF Flash Next disponible) → llama-server → (TensorFold si cualificado).
- [ ] Persistencia de Inference Profiles MEASURED.

### Fase 5 — Evidencia MEASURED

- [ ] Workload estándar LEONES (tok/s, TTFT, peak VRAM/RAM, contexto fijo).
- [ ] Matriz size × GPU de referencia del lab (no extrapolar).
- [ ] Documentar fallos de admisión (disco, RAM) como evidencia útil.

### Fase 6 — Hardening

- [ ] API key si bind ≠ loopback.
- [ ] Multi-GPU opcional documentado, no default.
- [ ] AMD HIP: experimental flag + sin promesa hasta MEASURED.
- [ ] Actualización de versión Strata pineada en manifest.

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Disco ~80 GB | Consentimiento explícito; comprobar espacio antes de pull |
| Solo Flash Next | Admisión estricta en registry; UI clara |
| Duplicar abstracciones sin cafe | Reutilizar servicio/registry de cafe; no segundo “plugin system” |
| i18n aún no mergeado | Incluir diccionarios en el PR Strata o esperar merge i18n |
| AMD HIP inmaduro | Default off; OBSERVED only |
| Confusión con TensorFold/cafe | Tabla de decisión en Dashboard (i18n) + docs |
| Benchmarks públicos mal usados | Clases de evidencia LEONES obligatorias |
| Windows vs Docker ODS | Seguir matriz de soporte ODS; documentar path soportado |

---

## 11. Qué no hacer

- No sustituir llama-server ni cafe-llama.
- No presentar Strata como runtime genérico multi-modelo.
- No activar por defecto en instalaciones nuevas.
- No mezclar catálogo GGUF ODS con pesos Strata.
- No hardcodear strings de UI (usar i18n en/es/zh-CN).
- No traducir nombres de modelo, sizes ni flags técnicos.
- No copiar tok/s de RTX 5070 como MEASURED en otro hardware.
- No abrir PR upstream sin revisión del diseño en LEONES.

---

## 12. Conclusión y siguientes pasos

Strata es el runtime **especialista en Qwen3.8-Flash-Next sobre GPU de consumo** dentro del ecosistema de motores opcionales de ODS. Su integración debe ser **delgada**: mismo armazón que cafe-llama (servicio, registry, ICD, proxy, evidencia) y **misma capa i18n** del Dashboard para toda UI nueva.

**Inmediato (LEONES):**

1. Revisar este esquema.
2. Registrar Strata en el ROADMAP / Runtime Registry experimental.
3. Fijar lista de claves i18n.

**Siguiente (ODS, tras cafe + i18n):**

4. Scaffold `extensions/services/strata/` opt-in.
5. Envelope checks + proxy + humo.
6. Dashboard avanzado + diccionarios en/es/zh-CN.
7. Primera pasada ICD + un MEASURED en hardware de lab.

---

## Referencias

- Strata: https://github.com/Niko1221/Strata  
- Strata models: https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md  
- cafe-llama propuesta: `docs/integrations/cafe-llama.cpp/README.md`  
- TensorFold propuesta: `docs/integrations/tensorfold/README.md`  
- Plan motores: `docs/integrations/PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md`  
- i18n Dashboard: `docs/ODS-DASHBOARD-I18N-PR.md`  
- Comparativa: `docs/integrations/cafe-llamacpp-vs-strata-vs-tensorfold-2026-10-06.html`  
