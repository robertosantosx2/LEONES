# RC2-G — End-to-End Beta Flow

**Estado:** 🟢 Contrato fijado

RC2-G integra RC2-A..F en un único recorrido de usuario. Es la primera especificación del producto beta completo; no sustituye los contratos anteriores.

## Recorrido canónico

```text
INSTALL LEONES
    ↓
PREFLIGHT
    ↓
HARDWARE OBSERVED
    ↓
LLMFIT PROFILE
    ↓
MODEL CANDIDATES
    ↓
USER MODEL CHOICE
    ↓
ODS / MAGNITUDE CAPABILITY PRESENTATION
    ↓
USER STACK CHOICE
    ↓
INSTALLATION PLAN
    ↓
INSTALL CONSENT
    ↓
INSTALL + VERIFY
    ↓
READY_FOR_BENCHMARK
    ↓
BENCHMARK EXPLANATION
    ↓
BENCHMARK CONSENT
   ┌┴──────────────┐
   NO              YES
   ↓                ↓
COMPLETE        EXECUTION
                    ↓
                 GRADER
                    ↓
                MEASUREMENT
                    ↓
                 EVIDENCE
```

## Persistencia

Cada etapa debe conservar un estado explícito y no depender de memoria de pantalla. Como mínimo se conservan: hardware observado, overrides declarados, perfil/candidatos LLMFit, modelo seleccionado, stack seleccionado, plan de instalación, consentimiento de instalación, verificación, decisión de benchmark y execution_id cuando exista ejecución.

## Reanudación

Si una etapa falla, el usuario debe poder reanudar desde el último estado válido sin repetir acciones ya verificadas. No se deben repetir descargas o instalaciones cuando el estado local ya demuestra que están completadas.

## Gates

- `HARDWARE_READY`: hardware suficiente para continuar o limitaciones explícitas.
- `MODEL_SELECTED`: selección humana válida.
- `STACK_SELECTED`: ODS o Magnitude seleccionado tras mostrar funcionalidades.
- `READY_FOR_INSTALL`: plan y preflight completos.
- `READY_FOR_BENCHMARK`: instalación verificada.
- `EXECUTION_AUTHORIZED`: consentimiento específico para benchmark.

Ningún gate se satisface por inferencia silenciosa.

## Errores

Los errores deben ser accionables: indicar etapa, causa, si es recuperable y qué debe hacer el usuario. Un dato desconocido se conserva como `unknown`/`null`; nunca se transforma en un valor favorable inventado.

## Privacidad

El flujo debe explicar qué datos locales se detectan y qué evidencia se conserva. No se envían resultados fuera del host por defecto.

## Regla RC1

La ejecución de benchmark reutiliza el pipeline efectivo validado en RC1. RC2-G no crea un segundo runner ni una segunda semántica de evidencia.

## Criterio de cierre

RC2-G estará listo para validación física cuando exista una implementación que pueda recorrer el flujo completo con fixtures y mocks sin hardware real, y todos los gates y transiciones estén cubiertos por tests. La validación física final requiere al menos un host Linux real.
