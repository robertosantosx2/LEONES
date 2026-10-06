# Bonsai 2 27B / small-GPU evidence — fuente externa de evidencia experimental

Fecha de incorporación: 2026-10-06

## Clasificación LEONES

- Tipo: fuente externa de evidencia experimental.
- Estado: REPORTED / MEASURED BY EXTERNAL PROJECT; NOT REPRODUCED BY LEONES.
- Papel: evidencia para calibrar el modelo de selección de LEONES + ODS.
- Dependencia: ninguna. LEONES no debe incorporar bonsai2-small-gpu como dependencia estructural.
- Proyecto fuente: sudoingX/bonsai2-small-gpu.
- Modelo fuente: Ternary Bonsai 2 27B PTQ1_0 con MTP.
- Runtime relevante: fork PrismML de llama.cpp y bundles publicados por el proyecto.
- Modelo: sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF.
- Kernel: PrismML llama.cpp PR #218.

## 1. Hallazgo estratégico

La investigación obliga a cambiar la unidad de decisión de LEONES + ODS.

La pregunta antigua es:

> ¿Qué modelo cabe en mi GPU?

La pregunta objetivo pasa a ser:

> ¿Qué configuración de inferencia produce la mejor capacidad real en mi GPU?

La unidad de selección deja de ser únicamente el modelo y pasa a ser un Inference Profile:

    hardware + model + quantization + runtime + kernel
    + GPU layers + context + KV-cache + MTP
    + vision + parallel slots + reasoning effort
    + flags + measured evidence

Esto importa porque la misma red puede tener capacidades radicalmente distintas según runtime, kernel, contexto, cache y hardware.

## 2. Por qué Bonsai 2 es especialmente útil

Bonsai 2 demuestra una cadena de optimización:

    Qwen 3.8 27B
          |
          v
    ternary/PTQ1_0 compression
          |
          v
       ~5.95 GB
          |
          +--> PrismML llama.cpp
          +--> optimized kernel
          +--> Qwen 3.8 MTP head
          +--> q4_0/q8_0 KV cache
          |
          v
    hardware-specific serving profiles

La conclusión correcta no es «27B necesita 6 GB», sino que una combinación concreta de representación, runtime, kernel, contexto, cache y hardware puede convertir un 27B en una capacidad viable para GPUs tradicionalmente consideradas pequeñas.

## 3. Evidencia externa disponible

El repositorio publica líneas de servicio por VRAM, scripts, sweeps por GPU, resultados de kernel y procedimientos reproducibles. Sus principales cifras proceden de una RTX 3060 12 GB y una RTX 5060 Ti 16 GB, mientras que otras tarjetas aparecen como contribuciones.

| Hardware | Configuración | Contexto | Resultado externo |
|---|---|---:|---:|
| RTX 3060 Ti 8 GB | Bonsai 2, MTP off | ~96K | ~42.8 tok/s |
| RTX 3060 12 GB | Bonsai 2 + kernel + MTP | 131K | ~50.1 tok/s |
| RTX 5060 Ti 16 GB | Bonsai 2 + MTP + visión | 262K | ~67.3 tok/s |
| RTX 3090 24 GB | Qwen 3.8 27B Q4 + MTP | 262K | ~41.3 tok/s |

Son cifras de evidencia externa, no mediciones LEONES.

La fuente documenta además en RTX 3060 12 GB un salto aproximado de 26.3 a 40.5 tok/s de decode fresco con el kernel optimizado, antes de añadir MTP, y documenta igualdad de salida greedy en sus pruebas MTP con batch invariance.

## 4. El kernel cambia la capacidad efectiva

Una misma GPU y los mismos pesos pueden producir aproximadamente:

    stock kernel       -> ~26 tok/s
    optimized kernel   -> ~40 tok/s
    kernel + MTP       -> ~50 tok/s

Por tanto, modelo + GPU no determina por sí solo el rendimiento.

ODS debe poder representar runtime y variante de kernel como parte del perfil de ejecución.

## 5. MTP no es una propiedad binaria del modelo

MTP/speculative decoding depende de head disponible, runtime compatible, configuración, coste de verificación, contexto, batch y kernel.

El beneficio puede ser grande con contexto fresco y disminuir al crecer el contexto. Por tanto MTP ON no significa always faster. La selección futura debe poder escoger MTP ON/OFF según el perfil completo.

## 6. El contexto es una dimensión de capacidad

La VRAM no define una única capacidad. La evidencia de 8 GB muestra una zona viable alrededor de 96K y una caída fuerte al acercarse a 112K en la RTX 3060 Ti.

Un registro «model -> 8 GB» es insuficiente. Debe existir:

    hardware + model + context + KV + runtime
        -> measured capability

## 7. KV cache forma parte de la decisión

La investigación muestra que cuantizar K/V puede liberar VRAM para aumentar el contexto.

    weights + KV cache + context + runtime overhead
        = real memory requirement

ODS no debe comparar modelos únicamente por tamaño de fichero.

## 8. 8 GB cambia de categoría

La fuente presenta una GPU de 8 GB como tarjeta de agente cuando el stack está optimizado para ella. Esto no significa que cualquier 27B funcione en 8 GB; significa que la capacidad efectiva depende de:

    VRAM + compression + quantization + runtime
    + kernel + context strategy + KV + MTP

La clasificación simple 8 GB = modelos pequeños deja de ser suficiente.

## 9. 6 GB y 4 GB: frontera experimental

La fuente indica que 6 GB ya es problemático para este Bonsai 2: parte de las capas deja de caber en GPU y el rendimiento cae a una zona útil para chat pero no para agente.

Esto es relevante para la RTX 3050 Laptop de 4 GB del entorno de referencia de LEONES. No debemos extrapolar la evidencia de 8 GB hacia 4 GB. En 4 GB LEONES debe producir evidencia física propia.

## 10. Nueva entidad: Inference Profile

LEONES + ODS debe evolucionar hacia una entidad explícita con:

- hardware: GPU, VRAM, RAM, driver, acelerador;
- model: familia, parámetros, parámetros activos, modalidad, licencia;
- representation: formato, cuantización, compresión;
- runtime: engine, versión/ref, API;
- kernel: implementación y versión/ref;
- execution: GPU layers, contexto, KV type, batch, slots, MTP, visión, reasoning effort;
- evidence: fuente, fecha, procedencia, estado y mediciones.

## 11. Nueva frontera entre LEONES y ODS

LEONES debe descubrir hardware, definir workload, generar candidatos, conservar procedencia, registrar configuraciones, ejecutar experimentos físicos, medir y conservar evidencia.

ODS debe instalar/servir, exponer capacidades, seleccionar o componer estrategia de ejecución, aplicar runtime/configuración, operar local/hybrid/remote y consumir evidencia disponible.

La separación queda:

    LEONES: prediction + experiment + evidence
                    |
                    v
    ODS: execution + orchestration
                    |
                    v
             physical inference
                    |
                    v
                measurement
                    |
                    v
                 LEONES

## 12. De selector de modelos a selector de capacidad

ANTES:

    hardware -> model selector -> «Qwen 4B fits»

OBJETIVO:

    hardware + workload
          |
          v
    candidate models
          |
          v
    candidate inference profiles
          |
          +--> runtime
          +--> quant
          +--> kernel
          +--> context
          +--> KV
          +--> MTP
          +--> flags
          |
          v
    estimated capability
          |
          v
    physical benchmark
          |
          v
    measured capability
          |
          v
    best real configuration

## 13. Integración con FATE + Edge0 + HOBBIT + HybriMoE

La evidencia refuerza la línea estratégica existente:

    FATE -> prediction
             |
             v
          Edge0 -> prefetch
             |
             v
          HOBBIT -> cache / precision adaptation
             |
             v
          HybriMoE -> GPU / CPU / RAM-NVMe
             |
             v
          runtime
             |
             v
          measured capability

Bonsai 2 demuestra que antes incluso del expert paging existe una capa de optimización de representación, kernel, contexto y speculative decoding que debe formar parte del mismo razonamiento de capacidad.

## 14. Evidencia externa frente a evidencia LEONES

La fuente debe registrarse como:

    EXTERNAL
    COMMUNITY
    MEASURED
    NOT_REPRODUCED_BY_LEONES

Nunca debe convertirse automáticamente en medición LEONES.

La cadena correcta es:

    external report
          |
          v
    candidate configuration
          |
          v
    LEONES reproduction
          |
          v
    MEASURED

## 15. Qué debe aprender ODS de esta fuente

ODS debería poder almacenar o consumir perfiles por GPU y VRAM tier, límites de contexto, variantes de runtime y kernel, cuantización KV, MTP, visión, slots, reasoning effort, flags reproducibles, rendimiento esperado y medido, procedencia, fecha y estado de reproducción.

La información externa no es una garantía.

## 16. Protocolo de benchmark LEONES

Cada Inference Profile debería conservar:

    hardware
    model / quant
    runtime / ref
    kernel / ref
    driver / CUDA
    context / KV
    GPU layers / batch / slots
    MTP / vision / reasoning effort
             |
             v
    TTFT
    prompt tok/s
    generation tok/s
    total latency
    VRAM peak
    RAM peak
    power
    temperature
    success / failure / OOM
    context limit
    agent workload result

La configuración exacta debe ser reproducible.

## 17. Caso LEONES inmediato

En la RTX 3050 4 GB:

    baseline:   Qwen 3.5 2B Q4
    candidate:  Qwen 3.5 4B Q4
    candidate:  Nemotron 3 Nano 4B Q4
                    |
                    v
               A01 benchmark
                    |
                    v
             measured capability

Bonsai 2 queda como referencia externa de arquitectura experimental, no como afirmación de que el 27B sea viable en 4 GB.

## 18. Consecuencia para MANADA

MANADA debe agregar resultados por GPU, VRAM tier, model, quant, runtime, kernel, context y workload, sin convertir automáticamente máquinas distintas en una única medición.

La comparación correcta es por Inference Profile, no únicamente por modelo.

## 19. Regla arquitectónica incorporada

> LEONES + ODS no deben preguntar solamente qué modelo cabe en una GPU. Deben determinar qué configuración de inferencia produce la mejor capacidad real para esa GPU, ese workload y esa política.

La capacidad debe distinguir ESTIMATED, REPORTED, OBSERVED, MEASURED y REPRODUCED.

La evidencia externa descubre candidatos y orienta experimentos; la evidencia LEONES valida el equipo real.

## 20. Estado de integración

- P0 arquitectura/metodología: incorporado a Evolución LEONES + ODS.
- P1 evidencia externa: incorporada con procedencia explícita.
- P1 Inference Profile: propuesta de arquitectura.
- P1 benchmark físico: pendiente de reproducción LEONES.
- P2 integración directa de Bonsai 2 en ODS: no recomendada como dependencia; tratar como provider/runtime/model profile externo.

## Fuentes externas

- https://github.com/sudoingX/bonsai2-small-gpu
- https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF
- https://github.com/PrismML-Eng/llama.cpp/pull/218
- https://github.com/sudoingX/llama.cpp
- https://github.com/sudoingX/qwen38-mtp
