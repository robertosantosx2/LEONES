# RC2-G — End-to-End Beta Flow

**Estado:** 🟢 Contrato fijado · operador canónico = `./leones`

RC2-G integra las puertas RC2 en un único recorrido. No sustituye los contratos de cada puerta; fija el orden y prohíbe cadenas paralelas.

## Recorrido canónico

```text
INSTALL LEONES (+ LLMFit en PATH)
    ↓
LANGUAGE CHOICE (one UI language)
    ↓
HARDWARE + CANDIDATES (LLMFit, ESTIMATED)
    ↓
USER MODEL CHOICE
    ↓
STACK PRESENTATION + USER STACK CHOICE
    ↓
INSTALL CONSENT → INSTALL (optional) → PHYSICAL STACK VERIFY
    ↓
MODEL → RUNTIME RESOLUTION (declarative)
    ↓
RUNTIME / ARTIFACT PREFLIGHT
    ↓
A01 EXPLANATION + BENCHMARK CONSENT
   ┌┴──────────────┐
   NO              YES
   ↓                ↓
COMPLETE*       EXECUTION_AUTHORIZED → RC1 A01 → EVIDENCE → COMPLETE

* sin medición; instalación intacta
```

## Gates

- `HARDWARE_READY`
- `MODEL_SELECTED`
- `STACK_SELECTED`
- `CONSENT_REQUIRED` → `INSTALLING`
- `READY_FOR_BENCHMARK` (solo tras verify física del stack)
- `BENCHMARK_CONSENT_REQUIRED`
- `EXECUTION_AUTHORIZED` → `COMPLETE` si A01 produce medición válida
- `BLOCKED` si falta runtime/artefacto o falla la ejecución

## Regla RC1

La medición reutiliza `a01_runtime_benchmark.py`. RC2 no crea un segundo runner.

## Criterio de cierre

- operador único `./leones`
- docs L/F/J/K/H/Q alineados (sin UI trilingüe simultánea)
- tests de sesión, wizard, i18n, verify y resolución
