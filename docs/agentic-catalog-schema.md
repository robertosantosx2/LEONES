# Esquema mínimo del catálogo Agentic

El catálogo es independiente de Atlas y conserva candidatos antes de su aceptación.

| Campo | Obligatorio | Función |
|---|---|---|
| `agentic_id` | sí | Identidad estable |
| `name` | sí | Nombre canónico |
| `type` | sí | agent / harness / framework / protocol / tool_runtime / sandbox / evaluator |
| `organization` | sí | Proyecto/organización |
| `primary_url` | sí | Fuente primaria |
| `repository_url` | cuando exista | Repositorio primario |
| `version` | sí | Versión comprobada |
| `discovered_at` | sí | Fecha de descubrimiento |
| `license` | sí | Licencia identificada |
| `osi_status` | sí | pending / pass / fail / unknown |
| `osi_evidence` | sí | Evidencia del Gate OSI |
| `evidence_status` | sí | pending / verified / disputed |
| `atlas_status` | sí | excluded / pending / eligible / verified |
| `last_verified_at` | sí | Fecha de verificación |

## Regla de promoción

```text
osi_status = pass
AND evidence_status = verified
→ atlas_status = eligible/verified
```

Cualquier otro estado permanece fuera del Atlas canónico.
