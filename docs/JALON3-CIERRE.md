# JALÓN 3 — Cierre

## Estado

**CERRADO como contrato operativo y primera ejecución física reproducible.**

JALÓN 3 fija el contrato `runtime-benchmark-evidence.v1.1`, el harness de ejecución, la conservación de stdout/stderr, el control de timeout, el inventario de hardware, el hash SHA-256 del artefacto y el resumen estadístico de las mediciones.

## Evidencia física

- Runtime: `llama.cpp` / `llama-cli` Debian.
- Modelo: `Qwen3-0.6B-Q4_K_M.gguf`.
- Backend: CPU.
- Contexto: 2048.
- Warm-up: 1.
- Iteraciones medidas: 3.
- Temperatura: 0.
- Top-p: 1.
- Seed: 42.
- Protocolo: `concise-paragraph-v1`.
- Evidencia: `artifacts/evidence/jalon3-qwen3-0.6b.json`.
- Execution ID: `rt-f0fc48e140e84bbda20d4939ed4770fd`.

Resultados agregados conservados en la evidencia:

| Métrica | Media | Mediana | Mín. | Máx. |
|---|---:|---:|---:|---:|
| TTFT / first-output proxy (ms) | 1068.52 | 1112.52 | 965.85 | 1127.19 |
| Generación (ms) | 3756.67 | 3613.00 | 3483.59 | 4173.42 |
| Tokens/s | 35.87 | 37.00 | 32.10 | 38.50 |
| Tiempo total (ms) | 4825.19 | 4740.19 | 4449.44 | 5285.95 |
| Memoria pico (MB) | 866.71 | 866.79 | 866.55 | 866.79 |

## Gate de calidad

- Suite completa: **262 tests pasan**.
- `git diff --check`: limpio.
- Evidencia JSON: parseable.
- Evidencia incluida explícitamente pese a `artifacts/` ignorado.
- Rama: `jalon3-runtime-execution-contract-v3`.
- Commit de cierre físico: `bc4bc5b`.
- Rama remota sincronizada.
- Árbol de trabajo local limpio en la ejecución de cierre.

## Interpretación

`ttft_ms` es actualmente un **proxy de first-output** del proceso CLI: el harness mide la primera línea no vacía recibida por stdout. No debe presentarse como TTFT de primer token a nivel de protocolo de streaming hasta disponer de un camino de salida que permita aislar inequívocamente el primer token generado.

La evidencia de JALÓN 3 es, por tanto, evidencia válida de ejecución física, latencia de primera salida, generación y throughput del CLI bajo el protocolo fijado; la semántica estricta de TTFT queda expresamente delimitada para una futura versión del protocolo.

## Regla de continuidad

No se rediseña `runtime-benchmark-evidence.v1.1` durante JALÓN 4. Las nuevas plataformas/runtimes deben adaptarse al contrato ya cerrado y producir evidencia compatible.

La siguiente fase puede centrarse en **JALÓN 4: expansión de runtimes/adapters y selección**, manteniendo la ejecución física como una capa posterior y separada.
