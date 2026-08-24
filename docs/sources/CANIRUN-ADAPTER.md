# CanIRun.ai adapter — preselector/cross-validator LEONES

**Fuente:** CanIRun.ai / GitHub midudev/canirun.ai  
**Tipo:** adaptador de estimación externa  
**Estado:** diseño inicial integrado en conocimiento  

## Propósito

CanIRun.ai debe entrar en LEONES como **segundo estimador independiente** de compatibilidad hardware ↔ modelo. No sustituye a LLMFit, al Atlas, al Router ni a las mediciones físicas.

La fuente expone un catálogo de modelos y una API de compatibilidad/recomendación. Su motor utiliza perfil de hardware, requisitos por cuantización y señales de velocidad/memoria para producir una evaluación S–F. Estas señales son externas y deben conservarse como `estimated`.

## Contrato normalizado propuesto

Entrada:

```json
{
  "hardware": {
    "ram_gb": 32,
    "gpu": {
      "name": "NVIDIA RTX 3060",
      "vram_gb": 12,
      "memory_bandwidth_gbps": null
    },
    "cpu": null,
    "os": "debian"
  },
  "intent": {
    "use_case": "coding",
    "context_tokens": null,
    "min_tps": null
  },
  "model": {
    "id": "llama3.1-8b",
    "quantization": "Q4_K_M"
  }
}
```

Salida LEONES:

```json
{
  "source": "canirun",
  "source_version": null,
  "model_id": "llama3.1-8b",
  "quantization": "Q4_K_M",
  "fit": "estimated",
  "grade": "S-F",
  "estimated_tps": null,
  "estimated_memory_gb": null,
  "memory_headroom_gb": null,
  "runtime": null,
  "evidence_status": "unknown",
  "measured_tps": null,
  "measurement_status": "not-measured"
}
```

Los nombres concretos deben ajustarse al contrato ejecutable vigente de candidatos antes de conectarlo al Router.

## Regla de separación

Nunca sobrescribir:

- `measured_tps` con `estimated_tps`;
- CABE/RULA con la nota S–F;
- evidencia Atlas con datos del catálogo de CanIRun;
- decisión final LEONES con la recomendación externa.

## Arquitectura

```text
hardware + intent
       │
       ├──────────────┐
       ↓              ↓
    LLMFit         CanIRun
       │              │
       └──────┬───────┘
              ↓
      candidate-normalizer
              ↓
       Atlas / evidence
              ↓
     runtime-selection.v1
              ↓
          executor
              ↓
           grader
              ↓
        measurement
```

## Uso previsto

1. LLMFit produce la primera shortlist.
2. CanIRun aporta una segunda estimación independiente.
3. El normalizador conserva ambas sin mezclarlas.
4. El selector elimina candidatos sin identidad/evidencia suficiente.
5. `runtime-selection.v1` elige candidatos ejecutables.
6. El benchmark físico produce `measured_*`.
7. LEONES compara predicción vs realidad para evaluar el error de ambos estimadores.

## Cross-validation

Para cada candidato se podrá calcular posteriormente, sin convertirlo en score soberano:

```text
prediction_delta_tps
prediction_delta_memory
fit_agreement
quantization_agreement
runtime_agreement
```

Estos campos sirven para evaluar la fiabilidad de los estimadores, no para alterar sus datos originales.

## Fuente y límites

CanIRun declara detección de hardware desde navegador y cálculo de requisitos en varias cuantizaciones; también ofrece endpoints `/api/models`, `/api/models/:id`, `/api/compatibility` y `/api/recommend`. Sus velocidades son estimaciones y la propia web advierte que las especificaciones reales pueden variar. Por ello LEONES debe tratarlo como **estimador externo** y no como benchmark.

## Siguiente implementación

- crear módulo ejecutable `canirun_adapter`;
- definir schema de entrada/salida contra el contrato real `runtime-selection.v1`;
- añadir fixtures de respuestas API;
- tests de contrato;
- test de fallo/timeout/API no disponible;
- integrar junto a LLMFit en la fase de preselección;
- registrar versión/fecha de la estimación;
- añadir comparación automática posterior contra `measured_tps`.
