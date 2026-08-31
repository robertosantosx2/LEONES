# RC2-J — Benchmark handoff to RC1

**Estado:** 🟢 Contrato fijado

RC2 no crea un segundo sistema de ejecución. Cuando el usuario autoriza el benchmark, la sesión produce un handoff explícito compatible con el pipeline de ejecución autorizado que RC1 ya validó.

## Flujo

```text
READY_FOR_BENCHMARK
        ↓
BENCHMARK_CONSENT_REQUIRED
        ↓
   ┌────┴────┐
   │         │
 DECLINE   AUTHORIZE
   │         │
   ↓         ↓
READY     EXECUTION_AUTHORIZED
             ↓
          RC1 handoff
             ↓
       runtime → A01 → grader
             ↓
       measured evidence
```

## Reglas

1. La instalación debe estar verificada antes de pedir consentimiento de benchmark.
2. El usuario debe poder aplazar o rechazar el benchmark.
3. `execution_authorized=true` solo aparece después del consentimiento explícito.
4. El handoff conserva benchmark, versión y tareas solicitadas.
5. RC2 no duplica el runner ni redefine la métrica de RC1.
6. El resultado de ejecución y la evidencia siguen siendo responsabilidad del pipeline existente.

## Resultado

El objetivo de RC2 es que el usuario llegue a la misma cadena que ya fue demostrada físicamente en RC1, pero mediante una experiencia guiada y con decisiones explícitas.
