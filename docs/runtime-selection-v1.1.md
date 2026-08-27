# runtime-selection.v1.1

V1.1 extends LEONES runtimes without changing the V1 evidence contract.

## Architecture

```text
selector
   ↓
runtime-selection.v1.1
   ↓
runtime registry + capability match
   ↓
trusted adapter
   ↓
runner
   ↓
runtime-benchmark.v1
   ↓
evidence / Router
```

## Boundary rules

1. The selector produces a declarative selection plan.
2. The selector MUST NOT contain runtime commands, argv, shell snippets or executable paths.
3. A registry descriptor declares capabilities; it does not prove execution availability.
4. A trusted adapter converts a validated selection plan into runtime-specific execution details.
5. Runtime-specific execution details MUST NOT be treated as benchmark evidence.
6. `runtime-benchmark.v1` is the only layer that may produce a runtime performance measurement.
7. `estimated_tps` is an estimate and MUST remain distinct from `measured_tps`.
8. Runtime-specific gates, such as FreeToken's eligibility gate, remain authoritative for that runtime.

## Initial registry

The initial V1.1 registry declares the intended runtime surface in implementation order:

- llama.cpp — canonical reference
- Ollama
- FreeToken — gated
- AirLLM

The remaining runtimes are added only after the preceding adapter/contract step is validated.

## Compatibility

The V1 evidence contract is unchanged. V1.1 adds a new selection/runtime boundary around it; it does not redefine evidence provenance, measurement semantics, or Router behavior.
