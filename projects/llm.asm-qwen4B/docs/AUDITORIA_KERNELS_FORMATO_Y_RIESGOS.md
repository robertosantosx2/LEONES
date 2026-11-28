# Auditoría de kernels, formato ASMBIN y riesgos de Qwen3-4B

**Proyecto:** llm.asm-qwen4B  
**Referencia upstream auditada:** `alesha-pro/llm.asm`  
**Commit upstream:** `48feccbfd57cb669440f31ff64958d95bb8b848e`  
**Fecha:** 26 de noviembre de 2026  
**Tipo de trabajo:** inspección estática del código; no equivale a compilación ni ejecución.

---

## 1. Alcance y fuentes

Se inspeccionaron los siguientes archivos en el commit fijado:

- [`shared/transformer.asm`](https://github.com/alesha-pro/llm.asm/blob/48feccbfd57cb669440f31ff64958d95bb8b848e/shared/transformer.asm)
- [`shared/matmul.asm`](https://github.com/alesha-pro/llm.asm/blob/48feccbfd57cb669440f31ff64958d95bb8b848e/shared/matmul.asm)
- [`shared/tokenizer.asm`](https://github.com/alesha-pro/llm.asm/blob/48feccbfd57cb669440f31ff64958d95bb8b848e/shared/tokenizer.asm)
- [`shared/constants.inc`](https://github.com/alesha-pro/llm.asm/blob/48feccbfd57cb669440f31ff64958d95bb8b848e/shared/constants.inc)
- [`scripts/export_weights.py`](https://github.com/alesha-pro/llm.asm/blob/48feccbfd57cb669440f31ff64958d95bb8b848e/scripts/export_weights.py)
- [`01-qwen3-inference/main.asm`](https://github.com/alesha-pro/llm.asm/blob/48feccbfd57cb669440f31ff64958d95bb8b848e/01-qwen3-inference/main.asm)
- [`02-baremetal-os/runtime.asm`](https://github.com/alesha-pro/llm.asm/blob/48feccbfd57cb669440f31ff64958d95bb8b848e/02-baremetal-os/runtime.asm)
- [`02-baremetal-os/boot.asm`](https://github.com/alesha-pro/llm.asm/blob/48feccbfd57cb669440f31ff64958d95bb8b848e/02-baremetal-os/boot.asm)
- [`02-baremetal-os/kernel.asm`](https://github.com/alesha-pro/llm.asm/blob/48feccbfd57cb669440f31ff64958d95bb8b848e/02-baremetal-os/kernel.asm)

El objetivo es decidir qué se puede reutilizar, qué requiere validación y qué debe endurecerse antes de exportar y ejecutar Qwen3-4B.

## 2. Kernel Q8_0: compatibilidad dimensional

### 2.1 Límites estáticos

En `shared/matmul.asm`:

```nasm
%define Q8_MAX_K 16384
```

El buffer global de activaciones cuantizadas se reserva para ese máximo:

```nasm
q8_xq: resb Q8_MAX_K
q8_xs: resb (Q8_MAX_K / 32) * 4
```

La rutina `quantize_x_q8_0` documenta como precondición que K sea múltiplo de 32 y no supere `Q8_MAX_K`. La rutina procesa K/32 bloques.

Dimensiones relevantes de Qwen3-4B:

| Operación | K |
|---|---:|
| Embedding / Q, K, V / gate / up | 2560 |
| Proyección O | 4096 |
| Proyección down | 9728 |

Todas son múltiplos de 32 y el máximo, 9728, es inferior a 16384. No aparece un bloqueo por capacidad del buffer Q8_0 para esta arquitectura.

**Importante:** el límite está expresado como precondición y tamaño de buffer; el loader no demuestra que valide todas las dimensiones del modelo contra él. El validador debe imponerlo antes de aceptar un artefacto.

### 2.2 Formato de fila y escalas

El exportador empaqueta cada fila como:

- K bytes de pesos int8.
- K/32 escalas.
- Dos bytes por escala para ASMBIN v2 FP16.
- Cuatro bytes por escala para ASMBIN v1 FP32.

Por tanto:

`row_bytes(K, v2) = K + 2(K/32) = 17K/16`

`row_bytes(K, v1) = K + 4(K/32) = 9K/8`

Los kernels leen los pesos y las escalas por separado. El stride de fila es determinista para cada K y versión. No se debe sustituir por una cuantización Q8_0 con layout GGUF u otro layout sin adaptar el kernel.

### 2.3 Conclusión del kernel

El kernel existente parece cubrir las dimensiones de Qwen3-4B sin cambiar el tamaño de sus buffers. La compatibilidad matemática no está demostrada por esta inspección: hay que comparar logits y resultados de inferencia con una implementación de referencia.

---

## 3. Buffers de activación y KV-cache

En `shared/transformer.asm`, el tamaño del arena se calcula usando las dimensiones del encabezado:

- X y XB: dim.
- Q y salida de atención: q_dim.
- K y V: kv_dim.
- Scores: n_heads × max_seq.
- Gate y up: hidden_dim.
- Logits y probabilidades: vocab_size.
- Activaciones Q8: máximo entre hidden_dim y q_dim.
- KV-cache: n_layers × max_seq × kv_dim × 4 bytes por cada una de K y V.

Para Qwen3-4B:

- dim = 2560.
- hidden_dim = 9728.
- q_dim = 32 × 128 = 4096.
- kv_dim = 8 × 128 = 1024.
- n_layers = 36.

La reserva Q8 cubre hidden_dim 9728, que es mayor que q_dim 4096 y menor que Q8_MAX_K 16384.

La KV-cache FP32 es:

`2 × 36 × contexto × 1024 × 4 bytes`

| Contexto | K + V |
|---:|---:|
| 512 | 144 MiB |
| 1024 | 288 MiB |
| 2048 | 576 MiB |
| 4096 | 1152 MiB |
| 8192 | 2304 MiB |

La fórmula es específica de la arquitectura Qwen3-4B con 8 KV heads y head_dim 128. No debe generalizarse a otras familias sin recalcularla.

El arena incluye además buffers de activación, scores de atención, logits, tokenizer y runtime. La suma de pesos y KV-cache no equivale al RSS total.

---

## 4. Hallazgo prioritario: validación insuficiente del encabezado ASMBIN

### 4.1 Comportamiento observado

En `model_init` de `shared/transformer.asm`, el flujo Linux:

1. Abre el archivo.
2. Ejecuta fstat y obtiene el tamaño.
3. Mapea el archivo completo.
4. Comprueba magic y versión.
5. Lee las dimensiones y offsets del encabezado.
6. Calcula punteros internos sumando offsets a la base del mmap.
7. Reserva el arena usando las dimensiones leídas.

La inspección de esta ruta no encontró comprobaciones explícitas suficientes para demostrar que:

- El archivo mide al menos 128 bytes antes de leer el encabezado completo.
- `HDR_FILE_SIZE` coincide con el tamaño real del archivo.
- Los offsets de tokenizer, embeddings, capas y norma final están dentro del archivo.
- Las secciones no se solapan.
- Los sub-offsets del tokenizer están dentro de la sección tokenizer.
- El stride de capa y el número de capas caben en el archivo.
- Las multiplicaciones usadas para calcular tamaños no desbordan.
- Las dimensiones no son cero ni incompatibles entre sí.
- `n_heads` es divisible por `n_kv_heads`.
- El valor de K no supera Q8_MAX_K.
- `HDR_HT_MASK` corresponde al tamaño de tabla que usa el tokenizer.

La constante `HDR_FILE_SIZE` está definida en `shared/constants.inc`, y el exportador la escribe en el encabezado. La búsqueda de referencias en el código inspeccionado solo encontró su definición; no se encontró una comprobación del campo en `model_init`.

La ruta de carga también calcula `q_dim` y `kv_dim` a partir de las dimensiones recibidas, y el forward pass usa esos valores para calcular offsets. Sin validación previa, un archivo truncado o un encabezado inconsistente puede producir accesos fuera del mmap o tamaños de arena incorrectos.

### 4.2 Impacto para Qwen3-4B

No se ha demostrado que un archivo Qwen3-4B generado por el exportador actual provoque un fallo. El riesgo es de robustez e integridad del formato: el modelo es más grande, y los offsets y tamaños deben validarse antes de ejecutar el forward pass.

No debemos confundir:
- **Compatibilidad dimensional:** las formas de Qwen3-4B caben en los límites del kernel.
- **Integridad del artefacto:** el archivo realmente contiene todas las regiones que el encabezado declara.
- **Corrección numérica:** el motor calcula resultados correctos para el modelo.

Son tres condiciones distintas y las tres deben aprobarse.

### 4.3 Requisito de diseño

Antes de permitir la inferencia, un validador debe comprobar como mínimo:

1. Tamaño real del archivo y tamaño declarado en encabezado.
2. Magic, versión y coherencia de flags.
3. Dimensiones positivas y relaciones entre dim, heads, KV heads y head_dim.
4. Divisibilidad de heads por KV heads.
5. K múltiplo de 32 y K no mayor que Q8_MAX_K.
6. Contexto positivo y dentro del máximo declarado.
7. Offsets alineados y regiones no solapadas.
8. Tamaño calculado de embeddings, capas, matrices y norma final.
9. Consistencia de layer_stride con las formas y la versión de escalas.
10. Límites y monotonicidad de los offsets del tokenizer.
11. Tamaño y máscara de la tabla BPE.
12. IDs de token, IDs combinados y ranks dentro de sus rangos.

La comprobación de rangos debe usar aritmética que detecte overflow. No se debe validar una expresión `offset + length` después de que haya podido desbordar; primero se debe comprobar `offset <= file_size` y luego `length <= file_size - offset`.

El loader NASM debe conservar una segunda capa de defensa, incluso si se añade un validador Python previo. La seguridad del formato no debe depender de que siempre se invoque una herramienta externa.

---

## 5. Tokenizer: límites y compatibilidad

El tokenizer de ensamblador espera una tabla BPE de 524.288 entradas de 16 bytes, con máscara 524.287 y hash Fibonacci. El exportador construye esa tabla a partir de `tokenizer.json`.

El formato de tokenizer almacena:
- byte-to-token: 256 IDs uint32.
- offsets por token: vocab_size + 1 uint32.
- bytes UTF-8 concatenados para cada token.
- tabla de merges hash de 524.288 entradas.

El loader resuelve punteros a estas estructuras directamente desde el mmap. El tokenizer los usa sin asignaciones adicionales.

Para Qwen3-4B el vocabulario de configuración es 151.936, igual al valor conocido en Qwen3-0.6B. Esto no demuestra que el contenido de `tokenizer.json` sea idéntico. Antes de declarar compatibilidad deben verificarse:
- vocabulario completo y correspondencia ID/pieza.
- added_tokens y tokens especiales.
- merges y su orden/rank.
- byte encoder/decoder.
- tokenización exacta en un corpus de regresión.

La prueba de referencia debe comparar IDs token a token con Hugging Face AutoTokenizer, no solo el texto decodificado.

---

## 6. Exportador: riesgo de memoria pico

El exportador convierte BF16 a FP32 para cuantizar matrices. En la lectura BF16 crea un buffer de bytes y un array uint32 intermedio antes de reinterpretar como float32. La cuantización genera además arrays temporales para bloques, máximos, escalas, pesos cuantizados y bytes empaquetados.

Para Qwen3-4B, la matriz de embeddings tiene forma 151936 × 2560. En BF16 ocupa aproximadamente 777 MB decimales; su representación FP32 ocupa aproximadamente 1,55 GB decimales. La cuantización empaquetada de embeddings ocupa aproximadamente 413 MB decimales.

La exportación completa puede tener un pico de memoria sensiblemente mayor que el tamaño final del modelo. La inspección estática no permite fijar ese pico con precisión.

Requisitos antes de ejecutar:
- No cargar todas las matrices del modelo simultáneamente.
- Liberar explícitamente temporales entre tensores.
- Evitar copias innecesarias durante BF16→FP32 y cuantización.
- Considerar cuantización por bloques o filas para embeddings grandes.
- Registrar RSS máximo, memoria disponible, swap y tiempo.
- Mantener intactos los Safetensors originales.
- Escribir primero a un archivo temporal y renombrar solo tras completar y validar el resultado.
- No ejecutar exportación y benchmark concurrentemente.

El primer intento local debe realizarse con monitorización y sin otras cargas intensivas.

---

## 7. Bare-metal: límite de direccionamiento confirmado en código

La inspección de `boot.asm`, `runtime.asm` y `kernel.asm` confirma:

- Entrada Multiboot 1 de 32 bits.
- Tablas de páginas de identidad para 0–4 GiB con páginas de 2 MiB.
- Direcciones de módulos Multiboot representadas en campos de 32 bits.
- El allocator selecciona una región libre por debajo de `0xF0000000` (3,75 GiB).
- El modelo se consume desde un módulo cargado en RAM.

La estimación corregida de embeddings, matrices y normas es 4.274.448.384 bytes (3,981 GiB), antes de tokenizer, cabecera y padding. Por tanto, las matrices por sí solas quedan ligeramente por debajo de 4 GiB binarios; no es correcto describirlas como un archivo superior a 4 GiB.

El problema bare-metal sigue siendo crítico, pero debe expresarse con precisión: el mapa identidad actual termina en 4 GiB y los campos de módulo Multiboot 1 son de 32 bits. Un módulo de aproximadamente 3,99 GiB solo podría quedar íntegramente dentro de ese mapa si su dirección física de inicio estuviera en una ventana muy pequeña próxima a cero. Esa región también contiene el kernel, estructuras de arranque y memoria que el runtime necesita. Además, el allocator busca RAM libre por debajo de 3,75 GiB y excluye el módulo.

La inspección estática no permite afirmar que cualquier colocación física sea matemáticamente imposible, porque no se ha ejecutado el cargador con un módulo de ese tamaño. Sí permite concluir que el diseño actual no ofrece una ruta viable y general para cargar y reservar memoria de trabajo para Qwen3-4B. El soporte bare-metal requiere rediseñar el protocolo de carga y el mapeo/allocator de memoria física, y validarlo por separado.

Este problema no afecta por sí mismo a la ruta Linux x86-64.

---

## 8. Decisiones de ingeniería

1. Mantener el commit upstream de referencia inmutable.
2. Separar las modificaciones genéricas del loader de los cambios específicos de Qwen3-4B.
3. Diseñar y probar un validador ASMBIN independiente antes de modificar el loader.
4. Añadir comprobaciones equivalentes en NASM para no depender exclusivamente del validador Python.
5. Mantener Qwen3-0.6B como prueba de regresión obligatoria.
6. Verificar tokenizer antes de exportar el checkpoint completo.
7. Empezar con contexto 512 o 1024 en el primer test Qwen3-4B.
8. No intentar el contexto máximo de 40960 en el MSI.
9. No iniciar todavía el rediseño bare-metal.
10. No afirmar compatibilidad hasta completar exportación, carga, paridad numérica y pruebas de rendimiento.

## 9. Próximos entregables antes de pedir el MSI

- Especificación formal del encabezado y layout ASMBIN v1/v2.
- Validador independiente con pruebas de archivos truncados, offsets inválidos, overflow, secciones solapadas y dimensiones no soportadas.
- Pruebas sintéticas del cálculo de strides para Qwen3-0.6B y Qwen3-4B.
- Diseño del endurecimiento del loader NASM.
- Diseño de exportación con memoria pico controlada.
- Plan de comparación de logits y tokenización.
- Lista cerrada de comandos de compilación y prueba local, por fases.

**Criterio para pasar a pruebas locales:** no pedir el MSI hasta que la especificación, el validador y las pruebas sintéticas estén preparados y revisados. La primera intervención local debe ser pequeña, reversible y con logs completos.
