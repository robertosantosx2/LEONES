# LLM-Hardware-Advisor

## 1. Identidad y procedencia
- **Fuente primaria:** https://github.com/gitstq/LLM-Hardware-Advisor
- **Capa LEONES:** preselector hardware-aware.
- **Licencia declarada:** MIT.
- **Estado LEONES:** `research-candidate`.
- **Revisión:** 2026-08-25.

La fuente actual declara Python 3.9+, funcionamiento en Windows/macOS/Linux, modo CPU-only, 66+ modelos integrados y 61 tests. También declara soporte para NVIDIA, AMD, Apple Silicon e Intel Arc. fileciteturn20file0

## 2. Qué es
CLI que intenta responder: **«¿qué LLM local tiene sentido en esta máquina?»**. Detecta hardware, estima memoria para distintas cuantizaciones, calcula un fitness score y devuelve recomendaciones y comandos para Ollama/llama.cpp.

La detección contempla CPU, GPU, RAM, disco y sistema operativo. La fuente enumera `nvidia-smi`, `rocm-smi`, `system_profiler` y `lspci` como mecanismos de detección según plataforma. fileciteturn20file0

## 3. Qué problema resuelve
Reduce el espacio de búsqueda antes de descargar o ejecutar modelos. Su diferencia importante frente a un simple calculador de VRAM es que combina:

- hardware detectado;
- modelo del catálogo;
- cuantización;
- longitud de contexto;
- fitness;
- categoría de uso;
- comando de ejecución.

## 4. Arquitectura funcional

```text
hardware detection
       ↓
model database
       ↓
VRAM / memory estimate
       ↓
fitness score 0–100
       ↓
quantization + context
       ↓
ranked recommendation
       ↓
Ollama / llama.cpp command
```

El proyecto es deliberadamente **offline-first**: el catálogo integrado permite recomendaciones sin red, mientras que la hoja de ruta contempla sincronización online con Hugging Face. fileciteturn20file0

## 5. Evidencia primaria
La fuente declara:

- 66+ modelos en la base integrada;
- scoring 0–100 basado en VRAM, cuantización y contexto;
- INT4, INT8 y FP16;
- exportación JSON/Markdown;
- comandos Ollama y llama.cpp;
- 61 tests;
- soporte CPU-only y varias familias de GPU. fileciteturn20file0

Estos datos son **claims de la fuente**, no mediciones LEONES.

## 6. Estimación
El núcleo de interés para LEONES es la estimación de memoria y fitness. La documentación explica que calcula requisitos de VRAM para cada modelo/cuanti y puntúa según utilización de VRAM, calidad de cuantización y soporte de contexto. fileciteturn20file0

Por tanto, LEONES debe conservar campos como:

```text
advisor_memory_estimate
advisor_fitness
advisor_quantization
advisor_context
advisor_category
advisor_runtime
advisor_version
```

Nunca convertir `fitness` en `measured_tps`.

## 7. Cuantización
La fuente presenta FP16, INT8 e INT4 como estrategias con diferentes compromisos de memoria, calidad y velocidad. Es una simplificación útil para la preselección, pero LEONES debe permitir granularidad superior cuando el runtime/modelo lo requiera: GGUF Q4/Q5/Q6/Q8, GPTQ, AWQ, FP8, etc. fileciteturn20file0

## 8. Workload
Admite categorías como `general`, `coding`, `math`, `reasoning` y `chat`. Esto es importante porque introduce una dimensión semántica que el mero fit de memoria no cubre. fileciteturn20file0

Para LEONES, la categoría externa debe convertirse en **señal de prospección**, no en decisión final. El Router debe cruzarla con la intención canónica del usuario y con evidencia de calidad.

## 9. Relación con LLMFit
Ambos atacan el mismo espacio, pero LEONES debe mantenerlos independientes:

| Dimensión | LLM-Hardware-Advisor | LLMFit | LEONES |
|---|---|---|---|
| Detección hardware | Sí | Sí | Sí/por perfil |
| RAM | Sí | Sí | Sí |
| GPU/VRAM | Sí | Sí | Sí |
| Disco | **Sí** | según backend | **Sí** |
| Cuantización | Sí | Sí | Sí |
| Contexto | Sí | Sí | Sí |
| Score externo | Sí | Sí | **no heredar** |
| Rendimiento medido | roadmap | evidencia externa/propia separada | **canónico** |
| Runtime | Ollama/llama.cpp | varios | `runtime-selection.v1` |

El valor está en la **triangulación**, no en escoger arbitrariamente uno como autoridad.

## 10. Relación con CanIRun.ai
CanIRun.ai aporta detección directa desde navegador; Hardware Advisor aporta una CLI local más explícita y un catálogo offline. La comparación permite estudiar qué parte del hardware debe ser detectada automáticamente y cuál debe permanecer como perfil declarativo.

## 11. Medición LEONES
**Actualmente: ninguna.**

La propia hoja de ruta de la fuente identifica benchmark GPU real como trabajo futuro. fileciteturn20file0

La prueba LEONES debe fijar:

```text
hardware
model_id exacto
quantization exacta
runtime + versión
context
prompt/workload
warmup
TTFT
TPOT/tok/s
RAM
VRAM
I/O
resultado funcional
```

## 12. Valor para LEONES
Muy alto como **generador de candidatos**. Su inclusión de RAM y disco es particularmente interesante para nuestra capa de hardware porque evita reducir el fit a VRAM.

Puede alimentar:

```text
hardware facts
      ↓
LLM-Hardware-Advisor
      ↓
external candidates
      ↓
Atlas identity/evidence
      ↓
runtime-selection.v1
      ↓
executor
```

## 13. Limitaciones
1. Catálogo integrado potencialmente obsoleto.
2. Fitness dependiente de los supuestos de la herramienta.
3. Tres niveles de cuantización no cubren todos los runtimes.
4. Fit no demuestra rendimiento.
5. Fit no demuestra calidad funcional.
6. El roadmap declara benchmark real como pendiente. fileciteturn20file0

## 14. Reutilización LEONES
No copiar código ni score al núcleo. Usarlo como fuente externa mediante un adaptador que preserve:

- versión;
- entrada hardware;
- candidato;
- score;
- estimación;
- procedencia.

## 15. Clasificación
**`research-candidate` → preselector potencial.**

No pasa a `measured` por sus propios tests ni por sus estimaciones.

## 16. Próximo paso
Construir un **caso común de cross-validation** con LLMFit, CanIRun.ai, localmodel.run y VRAMBudget sobre 5–10 combinaciones hardware/modelo. Las discrepancias deben generar casos de prueba, no promedios arbitrarios.