# LEONES — Ingesta Agentic → Atlas

## Regla absoluta

**Ningún elemento Agentic se incorpora directamente a Atlas.**

El inventario `docs/AGENTIC-INVENTORY-2026.md` es únicamente el radar de candidatos. La promoción sigue el contrato:

```text
DISCOVERED
 → IDENTIFIED
 → OSI_PENDING
 → OSI_PASS
 → EVIDENCE_PENDING
 → QUALITY_GATE
 → ATLAS_ELIGIBLE
 → ATLAS_VERIFIED
```

Cualquier estado anterior a `ATLAS_ELIGIBLE` queda fuera del Atlas canónico.

## Unidades de conocimiento

La ingesta conserva el tipo original:

- agente;
- harness;
- framework;
- protocolo;
- tool runtime;
- sandbox;
- evaluator.

No se transforma automáticamente en un `LLM` ni se mezcla con una familia de modelos.

## Campos mínimos de promoción

`agentic_id`, `name`, `type`, `organization`, `primary_url`, `version`, `license`, `osi_status`, `osi_evidence`, `evidence_status`, `atlas_status`, `last_verified_at`.

## Reglas

1. Sin identidad inequívoca → fuera.
2. Sin fuente primaria → fuera.
3. Sin licencia verificable → `OSI_UNKNOWN` y fuera.
4. `OSI_FAIL` → fuera.
5. `OSI_PASS` → todavía no es Atlas; debe superar evidencia/quality gate.
6. Evidencia insuficiente → `EVIDENCE_PENDING`.
7. Solo `ATLAS_ELIGIBLE/VERIFIED` puede alimentar el recomendador como conocimiento aceptado.
8. La procedencia debe conservarse.
9. No se sobrescriben estados históricos sin trazabilidad.
10. Ningún workflow paralelo puede escribir los artefactos canónicos.

## No concurrencia

Toda automatización de ingesta utiliza exclusivamente `leones-main-writers` y `cancel-in-progress: false`.

## Resultado esperado

El catálogo Agentic puede crecer continuamente sin contaminar Atlas. El Atlas solo contiene conocimiento Agentic que ha superado explícitamente el Gate OSI y los controles de evidencia posteriores.
