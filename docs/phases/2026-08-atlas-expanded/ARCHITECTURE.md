# H06 — Arquitectura de la capa canónica del Atlas

## 1. Problema que resuelve

LEONES tiene un feed operativo rico y cambiante y un Atlas canónico que debe ser estable, trazable y auditable. H06 introduce una frontera explícita para impedir que una fila del pipeline se convierta accidentalmente en conocimiento oficial.

## 2. Flujo

```text
FUENTES
  ↓
PROSPECCIÓN
  ↓
ATLAS FEED
  ↓
IDENTIDAD CANÓNICA
  ↓
EVIDENCIA / PROCEDENCIA
  ↓
QUALITY FLAGS
  ↓
VERIFIED-ONLY GATE
  ↓
ATLAS/CATALOG.JSON
  ↓
H10 / JGB / HARDWARE / ROUTER
```

## 3. Dos niveles de datos

### Feed operativo

`data/prospection/atlas_feed.csv` es tabular y está pensado para el trabajo diario. Puede contener descubrimientos, hipótesis, observaciones y datos todavía no verificados.

### Atlas canónico

`atlas/catalog.json` representa conocimiento aceptado según el contrato de `atlas/schema.json`. Cada registro necesita `id`, `kind`, `name` y `evidence`.

## 4. Identidad

La identidad se determina con esta precedencia:

1. `model_id`;
2. repositorio canónico;
3. organización + nombre.

El auditor genera candidatos de duplicación y colisión, pero no destruye registros.

## 5. Evidencia

La evidencia acompaña al hecho y conserva su procedencia. La promoción automática exige `evidence_status=verified` en el feed. Aun así, el registro promocionado conserva `evidence_type=external` cuando su soporte procede de fuentes externas.

Esto permite decir dos cosas simultáneamente:

- el dato ha superado el gate de aceptación del feed;
- el dato no es una medición física de LEONES salvo que exista una evidencia de ese tipo.

## 6. Calidad

Los quality flags son advertencias estructuradas. No sustituyen al valor original ni permiten que el programa invente un valor correcto.

Las categorías previstas por el schema incluyen `missing`, `unverified`, `stale`, `contradictory`, `duplicate`, `invalid_value`, `unsupported_claim`, `source_missing`, `identity_collision` e `inconsistent_units`.

## 7. Promoción

`scripts/atlas_promote_verified.py` es la puerta de entrada. Su comportamiento es deliberadamente conservador:

- solo acepta filas verificadas;
- mantiene identidad canónica;
- conserva URLs de evidencia;
- no inventa valores;
- no convierte ausencia en cero;
- no inventa JGB/CABE/RULA/rendimiento/economía;
- actualiza o incorpora el registro por identidad, sin merge destructivo.

## 8. Automatización

`.github/workflows/atlas-h06.yml` ejecuta el gate de forma repetible y publica los artefactos de auditoría. El workflow no usa datos ficticios para conseguir un resultado verde.

## 9. Consumidores

El Atlas canónico puede alimentar capas posteriores, pero cada consumidor debe respetar el estado de evidencia y devolver `unknown` cuando el dato necesario no exista.
