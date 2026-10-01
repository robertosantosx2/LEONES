# Propuesta de integración de TensorFold en ODS

**Línea experimental:** `ods-evolution`  
**Proyecto:** LEONES  
**Fecha:** 2026-10-01  
**Estado:** Estudio de arquitectura e integración — sin integración en producción

## 1. Resumen ejecutivo

TensorFold es un runtime especializado de inferencia local basado en motores específicos por familia de modelos, streaming con baja memoria residente, speculative decoding y verificaciones de exactitud frente a la decodificación serial del mismo motor.

El proyecto ha evolucionado de forma importante respecto al estudio inicial. Su documentación actual describe:

- ejecución MLX en Apple Silicon;
- ejecución CUDA en configuraciones NVIDIA compatibles;
- streaming de capas/tensores desde shards estándar;
- servidor compatible con OpenAI;
- motores CUDA específicos por familia;
- speculative decoding con MTP y drafters tipo DFlash;
- verificación byte-exact frente a la ejecución serial del mismo motor;
- checkpoints cuantizados de 4 bits y requisitos específicos por modelo;
- ejecución CUDA de uno o dos ranks para determinadas familias.

El papel adecuado en ODS sigue siendo:

> **runtime especializado y opcional para familias de modelos y combinaciones de hardware donde TensorFold disponga de una ruta soportada.**

Debe complementar, no sustituir, a `llama-server`.

## 2. Arquitectura actual de TensorFold

El diseño actual parte de una capa de virtualización de memoria:

```text
shards .safetensors
       ↓
manifest de TensorFold
       ↓
índice de capas / tensores
       ↓
acceso mediante mmap
       ↓
streaming según presupuesto de memoria
       ↓
motor de inferencia específico de la familia
       ↓
servidor compatible con OpenAI
```

El proyecto define el runtime como un sistema de inferencia local orientado a reducir la presión sobre la memoria residente sin modificar los pesos ni la arquitectura del transformer.

Esto encaja con la dirección de ODS de separar:

- modelo;
- hardware;
- estrategia de memoria/almacenamiento;
- capacidades de ejecución;
- runtime concreto.

## 3. Rutas de ejecución actuales

La documentación actual describe dos grandes rutas de hardware.

### Apple Silicon / MLX

TensorFold puede hacer streaming de checkpoints compatibles mediante MLX, conservando solo las capas y tensores fijados necesarios dentro de un presupuesto de memoria residente.

### NVIDIA / CUDA

TensorFold documenta ahora una ruta CUDA específica para varias familias, entre ellas:

- Qwen3.8-27B;
- Qwen3.8 Flash Next;
- GLM-5.3-Flash;
- familias Nemotron;
- otras recetas específicas, incluidas DeepSeek y otros checkpoints compatibles.

El soporte es **específico de familia y checkpoint**. Que exista soporte CUDA no significa que pueda cargarse cualquier modelo Hugging Face, SafeTensors, GGUF o cuantización.

El runbook NVIDIA actual utiliza un contenedor PyTorch de NVIDIA y ejecuta TensorFold dentro de él. Algunas familias CUDA usan un rank y otras requieren dos ranks y comunicación mediante NCCL.

## 4. API compatible con OpenAI

TensorFold proporciona una frontera de servicio compatible con OpenAI.

La documentación actual expone, entre otros:

```text
/v1/models
/v1/chat/completions
/v1/completions
/v1/responses
```

Esta es la principal ventaja de integración con ODS.

La frontera propuesta sería:

```text
consumidor ODS
     ↓
capa API ODS / LiteLLM
     ↓
TensorFold
     ↓
motor específico de familia
     ↓
checkpoint
```

Las aplicaciones de ODS no deberían necesitar saber si el modelo seleccionado está servido por llama-server o TensorFold.

## 5. Speculative decoding y exactitud

El speculative decoding es actualmente una parte central de TensorFold.

El runtime soporta mecanismos de generación especulativa como:

- prompt-lookup;
- cabezas MTP;
- modelos draft tipo DFlash;
- políticas específicas por familia.

La propiedad más interesante es el contrato de **exactitud dentro del mismo motor**.

TensorFold verifica los tokens propuestos contra la decodificación serial usando el mismo motor, pesos y configuración. Las recetas CUDA actuales documentan pruebas con resultados byte-identical frente a su referencia serial.

LEONES debe mantener explícita esta distinción:

```text
Exactitud de TensorFold
    =
mismo motor + mismos pesos + misma configuración

NO significa

salida de TensorFold
    =
todos los demás runtimes / cuantizaciones / hardware
```

Por tanto, los benchmarks publicados por TensorFold son **evidencia reportada**, no mediciones de LEONES.

## 6. Evidencia actual de rendimiento

Las recetas CUDA actuales de TensorFold publican mediciones realizadas sobre hardware NVIDIA DGX Spark / GB10.

Por ejemplo, documentan comparaciones de varios múltiplos frente a vLLM para determinadas cargas Qwen3.8 y GLM-5.3-Flash, además de verificar que la generación especulativa mantiene resultados byte-identical respecto a la referencia serial de TensorFold.

Estas cifras son útiles para valorar el potencial arquitectónico del runtime, pero no deben trasladarse como rendimiento esperado a una RTX 3050 ni a otra GPU.

LEONES debe registrarlas como:

```text
fuente = proyecto TensorFold
evidencia = reportada
hardware = hardware documentado por TensorFold
no es una medición de LEONES
```

## 7. Relevancia para el hardware actual de LEONES

La máquina utilizada en este estudio tiene:

```text
GPU:    NVIDIA RTX 3050 Laptop GPU
VRAM:   4 GB
RAM:    ~14 GB
CUDA:   disponible
```

Que TensorFold disponga ahora de una ruta CUDA documentada es un cambio importante: el soporte NVIDIA ya no es meramente teórico.

Sin embargo, las recetas CUDA documentadas actualmente están orientadas a sistemas NVIDIA con mucha más memoria y a combinaciones concretas de modelo/checkpoint. La documentación disponible no demuestra que esas rutas modernas quepan en una RTX 3050 Laptop de 4 GB.

Por tanto, la evidencia actual de LEONES es:

```text
relevancia arquitectónica       = alta
backend CUDA existente          = observado en la documentación
compatibilidad RTX 3050 4 GB    = no establecida
rendimiento RTX 3050            = no medido
throughput medido por LEONES    = no disponible
```

Esto es un límite de evidencia/compatibilidad, no una afirmación de que TensorFold nunca pueda ejecutarse en una NVIDIA de 4 GB.

## 8. Implicaciones para la selección de modelos en ODS

TensorFold debe representarse en el registro de capacidades de ODS como un **runtime condicional**.

Ejemplo:

```yaml
runtime:
  tensorfold:
    supported: conditional
    backends:
      - mlx
      - cuda
    api:
      openai_compatible: true
    capabilities:
      tensor_streaming: true
      speculative_decoding: true
      exact_same_engine_verification: true
    constraints:
      model_family_specific: true
      checkpoint_specific: true
      gguf: false
```

El registro debería incluir además:

- familia soportada;
- checkpoint/revisión exactos;
- cuantización;
- backend;
- requisitos de GPU;
- número de ranks;
- requisitos del modelo draft;
- límites de contexto;
- presupuesto de memoria;
- fuente y clase de evidencia.

Un modelo no debe marcarse como compatible con TensorFold solo por coincidir su nombre de arquitectura.

## 9. Diseño de integración en ODS

Una futura integración ODS podría exponer TensorFold como servicio opcional:

```text
extensions/services/tensorfold/
├── manifest.yaml
├── compose.yaml
├── Dockerfile
└── README.md
```

El servicio debería proporcionar:

- health check;
- descubrimiento mediante `/v1/models`;
- selección explícita de modelo/checkpoint;
- comprobaciones de compatibilidad con hardware;
- registro de versión de TensorFold;
- metadatos de capacidades modelo/runtime;
- routing opcional mediante LiteLLM;
- instalación explícitamente opt-in.

Dado que TensorFold utiliza kernels y requisitos específicos por familia, ODS no debería presentarlo como backend genérico.

## 10. Papel dentro del framework de ejecución de ODS

TensorFold encaja en la arquitectura adaptativa de ODS como proveedor de ejecución especializado:

```text
USUARIO / CARGA
       ↓
PERFIL DEL MODELO
       ↓
PERFIL DE HARDWARE + ALMACENAMIENTO
       ↓
REGISTRO DE CAPACIDADES ODS
       ↓
ESTRATEGIA DE EJECUCIÓN
       ↓
SELECTOR DE RUNTIME
       ↓
 ┌──────────────┬──────────────┬──────────────┐
 │ llama-server │ TensorFold   │ otros        │
 │ general      │ especializado│ runtimes     │
 └──────────────┴──────────────┴──────────────┘
       ↓
API ODS UNIFICADA
       ↓
validación LEONES
```

TensorFold refuerza así la idea de que ODS debería disponer de un selector basado en capacidades y no simplemente de una lista fija de backends intercambiables.

## 11. Relación con otras investigaciones de runtimes en LEONES

TensorFold ocupa una posición diferente de proyectos como MoE-Infinity, ramvamp, Edge0 o AirLLM.

```text
llama.cpp / llama-server
    compatibilidad amplia

ramvamp
    streaming CPU + RAM/NVMe

MoE-Infinity / WARP / otros
    offload y streaming para grandes MoE

AirLLM
    streaming de capas para Hugging Face

TensorFold
    ejecución optimizada por familia
    + streaming con baja memoria residente
    + speculative decoding
    + verificación exacta dentro del mismo motor
```

Esto hace que TensorFold sea especialmente interesante como **runtime/acelerador especializado**, no como otro backend genérico.

## 12. Qué no hacer

No:

- sustituir llama.cpp/llama-server;
- asumir que soporte CUDA implica soporte para cualquier GPU NVIDIA;
- asumir que una arquitectura es compatible sin comprobar la familia y receta exactas de TensorFold;
- tratar los resultados publicados en DGX Spark como estimaciones para la RTX 3050;
- afirmar una aceleración sin medir la misma carga en el hardware objetivo;
- interpretar la exactitud dentro del mismo motor como equivalencia entre runtimes;
- clasificar una configuración RTX 3050 no probada como `measured`.

## 13. Fases de implementación propuestas

### Fase 1 — integración de capacidades

Registrar TensorFold en ODS con restricciones explícitas de familia/checkpoint.

### Fase 2 — runtime independiente

Crear un servicio TensorFold opcional usando un modelo CUDA documentado y hardware NVIDIA adecuado.

### Fase 3 — integración API

Exponer el endpoint compatible con OpenAI mediante la capa API/LiteLLM de ODS.

### Fase 4 — admisión hardware/modelo

Hacer que ODS rechace o rebaje candidatos cuando no encajen la VRAM, topología de ranks, contexto o requisitos del checkpoint detectados.

### Fase 5 — adaptador de benchmark LEONES

Registrar:

- modelo/revisión exactos;
- formato y cuantización;
- versión de TensorFold;
- GPU/VRAM;
- contexto;
- configuración draft;
- TTFT;
- procesamiento del prompt;
- tok/s de generación;
- VRAM máxima;
- RAM máxima;
- equivalencia entre salida serial y especulativa.

### Fase 6 — validación comparativa

Cuando el mismo modelo/checkpoint sea compatible con ambos runtimes, comparar TensorFold con llama.cpp u otro runtime de ODS bajo condiciones idénticas.

## 14. Reglas de benchmark y evidencia

Para cada resultado TensorFold, LEONES debe distinguir:

```text
REPORTED
  resultado publicado por TensorFold.

OBSERVED
  capacidad o comportamiento comprobado en repositorio/runbook.

ESTIMATED
  inferencia de compatibilidad antes de ejecutar.

MEASURED
  resultado producido realmente por LEONES en la máquina objetivo.
```

Solo la última categoría debe utilizarse para afirmar rendimiento, latencia o consumo real en la RTX 3050.

## 15. Conclusión actualizada

TensorFold es ahora un candidato de integración ODS bastante más relevante que en el estudio inicial.

El cambio importante no es únicamente la existencia de CUDA: TensorFold documenta ahora un conjunto creciente de **motores CUDA específicos por familia, recetas de modelos, rutas de speculative decoding y pruebas de exactitud**, además de su arquitectura de streaming MLX.

Para ODS, la posición resultante es:

> **TensorFold debe mantenerse como runtime experimental especializado y seleccionado por capacidades, con especial interés para las familias CUDA soportadas y con admisión estricta de checkpoint y hardware.**

Para la RTX 3050 de 4 GB utilizada por LEONES:

> **No debe hacerse ninguna afirmación de compatibilidad o rendimiento hasta que un checkpoint documentadamente soportado pueda ser admitido y medido realmente.**

Esto mantiene la integración alineada con el principio de LEONES:

```text
DESCUBRIMIENTO
   ↓
PERFIL
   ↓
CANDIDATOS
   ↓
CONSENTIMIENTO
   ↓
INSTALACIÓN
   ↓
VERIFICACIÓN FÍSICA
   ↓
BENCHMARK
   ↓
MEDICIÓN
   ↓
EVIDENCIA
```

**Prioridad actual de integración:** investigación experimental P2/P3, con posibilidad de aumentar la prioridad si aparece un checkpoint CUDA pequeño soportado para hardware NVIDIA de baja VRAM.

## Referencias

- https://github.com/ashhart/TensorFold
- https://github.com/ashhart/TensorFold/blob/main/RUNBOOK.md
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/cuda.md
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash.md
