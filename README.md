# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open, autónoma y local para hardware de consumo.**

[🌐 **Web de LEONES y dashboard metaLEONES**](https://robertosantosx2.github.io/LEONES/)

LEONES construye una plataforma capaz de **descubrir, preparar, ejecutar, evaluar y optimizar modelos locales** según la tarea y el hardware disponible.

## Arquitectura LEONES 0.2 — CONGELADA

La arquitectura principal queda definida por estos componentes:

- **Leones Atlas** — conocimiento estructurado de modelos, hardware, runtimes, cuantizaciones y benchmarks.
- **Leones Router** — selecciona modelo, versión, cuantización, backend, dispositivo y configuración.
- **Leones Agents** — planificación, herramientas, memoria, RAG, workflows y agentes especializados.
- **Leones Runtime** — ejecución autónoma y abstracción de backends locales.
- **Leones Quant** — evaluación y asistencia a cuantización.
- **Leones Fine-Tuning** — asistencia y ejecución de adaptación de modelos, incluyendo LoRA/QLoRA cuando sea viable.
- **Benchmark & Evaluation** — medición reproducible de inferencia y tareas agentic; retroalimenta Atlas y Router.

La especificación congelada está en [`docs/LEONES_ARCHITECTURE_0.2.md`](docs/LEONES_ARCHITECTURE_0.2.md).

## Independencia de motores

LEONES **no depende de Unsloth Desktop** ni de ningún producto concreto. Los motores son adaptadores intercambiables. Entre los backends candidatos están llama.cpp, KTransformers, Unsloth, Ollama, vLLM, MLX, TensorRT-LLM y otros que aporten valor experimental.

Unsloth no es un componente principal de LEONES.

## Hardware objetivo

**8, 16, 32 y 64 GB de RAM**, con Intel i5/i7 o equivalentes, con o sin GPU. También se investigarán NPU y técnicas de offloading cuando sean relevantes.

## Principios fijados

- **Libre** se usa deliberadamente frente a «free»: interesa la libertad del software, no su precio.
- Se descarta lo que no sea Open y se prioriza especialmente **Copyleft**.
- **Buddy (GPL-3.0)** sigue siendo una pieza central de la pila agéntica candidata.
- **10 tok/s** es el umbral mínimo de usabilidad LEONES.
- **100 tok/s** es el techo de comparación, no un requisito universal.
- Medimos **tareas agentic**, no solo tokens por segundo.
- Los resultados oficiales deben ser mediciones propias y reproducibles.
- **metaLEONES** permite aportar resultados de hardware real mediante Markdown sin datos personales.

## Flujo autónomo

```text
TAREA
  ↓
TASK INTELLIGENCE
  ↓
HARDWARE INTELLIGENCE
  ↓
LEONES ATLAS
  ↓
LEONES ROUTER
  ↓
modelo + cuantización + backend + configuración
  ↓
LEONES RUNTIME
  ↓
EJECUCIÓN
  ↓
BENCHMARK / EVALUATION
  ↓
LEONES ATLAS
```

## LOTB

LOTB separa dos niveles:

1. **Inferencia:** modelo + backend + hardware.
2. **Agentic:** agente + herramientas + tareas.

Tareas iniciales:

- B01 — memoria/localidad
- B02 — operación sobre archivos
- B03 — tarea multietapa
- B04 — recuperación ante fallo
- B05 — coding local

Baseline inicial: **Qwen3-8B Q4_K_M GGUF**.

## metaLEONES

La comunidad puede aportar resultados técnicos al repositorio. No se publican nombres, emails, usuarios, hostnames identificables, números de serie, UUID, MAC/IP, ubicación exacta, rutas personales, credenciales ni otros datos personales.

Los resultados se clasifican como `reported`, `reproducible`, `verified` o `rejected`.

## Documento fundamental

- [`LEONES_DECISION_LOG.md`](LEONES_DECISION_LOG.md) — historia y decisiones.
- [`docs/LEONES_ARCHITECTURE_0.2.md`](docs/LEONES_ARCHITECTURE_0.2.md) — arquitectura congelada.

## Estado

**LEONES 0.2 — arquitectura congelada; implementación en marcha.**
