# LLM Smoke Test — esquema de resultados v0.1

## Estado

**Experimental / schema v0.1**.

Este esquema define la forma común de comunicar resultados entre el núcleo del test y los adaptadores de runtimes locales. No convierte por sí mismo el test en un benchmark oficial.

## Principios

- Un resultado debe poder reproducirse y auditarse.
- El runtime y el modelo son identificados explícitamente.
- Las métricas se distinguen de la configuración.
- Los valores desconocidos se representan como `null`, no como cero.
- El test no debe inventar métricas que el runtime no proporcione.
- Los tiempos deben expresarse en milisegundos y los caudales en tokens/segundo.
- El resultado debe ser JSON válido y versionado.

## Estructura canónica

```json
{
  "schema_version": "0.1",
  "test": {
    "name": "llm-smoke-test",
    "mode": "experimental"
  },
  "timestamp": "2026-08-16T00:00:00Z",
  "model": {
    "id": "string",
    "revision": null,
    "parameter_count": null,
    "quantization": null,
    "context_length": null
  },
  "runtime": {
    "name": "string",
    "version": null,
    "adapter": "string"
  },
  "hardware": {
    "os": "string",
    "architecture": "string",
    "cpu": "string",
    "ram_bytes": null,
    "gpu": null,
    "vram_bytes": null
  },
  "configuration": {
    "prompt_tokens": null,
    "requested_new_tokens": null,
    "temperature": null,
    "seed": null,
    "batch_size": null,
    "context_tokens": null
  },
  "warmup": {
    "enabled": false,
    "runs": 0
  },
  "repetitions": 1,
  "metrics": {
    "ttft_ms": null,
    "generation_ms": null,
    "total_ms": null,
    "prompt_tokens": null,
    "generated_tokens": null,
    "tokens_per_second": null,
    "peak_ram_bytes": null,
    "peak_vram_bytes": null
  },
  "result": {
    "status": "ok",
    "error": null
  }
}
```

## Métricas

### TTFT

`ttft_ms` = tiempo desde el inicio efectivo de generación hasta la disponibilidad del primer token, si el runtime permite medirlo.

Si no puede medirse, `null`.

### Generation time

`generation_ms` = tiempo dedicado a generar los tokens de salida, cuando el runtime permite separarlo del resto.

### Total time

`total_ms` = duración total de la operación medida por el adaptador.

### Tokens/s

`tokens_per_second` debe calcularse únicamente cuando el número de tokens generados y el tiempo de generación sean conocidos y compatibles.

No se debe calcular automáticamente a partir de `total_ms` si el tiempo incluye carga del modelo, salvo que el resultado lo marque expresamente como una métrica diferente.

### Memoria

`peak_ram_bytes` y `peak_vram_bytes` son opcionales. Sólo deben rellenarse con una medición real o una fuente explícita del runtime.

## Warm-up

El warm-up debe distinguirse de las mediciones.

```text
carga modelo
    ↓
warm-up (no medido como benchmark)
    ↓
repeticiones medidas
    ↓
resultados
```

La v0.1 permite `warmup.enabled=false` porque el núcleo todavía es experimental.

## Repeticiones

`repetitions` indica cuántas ejecuciones medidas se realizaron.

Cuando haya más de una repetición, los adaptadores deberán conservar los resultados individuales en una versión posterior del esquema o generar agregados documentados. La v0.1 no prescribe todavía una política estadística definitiva.

## Estado

`result.status` puede ser:

- `ok`
- `error`
- `partial`

`partial` significa que la prueba terminó pero alguna métrica disponible no pudo obtenerse.

## Qué NO define v0.1

Este esquema no fija todavía:

- benchmark oficial de LEONES;
- prompts universales;
- conjunto de modelos de referencia;
- número definitivo de repeticiones;
- intervalos de confianza;
- criterios de exclusión;
- puntuación agregada;
- ranking de modelos;
- comparación estadística entre máquinas.

Esas decisiones pertenecen a una metodología de benchmark posterior.
