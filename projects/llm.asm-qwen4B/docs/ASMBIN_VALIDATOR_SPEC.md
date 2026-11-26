# Especificación del validador ASMBIN v1/v2

**Estado:** diseño previo a implementación  
**Referencia:** `alesha-pro/llm.asm` commit `48feccbfd57cb669440f31ff64958d95bb8b848e`  
**Propósito:** validar estructura, dimensiones y rangos antes de mapear o ejecutar un modelo.

Esta especificación describe el layout escrito por `scripts/export_weights.py` y consumido por `shared/transformer.asm`. No es una especificación universal de otros formatos Q8_0.

---

## 1. Reglas generales

- Todas las cantidades enteras se almacenan little-endian.
- Las secciones principales y las matrices comienzan alineadas a 64 bytes.
- El encabezado tiene 128 bytes.
- Las matrices usan Q8_0 row-split.
- El tamaño de fila depende de K y de la versión de escalas.
- Las normas se almacenan como FP32.
- El archivo es mapeable directamente y los offsets del encabezado son relativos al inicio del archivo.

El validador debe usar lecturas acotadas y aritmética con comprobación de overflow. Nunca debe confiar en un offset antes de verificar que cabe dentro del tamaño real del archivo.

## 2. Encabezado de 128 bytes

| Offset | Tipo | Campo |
|---:|---|---|
| 0 | 4 bytes | magic `ASML` |
| 4 | u32 | version: 1 o 2 |
| 8 | u32 | dim |
| 12 | u32 | hidden_dim |
| 16 | u32 | n_layers |
| 20 | u32 | n_heads |
| 24 | u32 | n_kv_heads |
| 28 | u32 | head_dim |
| 32 | u32 | vocab_size |
| 36 | u32 | max_seq_len |
| 40 | f32 | rms_norm_eps |
| 44 | f32 | rope_theta |
| 48 | u32 | eos_1 |
| 52 | u32 | eos_2 |
| 56 | u32 | ht_mask |
| 60 | u32 | flags |
| 64 | u64 | off_tokenizer |
| 72 | u64 | off_embed |
| 80 | u64 | off_layers |
| 88 | u64 | layer_stride |
| 96 | u64 | off_final_norm |
| 104 | u64 | file_size |
| 112 | 16 bytes | reserved |

Flags conocidos:
- bit 0: tied embeddings.
- bit 1: QK-Norm.
- bit 2: escalas FP16.

Reglas:
- `file_size` debe coincidir con el tamaño real.
- `version=1` usa escalas FP32.
- `version=2` usa escalas FP16 y debe declarar el flag correspondiente.
- Bits no reconocidos deben rechazarse hasta definir su semántica.
- La cabecera debe estar completa antes de leer cualquiera de sus campos.

## 3. Restricciones dimensionales mínimas

Para el motor Qwen3 de esta referencia:

- Todas las dimensiones deben ser mayores que cero.
- `dim == n_heads * head_dim`.
- `n_heads % n_kv_heads == 0`.
- `kv_dim = n_kv_heads * head_dim`.
- `q_dim = n_heads * head_dim`.
- `dim`, `hidden_dim`, `q_dim` y `kv_dim` deben ser múltiplos de 32 para las matrices cuantizadas correspondientes.
- `max(dim, hidden_dim, q_dim) <= 16384`, por el buffer Q8 estático.
- `ht_mask == 524287` en esta implementación.
- `n_layers`, `n_heads`, `n_kv_heads`, `head_dim`, `vocab_size` y `max_seq_len` no pueden ser cero.
- Los valores de epsilon y RoPE deben ser finitos y positivos.
- El modelo debe declarar QK-Norm para esta ruta de ejecución.

La política de aceptación puede ser más estricta para el perfil Qwen3-4B:
`dim=2560, hidden_dim=9728, n_layers=36, n_heads=32, n_kv_heads=8, head_dim=128, vocab_size=151936`.

El validador genérico no debe aceptar automáticamente cualquier arquitectura que casualmente quepa en los buffers.

## 4. Tamaño de fila Q8_0

Para K múltiplo de 32:

- v1: `row_bytes = K + (K/32)*4 = 9K/8`.
- v2: `row_bytes = K + (K/32)*2 = 17K/16`.

Cada matriz `[rows, K]` ocupa `rows * row_bytes(K)`.

Antes de multiplicar, comprobar:
- K múltiplo de 32.
- K <= 16384.
- `rows <= UINT64_MAX / row_bytes`.

## 5. Sección tokenizer

El encabezado de tokenizer ocupa 64 bytes. Sus primeros cuatro campos son u64 relativos al comienzo de la sección:

| Offset | Campo |
|---:|---|
| 0 | off_byte_to_tok |
| 8 | off_tok_offsets |
| 16 | off_tok_bytes |
| 24 | off_merge_ht |

Layout esperado:

1. byte-to-token: 256 × u32 = 1024 bytes.
2. offsets: (vocab_size + 1) × u32.
3. bytes UTF-8 concatenados.
4. tabla BPE: 524288 × 16 = 8.388.608 bytes.

Los sub-offsets son relativos a `off_tokenizer`. Deben ser crecientes, estar dentro de la sección tokenizer y respetar alineación de 64 bytes donde corresponda.

Validaciones del tokenizer:
- Los 256 IDs byte-to-token son menores que vocab_size.
- offsets[0] == 0.
- Los offsets son monótonos no decrecientes.
- El último offset determina el tamaño de tok_bytes.
- La región de bytes no puede salir de la sección.
- Cada entrada de hash vacía se identifica por rank `0xFFFFFFFF`.
- En entradas ocupadas, ambos IDs de la clave y merged_id deben ser menores que vocab_size.
- El número de entradas ocupadas no puede superar 524288.
- La máscara debe coincidir con 524287.

La verificación semántica del vocabulario y los merges contra `tokenizer.json` es una prueba separada; no puede inferirse solo del layout binario.

## 6. Embeddings y capas

### 6.1 Embeddings

Comienzan en `off_embed` y tienen forma:

`[vocab_size, dim]`

Tamaño:

`vocab_size * row_bytes(dim)`

El final de embeddings debe quedar antes o en `off_layers`, con padding de alineación según el exportador.

### 6.2 Una capa Transformer

Cada capa comienza alineada a 64 bytes. El orden es:

1. input_layernorm: dim × FP32.
2. q_norm: head_dim × FP32.
3. k_norm: head_dim × FP32.
4. post_attention_layernorm: dim × FP32.
5. q_proj: [q_dim, dim].
6. k_proj: [kv_dim, dim].
7. v_proj: [kv_dim, dim].
8. o_proj: [dim, q_dim].
9. gate_proj: [hidden_dim, dim].
10. up_proj: [hidden_dim, dim].
11. down_proj: [dim, hidden_dim].

Antes de cada matriz se aplica padding a 64 bytes. Después de la última matriz, el final de capa también se alinea a 64 bytes.

El stride se calcula recorriendo ese layout exacto. El valor calculado debe coincidir con `layer_stride` del encabezado.

La sección completa de capas ocupa:

`n_layers * layer_stride`

Debe caber entre `off_layers` y `off_final_norm`.

### 6.3 Norma final

La norma final comienza en `off_final_norm` y contiene:

`dim * 4 bytes`

Su final alineado debe coincidir con `file_size` o quedar dentro del padding final permitido.

## 7. Validación de offsets sin overflow

No validar usando únicamente `offset + length <= file_size`, porque la suma puede desbordar.

Usar esta secuencia conceptual:

1. Comprobar `offset <= file_size`.
2. Calcular `remaining = file_size - offset`.
3. Comprobar `length <= remaining`.
4. Solo entonces construir el puntero o leer la región.

Para multiplicaciones:
- comprobar el límite antes de multiplicar.
- usar enteros sin signo de 64 bits con detección de overflow.
- rechazar offsets no alineados.
- rechazar regiones que se solapen o inviertan el orden requerido.

## 8. Pruebas unitarias requeridas

Fixtures pequeños y sintéticos, sin checkpoint real:

1. Encabezado truncado (0, 4, 127 bytes).
2. Magic inválido.
3. Versión desconocida.
4. Flags incompatibles con versión.
5. file_size distinto del tamaño real.
6. Dimensiones cero.
7. n_heads no divisible por n_kv_heads.
8. dim distinto de n_heads × head_dim.
9. K no múltiplo de 32.
10. K superior a Q8_MAX_K.
11. Overflow en rows × row_bytes.
12. Offset fuera del archivo.
13. Secciones solapadas.
14. layer_stride inferior al calculado.
15. Tokenizer sub-offset fuera de su sección.
16. Offsets de tokens no monótonos.
17. Token ID fuera del vocabulario.
18. Tabla BPE con máscara incorrecta.
19. Entrada hash con merged_id inválido.
20. Archivo válido v1.
21. Archivo válido v2.
22. Perfil dimensional sintético Qwen3-0.6B.
23. Perfil dimensional sintético Qwen3-4B.

Los fixtures deben ser pequeños: no se debe generar un modelo real de varios gigabytes para probar el parser.

## 9. Integración con el loader NASM

El validador Python es útil para diagnósticos y CI, pero no sustituye las defensas del loader.

La implementación NASM deberá:
- verificar tamaño mínimo antes de leer la cabecera;
- comparar HDR_FILE_SIZE con fstat;
- validar dimensiones y relaciones antes de calcular buffers;
- validar los rangos de todas las secciones;
- detectar overflow en cálculos de tamaños;
- rechazar offsets fuera del mmap;
- validar la máscara de tokenizer y el límite Q8;
- devolver error controlado sin ejecutar el forward pass.

No introducir simultáneamente el validador, el rediseño bare-metal y cambios en kernels. El primer cambio de código debe ser el validador independiente y sus pruebas.

---

## 10. Criterio de aceptación

El validador se considera listo cuando:
- todas las pruebas negativas son rechazadas;
- fixtures válidos v1 y v2 son aceptados;
- el perfil Qwen3-0.6B y el perfil Qwen3-4B calculan strides y tamaños coherentes;
- no existen lecturas fuera de límites en el parser;
- los resultados son reproducibles y no dependen de cargar el modelo entero en memoria.

La compatibilidad real con Qwen3-4B seguirá pendiente hasta exportar el checkpoint oficial y verificarlo en el MSI.
