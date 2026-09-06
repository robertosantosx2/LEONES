# LEONES RC4 — FitLLM recommender architecture

**Estado:** 🟡 Decisión fijada · implementación pendiente  
**Predecesor:** RC3 (CERRADA)  
**Decisión:** 6 de septiembre de 2026  
**Acta:** `docs/completed/RC4-DECISION-FITLLM-RECOMMENDER-2026-09-06.md`

## 1. Objetivo

RC4 mantiene la sonda física y la autoridad de medición de LEONES.
Cambia el tramo de **propuesta de modelo**: FitLLM actúa como recomendador
externo opcional. Hermes/OMH no son el selector canónico.

## 2. Flujo

```text
hardware_profile.py
        ↓
hardware-profile.v1
        ↓
LEONES candidate-set.v1
        ↓
FitLLM (opcional, ESTIMATED)
        ↓
usuario elige modelo
        ↓
usuario elige Magnitude | ODS
        ↓
consentimiento → install/prepare
        ↓
oferta opt-in: desinstalar FitLLM
        ↓
verificación física
        ↓
Leo001 … Leo010
        ↓
MEASURED (solo tras ejecución real)
        ↓
evidencia / recomendación
```

## 3. Responsabilidades

| Actor | Hace | No hace |
|-------|------|---------|
| LEONES | Sonda, contratos, consent log, verify, Leo*, MEASURED, evidencia | No sustituye instaladores de stack |
| FitLLM | Recomienda / ordena candidatos (ESTIMATED) | No mide; no es hard-dep de arranque; no elige stack |
| Usuario | Modelo, stack, consent, opt-in desinstalar FitLLM | — |
| Magnitude / ODS | Prepare/ejecute según su interfaz | No son selectores de modelo LEONES |
| Hermes / OMH | Opcional: agente / operación | No autoridad de selección RC4 |

## 4. Fronteras

- ESTIMATED ≠ MEASURED
- OBSERVED ≠ VALIDATED
- Recomendación ≠ ejecución
- FitLLM ausente ≠ LEONES roto
- Hermes ausente ≠ LEONES roto

## 5. Bootstrap

```text
LEONES (required)
  ↓
hardware_profile (required)
  ↓
FitLLM (optional — recommendation only)
  ↓
Hermes / OMH (optional — agent/ops; show disk/RAM/daemon cost in UI)
  ↓
Magnitude | ODS (user choice)
  ↓
optional uninstall FitLLM
  ↓
Leo001…Leo010 when measurement authorized
```

## 6. Relación con RC3

RC3 permanece documentada como fase cerrada.
RC4 no reabre RC3 ni invalida el acta `RC3-CLOSED-2026-09-05`.
La rama `rc3-hermes-task-benchmarks` es histórica respecto al selector;
no define el camino canónico RC4.

## 7. Implementación (pendiente)

Código, gate CI, tests y web se actualizan en commits posteriores a esta decisión.
EOF
