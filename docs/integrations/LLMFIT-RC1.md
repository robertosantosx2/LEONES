# LLMFit ↔ LEONES — contrato RC1

> **Estado: congelado para RC1**

## Propósito

LLMFit se utiliza como **estimador inicial de encaje modelo ↔ hardware**. No es el benchmark de LEONES, no sustituye Atlas y no decide por sí solo la recomendación final.

Referencia upstream: [AlexsJones/llmfit](https://github.com/AlexsJones/llmfit).

## Responsabilidades

### LLMFit

- analizar hardware/modelo según sus propios criterios;
- producir candidatos y señales de fit;
- aportar estimaciones como `estimated_tps` u otros datos disponibles;
- permitir reducir el espacio de búsqueda antes de una ejecución costosa.

### LEONES

- conservar procedencia;
- normalizar la salida;
- cruzarla con Atlas y evidencia;
- aplicar workload, runtime, contexto y memoria;
- generar el plan autorizado;
- ejecutar mediante el runtime elegido;
- medir físicamente;
- validar y publicar evidencia.

## Contrato de datos

El adaptador de LEONES conserva al menos:

```text
source
observed_at
hardware
model_id
provider
params
quantization
context
fit_level
estimated_tps
measured_tps = null
memory_required_gb
run_mode
runtime
quality_score
estimate_basis
raw
```

La presencia de `estimated_tps` no permite rellenar `measured_tps`.

## Flujo

```text
hardware real o perfil declarado
          ↓
       LLMFit
          ↓
  candidatos / fit estimado
          ↓
   adaptador LEONES
          ↓
 Atlas + evidencia + restricciones
          ↓
   selector LEONES
          ↓
 plan autorizado
          ↓
 ODS / Magnitude / runtime
          ↓
 ejecución física
          ↓
 benchmark LEONES
          ↓
 measured_tps
```

## Regla de promoción

```text
LLMFit estimate
     │
     │ nunca automáticamente
     ▼
LEONES physical execution
     │
     ▼
measured evidence
```

Un resultado de LLMFit puede ayudar a **descartar o priorizar**, pero no puede convertirse por sí mismo en evidencia medida.

## Hardware

Para RC1 el foco está en hardware de consumo:

- CPU-only;
- iGPU;
- GPU de consumo;
- 8/16/32/64 GB de RAM;
- 0/4/8/12/16+ GB de VRAM cuando corresponda.

Los tiers son una herramienta de clasificación. El hardware observado en la ejecución física es la fuente de verdad para el benchmark.

## Integración existente

LEONES ya contiene:

- `automation/discovery/llmfit_adapter.py`: normalización y ejecución opcional de LLMFit;
- `scripts/llmfit_to_recommendation_candidates.py`: puente hacia el selector;
- `tests/test_llmfit_to_recommendation_candidates.py`: protección contractual de la frontera estimate/measured.

## Gates

### Gate A — Normalización

Una salida válida de LLMFit se convierte en el formato común sin inventar campos.

### Gate B — Provenance

La fuente sigue identificada como `llmfit`.

### Gate C — No contaminación

`measured_tps` permanece `null` hasta que exista una medición LEONES.

### Gate D — Decisión

El selector puede combinar LLMFit con Atlas, hardware, runtime y restricciones.

### Gate E — Realidad

Una ejecución física puede confirmar, matizar o contradecir el fit.

## Próxima prueba física

No se requiere todavía. Antes de Ubuntu deben estar cerrados:

1. contrato de entrada;
2. perfil/tier de hardware;
3. ejecutor elegido (ODS o Magnitude);
4. protocolo de benchmark;
5. artefactos de evidencia.

Solo entonces se utilizará Ubuntu para demostrar el comportamiento físico.
