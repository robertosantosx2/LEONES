# RC2-F — Benchmark Consent and Execution Contract

**Estado:** 🟢 Contrato fijado

## Objetivo

Permitir que el beta tester decida explícitamente si quiere ejecutar un **benchmark A01 real** después de instalar y verificar el stack elegido.

## Benchmark canónico

| Campo | Valor |
|-------|--------|
| id | `LEONES-Agentic` |
| task | `A01` |
| prompt | `Execute A01. Return only JSONL tool calls.` |
| métricas | `wall_seconds`, `measured_tps`, `grader_pass` |
| runner | RC1 `scripts/a01_runtime_benchmark.py` |
| puente local | `scripts/ollama_a01_runtime.py` (requiere Ollama) |

## Flujo

```text
READY_FOR_BENCHMARK
        ↓
 explicación A01
        ↓
 consentimiento explícito
     ┌──┴──┐
    NO     SÍ
    ↓       ↓
   FIN    EXECUTION_AUTHORIZED
             ↓
          RC1 A01
             ↓
        measurement / evidence
```

## Antes de preguntar

LEONES debe explicar:

- qué tarea A01 se ejecutará;
- qué métricas se medirán;
- diferencia ESTIMATED vs MEASURED;
- modelo seleccionado;
- runtime previsto (Ollama local cuando esté disponible);
- que cancelar no invalida la instalación;
- que sin Ollama la ejecución queda bloqueada, no inventada.

## Respuestas

- `benchmark_declined`
- `benchmark_authorized`
- `benchmark_blocked` (p. ej. sin Ollama)
- `benchmark_completed` (medición válida + evidence)
- `benchmark_failed` (intento sin resultado válido)

## Reglas

1. No ejecutar benchmark por defecto.
2. Instalar ≠ autorizar benchmark.
3. Solo sobre plan autorizado y stack verificado.
4. Conservar `execution_id`, timestamps, modelo, runtime y evidencia.
5. Un fallo no se publica como medición válida.
6. Las estimaciones LLMFit permanecen diferenciadas.

Relacionado: `docs/RC2-J-BENCHMARK-CONSENT.md` (handoff RC1), `docs/RC2-L-INTEGRATED-BETA-JOURNEY.md` (operador).
