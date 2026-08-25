# LLMFit ↔ CanIRun ↔ medición LEONES

## Propósito

Este bloque define la comparación entre estimadores externos y la medición física de LEONES sin mezclar sus capas.

```text
LLMFit prediction ─┐
                   ├─> normalized candidate ─> runtime-selection.v1
CanIRun prediction ┘                              │
                                                 ↓
                                           real benchmark
                                                 │
                                                 ↓
                                           measured_tps
```

## Capas

| Campo | Procedencia | Papel |
|---|---|---|
| `llmfit.estimated_tps` | LLMFit | estimación externa |
| `canirun.estimated_tps` | CanIRun | estimación externa |
| `measured_tps` | benchmark LEONES | medición |
| `prediction_error_abs` | derivado LEONES | error absoluto |
| `prediction_error_pct` | derivado LEONES | error relativo |

`measured_tps` nunca se rellena a partir de LLMFit o CanIRun.

## Métricas

Para cada predicción `p` y medición `m`:

- error absoluto: `|p - m|`
- error relativo: `|p - m| / m * 100` cuando `m > 0`
- sesgo: `p - m`
- factor de predicción: `p / m` cuando `m > 0`

Los resultados deben conservar también modelo, cuantización, hardware, runtime y contexto para evitar comparar mediciones no equivalentes.

## Primera muestra

La primera muestra debe ser pequeña y reproducible. Cada fila debe contener las dos predicciones cuando estén disponibles y una medición real correspondiente. Las ausencias no se convierten en cero.

```json
{
  "model_id": "...",
  "quantization": "...",
  "runtime": "...",
  "hardware_profile_id": "...",
  "context_tokens": 4096,
  "llmfit": {"estimated_tps": null},
  "canirun": {"estimated_tps": null},
  "measured_tps": null,
  "errors": {
    "llmfit_abs": null,
    "llmfit_pct": null,
    "canirun_abs": null,
    "canirun_pct": null
  }
}
```

## Regla de decisión

Este análisis **no cambia todavía el Router**. Su objetivo inicial es medir la calidad de las predicciones. Solo después de acumular suficiente evidencia se podrá definir si una fuente merece mayor peso para una determinada familia de hardware/runtime.

## Integridad

CanIRun y LLMFit permanecen como fuentes de estimación. La medición LEONES es la referencia para evaluar ambas. No se usa la nota S–F de CanIRun como score LEONES.
