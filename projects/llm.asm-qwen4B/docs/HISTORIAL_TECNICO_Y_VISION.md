# llm.asm-qwen4B — Historial técnico y visión estratégica

**Proyecto:** LEONES / llm.asm-qwen4B
**Inicio:** 26 de noviembre de 2026
**Motor:** alesha-pro/llm.asm
**Modelo de partida:** Qwen3-0.6B
**Objetivo experimental:** Qwen3-4B

---

## 1. Objetivo estratégico

El objetivo final es desarrollar un **motor de inferencia LLM óptimo
de extremo a extremo**, capaz de funcionar en una máquina altamente
optimizada, con un sistema operativo mínimo o incluso sin sistema
operativo, y ofrecer inferencia mediante una API compatible o similar
a la API de OpenAI.

No buscamos únicamente ejecutar modelos. Buscamos construir una
plataforma propia de inferencia, eficiente, compacta, reproducible
y desplegable.

### Principios de diseño

- Optimización conjunta de hardware y software.
- Control explícito de memoria, asignaciones y transferencias.
- Kernels especializados para las instrucciones disponibles.
- Formatos de pesos diseñados para lectura e inferencia eficientes.
- Baja latencia, alto rendimiento y escalabilidad de contexto.
- Gestión eficiente de KV-cache.
- Paralelismo adaptado al hardware.
- Dependencias externas mínimas.
- Runtime pequeño y predecible.
- Posibilidad de ejecución bare-metal.
- API de inferencia familiar, compatible o similar a OpenAI.
- Trazabilidad de código, modelos, compilación, pruebas y resultados.

La optimización debe considerar rendimiento, memoria residente,
prefill, decode, latencia inicial, consumo energético, concurrencia,
estabilidad y tiempo de arranque.

### Arquitectura de destino

1. Hardware: CPU, SIMD, memoria, GPU y aceleradores.
2. Motor matemático: operaciones matriciales, normalización,
   activaciones, RoPE y kernels especializados.
3. Motor Transformer: atención, GQA, FFN, KV-cache y ejecución.
4. Formato de modelos: pesos, metadatos y tokenizer.
5. Runtime: memoria, planificación, concurrencia y recursos.
6. Plataforma mínima: Linux reducido, runtime propio o bare-metal.
7. Servicio: API HTTP compatible o similar a OpenAI.
8. Operación: monitorización, seguridad y reproducibilidad.

El núcleo de inferencia debe poder funcionar independientemente
del servicio HTTP. La API no debe introducir dependencias
innecesarias en el motor.

---

## 2. Plataforma experimental: MSI

| Elemento | Característica |
|---|---|
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| Arquitectura | x86-64 |
| RAM | Aproximadamente 14 GiB |
| GPU | NVIDIA RTX 3050 Laptop |
| VRAM | 4 GiB |
| SIMD | AVX2, FMA, F16C, AVX-VNNI |
| Sistema | Ubuntu |
| Kernel registrado | 7.0.0-38-generic |
| CUDA Toolkit registrado | 13.4 |

Las mediciones históricas de llm.asm Qwen3-0.6B se realizaron
en CPU. No atribuirlas a la GPU.

En la auditoría del 26-11-2026 se observaron:

- RAM total: 15.541.068 kB.
- RAM disponible: 7.502.508 kB.
- Swap total: 33.554.428 kB.
- Swap libre: 24.780.404 kB.
- Espacio libre en disco: aproximadamente 165 GB.

Son valores puntuales, no garantías para futuras pruebas.

---

## 3. Procedencia del código

Repositorio upstream:

https://github.com/alesha-pro/llm.asm

Repositorio local inicial:

`~/llm-asm-qwen3-experiment/source`

Commit de referencia:

`48feccbfd57cb669440f31ff64958d95bb8b848e`

Mensaje:

`Add FAST_Q8=1 INT8xINT8 AVX2+F16C kernel, .asmbin v2 FP16 scales, and parallel GQA attention`

La copia inicial se obtuvo mediante clonación superficial.

### Clon independiente para Qwen3-4B

Ruta:

`~/leones-work/llm.asm-qwen4B-reference`

Se creó fuera del árbol Git de LEONES para disponer de una
referencia independiente. Su propósito es estudiar el código,
comparar implementaciones e identificar las relaciones entre
ensamblador, exportador y formato de pesos.

No confundir este clon con el código de trabajo del subproyecto.

---

## 4. Arquitectura conocida del motor

llm.asm contiene una implementación de inferencia en ensamblador
x86-64, con optimizaciones AVX2, FMA y F16C.

La fase Linux incluye:

- Motor estático ELF.
- Tokenizer BPE integrado.
- Codificación y decodificación UTF-8.
- Plantilla conversacional Qwen.
- Forward pass Transformer.
- Grouped Query Attention (GQA).
- QK-Norm.
- RoPE.
- SwiGLU.
- KV-cache.
- Inferencia de una sola petición.
- Modo conversacional multi-turn.
- Kernels SIMD y cálculo Q8_0.

Binario utilizado:

`build/asm-llm`

Características observadas:

- ELF de 64 bits.
- Enlazado estático.
- Tamaño aproximado: 14.712 bytes.
- Sin sección dinámica en la comprobación realizada.

El repositorio también incluye una fase bare-metal que permite
arrancar un entorno de inferencia sin Linux convencional.
Esta capacidad es especialmente relevante para el objetivo final.

---

## 5. Formato ASMBIN

El motor no consume directamente los archivos originales de
Hugging Face. El flujo probado fue:

1. Descargar el modelo original.
2. Leer `config.json`.
3. Leer `model.safetensors`.
4. Leer `tokenizer.json`.
5. Convertir los pesos a `.asmbin`.
6. Ejecutar el motor con el archivo convertido.

En Qwen3-0.6B se utilizó cuantización Q8_0, formato ASMBIN v2,
escalas FP16 y tokenizer BPE incorporado.

El formato contiene cabecera, tokenizer, embeddings, capas
Transformer y normalización final.

La ampliación a Qwen3-4B exige estudiar dimensiones variables,
metadatos, offsets, strides, límites de contexto y supuestos
estáticos del exportador y del motor.

---

## 6. Primer modelo: Qwen3-0.6B

El primer ciclo experimental se realizó en:

`~/llm-asm-qwen3-experiment`

Repositorio de trabajo:

`~/llm-asm-qwen3-experiment/source`

Modelo original: `Qwen/Qwen3-0.6B`.

Arquitectura identificada en la configuración:

| Parámetro | Valor |
|---|---:|
| Arquitectura | Qwen3ForCausalLM |
| hidden_size | 1024 |
| Capas Transformer | 28 |
| Attention heads | 16 |
| KV heads | 8 |
| head_dim | 128 |
| intermediate_size | 3072 |
| vocab_size | 151936 |
| Pesos originales | BF16 |
| Embeddings | Tied embeddings |

Archivos originales:
- `config.json`: 726 bytes.
- `model.safetensors`: 1.503.300.328 bytes.
- `tokenizer.json`: 11.422.654 bytes.

Safetensors validado: 311 tensores. Tokenizer BPE: 151.387 merges.
El modelo original BF16 se conservó intacto.

## 7. Conversión a ASMBIN

La exportación se hizo con el entorno Python virtual del proyecto.
No se instalaron PyTorch ni dependencias de inferencia globales.

Entorno:
- Python 3.14.4.
- NumPy 2.5.5.
- Hugging Face CLI global 2.0.0.

Comando empleado:

```bash
nice -n 10 ionice -c 2 -n 7 \
 "$PROJECT/.venv/bin/python" scripts/export_weights.py \
 --model-dir "$MODEL_DIR" --out "$OUTPUT" --scale-dtype fp16
```

Artefacto: `models/qwen3-0.6b-q8_0.asmbin`.

Características:
- ASMBIN v2.
- Cuantización Q8_0.
- Escalas FP16.
- Flags `0x7`.
- 28 capas exportadas.
- 151.387 merges.
- `tok_bytes`: 976.309 bytes.
- Embeddings y `lm_head` exactos: `max_diff=0`.

Tamaño: 643.469.504 bytes (613,66 MiB).
SHA-256: `14dc92c18dfd4182be6627558f716b9e7c5ebf9bc657b0ff700304e5a6502796`.
Tiempo registrado: 11,34 segundos.

## 8. Compilación y pruebas matemáticas

Herramientas registradas:
- NASM 3.01.
- GNU binutils 2.46.
- GNU Make 4.4.1.

Compilación:

```bash
make inference test-math FAST_Q8=1
```

Validación:

```bash
"$PROJECT/.venv/bin/python" scripts/test_math.py build/test_math
```

Resultados:

| Kernel | Error máximo |
|---|---:|
| fast_expf | 1,394e-07 relativo |
| sincos | 2,94e-08 absoluto |
| RoPE | 4,366e-14 |
| RMSNorm | 2,056e-07 |
| SiLU | 6,774e-08 |
| Matmul Q8_0 v1 | 9,537e-07 |
| Matmul Q8_0 v2 | 5,960e-07 |

Todos los kernels matemáticos/SIMD evaluados superaron las pruebas.
`make check` confirmó un ELF de 64 bits estático, sin sección
dinámica, de aproximadamente 14.712 bytes.

**No ejecutar `make all` en la campaña inicial:** construye también
las fases bare-metal OS y training. La validación del motor Linux
se limita a los objetivos `inference`, `test-math` y `check`.

## 9. Inferencia y rendimiento Qwen3-0.6B

La primera inferencia produjo texto coherente. Se ejecutó en CPU,
no en la RTX 3050.

Medición inicial a 8 hilos, 64 tokens:
- Prefill: aproximadamente 83 tok/s.
- Decode: 59,74 tok/s.
- RSS: aproximadamente 634,4 MiB.
- Sin swap observado.

Se compararon 1, 4, 8, 12 y 16 hilos. En tres repeticiones alternas
de 4 y 12 hilos se obtuvieron estas medianas:

| Hilos | Decode | Prefill |
|---:|---:|---:|
| 4 | 62,28 tok/s | 86,09 tok/s |
| 12 | 62,49 tok/s | 88,30 tok/s |

La diferencia de decode fue aproximadamente 0,34 %, sin evidencia
de una mejora práctica significativa con 12 hilos. Se eligieron
4 hilos como referencia provisional por menor paralelismo.

Otra ejecución a cuatro hilos registró 87,02 tok/s de prefill,
62,84 tok/s de decode y RSS aproximado de 634,4 MiB.

Con prompts de aproximadamente 20, 43 y 97 tokens y generación
máxima de 128 tokens, decode quedó entre 60,5 y 61,2 tok/s y
prefill entre 74 y 85 tok/s. Tres muestras no permiten inferir
una tendencia estadística.

Prueba de texto larga anterior, contexto 512:
- 78 tokens de entrada.
- Prefill: 87,25 tok/s.
- Decode: 62,37 tok/s.
- RSS: 651.896 KiB (aprox. 636,6 MiB).

## 10. Escalado de contexto Qwen3-0.6B

El contexto máximo declarado por la cabecera del motor era 4096.
El valor por defecto de `-c` era 2048. Valores superiores se
ajustaban al máximo de cabecera.

La KV-cache FP32 teórica para Qwen3-0.6B:

`2 × 28 capas × contexto × 1024 KV-dim × 4 bytes`.

| Entrada sintética | Contexto | Prefill | Decode | RSS máximo | Tiempo |
|---:|---:|---:|---:|---:|---:|
| 400 | 512 | 80,76 tok/s | 54,58 tok/s | 698,0 MiB | 5,23 s |
| 900 | 1024 | 69,06 tok/s | 45,50 tok/s | 808,1 MiB | 13,37 s |
| 1800 | 2048 | 54,88 tok/s | 32,51 tok/s | 1.004,1 MiB | 33,28 s |
| 3800 | 4096 | 34,57 tok/s | 18,42 tok/s | 1.441,5 MiB | 1:50,79 |
| 4080 | 4096 | 33,09 tok/s | 17,27 tok/s | 1.501,0 MiB | 2:04,22 |

Las cinco pruebas usaron el token ID 198 repetido, cuatro hilos
y generación máxima de 16 tokens. Se validaron el número exacto
de tokens, generación, código de salida 0 y ausencia de swap.

La última prueba ocupó exactamente 4096/4096 posiciones y superó
la prueba funcional de frontera.

Estimación KV-cache Qwen3-0.6B:

| Contexto | KV-cache |
|---:|---:|
| 512 | 112 MiB |
| 1024 | 224 MiB |
| 2048 | 448 MiB |
| 4096 | 896 MiB |

La reserva virtual no implica que todas las páginas estén residentes.
El RSS total no debe atribuirse exclusivamente a la KV-cache.

**Limitaciones metodológicas:** entradas sintéticas, una ejecución
por tamaño, sin medianas y sin evaluación de calidad lingüística.
No permiten establecer causalidad ni extrapolar rendimiento a
otros modelos o máquinas.

## 11. Logs y archivo de resultados Qwen3-0.6B

Logs completos en:

`~/llm-asm-qwen3-experiment/logs/context-scaling/`

- `direct-400-tokens.log`
- `direct-900-tokens.log`
- `direct-1800-tokens.log`
- `direct-3800-tokens.log`
- `direct-4080-boundary.log`

El intercambio local fue archivado en:

`~/intercambio/leones-llm-asm-qwen3-2026-11-25`

Incluye los logs y `SHA256SUMS`, con hashes verificados.

Informe integrado en LEONES:

`docs/benchmarks/llm-asm-qwen3-0.6b-context-2026-11-25.md`

Los artefactos brutos se encuentran en:

`docs/benchmarks/artifacts/llm-asm-qwen3-0.6b-context-2026-11-25/`

El informe se incorporó mediante PR #288, merge squash
`7ea1aca9ff162328ecbb172087014063dac38e8d`.

---

## 12. Auditoría estática de compatibilidad con Qwen3-4B

Esta sección registra una inspección del código upstream en el
commit `48feccbfd57cb669440f31ff64958d95bb8b848e`. No es todavía
una prueba de exportación, compilación ni inferencia con Qwen3-4B.

### 12.1 Configuración oficial del modelo

Fuente primaria: [Qwen/Qwen3-4B config.json](https://huggingface.co/Qwen/Qwen3-4B/blob/main/config.json).

| Parámetro | Qwen3-0.6B | Qwen3-4B |
|---|---:|---:|
| hidden_size | 1024 | 2560 |
| intermediate_size | 3072 | 9728 |
| num_hidden_layers | 28 | 36 |
| num_attention_heads | 16 | 32 |
| num_key_value_heads | 8 | 8 |
| head_dim | 128 | 128 |
| vocab_size | 151936 | 151936 |
| max_position_embeddings | 32768 (config del experimento) | 40960 |
| rope_theta | 1000000 | 1000000 |
| rms_norm_eps | 1e-6 | 1e-6 |
| tie_word_embeddings | true | true |
| rope_scaling | — | null |

La arquitectura declarada es Qwen3ForCausalLM. Se mantienen
QK-Norm, RoPE, SwiGLU, GQA y el vocabulario Qwen3. Las dimensiones
de matrices cambian, pero siguen siendo múltiplos de 32.

### 12.2 Exportador: hallazgos

Archivo upstream: `scripts/export_weights.py`.

El exportador **no está limitado estructuralmente a las dimensiones
del modelo 0.6B**: lee hidden_size, intermediate_size, número de
capas, cabezas, KV heads, head_dim y vocab_size desde config.json.

También construye las formas esperadas de las siete matrices por
capa a partir de esas dimensiones y valida las formas de los
tensores Safetensors.

El cuantizador Q8_0 exige que K sea múltiplo de 32. En Qwen3-4B,
las dimensiones de entrada relevantes son 2560, 4096, 1024 y 9728;
todas cumplen esa condición.

Por tanto, el exportador parece reutilizable para Qwen3-4B en
términos de dimensiones y empaquetado. No debe declararse compatible
hasta verificar:
- Nombres y formas reales de todos los tensores del checkpoint.
- Igualdad real de embeddings y lm_head si se declaran tied.
- Vocabulario, merges, added_tokens y tokenizer JSON.
- Ausencia de tensores adicionales o variantes de arquitectura.
- Integridad del ASMBIN resultante y paridad numérica.

Las limitaciones explícitas detectadas en el exportador son
principalmente descriptivas: docstring, ejemplos y argumentos CLI
mencionan Qwen3-0.6B. El valor por defecto de contexto de exportación
es 4096, no el máximo 40960 del config de Qwen3-4B.

La tabla hash BPE tiene 524.288 entradas y se dimensionó para
151.387 merges. El vocabulario oficial de Qwen3-4B coincide en
tamaño con Qwen3-0.6B, pero el número y contenido de merges debe
verificarse contra el tokenizer descargado.

### 12.3 Motor NASM: hallazgos

Archivos principales inspeccionados:
- `shared/constants.inc`
- `shared/transformer.asm`
- `shared/matmul.asm`
- `shared/tokenizer.asm`
- `01-qwen3-inference/main.asm`

El cargador ASMBIN lee del encabezado las dimensiones, el número
de capas, las cabezas, las dimensiones Q/KV, vocabulario,
contexto y stride de capa. Calcula dinámicamente q_dim, kv_dim,
las asignaciones de activaciones y el tamaño de KV-cache.

El forward pass recorre el número de capas del encabezado y calcula
los offsets de matrices a partir de dim, q_dim, kv_dim, hidden_dim
y layer_stride. Esto es favorable para ampliar dimensiones sin
cambiar el formato.

El límite estático `Q8_MAX_K=16384` del kernel de matmul cubre
el mayor K de Qwen3-4B (9728). Los tamaños de cabeza siguen siendo
128. La tabla de tokens especiales Qwen3 coincide con los IDs
de configuración publicados.

No obstante, hay comentarios, mensajes de ayuda y documentación
que identifican expresamente el motor como Qwen3-0.6B. Además,
el loader confía en offsets y tamaños almacenados en el archivo;
la validación de rangos y coherencia del encabezado debe revisarse
antes de admitir artefactos de mayor tamaño.

La inspección estática no demuestra ausencia de errores en el
forward pass para dimensiones nuevas. Se requiere una prueba
numérica de extremo a extremo.

### 12.4 Estimación de almacenamiento Q8_0

Con escalas FP16, cada fila de K elementos ocupa:

`K + 2 × (K / 32) = 1,0625 × K bytes`.

Estimación calculada desde las formas oficiales de Qwen3-4B y
el formato row-split del exportador:

| Tensor | Filas | Columnas | Bytes aproximados |
|---|---:|---:|---:|
| Embeddings | 151936 | 2560 | 413.265.920 |
| Q projection/capa | 4096 | 2560 | 11.141.120 |
| K projection/capa | 1024 | 2560 | 2.785.280 |
| V projection/capa | 1024 | 2560 | 2.785.280 |
| O projection/capa | 2560 | 4096 | 11.141.120 |
| Gate projection/capa | 9728 | 2560 | 26.460.160 |
| Up projection/capa | 9728 | 2560 | 26.460.160 |
| Down projection/capa | 2560 | 9728 | 26.460.160 |

La estimación agregada de matrices y normas es aproximadamente
4.275.185.664 bytes (3,982 GiB), antes de tokenizer, cabecera
y cualquier padding adicional. Debe confirmarse con el exportador
real y el tamaño final del archivo.

### 12.5 Estimación de KV-cache y memoria

Qwen3-4B tiene 36 capas y kv_dim = 8 × 128 = 1024.
Con K y V FP32:

`KV bytes = 2 × 36 × contexto × 1024 × 4`.

| Contexto | KV-cache estimada |
|---:|---:|
| 512 | 144 MiB |
| 1024 | 288 MiB |
| 2048 | 576 MiB |
| 4096 | 1152 MiB (1,125 GiB) |
| 8192 | 2304 MiB (2,25 GiB) |
| 40960 | 11520 MiB (11,25 GiB) |

A 4096 tokens, pesos Q8_0 estimados más KV-cache rondan 5,11 GiB,
sin contar buffers, tokenizer, runtime, sistema operativo ni
páginas temporales. La máquina MSI tiene aproximadamente 14 GiB
de RAM y 4 GiB de VRAM; el motor actual es CPU, por lo que la VRAM
no se debe sumar a la memoria disponible del proceso.

**Hipótesis de planificación:** comenzar con contexto 512 o 1024
para validar corrección y memoria; ampliar después a 2048 y 4096.
No probar inicialmente 40960 en el MSI. Aunque figure en la
configuración del modelo, el contexto operativo debe elegirse
según memoria real y latencia.

### 12.6 Riesgos y cuestiones abiertas

1. Confirmar la compatibilidad real del tokenizer y sus merges.
2. Confirmar todos los nombres, formas y dtypes de Safetensors.
3. Medir el pico de RAM del exportador: la conversión BF16 a FP32
   y las matrices temporales pueden elevar el uso durante la
   cuantización, especialmente en embeddings.
4. Validar strides, alineación y offsets del ASMBIN.
5. Revisar límites y validaciones del encabezado en el loader.
6. Confirmar que el kernel Q8_0 procesa correctamente K=9728.
7. Comparar logits y tokens greedy con una implementación de
   referencia independiente.
8. Medir RSS, swap, prefill, decode y latencia inicial.
9. Evaluar si el rendimiento de cuatro hilos sigue siendo adecuado;
   no asumir que la configuración del 0.6B se mantiene óptima.
10. Mantener el modelo original y los resultados de 0.6B intactos.

**Conclusión de auditoría:** el diseño del formato ASMBIN y buena
parte del motor ya son parametrizados y no muestran un bloqueo
obvio para las dimensiones de Qwen3-4B. El exportador parece
adaptable con cambios descriptivos menores, pero la compatibilidad
sigue siendo provisional hasta validar los tensores y ejecutar
pruebas numéricas. No se debe modificar el código upstream de
referencia; cualquier adaptación se hará en una rama de trabajo
controlada y con pruebas de regresión para Qwen3-0.6B.

---

### 12.7 Bloqueo identificado para la fase bare-metal actual

Se inspeccionaron también `02-baremetal-os/runtime.asm`,
`os_constants.inc`, `boot.asm`, `kernel.asm` y `linker.ld`.

La fase bare-metal actual no puede cargar directamente el Qwen3-4B
Q8_0 estimado:

1. El arranque Multiboot 1 representa las direcciones de módulo con
   campos de 32 bits.
2. `boot.asm` crea tablas de páginas de identidad para 0–4 GiB,
   mediante páginas enormes de 2 MiB.
3. `runtime.asm` busca la mayor región utilizable por debajo de
   `0xF0000000` (3,75 GiB).
4. El kernel consume el modelo como módulo Multiboot, sin copia.
5. Las matrices Q8_0 estimadas ocupan 4.275.185.664 bytes, más de
   4 GiB, antes de tokenizer y cabecera.

Por tanto, el modelo completo no cabe en el espacio de direcciones
que el arranque actual mapea ni en la región que el allocator actual
puede gestionar. Aumentar solamente la RAM asignada a QEMU no resuelve
el límite de direccionamiento y del protocolo de módulos.

**Conclusión:** la adaptación Linux y la adaptación bare-metal son
dos campañas distintas. El soporte Linux puede investigarse con el
cargador y las asignaciones dinámicas actuales, sujeto a validación.
Qwen3-4B bare-metal exige rediseñar el arranque y la memoria física.

Opciones para una fase posterior:
- Migrar el arranque a UEFI y obtener un mapa de memoria de 64 bits.
- Mapear RAM física por encima de 4 GiB con tablas de páginas adecuadas.
- Sustituir los módulos Multiboot 1 de 32 bits por un protocolo de carga
  con direcciones físicas de 64 bits.
- Crear un allocator físico capaz de mapear regiones de memoria alta,
  sin exigir una región contigua inferior a 3,75 GiB.
- Evaluar carga segmentada/paginada si el diseño de almacenamiento
  y el hardware lo justifican.

No mezclar este rediseño con la primera campaña Linux. Primero se
validará Qwen3-4B en Linux; después se abordará bare-metal preservando
las pruebas de regresión Qwen3-0.6B.

## 13. Plan de trabajo remoto antes de usar el MSI

Las siguientes tareas no requieren todavía el equipo local:

1. Completar auditoría estática de los archivos NASM y del formato.
2. Preparar especificación de compatibilidad Qwen3-4B.
3. Diseñar pruebas unitarias de dimensiones, strides y offsets.
4. Diseñar un validador de encabezado ASMBIN con límites y checks.
5. Preparar un plan de exportación con observabilidad de memoria.
6. Definir pruebas de paridad con PyTorch/Transformers.
7. Definir el protocolo de medición y criterios de aceptación.
8. Separar cambios genéricos del motor de los cambios exclusivos
   de Qwen3-4B.

## 14. Criterio para solicitar el MSI

Se solicitará intervención local cuando exista una tarea que
requiera una o varias de estas capacidades:
- Clonar o sincronizar el árbol de trabajo local.
- Compilar NASM/ELF y ejecutar los tests nativos.
- Descargar el checkpoint oficial y verificar sus archivos.
- Medir memoria real, swap, RSS y tiempos de exportación.
- Ejecutar inferencia y comparar logits/tokens.
- Medir prefill, decode y escalado de contexto.

Hasta entonces, la auditoría, el diseño, la documentación y los
cambios de código/documentación que puedan revisarse de forma
estática se desarrollarán directamente en GitHub.
