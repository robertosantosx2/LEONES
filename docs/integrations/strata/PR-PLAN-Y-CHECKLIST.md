# Plan y checklist de PR — Strata → Osmantic/ODS

**Taller:** LEONES `docs/integrations/strata/`  
**Implementación:** **Osmantic/ODS**  
**Fecha:** 2026-10-11

LEONES solo aloja el diseño y el skeleton. Los PRs de producto van al repo **Osmantic/ODS** (o fork de trabajo).

---

## Tren de PRs

| PR | Ámbito | Repo |
|----|--------|------|
| **A** | Docs + skeleton (este PR en LEONES) | LEONES |
| **B** | i18n Dashboard si falta | ODS |
| **C** | Scaffold `extensions/services/strata/` | **ODS** |
| **D** | Proxy + humo API | **ODS** |
| **E** | Dashboard + i18n Strata | **ODS** |
| **F** | ICD / admisión / fallback | **ODS** |
| **G** | Hardening | **ODS** |

---

## PR A (este) — LEONES

- [x] `docs/integrations/strata/README.md`
- [x] `docs/integrations/strata/PR-PLAN-Y-CHECKLIST.md`
- [x] `docs/integrations/strata/skeleton/*` con **manifest schema-valid** (`ods.services.v1`)

---

## PR C — Scaffold en Osmantic/ODS

Copiar desde `skeleton/`:

```text
extensions/services/strata/
├── manifest.yaml
├── compose.yaml
├── compose.nvidia.yaml
└── entrypoint.sh   # opcional
```

**Criterios**

- [ ] Pin real de imagen/commit (no `TODO-pin`)
- [ ] `python scripts/audit-extensions.py --project-dir . strata`
- [ ] `docker compose … config` con overlay nvidia
- [ ] `ods enable/disable strata`; no default-on
- [ ] Volumen `data/strata` ≠ catálogo GGUF
- [ ] Health start_period ≥ 600s

---

## Manifest (schema real)

Campos usados según `service-manifest.v1.json`:

- `schema_version`, `compatibility.ods_min`
- `service.id|name|port|health|type|category|gpu_backends|compose_file|…`
- `service.env_vars[]` con **`key`** (no `name` en raíz)
- `service.llm.consumes: false` (Strata provee inferencia; no es cliente del gateway)
- `features[]` con id, name, description, icon, category, requirements, priority

Notas de envelope/ICD solo en comentarios del manifest o en registry aparte.

---

## Plantilla PR hacia Osmantic/ODS

```markdown
## Summary
Optional Strata runtime for Qwen3.8-Flash-Next in ODS.
Design/skeleton prepared in LEONES docs/integrations/strata/.
Not enabled by default. Does not replace llama-server.

## Test plan
- [ ] audit-extensions.py strata
- [ ] compose config (+ nvidia overlay)
- [ ] enable → health → /v1/models → short chat
- [ ] disable; llama-server still healthy
```

---

## Referencias

- Propuesta: `README.md`
- Skeleton: `skeleton/`
- Upstream: https://github.com/Niko1221/Strata
