# Esqueleto de servicio Strata — destino Osmantic/ODS

**LEONES solo es el taller de diseño.** La implementación de producto va a **Osmantic/ODS** (`extensions/services/strata/`).

```text
extensions/services/strata/
├── manifest.yaml          # schema ods.services.v1
├── compose.yaml
├── compose.nvidia.yaml
├── entrypoint.sh          # opcional
└── README.md
```

| Archivo aquí | Destino en Osmantic/ODS |
|--------------|-------------------------|
| `manifest.yaml` | `extensions/services/strata/manifest.yaml` |
| `compose.yaml` | `extensions/services/strata/compose.yaml` |
| `compose.nvidia.yaml` | `extensions/services/strata/compose.nvidia.yaml` |
| `entrypoint.sh` | opcional |
| `env.example` | claves → `.env.example` de ODS |

## Antes del PR de implementación en ODS

1. Pin real de imagen/commit Strata (sustituir `TODO-pin`).
2. Validar con `audit-extensions.py` y `docker compose … config`.
3. No default-on; volumen `data/strata` aparte del catálogo GGUF.
4. Consentimiento de descarga ~70–80 GB + envelope VRAM/RAM en enable.

Ver propuesta: `../README.md` · checklist: `../PR-PLAN-Y-CHECKLIST.md`.
