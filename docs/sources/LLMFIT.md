# LLMFit en LEONES

## Papel

[LLMFit](https://www.llmfit.org/) se incorpora a LEONES como **preselector de hardware/modelo**. Reduce el espacio de búsqueda antes de consultar la evidencia canónica de Atlas y antes de ejecutar mediciones propias.

LLMFit detecta CPU, RAM, GPU/VRAM y runtimes disponibles, y proporciona recomendaciones y planificación orientadas a hardware. Su salida sigue siendo una **estimación externa**: no se convierte automáticamente en una medición LEONES.

## Arquitectura

```text
INTENCIÓN DEL USUARIO
        ↓
HARDWARE LOCAL
        ↓
LLMFIT: fit / recommend / plan
        ↓
CANDIDATOS
        ↓
ATLAS: identidad + evidencia
        ↓
CABE/RULA + rendimiento medido LEONES
        ↓
ODS / Magnitude / runtime
        ↓
Harness (Buddy / DeepSeek Harness / otros)
        ↓
Benchmark y resultado LEONES
```

## Reglas

1. `llmfit` no publica directamente en el Atlas canónico.
2. `estimated_tps` es estimación; `measured_tps` es medición.
3. Una medición LEONES de la misma configuración tiene prioridad sobre la estimación.
4. El hardware debe conservar CPU, núcleos, RAM total/disponible, GPU, memoria compartida/dedicada y backend detectado.
5. La disponibilidad de un runtime forma parte de la compatibilidad, no de la calidad del modelo.
6. El contexto usado para estimar memoria debe quedar registrado.
7. `fit_level` no sustituye a CABE/RULA.
8. Los modelos descartados por backend incompatible se conservan como diagnóstico, pero no se recomiendan.
9. Para automatización se prefieren salidas JSON/API frente al scraping de la TUI.

## Contrato normalizado

```text
source
source_version
observed_at
hardware
runtime
model_id
provider
params
quantization
context
fit_level
estimated_tps
measured_tps
memory_required_gb
estimate_basis
verify_command
use_case
raw_reference
```

## Política del Router

El Router de LEONES aplica:

1. restricciones duras de hardware/OS/backend;
2. identidad y evidencia Atlas;
3. caso de uso;
4. política de apertura/JGB;
5. estimación LLMFit;
6. mediciones LEONES existentes;
7. CABE/RULA;
8. compatibilidad con ODS/Magnitude/runtime/harness;
9. preferencias del usuario: calidad, latencia, privacidad, coste y contexto.

LLMFit es la **primera criba cuantitativa**, no el juez final.

## Integración reproducible

El código upstream está fijado como submódulo en `subprojects/LLMFit`. LEONES mantiene sus adaptadores fuera del submódulo para evitar modificar el upstream.

Upstream: https://github.com/AlexsJones/llmfit

Revisión fijada inicialmente: `70fea7d2eb42d887700cb5d146879f463f37fc98`.

## Validación empírica

La campaña de calibración compara:

```text
LLMFIT estimated_tps
        vs
LEONES measured_tps
        ↓
error / ratio de calibración
```

Una medición debe conservar hardware, runtime, versión, cuantización, contexto, TTFT si está disponible, tok/s y estabilidad.
