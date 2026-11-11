# Viabilidad de Qwen3.5-9B en NVIDIA RTX 3050 Laptop de 4 GiB

**Fecha:** 2026-11-11  
**Estado:** evaluación técnica documental; **NO MEASURED**  
**Equipo objetivo:** MSI Thin 15 B12UC · Intel Core i7-12650H · NVIDIA RTX 3050 Laptop 4 GiB · 14 GiB RAM · Ubuntu · driver 580.178.04 · CUDA runtime 13.0 · CUDA Toolkit 13.4  
**Entorno de referencia del usuario:** TensorFold 1.2.3; llama.cpp local con builds 0.7.0-dev/0.8.0-dev registradas en el inventario previo.

> **Conclusión ejecutiva:** Qwen3.5-9B no es un candidato razonable para residir íntegramente en los 4 GiB de la RTX 3050. Incluso una cuantización nominal de 2 bits consume aproximadamente 2.1–2.3 GiB solo en pesos teóricos; faltan buffers de ejecución, estado recurrente, cachés, módulos multimodales y margen para el controlador/escritorio. La vía técnicamente plausible es CPU+GPU híbrida, con una fracción pequeña de capas en GPU, **pero solo si el motor y el formato concretos soportan Qwen3.5-9B y su arquitectura**. No se ha demostrado esa combinación en este equipo. La alternativa segura y ya más próxima a la evidencia disponible es continuar con Qwen3.5-4B.

## 1. Alcance y criterio de evidencia

Este informe responde a una pregunta concreta: si el modelo oficial **Qwen/Qwen3.5-9B** puede ejecutarse en una RTX 3050 Laptop con 4 GiB de VRAM, dentro de la máquina descrita arriba.

Se separan cuatro niveles:

- **SOURCE:** datos publicados por el proyecto del modelo o por el runtime.
- **CALCULATED / ESTIMATED:** cálculos de memoria y recomendaciones de configuración. No son medidas de ejecución.
- **MEASURED:** resultado obtenido ejecutando la combinación exacta de modelo, cuantización, runtime, versión y hardware, con logs y telemetría.
- **UNKNOWN / NOT VERIFIED:** compatibilidad o comportamiento que no se puede deducir de una lista genérica de capacidades.

No se presenta ninguna cifra estimada como benchmark medido. A fecha de este informe no hay una ejecución física de Qwen3.5-9B en esta RTX 3050 adjunta como evidencia.

## 2. Modelo y arquitectura

La ficha oficial de Hugging Face clasifica Qwen3.5-9B como un modelo causal multimodal con encoder visual y publica **9B parámetros** (cifra nominal/redondeada), 32 capas, dimensión oculta 4096, dimensión intermedia 12288, vocabulario 248320 y contexto nativo de 262144 tokens. La configuración descargable declara `model_type=qwen3_5`, arquitectura `Qwen3_5ForConditionalGeneration`, `head_dim=256`, 16 cabezas de atención, 4 cabezas KV y un patrón híbrido de atención lineal y completa.

La pila de texto es híbrida: tres bloques de atención lineal Gated DeltaNet por cada bloque de atención completa. En 32 capas, el patrón publicado implica 24 capas lineales y 8 de atención completa. La atención lineal reduce el coste de atención en comparación con aplicar atención completa en todos los bloques, pero **no convierte el modelo en un modelo pequeño ni elimina el coste de almacenar los pesos**.

La configuración también incluye un encoder visual: profundidad 27, dimensión oculta 1152 y salida 4096. Por tanto, no debe suponerse que una conversión o ejecución multimodal tendrá exactamente el coste de una carga de texto-only. El coste real depende de si el runtime carga el encoder/proyector visual, de la conversión y del camino de inferencia utilizado.

Fuentes primarias:
- Modelo: https://huggingface.co/Qwen/Qwen3.5-9B
- Configuración exacta publicada: https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/config.json
- Documentación de arquitectura Qwen3.5 en Transformers: https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/qwen3_5.md

## 3. Hardware disponible y límites prácticos

| Recurso | Equipo | Implicación |
|---|---:|---|
| GPU | RTX 3050 Laptop, 4 GiB VRAM | Capacidad muy inferior a la necesaria para todos los pesos más buffers |
| Arquitectura GPU | SM 8.6 | CUDA disponible; no implica compatibilidad automática de cada kernel/modelo |
| RAM | 14 GiB | Puede alojar pesos parcialmente/totalmente en CPU si el formato y runtime lo permiten, pero comparte memoria con Ubuntu y servicios |
| Swap | 31 GiB | Amortigua presión de memoria; no equivale a RAM y puede hacer la inferencia extremadamente lenta |
| CPU | Intel Core i7-12650H | Permite offload CPU, con velocidad dependiente de cuantización, kernels, hilos y ancho de banda |
| Driver | 580.178.04 | Cumple el requisito de driver R580+ indicado por TensorFold para sus binarios CUDA recientes |
| CUDA | runtime 13.0; Toolkit 13.4 | Entorno CUDA instalado; no garantiza que un backend admita este checkpoint |

La memoria anunciada de 4 GiB no está íntegramente disponible para el modelo: el controlador, el escritorio gráfico, buffers CUDA y otros procesos consumen parte de ella. La memoria libre debe medirse inmediatamente antes de cada prueba con `nvidia-smi`; no debe fijarse una cifra de VRAM libre a partir de la capacidad nominal.

## 4. Estimación de memoria de pesos

Para comparar cuantizaciones se utiliza el límite ideal:

`GiB_pesos ≈ parámetros_en_miles_de_millones × bits_por_peso / (8 × 1.073741824)`

La ficha oficial dice 9B; para planificación conservadora se incluye también 9.7B como sensibilidad superior, no como recuento exacto confirmado por el model card. Los bits son **bits efectivos medios teóricos**: no identifican por sí mismos un formato real como Q2_K, IQ2_XXS, Q3_K_M o una cuantización ModelOpt.

| Bits efectivos medios | 9.0B parámetros | 9.7B parámetros | Lectura |
|---:|---:|---:|---|
| 2.0 | 2.10 GiB | 2.26 GiB | Extremadamente agresivo; pérdida de calidad potencialmente importante |
| 2.5 | 2.62 GiB | 2.82 GiB | Hipótesis de presupuesto, no formato concreto garantizado |
| 3.0 | 3.14 GiB | 3.39 GiB | Ya ocupa gran parte de la VRAM antes de buffers |
| 4.0 | 4.19 GiB | 4.52 GiB | Supera 4 GiB solo con los pesos ideales |
| 5.0 | 5.24 GiB | 5.65 GiB | No cabe en VRAM |
| 6.0 | 6.29 GiB | 6.78 GiB | No cabe en VRAM |
| 8.0 | 8.38 GiB | 9.03 GiB | No cabe en VRAM |

Estos valores son un suelo matemático, no el tamaño exacto de un archivo descargable ni el pico de VRAM. Los formatos reales incluyen escalas, metadatos, bloques, tensores que pueden conservar más precisión, embeddings, cabezas y, en algunos casos, tensores auxiliares. La cuantización multimodal puede tratar de forma distinta los componentes del modelo.

### Interpretación

- **Q4:** descartado para carga íntegra en 4 GiB; los pesos ideales ya superan la capacidad.
- **Q3:** descartado para carga íntegra; los pesos ideales consumen aproximadamente 3.1–3.4 GiB y no dejan margen operativo.
- **Q2.5:** tampoco debe considerarse viable íntegramente en GPU; el peso teórico por sí solo ocupa 2.6–2.8 GiB.
- **Q2 / IQ2:** es el único rango que podría dejar margen teórico apreciable, pero sigue sin demostrar que quepa el conjunto de pesos + visión + estado + buffers. La calidad puede degradarse sustancialmente y depende del esquema concreto.

## 5. Memoria de ejecución: por qué los pesos no bastan

El consumo real se compone de varios elementos:

`VRAM_pico = pesos_GPU + buffers_de_capas + activaciones + estado_KV/SSM + scratch + workspace + CUDA/contexto + fragmentación`

En Qwen3.5 hay que considerar, como mínimo:

1. Pesos colocados en GPU.
2. Buffers temporales de proyecciones y MLP.
3. Scratch y workspace específicos del motor.
4. Estado de las capas lineales/recurrentes (DeltaNet) y caché de las capas de atención completa.
5. Buffers de prefill y del tamaño de lote.
6. Posible encoder/procesamiento visual.
7. Contexto CUDA, asignaciones del runtime y fragmentación.
8. Memoria reservada por el controlador y el escritorio Ubuntu.

No se asigna aquí un valor fijo de scratch/KV/SSM para 9B: depende del backend, del contexto, batch, número de secuencias, kernels y precisión del estado. Dar una cifra única sin ejecutar el motor sería falsa precisión.

El contexto de 262144 tokens publicado por el modelo es un máximo arquitectónico, no una recomendación para esta GPU. Para una primera prueba de hardware limitado se debe empezar con contexto 1024–2048, batch/parallel 1 y prefill pequeño, y aumentar solo después de medir.

## 6. Cuantización: Q2, Q2.5, Q3, Q4 y E-means

Los nombres Q2/Q3/Q4 describen aproximadamente una familia de precisión/tasa de bits, pero el coste real depende del formato. No deben confundirse:

- **bits nominales** con bits efectivos por parámetro;
- **tamaño del fichero** con VRAM pico;
- **cuantización del modelo** con el algoritmo utilizado para calcular centroides;
- **calidad estimada** con calidad medida en tareas.

E-means es un método de optimización de centroides para clustering relacionado con k-means. No es un formato de cuantización de pesos ni crea automáticamente un checkpoint “Q3 E-means”. A igual número de bits, estructura de bloques y codificación, E-means no reduce por sí solo el límite de memoria. Solo una cuantización concreta, publicada y validada podría justificar una comparación de calidad/memoria.

Por tanto, en este informe “2.5 bits” es una columna matemática de sensibilidad, no una recomendación de descargar un archivo Q2.5 inexistente. Para elegir un artefacto se necesita su repositorio, formato, licencia, tamaño real, metadata de cuantización y compatibilidad con el runtime.

## 6.1. E-means frente a K-means: implicaciones para cuantizar Qwen3.5-9B

Esta sección amplía la comparación de cuantización para evitar una conclusión incorrecta: **E-means y K-means no pueden considerarse equivalentes en calidad para los pesos de Qwen3.5-9B sin generar y evaluar cuantizaciones concretas**.

### Qué optimiza cada método

- **K-means** agrupa valores (por ejemplo, bloques o vectores de pesos) alrededor de centroides y minimiza la suma de distancias cuadráticas dentro de cada grupo mediante asignación y actualización de centroides.
- **E-means** es un método de optimización de centroides relacionado con k-means que utiliza actualizaciones tipo *exponential moving average* (EMA) en un esquema mini-batch. Su objetivo principal es acelerar la convergencia hacia una solución de clustering de baja pérdida; no define por sí mismo un formato de cuantización, un número de bits ni una codificación de pesos.

El trabajo publicado como **“e-means: outperforming k-means (in one-tenth the epochs)”** informa de una mediana de 12,6× menos épocas para alcanzar la pérdida de Lloyd K-means tras 25 épocas, en 234 configuraciones y 16 conjuntos de datos, con tamaños de 100.000 a 100 millones de puntos. Estos resultados describen optimización de clustering; **no son una evaluación de cuantización de LLM, no miden perplexity de Qwen y no prueban equivalencia de calidad entre pesos cuantizados E-means y K-means**.

Fuentes:
- Paper: https://arxiv.org/abs/2611.09501
- Implementación de referencia FAISS: https://github.com/facebookresearch/faiss/tree/main/contrib/e_means

### ¿Son equivalentes en calidad?

No hay base suficiente para afirmar que una cuantización E-means a 3 bits iguale a una K-means a 3 bits, ni que E-means a menos bits iguale a K-means a más bits, en Qwen3.5-9B. Una convergencia más rápida o una menor pérdida de clustering no garantiza por sí sola menor error funcional del modelo.

La calidad final depende, entre otros factores, de:
- qué tensores se cuantizan y cuáles permanecen en mayor precisión;
- agrupación por tensor, canal, grupo o bloque;
- tamaño de bloque y número de centroides;
- bits efectivos reales, escalas, índices y metadatos;
- tratamiento de outliers y pesos sensibles;
- calibración, datos representativos y *fine-tuning* posterior;
- implementación de kernels y des cuantización en el runtime.

Si se mantienen idénticos el número de centroides/código, bits efectivos, estructura de bloques y representación de índices, el método de búsqueda de centroides **no cambia por sí mismo el presupuesto teórico de memoria**. E-means podría encontrar centroides útiles en menos iteraciones o mejorar el objetivo de clustering, pero la equivalencia de calidad del modelo debe medirse por separado.

### Implicación para TensorFold

No debe asumirse que TensorFold 1.2.3 incorpora E-means como cuantizador, que acepta automáticamente artefactos creados con FAISS ni que el backend CUDA ejecute directamente cualquier codebook generado externamente. E-means sería, en principio, parte del proceso de preparación/calibración de pesos; TensorFold necesitaría reconocer el formato resultante y disponer de kernels de carga y ejecución compatibles.

Antes de atribuir soporte a TensorFold, verificar:
1. formato exportado y especificación de almacenamiento de centroides/índices;
2. conversión de todos los tensores necesarios, incluidos embeddings y capas sensibles;
3. parser y kernels del backend TensorFold para ese formato;
4. tamaño real del artefacto y memoria pico de carga/ejecución;
5. exactitud numérica y calidad funcional frente a un baseline comparable.

### Protocolo de comparación recomendado

Para probar la hipótesis en Qwen3.5-9B, producir dos artefactos desde el mismo checkpoint y con idéntica configuración: uno con K-means y otro con E-means. Mantener iguales los bits efectivos, grupos, centroides, tensores excluidos, calibración y precisión de los componentes auxiliares. Comparar:

- error de reconstrucción de pesos y de activaciones;
- perplexity en un conjunto de evaluación fijo;
- tareas de razonamiento, conocimiento, código e instrucciones;
- estabilidad de generación, repeticiones y degradación multimodal si se evalúa visión;
- tamaño en disco, memoria residente, VRAM pico y velocidad en el mismo runtime.

Añadir una segunda comparación de tasa-distorsión (por ejemplo, E-means a menor bit-rate frente a K-means a mayor bit-rate) solo después de establecer el resultado a igual presupuesto. Todas las pruebas deben registrar versiones, hashes, datos de calibración y comandos.

**Conclusión operativa:** E-means es una alternativa prometedora para acelerar u optimizar la fase de clustering de una cuantización, pero no es correcto etiquetarlo como “misma calidad que K-means” para Qwen3.5-9B. En este informe no existe todavía una cuantización E-means de Qwen3.5-9B validada en TensorFold ni una comparación medida. Mantener el estado como **NOT MEASURED / NOT VERIFIED** hasta ejecutar el protocolo anterior.

## 7. Compatibilidad de runtimes: lo que está demostrado y lo que no

### TensorFold

El usuario tiene TensorFold 1.2.3 instalado. La línea 1.2.2/1.2.3 incorporó soporte Qwen3.5 en distintas rutas, pero la documentación/release distingue backend y formato: la publicación 1.2.2 indica Qwen3.5-9B sobre el motor Metal derivado del motor 27B; 1.2.3 menciona Qwen3.5 BF16 sobre HIP/rocBLAS. Eso **no demuestra Qwen3.5-9B en CUDA sobre RTX 3050**.

La capacidad genérica `qwen3_5` o el hecho de que TensorFold arranque con CUDA no basta para concluir que cualquier checkpoint Qwen3.5, cuantización y tamaño estén admitidos. Se requiere una receta que nombre exactamente:
- TensorFold release/commit;
- familia y tamaño Qwen3.5-9B;
- formato y origen del checkpoint;
- backend CUDA;
- arquitectura GPU;
- contexto y reserva de memoria;
- ejecución real con logs y telemetría.

### PR #1879 — lazy scratch CUDA

El trabajo previo del usuario en TensorFold PR #1879 aborda una cuestión real de asignación de memoria: evitar reservar desde el inicio el scratch máximo de Qwen3.5 y crecerlo bajo demanda. La validación local registrada fue 322/322 pasos y 113/113 tests host CUDA. El usuario también informó de una validación específica Qwen3.5-4B en CUDA.

Esto es evidencia de corrección de una ruta de gestión de memoria y de la validación del caso 4B documentado. **No prueba** que el 9B quepa en 4 GiB, que el 9B esté habilitado en CUDA, ni que exista offload CPU/GPU para ese checkpoint. Una reserva más eficiente no cambia el tamaño de los pesos.

Referencias:
- PR: https://github.com/ashhart/TensorFold/pull/1879
- Releases: https://github.com/ashhart/TensorFold/releases
- Repositorio: https://github.com/ashhart/TensorFold

### llama.cpp

llama.cpp documenta inferencia híbrida CPU+GPU y cuantizaciones desde 1.5 hasta 8 bits. Eso hace que el enfoque de offload parcial sea conceptualmente adecuado para una GPU menor que el modelo. Sin embargo, la capacidad general del runtime no prueba que la versión local del usuario soporte correctamente Qwen3.5-9B y el GGUF concreto. La documentación upstream muestra Qwen3.5 en el flujo de ejecución y el proyecto tiene soporte CPU+GPU híbrido; antes de recomendar un comando concreto hay que verificar el soporte del modelo/arquitectura en el commit local y que exista un GGUF 9B compatible.

El inventario anterior del usuario registra builds locales 0.7.0-dev y 0.8.0-dev. Debe verificarse el commit exacto, la salida de `llama-cli --version`, el listado de tipos de tensor y la carga del modelo. No se debe asumir que la rama local tiene las mismas capacidades que el upstream actual.

Referencia: https://github.com/ggml-org/llama.cpp

## 8. Matriz de viabilidad

| Escenario | Viabilidad en RTX 3050 4 GiB | Estado |
|---|---|---|
| 9B Q4 íntegro en GPU | No | Descartado por pesos teóricos |
| 9B Q3 íntegro en GPU | No práctico | Descartado por falta de margen |
| 9B Q2.5 íntegro en GPU | No recomendable | Pesos teóricos dejan margen insuficiente |
| 9B Q2/IQ2 íntegro en GPU | Muy improbable/no demostrado | Requiere medición; no asumir |
| 9B CPU-only | Posible en principio | Depende del formato, RAM disponible y runtime; rendimiento no medido |
| 9B CPU+GPU parcial | Candidato experimental | Requiere soporte explícito y validación exacta del runtime |
| 9B TensorFold CUDA 1.2.3 | No confirmado | No se ha acreditado receta 9B CUDA para esta GPU |
| 9B TensorFold Metal | No aplicable | Backend para Apple Silicon, no RTX |
| 9B llama.cpp GGUF híbrido | Candidato condicionado | Confirmar GGUF/arquitectura en la build local |
| Qwen3.5-4B CUDA | Mejor punto de partida | Hay trabajo y validación previa del usuario con PR #1879; no extrapolar sus cifras al 9B |

## 9. Recomendación para este MSI

**Recomendación principal: no invertir tiempo en intentar cargar Qwen3.5-9B íntegramente en la RTX 3050.** Si el objetivo es experimentar con el 9B, hacerlo como prueba híbrida CPU+GPU en llama.cpp solo después de confirmar que el build local reconoce la arquitectura y el GGUF. Si el objetivo es disponer de una ejecución CUDA fiable con memoria limitada, continuar primero con Qwen3.5-4B y cerrar sus pruebas de contexto, prefill y pico de VRAM.

Orden recomendado:

1. **Baseline:** capturar VRAM libre, RAM disponible, swap y procesos GPU antes de arrancar.
2. **Verificar artefacto:** identificar repositorio, archivo, tamaño, cuantización efectiva, metadata, licencia y hash.
3. **Verificar backend:** confirmar soporte exacto Qwen3.5-9B + formato + CUDA o CPU/GPU híbrido en la versión local.
4. **CPU-only de control:** si el runtime lo admite, ejecutar una prueba breve para validar carga/tokenización y consumo RAM.
5. **Híbrido conservador:** batch 1, contexto 1024, prefill 32–64 y pocas capas GPU; medir antes de aumentar offload.
6. **Escalado:** contexto 2048 y mayor número de capas GPU solo si no hay OOM y la RAM/swap permanecen dentro de límites.
7. **Calidad:** comparar la cuantización con un baseline de mayor precisión mediante prompts fijos y evaluación reproducible.
8. **Benchmark:** medir TTFT, prompt tokens/s, generation tokens/s, pico VRAM, pico RSS, swap, consumo y estabilidad en varias repeticiones.

No se recomienda desactivar la reserva de memoria del motor para forzar el arranque. La reserva protege al proceso de quedarse sin VRAM; reducirla puede ser una variable experimental, no una solución al tamaño de los pesos.

## 10. Plan de validación reproducible

Antes de descargar o iniciar un modelo:

```bash
nvidia-smi
free -h
swapon --show
df -h "$HOME"
```

Registrar versiones:

```bash
nvidia-smi
nvcc --version
command -v llama-cli || true
llama-cli --version 2>&1 || true
```

Para cada ejecución guardar:
- nombre exacto del modelo y URL del repositorio;
- revisión/commit del modelo;
- nombre de archivo y SHA-256;
- tamaño real en disco;
- formato y metadata de cuantización;
- runtime, versión, commit y backend;
- argumentos completos;
- contexto, batch, ubatch, capas GPU, threads y número de secuencias;
- `nvidia-smi` antes/durante/después;
- RSS máximo, memoria libre, swap y tiempo;
- prompt exacto, tokens de entrada/salida y métricas TTFT/PP/TG;
- código de salida y log completo.

La ejecución se considera **MEASURED** solo si la prueba termina y el registro permite atribuir el resultado a esta máquina y a esa combinación concreta. Un arranque parcial, un test de compilación o una prueba de otra GPU no cuentan como medición del 9B en este MSI.

## 11. Riesgos y condiciones de parada

Detener la prueba si:
- aparece OOM o el proceso entra en asignaciones/reintentos repetidos;
- la RAM disponible cae a un nivel que compromete Ubuntu;
- el swap crece rápidamente y el sistema empieza a bloquearse;
- la GPU comparte VRAM con aplicaciones gráficas y la memoria libre es insuficiente;
- el runtime no reconoce explícitamente la arquitectura o ignora tensores;
- el modelo genera salidas corruptas, NaN, repeticiones o errores de estado;
- la cuantización no tiene origen/licencia/metadata verificables.

No usar el swap como sustituto de VRAM para inferencia interactiva: puede permitir que el proceso sobreviva, pero no garantiza rendimiento utilizable.

## 12. Veredicto final

**¿Se puede ejecutar Qwen3.5-9B en una RTX 3050 Laptop de 4 GiB?**

- **Todo en GPU:** no de forma práctica; Q3/Q4 superan el presupuesto incluso en el cálculo ideal y Q2 deja un margen que no garantiza buffers ni estado.
- **CPU-only:** técnicamente posible si existe un formato compatible y la RAM del sistema basta, pero la velocidad no está medida.
- **CPU+GPU:** es la vía experimental más razonable, siempre que el runtime admita expresamente Qwen3.5-9B y el formato elegido. llama.cpp ofrece infraestructura híbrida general, pero hay que validar la versión y el GGUF concretos.
- **TensorFold 1.2.3 CUDA:** no se debe dar por soportado el 9B en la RTX 3050 basándose en soporte genérico Qwen3.5, PR #1879 o soporte de otros backends.
- **Opción recomendada:** Qwen3.5-4B para CUDA local; 9B como experimento híbrido CPU+GPU y no como despliegue íntegro en VRAM.

**Estado LEONES:** ESTIMATED / SOURCE REVIEW. Sin benchmark físico Qwen3.5-9B en este equipo. No publicar tokens/s, VRAM pico ni calidad como resultados medidos hasta completar el plan de validación.

## Fuentes

1. Qwen, modelo oficial Qwen3.5-9B: https://huggingface.co/Qwen/Qwen3.5-9B
2. Qwen, configuración oficial: https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/config.json
3. Hugging Face Transformers, arquitectura Qwen3.5: https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/qwen3_5.md
4. TensorFold, releases: https://github.com/ashhart/TensorFold/releases
5. TensorFold, PR #1879: https://github.com/ashhart/TensorFold/pull/1879
6. llama.cpp, proyecto y documentación: https://github.com/ggml-org/llama.cpp
7. Perfil de hardware LEONES: `hardware/UBUNTU-MSI-THIN-15-B12UC.md`

---
**Nota de mantenimiento:** actualizar este informe cuando se disponga de una ejecución reproducible del 9B en el MSI o cuando el runtime publique una receta explícita Qwen3.5-9B + CUDA/CPU-offload para la versión instalada.
