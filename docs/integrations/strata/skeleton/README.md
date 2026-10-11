# Esqueleto de servicio Strata (para PR C en ODS)

Archivos de referencia para copiar a:

```text
extensions/services/strata/
├── manifest.yaml
├── compose.yaml
├── compose.nvidia.yaml
└── README.md          # docs del servicio en ODS
```

Alineados con:

- Contrato ODS `schema_version: ods.services.v1`
- Plantillas en `ods/extensions/templates/`
- Docker upstream de Strata (`FAMILY`, `MODEL`, `CONTEXT`, `VISION`, `KV`, `GPU`/`GPUS`, `LOW_RAM`, `API_KEY`, health `/health`, `start_period` alto)
- Propuesta LEONES: `docs/integrations/strata/README.md`
- Checklist PR: `docs/integrations/strata/PR-PLAN-Y-CHECKLIST.md`

## Antes de mergear en ODS

1. Sustituir `TODO-pin` / `version_pin` por tag o commit inmutable de Strata.
2. Decidir imagen prebuild vs `build` desde git (`ods-source-strata:<commit>`).
3. Integrar con el mecanismo real de `ods enable` / profiles del instalador (el `profiles: [strata]` del compose es orientativo).
4. Validar:

```bash
python scripts/audit-extensions.py --project-dir . strata
docker compose -f docker-compose.base.yml \
  -f docker-compose.nvidia.yml \
  -f extensions/services/strata/compose.yaml \
  -f extensions/services/strata/compose.nvidia.yaml config
git diff --check
```

5. No activar por defecto. No mezclar volúmenes con `data/models` GGUF.
6. Consentimiento de descarga ~70–80 GB y envelope VRAM/RAM en la ruta de enable (producto + scripts).

## Fuera de este esqueleto

- Proxy unificado (PR D)
- Dashboard + i18n (PR E)
- ICD / perfiles (PR F)
- API key obligatoria fuera de loopback, multi-GPU default, HIP (PR G)
