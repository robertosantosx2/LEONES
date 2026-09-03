# RC2-F — Benchmark Consent and Execution Contract

**Estado:** 🟢 Contrato fijado

## Objetivo

Permitir que el beta tester decida explícitamente si quiere ejecutar un **benchmark A01 real** después de verificar el stack y resolver el runtime del modelo.

## Benchmark canónico

| Campo | Valor |
|-------|--------|
| id | `LEONES-Agentic` |
| task | `A01` |
| prompt | `Execute A01. Return only JSONL tool calls.` |
| métricas | `wall_seconds`, `measured_tps`, `grader_pass` |
| runner | RC1 `scripts/a01_runtime_benchmark.py` |
| puentes | `ollama_a01_runtime.py`, `llama_cpp_a01_runtime.py` |

## Flujo

```text
READY_FOR_BENCHMARK
        ↓
 resolución modelo → runtime
        ↓
 preflight runtime/artefacto
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

## Reglas

1. No ejecutar benchmark por defecto.
2. Instalar ≠ verificar ≠ resolver runtime ≠ autorizar benchmark.
3. GGUF/HF id no se trata como nombre Ollama.
4. Sin runtime/artefacto → `benchmark_blocked`, no MEASURED inventado.
5. Conservar `execution_id` y evidencia cuando la medición sea real.
6. Un fallo no se publica como medición válida.

Relacionado: `RC2-J-BENCHMARK-HANDOFF.md`, `RC2-L-INTEGRATED-BETA-JOURNEY.md`, `RC2-K-MULTILINGUAL-UI.md`.
