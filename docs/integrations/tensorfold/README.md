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


## 16. Actualización profunda — 2026-10-02: reevaluación de madurez

Esta sección actualiza la investigación original tras una nueva revisión de la documentación actual de TensorFold.

### 16.1 Qué ha cambiado desde la evaluación anterior

El cambio importante no es simplemente que ahora exista CUDA. TensorFold dispone actualmente de un conjunto coherente de capacidades:

- ejecución Apple Silicon / MLX;
- ejecución NVIDIA / CUDA;
- motores CUDA específicos por familia;
- recetas explícitas de modelo y checkpoint;
- ejecución CUDA de uno y dos ranks para determinadas familias;
- drafting mediante MTP, DFlash2 y prompt lookup;
- referencias seriales dentro del mismo motor;
- comprobaciones de exactitud a nivel de bits y tokens;
- admisión de contexto según memoria;
- API compatible con OpenAI;
- benchmarks CUDA documentados sobre GB10 / DGX Spark;
- notas detalladas sobre kernels, CUDA graphs, NCCL, prefix caches y migración de páginas.

La web oficial presenta actualmente TensorFold como runtime de decodificación paralela para Apple Silicon y NVIDIA con API compatible con OpenAI. El ejemplo público utiliza Nemotron 3.5 Lightning y expone la base del cliente en http://127.0.0.1:8080/v1. También publica mediciones MLX anteriores y señala explícitamente que los benchmarks de la release actual están pendientes. Esto constituye una evidencia de madurez mucho mayor que la disponible en el estudio inicial.

### 16.2 Matriz actual de capacidades CUDA

El runbook NVIDIA actual es documentación operativa, no únicamente una hoja de ruta futura. Especifica un contenedor PyTorch de NVIDIA, instalación dentro de ese entorno, comandos de serving CUDA y requisitos por familia.

| Familia | Ruta CUDA | Draft | Topología |
|---|---|---|---|
| Qwen3.8-27B | documentada | DFlash2; serial sin drafts | 1 o 2 ranks |
| Qwen3.8 Flash Next | documentada | MTP | 1 o 2 ranks |
| GLM-5.3-Flash | documentada | MTP y DFlash2 | 2 ranks |
| Nemotron | documentada | cabeza MTP incluida | 1 o 2 ranks |

Esta matriz debe interpretarse como matriz de capacidades, no como compatibilidad universal. Cada fila depende del checkpoint exacto, cuantización/layout, contexto, memoria y topología de hardware.

### 16.3 Evidencia actual de benchmarks CUDA

El recetario CUDA publica mediciones sobre hardware NVIDIA GB10 / DGX Spark:

| Carga | Resultado TensorFold frente a vLLM con MTP |
|---|---:|
| Qwen3.8-27B, 1 Spark | 2,70–3,05x |
| Qwen3.8-27B, 2 Sparks | 1,94–2,49x |
| Qwen3.8 Flash Next, 1 Spark | 1,60–1,79x |
| Qwen3.8 Flash Next, 2 Sparks | 1,74–2,24x |
| GLM-5.3-Flash, 2 Sparks | 1,78–2,06x |

Las condiciones incluyen un stream, respuestas de 64 tokens, cargas greedy y sampled y medianas sobre varias semillas. Los resultados speculative de TensorFold se contrastan con su referencia serial.

Son mediciones reportadas por el proyecto. No son mediciones de LEONES y no deben transformarse en estimaciones de rendimiento para la RTX 3050.

### 16.4 La exactitud es un contrato de ingeniería limitado

La afirmación de exactitud debe registrarse con precisión:

mismo motor TensorFold + mismos pesos + misma configuración + misma regla de sampling = resultado speculative idéntico a la referencia serial.

El recetario CUDA explica que se utilizan kernels row-invariant para que una fila verificada dentro de una ventana reciba los mismos bits que en su ejecución serial. Es un contrato interno del motor.

No establece identidad numérica entre runtimes. LEONES no debe transformar “TensorFold speculative igual a TensorFold serial” en “TensorFold igual a vLLM, llama.cpp o PyTorch estándar”.

### 16.5 La ingeniería específica por familia ya es una propiedad central

TensorFold se modela mejor como un conjunto de motores especializados detrás de una interfaz de servicio común que como un loader universal de transformers.

La receta GLM es un ejemplo claro: la implementación CUDA actual utiliza dos sistemas GB10 de 128 GB, un checkpoint 4-bit de aproximadamente 182 GB, tensor parallelism, NCCL, CUDA graphs, drafting MTP/DFlash2 y pruebas extensas de exactitud.

La receta DeepSeek-V4-Flash muestra la misma especialización en MLX: kernels específicos de familia, estructuras comprimidas/routed, lógica custom de draft/verify y contabilidad de memoria para contexto largo. Esa receta indica además que su ruta CUDA sobre dos DGX Sparks todavía no está implementada.

Por tanto, ODS debe registrar el soporte por familia independientemente del soporte general del runtime.

### 16.6 La admisión de memoria debe ser explícita

El runbook actual indica que el tamaño del fichero del modelo no equivale al footprint completo del proceso y que la admisión CUDA puede fallar cuando la memoria disponible no es suficiente. La longitud de la respuesta también necesita espacio para cachés.

Para ODS, cada candidato TensorFold debe registrar como mínimo:

- runtime;
- backend;
- familia exacta;
- checkpoint y revisión exactos;
- cuantización/layout;
- clase de GPU requerida;
- VRAM requerida y observada;
- RAM requerida y observada;
- número de ranks;
- contexto admitido;
- mecanismo de draft;
- fuente y clase de evidencia.

Un modelo no debe marcarse como compatible con TensorFold solamente por el nombre de su arquitectura.

### 16.7 RTX 3050 4 GB: frontera de evidencia actual

El objetivo actual de LEONES sigue siendo:

GPU: NVIDIA GeForce RTX 3050 Laptop GPU  
VRAM: 4 GB  
RAM del sistema: aproximadamente 14–16 GB disponibles para el entorno ODS  
Backend: NVIDIA CUDA

La evidencia actual establece:

- TensorFold CUDA existe: OBSERVED.
- Existen motores CUDA específicos por familia: OBSERVED.
- Existe serving compatible con OpenAI: OBSERVED.
- Compatibilidad RTX 3050 4 GB: NOT ESTABLISHED.
- Throughput RTX 3050: NOT MEASURED.
- Benchmark comparativo ODS/TensorFold: NOT MEASURED.

Esto no es un veredicto negativo de compatibilidad. Es una frontera de evidencia.

Aunque un checkpoint 4-bit fuese menor que 4 GB, eso no demostraría que quepa todo el proceso. También cuentan estado del runtime, KV cache, activaciones, buffers temporales, asignaciones CUDA y overhead adicional.

### 16.8 Por qué P1 está justificado aunque no exista validación RTX 3050

P1 describe prioridad de integración, no compatibilidad de hardware.

TensorFold dispone ahora de:

1. una frontera de servicio concreta;
2. una implementación CUDA real;
3. recetas reproducibles por familia;
4. una matriz de capacidades de modelo/checkpoint;
5. infraestructura de speculative decoding;
6. metodología explícita de exactitud;
7. ejecución multi-rank;
8. mediciones CUDA publicadas;
9. lógica de admisión de memoria/contexto;
10. suficiente arquitectura para justificar investigación seria de integración en ODS.

Esto es materialmente diferente de un proyecto que deba permanecer únicamente en radar.

### 16.9 Arquitectura de integración recomendada en ODS

La frontera limpia es:

ODS capability registry
→ admisión de modelo/familia
→ admisión de checkpoint
→ admisión de hardware/VRAM
→ admisión de rank/topología
→ admisión de modelo draft
→ servicio TensorFold
→ API /v1 compatible con OpenAI

Las aplicaciones ODS no deberían necesitar saber si el modelo seleccionado está servido por llama-server o TensorFold.

Una futura integración opcional podría utilizar una estructura extensions/services/tensorfold con manifest, Compose, Dockerfile, health check y documentación. El manifest debe declarar familias soportadas, restricciones de checkpoint, requisitos de memoria, topología de ranks, requisitos de draft y estado de evidencia.

ODS no debería descargar automáticamente un checkpoint grande simplemente porque TensorFold esté habilitado.

### 16.10 Flujo correcto de admisión

El flujo LEONES se mantiene:

DISCOVERY → PROFILE → CANDIDATES → CHOICE → CONSENT → INSTALL → PHYSICAL VERIFICATION → BENCHMARK → MEASUREMENT → EVIDENCE

Para TensorFold:

1. detectar el hardware;
2. leer el soporte actual de familias/checkpoints;
3. filtrar por VRAM, RAM, contexto y ranks;
4. identificar el checkpoint viable más pequeño;
5. obtener consentimiento explícito para la descarga;
6. servirlo;
7. comprobar health;
8. consultar /v1/models;
9. ejecutar una completion mínima;
10. hacer benchmark;
11. separar evidencia de estimaciones y resultados publicados por el proyecto.

### 16.11 Campos de benchmark requeridos por LEONES

Una futura prueba TensorFold debe registrar:

- versión y commit de TensorFold;
- repositorio y revisión exactos del modelo;
- ficheros y cuantización;
- modelo draft y revisión;
- GPU, VRAM, driver y CUDA;
- CPU y RAM;
- imagen del contenedor;
- versión de Python;
- argumentos de lanzamiento;
- ranks y configuración NCCL;
- contexto;
- tiempo de compilación de kernels;
- tiempo de carga;
- TTFT;
- tok/s de prompt;
- tok/s de generación;
- VRAM máxima;
- RAM máxima;
- tasa de aceptación y commit speculative;
- token IDs o hashes serial frente a speculative;
- estabilidad entre ejecuciones;
- comportamiento con prompts largos.

Si el mismo modelo/checkpoint funciona en otro runtime ODS, la comparación debe usar el mismo hardware, revisión, prompts, contexto, configuración de generación y protocolo de repetición.

### 16.12 Taxonomía de evidencia

LEONES debe conservar cuatro clases:

- REPORTED — publicado por TensorFold;
- OBSERVED — verificado en source o runbook;
- ESTIMATED — inferido antes de ejecutar;
- MEASURED — producido por LEONES en el hardware objetivo.

Solo MEASURED puede establecer el rendimiento real de la RTX 3050.

### 16.13 Salvedad sobre madurez documental

Existe una separación importante en la documentación pública actual.

El README raíz sigue centrado en el fundamento V0/V1 de virtualización de memoria y streaming MLX. El RUNBOOK y las recetas CUDA contienen ahora instrucciones operativas NVIDIA y procedimientos de benchmark por familia mucho más detallados.

Para LEONES debe interpretarse así:

README raíz = fundamento arquitectónico  
RUNBOOK + recetas por familia = evidencia operativa CUDA actual

El runbook también marca los resultados de memoria y velocidad release-qualified como pendientes bajo su referencia release-0.3.5. Por tanto, el proyecto es suficientemente maduro para P1, pero no toda cifra actual debe describirse como dato release-qualified definitivo.

### 16.14 Conclusión actualizada

TensorFold merece ahora P1 porque ha pasado de un perfil inicial de prototipo/radar a un runtime especializado documentado con motores CUDA por familia, recetas reproducibles, speculative decoding, exactitud dentro del mismo motor y una frontera de serving compatible con OpenAI.

El modelo correcto para ODS es:

TensorFold = proveedor especializado de ejecución + admisión por familia + admisión por checkpoint + admisión por hardware + validación basada en evidencia.

Para la RTX 3050 de 4 GB no debe hacerse todavía ninguna afirmación de compatibilidad ni throughput. La siguiente acción es localizar el checkpoint CUDA soportado más pequeño y probarlo físicamente antes de modificar la instalación de ODS.

**Clasificación LEONES revisada: P1 — investigación de integración de alta prioridad.**
