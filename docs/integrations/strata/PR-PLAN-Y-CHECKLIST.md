# Plan y checklist de PR — Integración Strata en ODS

**Línea:** `ods-evolution` (LEONES) → PR de implementación en Osmantic/ODS (o fork de trabajo)  
**Fecha:** 2026-10-11  
**Referencias:**

- Propuesta: `docs/integrations/strata/README.md`
- Plan motores: `docs/integrations/PLAN-INTEGRACION-MOTORES-INFERENCIA-ODS.md`
- Patrón: `docs/integrations/cafe-llama.cpp/README.md`
- i18n Dashboard: `docs/ODS-DASHBOARD-I18N-PR.md`
- Upstream: https://github.com/Niko1221/Strata

---

## 1. Objetivo de los PRs

Integrar **Strata** como runtime **opcional y especializado** (solo Qwen3.8-Flash-Next y variantes admitidas) reutilizando el armazón de cafe-llama (servicio opt-in, Runtime Registry, ICD, proxy OpenAI-compatible, evidencia LEONES) y la capa i18n del Dashboard (`en` / `es` / `zh-CN`).

**No** sustituye `llama-server` ni cafe-llama. **No** se activa por defecto.

---

## 2. Estrategia de PRs (recomendado)

Evitar un único PR monolítico. Tren de PRs pequeños y revisables:

| PR | Ámbito | Repo | Bloquea |
|----|--------|------|---------|
| **A** | Docs + registry experimental Strata | LEONES | — |
| **B** | i18n Dashboard (si aún no mergeado) | ODS | — |
| **C** | Scaffold servicio `strata` (manifest, compose, health, enable/disable) | ODS | Idealmente A + café estable |
| **D** | Proxy unificado + humo API | ODS | C |
| **E** | Dashboard avanzado + claves i18n Strata | ODS | B (o incluye diccionarios), C |
| **F** | ICD: admisión, perfiles, fallback | ODS | C–E |
| **G** | Hardening (API key, timeouts, pin versión, HIP off) | ODS | F |

**Nota:** Si el scaffold de cafe-llama aún no está mergeado, el PR **C** puede compartir o depender de la misma abstracción de “runtime opcional”; no duplicar un segundo sistema de plugins.

---

## 3. Plan por PR

### PR A — LEONES (docs y registro)

**Alcance**

- [x] `docs/integrations/strata/README.md` (propuesta detallada)
- [x] Este plan/checklist
- [ ] Entrada en ROADMAP / Runtime Registry experimental
- [ ] (Opcional) `README-eng.mkd` espejo

**Criterios de aceptación**

- [ ] Enlaces cruzados con plan de motores y cafe-llama
- [ ] Rol “conditional / Flash Next only” explícito
- [ ] Clases de evidencia REPORTED/OBSERVED/ESTIMATED/MEASURED recordadas

---

### PR B — i18n Dashboard (si falta)

**Alcance**

- Capa i18n `en` / `es` / `zh-CN` (ver `docs/ODS-DASHBOARD-I18N-PR.md`)
- FirstBoot + Settings → Profile

**Criterios de aceptación**

- [ ] Inglés default + fallback
- [ ] Persistencia `ods.language.v1`
- [ ] Tests de i18n pasan
- [ ] Sin cambios de backend/API

**Si B ya está mergeado:** omitir; pasar claves Strata al PR E.

---

### PR C — Scaffold servicio Strata (MVP)

**Archivos esperados**

```text
extensions/services/strata/
├── manifest.yaml
├── docker-compose.yml
├── Dockerfile              # o FROM adaptado de upstream
├── entrypoint.sh
├── native-install.sh       # opcional
└── README.md
```

**Alcance funcional**

- [ ] `ods enable strata` / `ods disable strata`
- [ ] Estado en `ods status`
- [ ] Pin de versión Strata en `manifest.yaml`
- [ ] Healthcheck (proceso + endpoint HTTP interno)
- [ ] Envelope mínimo documentado (VRAM ≥ 12, RAM ≥ 32, disco ~80 GB) — al menos log + fallo claro
- [ ] Volumen/ruta de datos dedicada (`data/strata/` o equivalente)
- [ ] **No** enabled por defecto en instalaciones nuevas

**Criterios de aceptación**

- [ ] `git diff --check` limpio
- [ ] Compose arranca en entorno de lab NVIDIA (o CI con mocks documentados)
- [ ] Disable limpia/para el servicio sin romper llama-server
- [ ] Documentado: primer arranque puede tardar 1–3 min (host bajo presión)

**Fuera de alcance de C**

- UI Dashboard completa
- ICD / perfiles
- Multi-GPU / HIP como default

---

### PR D — Proxy unificado + humo API

**Alcance**

- [ ] Strata detrás del proxy OpenAI-compatible de ODS
- [ ] `/v1/models` expone alias estable documentado
- [ ] Chat completion corta de extremo a extremo vía proxy
- [ ] (Opcional) Anthropic messages / responses si el proxy ODS ya los enruta

**Criterios de aceptación**

- [ ] Cliente existente (Open WebUI / agente) funciona sin cambios de URL de producto
- [ ] Test de humo automatizado o script documentado en el PR
- [ ] Fallo de Strata no tumba el proxy de otros runtimes

---

### PR E — Dashboard + i18n Strata

**Alcance UI**

- [ ] Formulario avanzado: `modelSize`, `family`, `context`, `vision`, `kvCache`, `gpu`, `lowRam`
- [ ] Estados: ready / downloading / starting / failed / notInstalled / notQualified
- [ ] Consentimiento de descarga (~70–80 GB) con texto i18n
- [ ] Aviso first-start
- [ ] Hints de fallback (cafe / llama / TensorFold)

**i18n**

- [ ] Claves `runtime.strata.*` en `en.js`, `es.js`, `zh-CN.js`
- [ ] Sin strings hardcodeados en JSX
- [ ] Identificadores técnicos sin traducir (`Strata`, `Q2_0`, `IQ2_XS`, flags)

**Criterios de aceptación**

- [ ] Cambio de idioma refleja las nuevas cadenas
- [ ] Fallback a inglés si falta clave
- [ ] No modificar `SettingsModal` si la política i18n lo prohíbe
- [ ] Tests de componente/i18n relevantes pasan

---

### PR F — ICD (admisión, perfiles, fallback)

**Alcance**

- [ ] Entrada Runtime Registry (YAML alineado con README §5.6)
- [ ] Candidato solo si familia Flash Next (o variante) **y** envelope OK
- [ ] Perfiles iniciales (ej.):
  - `strata-flash-next-32gb-coder`
  - `strata-flash-next-48gb-iq2`
  - `strata-flash-next-64gb-iq2`
  - `strata-flash-next-64gb-iq3s`
  - `strata-flash-next-vision`
- [ ] Fallback ordenado: Strata → cafe-llama → llama-server → TensorFold (si cualificado)
- [ ] Persistencia de perfil cuando exista evidencia MEASURED (hook o placeholder documentado)

**Criterios de aceptación**

- [ ] Modelo no Flash Next → Strata no aparece como candidato
- [ ] Envelope fallido → `notQualified` + no descarga
- [ ] Documentado qué es ESTIMATED vs MEASURED en este flujo

---

### PR G — Hardening

**Alcance**

- [ ] API key obligatoria si bind ≠ loopback
- [ ] Timeouts de health/start acordes al first-load
- [ ] Multi-GPU documentado, no default
- [ ] HIP/AMD: flag experimental, default off
- [ ] Procedimiento de actualización de versión (pin en manifest)
- [ ] Revisión de logs (no filtrar secretos; API key no en claro en UI)

**Criterios de aceptación**

- [ ] Checklist de seguridad de red ODS revisada
- [ ] README del servicio actualizado con límites y no-goals

---

## 4. Checklist global antes del primer PR de implementación (C)

### Diseño y dependencia

- [ ] Propuesta Strata revisada en LEONES
- [ ] Cafe-llama: patrón de servicio opt-in estable o PR hermano enlazado
- [ ] i18n: mergeado **o** plan explícito de incluir diccionarios en E
- [ ] Decisión de despliegue por plataforma (Docker NVIDIA Linux = path principal documentado)

### Seguridad y producto

- [ ] Strata **no** default-on
- [ ] Catálogo GGUF **no** mezclado con pesos Strata
- [ ] Consentimiento de descarga de ~70–80 GB obligatorio en UX
- [ ] Bind default loopback

### Evidencia

- [ ] Ningún número de tok/s de RTX 5070 presentado como MEASURED de otra máquina
- [ ] Clases REPORTED / OBSERVED / ESTIMATED / MEASURED usadas en docs del PR

---

## 5. Checklist de revisión (reviewer)

Usar en cada PR C–G según aplique:

**Funcional**

- [ ] Enable/disable no rompe `llama-server` ni cafe-llama
- [ ] Health y status coherentes
- [ ] Proxy no acopla fallos entre runtimes
- [ ] Envelope y consentimiento funcionan (o están explícitamente “follow-up” en el PR)

**Código y repo**

- [ ] Diff mínimo; sin refactors ajenos
- [ ] `git diff --check`
- [ ] Sin secretos en el diff
- [ ] Versión upstream pineada y citada

**UX / i18n**

- [ ] Cadenas nuevas en en/es/zh-CN (cuando toque UI)
- [ ] Identificadores técnicos sin traducir
- [ ] Estados de error comprensibles

**Docs**

- [ ] README del servicio o sección en docs ODS actualizada
- [ ] Enlace a propuesta LEONES
- [ ] “Qué no hacer” reflejado (no genérico, no default-on)

---

## 6. Plantilla de descripción de PR (ODS)

```markdown
## Summary

Optional Strata runtime for Qwen3.8-Flash-Next (and admitted variants) in ODS.
Reuses the cafe-llama optional-runtime pattern (service layout, registry, unified
OpenAI-compatible proxy). Not enabled by default. Does not replace llama-server.

## Motivation

- LEONES proposal: docs/integrations/strata/README.md (ods-evolution)
- Consumer GPU path for Flash Next with multi-tier placement
- Same ICD / evidence discipline as other experimental runtimes

## Changes

- extensions/services/strata/ …
- …

## Test plan

- [ ] ods enable strata (lab NVIDIA, envelope OK)
- [ ] health → /v1/models → short chat via ODS proxy
- [ ] ods disable strata; llama-server still healthy
- [ ] envelope fail → notQualified, no download
- [ ] (UI) i18n keys en/es/zh-CN for new strings

## Out of scope

- Default-on install
- Generic multi-model GGUF serving via Strata
- AMD HIP as default
- Claiming upstream tok/s as MEASURED on other hardware

## Depends on

- cafe-llama optional runtime scaffold (link)
- Dashboard i18n PR (link) — or dictionaries included here
```

---

## 7. Criterios de “listo para producción experimental”

Se considera la integración **experimental usable** cuando:

1. PR C + D mergeados y humo verde en lab NVIDIA.  
2. PR E permite configurar size/family sin editar YAML a mano.  
3. PR F evita ofrecer Strata en hardware/modelo no cualificado.  
4. Al menos un resultado **MEASURED** documentado en LEONES para un perfil (size + GPU de lab).  
5. PR G aplicado o issues abiertos con owners para API key / HIP / multi-GPU.

**Producción general (default stack):** fuera de alcance hasta que el proyecto decida promover Strata; hasta entonces permanece opt-in.

---

## 8. Orden de ejecución sugerido (resumen)

```text
A (LEONES docs/registry)
    ↓
B (i18n) —— paralelo si falta
    ↓
C (servicio MVP)
    ↓
D (proxy + humo)
    ↓
E (Dashboard + i18n Strata)
    ↓
F (ICD)
    ↓
G (hardening)
    ↓
MEASURED en lab → actualizar evidencia LEONES
```

---

## 9. Contacto de diseño

- Propuesta y este checklist: LEONES `docs/integrations/strata/`
- Upstream Strata: https://github.com/Niko1221/Strata
- Comparativa motores: `docs/integrations/cafe-llamacpp-vs-strata-vs-tensorfold-2026-10-06.html`
