# External Estimates → Atlas review

Las estimaciones descubiertas en Internet pueden entrar en una **cola de revisión**, pero nunca se promocionan automáticamente a Leones Atlas.

```text
Internet
   ↓
external-unvalidated
   ↓
review queue
   ↓
revisión explícita
   ├── rejected
   └── atlas-evidence
```

`external_to_atlas` solo prepara el registro para revisión y conserva fuente, tipo de evidencia y tipo de fuente.

## Garantía

El script no:

- valida la afirmación;
- cambia el estado a `atlas-evidence`;
- modifica Router;
- modifica automáticamente el catálogo de modelos.

Esta separación permite que la alimentación semanal de información externa sea automática sin convertirla en conocimiento operativo de LEONES sin revisión.
