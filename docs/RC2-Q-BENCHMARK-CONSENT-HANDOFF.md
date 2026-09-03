# RC2-Q — Consentimiento de benchmark y handoff a RC1

**Estado:** 🟢 Resumen canónico (detalle en RC2-F / RC2-J)

RC2 termina la preparación y deja que el usuario decida explícitamente si desea medir el modelo elegido. La instalación y el benchmark son consentimientos independientes.

## Fuentes canónicas

| Tema | Documento |
|------|-----------|
| Contrato de consentimiento y A01 | `docs/RC2-F-BENCHMARK-CONSENT.md` |
| Handoff a RC1 | `docs/RC2-J-BENCHMARK-HANDOFF.md` |
| Operador y recorrido real | `docs/RC2-L-INTEGRATED-BETA-JOURNEY.md` |
| Idioma de UI | `docs/RC2-K-MULTILINGUAL-UI.md` |

RC2-Q no redefine esos contratos; solo resume el punto de decisión.

## Decisión

```text
READY_FOR_BENCHMARK
        ↓
resolución modelo → runtime (declarativa)
        ↓
preflight físico del runtime/artefacto
        ↓
¿EJECUTAR BENCHMARK A01?
   ├── NO → READY_FOR_BENCHMARK (nada medido)
   └── SÍ → EXECUTION_AUTHORIZED → runner RC1 → evidence
```

Si el usuario rechaza, no se ejecuta ningún runtime.
Si acepta, RC2 genera `rc1_handoff` con `execution_authorized=true`. RC2 no duplica runner, grader ni evidencia.

## Reglas

1. Instalación y benchmark son consentimientos independientes.
2. `execution_authorized` solo tras consentimiento positivo y estados previos.
3. Una evidencia histórica no satisface una nueva medición.
4. Sin runtime/artefacto disponible → `benchmark_blocked`, nunca MEASURED inventado.
5. UI: **un idioma por sesión** (RC2-K). No se muestran ES+EN+ZH en cada línea.

## Criterio de cierre

El recorrido lógico llega al punto en que RC1 toma el control. La validación física debe hacerse en host real.
