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
