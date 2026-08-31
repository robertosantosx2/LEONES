# RC2-J — Benchmark consent and RC1 handoff

**Estado:** 🟢 Contrato fijado

RC2-J cierra el recorrido de usuario hasta el punto inmediatamente anterior a la ejecución física. Una instalación verificada deja el sistema en `READY_FOR_BENCHMARK`; no autoriza por sí sola ninguna medición.

## Flujo

```text
INSTALL_VERIFIED
      ↓
READY_FOR_BENCHMARK
      ↓
┌──────────────────────────────────────────────┐
│ LEONES muestra antes de ejecutar:            │
│ • benchmark y versión                        │
│ • tareas previstas                            │
│ • runtime/modelo seleccionados                │
│ • qué métricas se recogerán                  │
│ • duración/impacto si se conoce              │
│ • evidencia que se conservará                │
└──────────────────────┬───────────────────────┘
                       ↓
             ¿EJECUTAR BENCHMARK?
                /             \
              NO              SÍ
              ↓                ↓
       BENCHMARK_DECLINED  EXECUTION_AUTHORIZED
                                ↓
                         runner RC1 existente
                                ↓
                    measured → evidence
                                ↓
                            COMPLETE
```

## Reglas

1. El consentimiento identifica el benchmark concreto y su versión.
2. El consentimiento identifica el modelo, runtime y stack seleccionados.
3. Rechazar es una salida válida, no un error.
4. Instalar no implica ejecutar.
5. Una medición previa nunca satisface el consentimiento actual.
6. Una evidencia anterior no se reutiliza como ejecución actual.
7. La ejecución debe producir un `execution_id` nuevo.
8. La capa RC2 no redefine el runner de RC1 ni sus contratos de evidencia.
9. Si la ejecución real no puede garantizarse, el estado debe ser `BLOCKED`, nunca `success`.

## Handoff canónico

RC2 entrega al runner únicamente un plan ya seleccionado y autorizado. El runner de RC1 conserva la responsabilidad de ejecutar, medir, validar y producir evidencia.

```text
RC2 session
   │
   ├── model_selection
   ├── stack_selection
   ├── installation.verification
   └── benchmark_consent = granted
              ↓
       execution_authorized
              ↓
        RC1 execution
              ↓
       runtime evidence
```

Este contrato mantiene una única cadena de verdad: **selección → consentimiento → ejecución → medición → evidencia**.
