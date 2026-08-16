# H06 — Informe de cierre técnico

**Corte:** 16/08/2026  
**Estado técnico:** 🟡 implementación completa; aceptación CI pendiente de la primera ejecución del gate H06.

## Qué queda terminado

### H06.1 — Auditoría inicial

- Contrato `atlas/schema.json` auditado.
- Diferencia entre feed operativo y Atlas canónico documentada.
- Se confirma que `catalog.json` parte de cero y no debe rellenarse manualmente.

### H06.2 — Identidad

- Precedencia: `model_id` → repositorio canónico → organización + nombre.
- No hay merge destructivo.
- Variantes, cuantizaciones y configuraciones se conservan separadas cuando pueden representar artefactos distintos.
- `scripts/atlas_identity_audit.py` produce candidatos de revisión.

### H06.3 — Evidencia

- Solo `evidence_status=verified` puede cruzar la frontera de promoción.
- Se conserva la URL y la procedencia disponible.
- La evidencia externa se mantiene como `external` y no se transforma en medición LEONES.
- Los estados `reported`, `reproducible`, `verified` y `rejected` mantienen significado independiente.

### H06.4 — Calidad

- `scripts/atlas_quality_audit.py` genera flags deterministas.
- Los flags son incidencias de revisión, no valores de verdad.
- No se convierten ausencias en cero.
- Las colisiones de identidad se señalan, no se fusionan automáticamente.

### H06.5 — Normalización y promoción

- `scripts/atlas_promote_verified.py` constituye la frontera explícita feed → Atlas.
- Produce registros canónicos de tipo `model`.
- Conserva identidad, ejecución, sistema del modelo, evidencia y lifecycle.
- No inventa JGB, CABE, RULA, rendimiento ni economía.
- Genera `atlas_promotion_report.json`.

### H06.6 — Validación automatizada

El workflow `.github/workflows/atlas-h06.yml` ejecuta:

```text
pruebas de promoción
        ↓
auditoría de identidad
        ↓
auditoría de calidad
        ↓
promoción verified-only
        ↓
validación JSON Schema
        ↓
informe H06
        ↓
publicación de outputs
```

La validación del catálogo usa JSON Schema Draft 2020-12 y el esquema canónico de `atlas/schema.json`.

### H06.7 — Documentación

La fase queda documentada en:

- `README.md`
- `H06_SCOPE.md`
- `COVERAGE-AUDIT.md`
- `IDENTITY-RULES.md`
- `EVIDENCE-RULES.md`
- `DECISIONS.md`
- `H06_FINAL.md`

## Qué NO se considera terminado

H06 no afirma que todos los modelos descubiertos estén verificados, benchmarkeados o medidos físicamente. La cantidad de registros aceptados dependerá del feed y de su evidencia en cada ejecución.

Tampoco se cierran aquí:

- JGB sistemático completo;
- CABE/RULA completo;
- matriz hardware completa;
- benchmarks físicos;
- optimización multiobjetivo.

Esas capacidades son fases posteriores y consumen conocimiento del Atlas cuando existe evidencia adecuada.

## Criterio final

La fase se considera **operativamente cerrada** cuando el workflow H06 termina en verde y deja publicados:

- `atlas/catalog.json` válido;
- `atlas_identity_audit.csv`;
- `atlas_quality_flags.csv`;
- `atlas_promotion_report.json`;
- `h06_audit_report.json`.

Si el feed contiene cero registros verificados, el resultado correcto es un Atlas canónico vacío; nunca se introducen datos ficticios para conseguir un estado verde.
