# H06 — P1 Evidencia canónica

## Objetivo

Establecer una auditoría reproducible de procedencia y estado de evidencia antes de promover afirmaciones al Atlas canónico.

## Estados

- `reported`: existe una fuente/afirmación reportada, sin verificación LEONES.
- `reproducible`: existe evidencia suficiente para intentar reproducir la afirmación.
- `verified`: la afirmación ha sido verificada conforme al protocolo aplicable.
- `rejected`: la evidencia disponible contradice o invalida la afirmación.
- `unknown`: estado operativo cuando el feed no aporta evidencia suficiente; no es un estado canónico permitido y debe resolverse antes de promoción.

## Tipos

El schema canónico admite `external`, `manada`, `leones_measurement`, `documentary` y `unknown`. Una fuente externa no se transforma automáticamente en `verified`.

## Reglas

1. La URL es procedencia, no verificación.
2. `retrieved_at` indica cuándo se obtuvo la fuente, no cuándo se produjo el dato.
3. Una afirmación debe conservar su fuente y poder rastrearse hasta el registro original.
4. No se elevan estados automáticamente.
5. Ausencia de fuente produce una incidencia; nunca se rellena con una URL inventada.
6. La evidencia de rendimiento, memoria, contexto, apertura y benchmarks debe poder distinguirse por afirmación.

## Flujo

```text
FUENTE
  ↓
REGISTRO DESCUBIERTO
  ↓
AFIRMACIÓN
  ↓
EVIDENCIA
  ↓
ESTADO
  ↓
ATLAS
```

## Auditor

`scripts/atlas_evidence_audit.py` genera `data/prospection/atlas_evidence_audit.csv`. El auditor es conservador: clasifica procedencia y necesidades de revisión, pero no eleva evidencia a `verified`.

## Criterio de aceptación P1

P1 se cerrará cuando el pipeline produzca una auditoría sobre el feed real, todas las filas tengan una procedencia trazable o una incidencia explícita, los estados estén normalizados y se documente qué afirmaciones pueden promocionarse al Atlas canónico.
