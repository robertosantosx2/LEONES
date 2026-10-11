# Propuesta de integración de Strata en ODS (Osmantic/ODS)

**Taller de diseño:** LEONES (`docs/integrations/strata/`)  
**Destino de implementación:** **Osmantic/ODS** (`extensions/services/strata/`)  
**Fecha:** 2026-10-11  
**Estado:** Diseño y esqueleto listos para PR de implementación en ODS  
**Upstream:** https://github.com/Niko1221/Strata (MIT)

> LEONES no integra Strata como producto. Aquí se prepara el diseño, el checklist y el skeleton que luego se llevan al repositorio **Osmantic/ODS**.

---

## 1. Resumen ejecutivo

**Strata** ejecuta **Qwen3.8-Flash-Next** en PC de consumo (GPU ≥ 12 GB, RAM 32–64 GB) con placement multi-tier y API OpenAI/Anthropic en localhost.

**Papel en ODS:** runtime **opcional y especializado** (solo Flash Next y variantes admitidas). Complementa, no sustituye, a `llama-server`. Reutiliza el patrón de runtime opt-in (p. ej. cafe-llama) y la i18n del Dashboard.

---

## 2. Patrón a reutilizar en Osmantic/ODS

| Pieza | Uso en Strata |
|-------|----------------|
| `extensions/services/strata/` | manifest + compose + overlay NVIDIA |
| `ods enable strata` | opt-in; no default-on |
| Proxy OpenAI-compatible | clientes agnósticos al runtime |
| Dashboard + i18n | params size/family/context/vision; claves `runtime.strata.*` |
| Envelope | VRAM ≥ 12, RAM ≥ 32 (64 recom.), disco ~80 GB |

Skeleton listo para copiar: `docs/integrations/strata/skeleton/` (manifest **alineado a `ods.services.v1`**).

---

## 3. Envelope y modelo (upstream — REPORTED/OBSERVED)

| Recurso | Requisito |
|---------|-----------|
| GPU | NVIDIA (path Docker) ≥ 12 GB; AMD HIP experimental |
| RAM | ≥ 32 GB; 64 GB para todos los sizes principales |
| Disco | ~80 GB |

Sizes: Q2_0, IQ2_XS (recomendado), IQ3_XXS, IQ3_S; familias Coder / Swift / Unsloth. Benchmarks públicos = **REPORTED**, no MEASURED en otro hardware.

---

## 4. Implementación en Osmantic/ODS (resumen)

1. Copiar skeleton → `extensions/services/strata/`
2. Pin de imagen/commit Strata
3. `audit-extensions.py` + `docker compose … config`
4. enable/disable/status/health; volumen `data/strata`
5. Proxy unificado; Dashboard + i18n; ICD/fallback
6. Hardening (API key fuera de loopback, HIP off)

Detalle: `PR-PLAN-Y-CHECKLIST.md`.

---

## 5. Qué no hacer

- No activar por defecto ni sustituir llama-server.
- No mezclar catálogo GGUF con pesos Strata.
- No tratar tok/s de RTX 5070 como MEASURED ajeno.
- No abrir PR a Osmantic/ODS sin pin de versión y validación de schema.

---

## Referencias

- https://github.com/Niko1221/Strata
- Skeleton: `docs/integrations/strata/skeleton/`
- Checklist PR: `docs/integrations/strata/PR-PLAN-Y-CHECKLIST.md`
