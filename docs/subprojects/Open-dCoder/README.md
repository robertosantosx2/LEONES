# Open-dCoder — ejecución local y benchmark inicial

**Estado:** ejecutado localmente; incluye pruebas iniciales V1, benchmark repetido V2 y batching real V3. Evidencia específica de una tarea, no evaluación general de inteligencia.  
**Fecha de las pruebas:** 2026-10-31.  
**Equipo:** Ubuntu, MSI Thin 15 B12UC, Intel Core i7-12650H, 16 hilos lógicos, 14.8 GiB RAM, NVIDIA RTX 3050 Laptop de 4 GiB VRAM.  
**Repositorio de documentación:** [LEONES](https://github.com/robertosantosx2/LEONES).

## Navegación de resultados y experimentos

- [Resumen ejecutivo y mapa de todos los experimentos](EXECUTIVE-SUMMARY.md)
- [Cuaderno detallado V1/V2: metodología, validador, resultados y auditoría](EXPERIMENT-2026-10-31.md)
- [Experimento V3: batching real, nueve configuraciones y auditoría de resultados](EXPERIMENT-V3-BATCH-2026-10-31.md)

V2 proporciona el baseline de secuencia única; V3 amplía la medición a batches reales de 1, 2 y 4 secuencias. El resumen ejecutivo enlaza todos los registros y distingue las mediciones históricas de las referencias vigentes.

## 1. Objetivo y alcance

Se ha desplegado y ejecutado el modelo de difusión de texto **`fredzzp/open-dcoder-0.5B`** desde el proyecto Open-dLLM/Open-dCoder en Ubuntu, utilizando la GPU NVIDIA mediante PyTorch CUDA.

A diferencia de un LLM autoregresivo convencional, Open-dCoder genera/refina varias posiciones de salida mediante un proceso de difusión. Por tanto, las tasas de esta prueba se expresan como **posiciones de salida por segundo** y no deben compararse directamente con tokens/s autoregresivos.

Esta primera validación comprueba:
- carga del modelo en GPU;
- ejecución real de `diffusion_generate`;
- generación de código Python;
- sintaxis Python mediante `ast.parse`;
- comportamiento funcional de la función generada para entradas positivas y negativas.

No es todavía una evaluación general de capacidad de programación ni un benchmark estadístico definitivo.

## 2. Hardware y entorno

| Elemento | Configuración |
|---|---|
| Sistema | Ubuntu |
| Portátil | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| CPU lógica | 16 hilos |
| RAM | 14.8 GiB |
| GPU | NVIDIA GeForce RTX 3050 Laptop |
| VRAM | 4 GiB |
| Driver NVIDIA | 580.178.04 |
| CUDA del driver | 13.0 |
| Python | 3.12.15 |
| PyTorch | 2.11.0+cu128 |
| Transformers | 4.54.1 |
| huggingface-hub | 0.36.2 |
| datasets | 4.4.1 |
| torchdata | 0.11.0 |
| einops | 0.8.2 |

El entorno Python está aislado en `~/open-dcoder/.venv`. El repositorio se encuentra en `~/open-dcoder/Open-dLLM` y se instaló en editable como paquete `open-dcoder 0.1.0`.

**Trazabilidad pendiente:** no se capturó en esta sesión el SHA del commit de Open-dLLM ni un manifiesto completo de dependencias. Deben añadirse en una repetición antes de considerar el benchmark plenamente reproducible.

## 3. Modelo

| Campo | Valor |
|---|---|
| Modelo | `fredzzp/open-dcoder-0.5B` |
| Arquitectura | Qwen2 adaptada para difusión de texto |
| Parámetros | 494,032,768 |
| Precisión de carga | BF16 |
| Formato de pesos | Safetensors |
| Tamaño de `model.safetensors` | 1,260,367,448 bytes (~1.174 GiB) |
| Tokenizer | Qwen2TokenizerFast |
| Vocabulario | 151,666 |
| Token de máscara | `<M>` |
| ID del token de máscara | 151665 |
| Snapshot HF | `d0d86d5b99960c05258bb1f8265dd91564dbac67` |

Pesos descargados desde Hugging Face y cargados correctamente en la RTX 3050. La ocupación medida anteriormente fue aproximadamente 0.928 GiB para los pesos; durante generación se observaron picos de alrededor de 1.15–1.22 GiB, dependiendo de la prueba.

## 4. Adaptaciones necesarias del entorno

La importación inicial de módulos del proyecto cargaba de forma anticipada componentes multimodales no necesarios para esta prueba. Uno de ellos fallaba con Transformers 4.54.1 por la importación de `PILImageResampling`.

Para poder importar el camino de inferencia Qwen2 se sustituyeron temporalmente por inicializadores ligeros estos tres ficheros:

- `veomni/models/__init__.py`
- `veomni/models/transformers/__init__.py`
- `veomni/data/__init__.py`

Se conservaron copias de seguridad junto a los originales con el sufijo `.open-dcoder-backup`.

**Importante:** son cambios locales de compatibilidad, no una modificación upstream ni una solución general para los componentes multimodales. No se deben eliminar las copias ni restaurar los inicializadores hasta decidir cómo cerrar el entorno. La inferencia se hizo importando directamente `Qwen2ForCausalLM`, `MDMGenerationConfig` y usando `model.diffusion_generate`, no `model.generate()`.

Durante ejecución aparece el aviso de VeOmni indicando que no se ha inicializado el estado distribuido y que se usa el modo single-process. Es coherente con esta prueba de una sola GPU.

## 5. Prueba funcional de generación de código

Prompt utilizado, resumido:

> Write only Python code. Implement factorial(n) recursively. Raise ValueError for negative integers. Include print(factorial(5)).

Configuración común:
- `max_new_tokens=64`
- `alg="p2"`
- `alg_temp=0.5`
- `temperature=0.2`
- `top_k=200`
- `num_return_sequences=1`
- `output_history=False)

La salida se decodificó, se retiró una envoltura inicial de comillas triples cuando apareció y se comprobó con el parser de Python. Después se ejecutó la función generada para verificar que `factorial(5) == 120` y que `factorial(-1)` lanzaba `ValueError`.

### Resultados del barrido de pasos

| Pasos de difusión | Tiempo | Posiciones de salida/s | Sintaxis | Prueba funcional |
|---:|---:|---:|:---:|:---:|
| 16 | 0.968 s | 66.1 | OK | OK |
| 32 | **0.891 s** | **71.8** | OK | OK |
| 64 | 1.791 s | 35.7 | OK | OK |
| 128 | 3.523 s | 18.2 | OK | OK |

En las cuatro ejecuciones el código generado superó la comprobación sintáctica y las dos comprobaciones funcionales. Las salidas imprimieron `120`.

La velocidad se calcula como 64 posiciones de salida divididas por el tiempo de generación. **No equivale a tokens/s de decodificación autoregresiva.**

### Interpretación

- En esta muestra, 32 pasos ofrecieron el menor tiempo y la mayor tasa de posiciones/s.
- 64 y 128 pasos aumentaron el tiempo sin aportar una mejora funcional observable en esta tarea.
- La diferencia entre 16 y 32 pasos es pequeña (0.077 s) y procede de una sola ejecución por configuración; no permite afirmar todavía que 32 sea estadísticamente superior.
- Resultado recomendado provisional para nuevas pruebas: **32 pasos**, manteniendo 16 como referencia de baja latencia.

## 6. Otras mediciones exploratorias

En ejecuciones previas del mismo entorno y modelo:
- una primera generación de 64 posiciones tardó 1.622 s (39.47 posiciones/s), con un pico VRAM registrado de 1.149 GiB;
- tres ejecuciones de la tarea factorial con 16 pasos registraron 1.276 s, 0.471 s y 0.471 s; media 0.739 s;
- el pico de VRAM registrado para esa serie fue 1.215 GiB (memoria reservada: 1.383 GiB).

Son mediciones exploratorias separadas; no deben mezclarse con la tabla principal como si fueran repeticiones idénticas y controladas.

## 7. Advertencias y limitaciones

1. Transformers mostró el aviso `The following generation flags are not valid and may be ignored: ['temperature', 'top_k']`. La generación terminó correctamente, pero debe investigarse si esos parámetros se aplican realmente en esta versión/configuración. No se debe asumir que el valor de temperatura se respetó.
2. La salida de código se ha validado con una tarea pequeña y determinista. No representa una evaluación amplia de coding, razonamiento o seguridad.
3. La ejecución de código generado solo debe hacerse en un entorno controlado. En esta prueba el código se limitó a una función factorial sencilla.
4. No se ha medido consumo eléctrico ni rendimiento sostenido.
5. No se ha realizado comparación equivalente con llama.cpp, TensorFold, Transformers estándar u otros motores de difusión.
6. No se asigna puntuación Artificial Analysis: no existe aquí una medición comparable y validada para este modelo/tarea.

## 8. Estado actual y siguientes pasos

La fase inicial descrita en este README se ha ampliado con dos experimentos posteriores:
- **V2:** tres repeticiones medidas por configuración, warmup excluido y validador AST/funcional corregido. Véase el [cuaderno V1/V2](EXPERIMENT-2026-10-31.md).
- **V3:** nueve configuraciones de batch real (1/2/4) y pasos (16/32/64), tres repeticiones por configuración. Véase el [informe V3](EXPERIMENT-V3-BATCH-2026-10-31.md).

La navegación y comparación conjunta están en el [resumen ejecutivo](EXECUTIVE-SUMMARY.md).

Pendiente para cerrar la trazabilidad: incorporar los artefactos locales originales V3 (runner, CSV, JSONL, JSON y log), registrar SHA del commit Open-dLLM y manifiesto exacto de dependencias, y realizar nuevas tareas y ablaciones controladas de `temperature`/`top_k`. El estado global es **MEASURED — experimentos V1/V2/V3 sobre una tarea factorial**, no benchmark general ni ranking de inteligencia.

## 9. Referencias

- Proyecto Open-dLLM: https://github.com/zhangsheng93/Open-dLLM
- Modelo: https://huggingface.co/fredzzp/open-dcoder-0.5B
- Documentación LEONES: https://github.com/robertosantosx2/LEONES
