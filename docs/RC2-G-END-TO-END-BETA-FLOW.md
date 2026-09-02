# RC2-G — End-to-End Beta Flow

**Estado:** 🟢 Contrato fijado · operador canónico = `./leones`

RC2-G integra RC2-A..F (y J/K/L) en un único recorrido de usuario. No sustituye los contratos de cada puerta; fija el orden y prohíbe cadenas paralelas.

## Recorrido canónico

```text
INSTALL LEONES (+ LLMFit en PATH)
    ↓
LANGUAGE CHOICE (one UI language for the session)
    ↓
PREFLIGHT / HARDWARE OBSERVED (LLMFit)
    ↓
MODEL CANDIDATES (ESTIMATED)
    ↓
USER MODEL CHOICE
    ↓
ODS / MAGNITUDE CAPABILITY PRESENTATION
    ↓
USER STACK CHOICE
    ↓
INSTALL CONSENT
    ↓
INSTALL (canonical script, optional now/later)
    ↓
PHYSICAL VERIFY (observe host)
    ↓
READY_FOR_BENCHMARK
    ↓
A01 EXPLANATION
    ↓
BENCHMARK CONSENT
   ┌┴──────────────┐
   NO              YES
   ↓                ↓
COMPLETE*       EXECUTION_AUTHORIZED
                    ↓
              RC1 A01 runner
                    ↓
              GRADER + MEASUREMENT
                    ↓
                 EVIDENCE
                    ↓
                 COMPLETE

* sin medición; instalación intacta
```

## Gates

- `HARDWARE_READY`
- `MODEL_SELECTED`
- `STACK_SELECTED`
- `CONSENT_REQUIRED` → `INSTALLING`
- `READY_FOR_BENCHMARK` (solo tras `real_installation: true`)
- `BENCHMARK_CONSENT_REQUIRED`
- `EXECUTION_AUTHORIZED` → `COMPLETE` (si A01 produce medición válida)

Ningún gate se satisface por inferencia silenciosa.

## Regla RC1

La ejecución de benchmark reutiliza el pipeline RC1 (`a01_runtime_benchmark.py`). RC2 no crea un segundo runner ni una segunda semántica de evidencia.

## Criterio de cierre

- tests de sesión, wizard, i18n y verificación física;
- operador único `./leones`;
- documentación alineada en RC2-L, RC2-F/J, RC2-K, RC2-H.
