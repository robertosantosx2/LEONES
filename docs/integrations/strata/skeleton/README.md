# Esqueleto de servicio Strata (para PR C en ODS)

Referencia en LEONES para copiar a ODS:

```text
extensions/services/strata/
├── manifest.yaml
├── compose.yaml
├── compose.nvidia.yaml
├── entrypoint.sh          # opcional si la imagen ya trae docker-entrypoint.sh
└── README.md              # docs del servicio en el repo ODS
```

Variables de ejemplo: `env.example` (fusionar en `.env` / `.env.example` de ODS).

## Inventario (esta carpeta)

| Archivo | Destino en ODS |
|---------|----------------|
| `manifest.yaml` | `extensions/services/strata/manifest.yaml` |
| `compose.yaml` | `extensions/services/strata/compose.yaml` |
| `compose.nvidia.yaml` | `extensions/services/strata/compose.nvidia.yaml` |
| `entrypoint.sh` | opcional; o confiar en el ENTRYPOINT de la imagen |
| `env.example` | claves → `.env.example` del proyecto ODS |

## Alineación

- Contrato ODS: `schema_version: ods.services.v1`
- Plantillas: `ods/extensions/templates/`
- Upstream Strata: env `FAMILY`, `MODEL`, `CONTEXT`, `VISION`, `KV`, `GPU`/`GPUS`, `LOW_RAM`, `API_KEY`; health `/health`; start period alto
- Propuesta: `docs/integrations/strata/README.md`
- Checklist PR: `docs/integrations/strata/PR-PLAN-Y-CHECKLIST.md`

## Antes de mergear en ODS

1. Sustituir `TODO-pin` / `version_pin` por tag o commit inmutable de Strata.
2. Decidir imagen prebuild vs build desde git (`ods-source-strata:<commit>`).
3. Enganchar `ods enable strata` / profiles del instalador (el `profiles: [strata]` del compose es orientativo).
4. Validar:

```bash
python scripts/audit-extensions.py --project-dir . strata
docker compose -f docker-compose.base.yml \
  -f docker-compose.nvidia.yml \
  -f extensions/services/strata/compose.yaml \
  -f extensions/services/strata/compose.nvidia.yaml config
git diff --check
```

5. No activar por defecto. No mezclar volúmenes con el catálogo GGUF (`data/models`).
6. Consentimiento de descarga ~70–80 GB y comprobación de envelope VRAM/RAM en la ruta de enable.

## Fuera de este esqueleto

- Proxy unificado (PR D)
- Dashboard + i18n (PR E)
- ICD / perfiles (PR F)
- API key obligatoria fuera de loopback, multi-GPU default, HIP (PR G)
