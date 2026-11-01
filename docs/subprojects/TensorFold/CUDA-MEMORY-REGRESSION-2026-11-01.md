# Auditoría profunda: regresión de memoria CUDA en Qwen3.5-4B

**Estado documental:** auditoría de código fuente; no equivale a una validación física nueva.  
**Fecha de documentación:** 2026-11-01.  
**Issue upstream:** [TensorFold #1827 — CUDA memory regression: Qwen3.5-4B no longer fits on a 4 GB RTX 3050](https://github.com/ashhart/TensorFold/issues/1827).  
**Repositorio auditado:** [ashhart/TensorFold](https://github.com/ashhart/TensorFold).  
**Equipo de referencia:** Ubuntu 26.04.1, MSI Thin 15 B12UC, Intel Core i7-12650H, 16 hilos lógicos, 14.8 GiB RAM, NVIDIA RTX 3050 Laptop 4 GiB, driver 580.178.04, CUDA toolkit 13.4, kernel 7.0.0-38-generic.  
**Restricción de esta auditoría:** no se han ejecutado pruebas GPU, benchmarks, builds ni modificaciones de código durante la inspección de fuentes aquí documentada.

---

## 1. Resumen ejecutivo

La comparación de las rutas de asignación CUDA de TensorFold identifica un incremento importante de memoria reservado por el motor Qwen3.5 al pasar la capacidad máxima de filas de 128 a 4096.

El cambio se introdujo para acelerar el prefill de prompts largos mediante chunks de hasta 4096 filas, atención prompt especializada y una cadena GDN delta-rule. La optimización tiene una motivación de rendimiento legítima, especialmente en GPU de gama alta. Sin embargo, el motor calcula y reserva varias activaciones y buffers de scratch usando siempre la capacidad máxima, aunque el contexto o el prompt configurado no puedan aprovecharla.

Para el checkpoint denso Qwen3.5-4B examinado, las fórmulas de `Engine.scratch()` producen:

| Magnitud | Capacidad 128 | Capacidad 4096 |
|---|---:|---:|
| Scratch escalado por filas | 19.484 MiB | 623.500 MiB |
| Scratch fijo de verify/decode, incluyendo sampling | 190.685 MiB | 190.685 MiB |
| **Scratch total reconstruido** | **209.169 MiB** | **814.185 MiB** |

Diferencia total estimada: **605.016 MiB**. La parte dominante son **604.016 MiB** adicionales de buffers escalados por filas.

Son cifras derivadas de las fórmulas de asignación, la geometría del modelo y las reglas de alineación del código. No son mediciones físicas de VRAM ni lecturas de `nvidia-smi`.

Hay una distinción diagnóstica esencial: este crecimiento de scratch es una regresión real del footprint de memoria después de la admisión del modelo, pero no explica por sí solo un rechazo temprano que compara únicamente el tamaño de los pesos con el presupuesto CUDA antes de crear el arena del motor. El mantenedor señaló expresamente esa separación en el issue.

Por tanto, el incidente debe dividirse en dos problemas que requieren evidencia diferente:

1. **Rechazo temprano de pesos:** por qué el presupuesto disponible se calculó como aproximadamente 2.6 GiB frente a pesos de aproximadamente 2.8 GiB en la ejecución fallida.
2. **Regresión de reserva del motor:** cuánto scratch adicional se reserva una vez admitido el modelo debido a `max_rows = 4096`.

No se deben presentar ambos fenómenos como una única causa sin una reproducción controlada.

## 2. Alcance, estado y vocabulario de evidencia

Esta documentación es una auditoría estática de implementación y fórmulas. Distingue:

- **HECHO DE CÓDIGO:** comportamiento visible directamente en las fuentes examinadas.
- **CÁLCULO DERIVADO:** resultado aritmético de fórmulas y dimensiones conocidas.
- **MEDICIÓN HISTÓRICA:** ejecución previa documentada en el historial del experimento.
- **HIPÓTESIS / PROPUESTA:** explicación o dirección técnica aún no demostrada.
- **PENDIENTE:** evidencia necesaria para cerrar una cuestión.

La regla LEONES es no confundir ESTIMATED con MEASURED. Los cálculos de scratch de este informe son estimaciones exactas respecto a las fórmulas y geometría usadas, pero no una medición de consumo físico de GPU.

### Fuera de alcance

No se ha realizado en esta auditoría:

- ejecución de TensorFold;
- asignación o liberación CUDA;
- benchmark comparativo nuevo;
- compilación;
- modificación de código;
- cambio de configuración del sistema;
- publicación de un parche;
- prueba de corrección de un tamaño de scratch reducido.

## 3. Identificación del cambio upstream

Commit relevante:

[`c50b59a23418c3f8436db68827ab8fe45ea5c603`](https://github.com/ashhart/TensorFold/commit/c50b59a23418c3f8436db68827ab8fe45ea5c603)

Título:

> qwen CUDA: prompts in 4096-row chunks with tensor-core attention and the delta-rule chain

Commit padre:

[`184a938e3a5a96dda7692017eeaa2a3213b82b7c`](https://github.com/ashhart/TensorFold/commit/184a938e3a5a96dda7692017eeaa2a3213b82b7c)

Metadatos de la inspección Git:

- Autor: BobClawblaw.
- Committer: ashhart.
- Fecha de autoría indicada: 2026-10-19 21:10:06 UTC.
- El mantenedor identifica 1.1.4 como la primera versión publicada que contiene el cambio.

El commit se motivó por la latencia de prompts muy largos. El mensaje informa de una mejora de aproximadamente 144.5 s a 26.9 s para un prompt de 75,616 tokens en un RTX 5090, con Qwen3.8-27B MLX 4-bit y una configuración de ventana extensa. Esa mejora es un resultado declarado por el commit para otro modelo y otra GPU; no debe atribuirse automáticamente a Qwen3.5-4B en la RTX 3050.

### Cambio de capacidad

Antes:

```zig
pub const max_rows = 128;
```

Después, el motor toma la capacidad de `Round.max_rows`, que pasa a ser 4096.

En `cuda_round.zig`:

```zig
pub const max_rows = 4096;
pub const max_segs = 128;
pub const most_verify = 128;
pub const most_window = 64;
```

La optimización aumenta el máximo de filas para prompt/forward. No convierte verify ni window en estructuras de 4096 filas: ambas continúan limitadas a 128 y 64, respectivamente.

## 4. Modelo y geometría usada en el cálculo

Checkpoint:

[`mlx-community/Qwen3.5-4B-MLX-4bit`](https://huggingface.co/mlx-community/Qwen3.5-4B-MLX-4bit)

Snapshot local observado:

```text
32f3e8ecf65426fc3306969496342d504bfa13f3
```

Es un checkpoint MLX affine 4-bit, group size 64. La configuración de texto corresponde a `qwen3_5_text`, no a `qwen3_5_moe_text`: se trata de un modelo denso.

Dimensiones relevantes de la configuración:

| Parámetro | Valor |
|---|---:|
| hidden_size | 2560 |
| intermediate_size | 9216 |
| num_hidden_layers | 32 |
| vocab_size | 248320 |
| linear_num_key_heads | 16 |
| linear_num_value_heads | 32 |
| linear_key_head_dim | 128 |
| linear_value_head_dim | 128 |
| num_attention_heads | 16 |
| num_key_value_heads | 4 |
| head_dim | 256 |
| linear_conv_kernel_dim | 4 |
| Capas de atención lineal | 24 |
| Capas de atención completa | 8 |

La geometría CUDA fija `dk = 128` y `head_dim = 256`. Para el cálculo:

```text
valueWidth = v_heads * dk
           = 32 * 128 = 4096

attnWidth  = q_heads * head_dim
           = 16 * 256 = 4096

convWidth  = (2 * k_heads + v_heads) * dk
           = (32 + 32) * 128 = 8192

wide       = max(valueWidth, attnWidth, hidden)
           = 4096
```

Fuentes principales: `config.json` del checkpoint y `zig/src/families/qwen3_5/cuda_geometry.zig`.

## 5. Ruta de asignación del arena principal

En `zig/src/families/qwen3_5/cuda_engine.zig`, el motor mide el scratch y lo suma al tamaño de los pesos:

```zig
e.arena = try DeviceBuffer.alloc(d, wbytes + try e.scratch(.measure));
errdefer e.arena.free();

try e.arena.fill8(0, null);
```

Consecuencias:

1. Pesos y scratch viven en una misma asignación grande del dispositivo.
2. El scratch no es solo una cifra contable: forma parte del tamaño real solicitado al allocator CUDA.
3. `fill8` toca toda la arena durante la inicialización. El comentario del código explica que el primer acceso hace que el driver comprometa la memoria y que esto puede ser lento.
4. La arena permanece asociada al motor hasta su liberación durante el teardown.

La función `scratch()` usa `const R = max_rows`. Por ello, el tamaño se calcula con 4096 aunque una petición concreta vaya a procesar muchas menos filas.

## 6. Reconstrucción de scratch escalado por filas

Para Qwen3.5-4B, cada fila añade los siguientes bytes a la reserva. Los buffers están en BF16/16-bit salvo los acumuladores y metadatos que usan 32-bit según la fórmula.

| Buffer(s) | Fórmula por fila | Bytes/fila |
|---|---:|---:|
| `h`, `x`, `r` | `3 * hidden * 2` | 15,360 |
| `y`, `mix`, `z`, `v` | `4 * wide * 2` | 32,768 |
| `q`, `k` | `2 * k_heads * dk * 2` | 8,192 |
| `qkv` | `convWidth * 2` | 16,384 |
| `gate`, `up`, `act` | `3 * intermediate * 2` | 55,296 |
| `xs` | `(max(intermediate, wide) / 64) * 4` | 576 |
| `a`, `b`, `beta` | `3 * v_heads * 2` | 192 |
| `g_` | `v_heads * 4` | 128 |
| `qraw` | `2 * attnWidth * 2` | 16,384 |
| `qn` | `attnWidth * 2` | 8,192 |
| `kraw`, `vraw`, `kn` | `3 * kv_heads * head_dim * 2` | 6,144 |
| **Total** | | **159,616** |

La implementación correspondiente:

```zig
inline for (.{"h", "x", "r"}) |name|
    @field(e, name) = try t.alloc(R * g.hidden * 2);

inline for (.{"y", "mix", "z", "v"}) |name|
    @field(e, name) = try t.alloc(R * wide * 2);

inline for (.{"q", "k"}) |name|
    @field(e, name) = try t.alloc(R * g.k_heads * geometry.dk * 2);

e.qkv = try t.alloc(R * g.convWidth() * 2);

inline for (.{"gate", "up", "act"}) |name|
    @field(e, name) = try t.alloc(R * g.intermediate * 2);

e.xs = try t.alloc(R * (@max(g.intermediate, wide) / 64) * 4);

inline for (.{"a", "b", "beta"}) |name|
    @field(e, name) = try t.alloc(R * g.v_heads * 2);

e.g_ = try t.alloc(R * g.v_heads * 4);

e.qraw = try t.alloc(R * 2 * g.attnWidth() * 2);
e.qn = try t.alloc(R * g.attnWidth() * 2);

inline for (.{"kraw", "vraw", "kn"}) |name|
    @field(e, name) = try t.alloc(R * g.kv_heads * head_dim * 2);
```

Para estas dimensiones, los tamaños individuales ya cumplen la alineación de 256 bytes aplicada por el arena. El total por fila es 159,616 bytes.

### Comparación aritmética

```text
128 rows:
159,616 * 128 = 20,430,848 bytes
             = 19.484375 MiB

4096 rows:
159,616 * 4096 = 653,787,136 bytes
               = 623.500000 MiB

Difference:
159,616 * (4096 - 128)
= 633,356,288 bytes
= 604.015625 MiB

La diferencia exacta en bytes es **633,356,288**.

## 7. Scratch fijo de verify/decode

La función reserva otros buffers con `most_verify`, que sigue siendo 128:

```zig
e.pm = try t.alloc(most_verify * g.q_heads * max_chunks * 4);
e.pl = try t.alloc(most_verify * g.q_heads * max_chunks * 4);
e.po = try t.alloc(most_verify * g.q_heads * max_chunks * head_dim * 4);

e.logits = try t.alloc(most_verify * g.vocab * 2);

e.amax = try t.alloc(most_verify * argmaxSlices(g.vocab) * 8);
e.picks = try t.alloc(most_verify * cuda.sample.Draws.row_scratch);
```

Con `max_chunks = 64`, `vocab = 248320` y `argmaxSlices = ceil(vocab / 4096) = 61`:

| Buffer | Bytes |
|---|---:|
| `pm` | 524,288 |
| `pl` | 524,288 |
| `po` | 134,217,728 |
| `logits` | 63,569,920 |
| `amax` | 62,464 |
| `picks` | 1,048,576 |
| **Total** | **199,947,264 bytes** |
| **Total MiB** | **190.684570 MiB** |

`picks` usa `row_scratch = 2 * 1024 * 4 = 8192` bytes por fila. La comparación histórica identifica aproximadamente 1 MiB de sampling scratch como una adición menor posterior a 1.1.2.

Reconstrucción comparativa:

| Componente | Baseline 128 filas | Actual 4096 filas |
|---|---:|---:|
| Buffers escalados por filas | 19.484 MiB | 623.500 MiB |
| Scratch fijo, excluyendo sampling añadido posteriormente | 189.685 MiB | — |
| Scratch fijo, incluyendo sampling | — | 190.685 MiB |
| **Scratch total** | **≈209.169 MiB** | **≈814.185 MiB** |

La diferencia calculada entre esos totales es aproximadamente **605.016 MiB**. Debe conservarse la precisión de estas cifras como cálculo de fórmulas; no convertirlas en “VRAM medida”.

## 8. Capacidad máxima, filas reales y reserva

Hay tres conceptos que no deben confundirse:

1. **Capacidad máxima:** máximo de filas que el motor admite en un forward/prompt chunk.
2. **Filas reales:** número de filas procesadas por una invocación concreta.
3. **Reserva:** memoria que se solicita por adelantado para que los buffers puedan cubrir la capacidad máxima.

El cambio no implica que cada prompt ejecute 4096 filas. Las funciones de ejecución reciben el número real de filas. El problema de memoria aparece porque la reserva se hace antes, usando la capacidad máxima.

Con un contexto configurado de 256 tokens, una petición no puede aprovechar un chunk de 4096 filas. Sin embargo, la reserva de scratch continúa basada en 4096.

La oportunidad de diseño es separar la capacidad del kernel de la capacidad reservada por el plan de ejecución. Eso requiere auditoría de todos los consumidores y no autoriza a reducir buffers de forma mecánica.

## 9. Kernels de prompt: filas reales y límites

Rutas relevantes:

- `cuda_prompt.zig`
- `cuda_projection.zig`
- `cuda_prompt_int8.zig`
- `prefill_attention.cu`
- `prefill_attention_rows.cuh`
- `gdn_prefill.cu`
- `cuda_forward.zig`

### Atención prompt

El launcher calcula la grid a partir del número real de filas, con bloques de 64 filas para la configuración examinada. El código de `prefill_attention_rows.cuh` protege lecturas y escrituras de las filas parciales mediante predicados `row < W`.

Por tanto, los bloques finales incompletos de atención enmascaran las filas fuera del rango. El kernel no necesita ejecutar un múltiplo exacto de 64 filas para que el acceso a filas sea válido.

### Proyecciones

`cuda_projection.zig` recibe `rows` como argumento y, para prompt con más de 16 filas, dirige la ejecución a kernels específicos de prompt pasando el número real. La ruta de proyección individual ya distingue capacidad máxima de tamaño de operación.

La ruta fused prompt tiene condiciones de forma y arquitectura específicas; no es una solución general para el Qwen3.5-4B en la RTX 3050.

### GDN prefill

La especialización Qwen3.5 del kernel de cadena GDN usa dimensiones de tile constantes, incluidas 64 filas y 32 pasos. Su memoria shared/local depende de esos tiles, no de una matriz global de 4096 filas.

La inspección identificó que el kernel calcula filas a partir de `blockIdx.y` y que la seguridad de la cobertura depende de que la grid se lance con la geometría prevista. El kernel no muestra una comprobación general de límite de fila en cada acceso. La auditoría de su launcher y de los invariantes de la grid debe conservarse antes de modificar capacidades.

**Conclusión limitada:** hay evidencia de que varias rutas de kernels reciben el número real de filas y que atención/proyección manejan tamaños parciales. No demuestra que todos los buffers compartidos puedan reducirse sin efectos sobre otros caminos, concurrencia o vida útil asíncrona.

## 10. Tablas de ronda y staging

`cuda_round.zig` dimensiona tablas según `max_rows`. El aumento 128 → 4096 incrementa la capacidad completa en aproximadamente 222,208 bytes, es decir, unos 217 KiB.

Hay que distinguir:

- `e.tables`: DeviceBuffer en GPU.
- `e.staged`: buffer host pinned.
- `host_logits`: host pinned.
- `src_at`: final del prefijo usado en el upload ordinario de texto.

Para texto ordinario, `uploadAsync` copia solo el prefijo hasta `src_at`; el término dependiente de filas antes de ese punto equivale a 44 bytes por fila, unos 170.5 KiB de diferencia entre 128 y 4096 filas. Los campos de origen/posiciones posteriores se utilizan para el manejo especial de imágenes.

La capacidad de la tabla completa y el tamaño realmente transferido en una petición de texto no son la misma magnitud.

## 11. Tap ring y drafter: coste condicional

En `cuda_cache.zig`:

```zig
pub const tap_rows = 2048 + engine.max_rows;
```

En `cuda_engine.zig`:

```zig
pub fn tapBytes(e: *const Engine) usize {
    return tap_rows * e.n_taps * e.g.hidden * 2;
}
```

Con hidden=2560:

| Capacidad | Filas del ring | MiB por tap y stream |
|---|---:|---:|
| 128 | 2176 | 10.625 |
| 4096 | 6144 | 30.000 |
| Diferencia | 3968 | **19.375** |

Con ocho taps, el incremento sería **155 MiB por stream**.

No se debe incluir ese coste en el escenario normal sin drafter:

- `n_taps` comienza en cero.
- `setTaps()` configura las capas que necesita el drafter.
- `Cache.fixed()` solo asigna el ring si `n_taps > 0`.
- En el pool, el layout de run incluye el ring, pero solo se mapea/usa cuando corresponde.

El código del drafter absorbe taps en piezas de `most_verify`, no en piezas de 4096 filas. MTP también limita la absorción por llamada a `most_verify`.

## 12. Otras asignaciones y rutas condicionales

### KV cache

El KV cache ordinario se calcula según capacidad de contexto/cache y geometría K/V, no directamente por `max_rows`. La prueba diagnóstica `TF_QWEN_KV_PAGE_TEST` redondea capacidad a páginas y añade padding y tabla de páginas. No es el modo ordinario por defecto.

### Páginas CUDA y pool

`Cache.initPaged()` asigna una tabla de páginas según el número de páginas proporcionado por el caller. La arena de páginas se asigna a partir de `pages * page_bytes`. El código revisado no demuestra que el cambio de prompt rows incremente automáticamente el número ordinario de páginas; es necesario seguir el cálculo completo de los call sites antes de atribuirle un delta.

### Estado recurrente

El estado recurrente GDN y las colas de convolución dependen de la geometría del modelo y del número de streams/caches. No están directamente multiplicados por `max_rows`.

### Scratch MoE

La llamada a `routed.Scratch.carve()` está condicionada por `g.moe()`. El checkpoint estudiado es denso `qwen3_5_text`; el scratch routed/MoE no forma parte de la estimación normal de este caso.

### Workspace INT8 de prompt

`cuda_prompt_int8.zig` crea un workspace independiente solo si se activa explícitamente prompt INT8. Para el modelo:

- dimensión más ancha: 9216;
- filas reservadas: 4096;
- workspace: 42,467,328 bytes = 40.5 MiB;
- más un flag de 4 bytes.

Es un coste opcional, no parte de la ruta por defecto. El workspace se dimensiona por máximo de filas, aunque las llamadas a proyección reciben las filas reales.

### MTP y draft

MTP rechaza modelos que no sean MoE (`if (!e.g.moe()) return error.NotRouted`). El checkpoint denso no entra en esa ruta. El drafter convencional es otra capacidad opcional y tiene sus propias asignaciones y buffers.

### Split-K y otras reservas

El análisis del mantenedor también menciona pequeñas diferencias posteriores a 1.1.2: aproximadamente 1 MiB de sampling, 0.2 MB de tablas de ronda y 4.7 MB de workspaces split-K. Deben mantenerse separadas del incremento principal de scratch escalado por filas.

## 13. La admisión temprana de pesos es un problema distinto

La comprobación temprana de presupuesto compara los bytes de los pesos con la memoria CUDA disponible antes de reservar el arena de scratch del motor.

Por orden de ejecución, el scratch calculado posteriormente no puede explicar directamente que esa comprobación temprana rechace el modelo antes de crear el arena.

El diagnóstico comunicado para la ejecución fallida fue aproximadamente:

- pesos: 2.8 GiB;
- presupuesto disponible tras reserva: 2.6 GiB;
- VRAM libre observada: aproximadamente 3.6 GiB;
- reserva configurada/efectiva mencionada: 1 GiB.

La política de reserva de `cuda_memory.zig` no había cambiado entre las versiones comparadas. Cuando no se configura la variable, el reserve por defecto para GPU discreta es `max(1 GiB, total/32)`. Con `TENSORFOLD_MEMORY_RESERVE_GIB=0.5`, el reserve explícito es 0.5 GiB.

El cálculo de espacio utilizable tiene en cuenta memoria libre y, si existe, cap menos memoria ya retenida. La función de presupuesto por sí sola no explica una diferencia de memoria libre entre dos arranques.

Para explicar el rechazo temprano hay que comparar, en el instante inmediatamente anterior al arranque:

- VRAM libre;
- otros procesos GPU;
- contextos CUDA;
- versión/revisión exacta del checkpoint;
- archivos descargados y tamaños reales;
- línea de comandos;
- variables de entorno;
- reserve efectivo.

La igualdad del nombre del repositorio de Hugging Face no garantiza que las dos ejecuciones usaran los mismos bytes de checkpoint.

La regresión de scratch sí puede reducir el margen disponible después de superar la admisión de pesos, al solicitar una arena conjunta de pesos + scratch y tocarla durante la inicialización.

## 14. Evidencia histórica de ejecución en la RTX 3050

En la investigación previa del mismo equipo se registró una ejecución funcional con TensorFold 1.1.2:

```bash
TF="$HOME/.local/opt/tensorfold-1.1.2-linux-x86_64/bin/tensorfold-native"
export TENSORFOLD_MEMORY_RESERVE_GIB=0.5

"$TF" serve mlx-community/Qwen3.5-4B-MLX-4bit \
  --host 127.0.0.1 --port 18084 --backend cuda \
  --context 256 --parallel 1 --max-tokens 64 \
  --no-thinking --no-update-check
```

Resultados históricos documentados:

| Métrica | TensorFold 1.1.2 |
|---|---:|
| Carga | ~7.2 s |
| Pesos | ~2.75 GiB |
| Decode | 54.2 tok/s |
| Generación | 1.162 s |
| Prefill | 0.195 s |
| TTFT | 0.198 s |

En versiones 1.1.5, 1.1.6 y 1.2.0 se observaron rechazos OOM durante la investigación. El diagnóstico 1.1.5 indicaba pesos ~2.8 GiB frente a un presupuesto CUDA ~2.6 GiB, con ~3.6 GiB libres y reserve de 1 GiB.

Estos resultados son evidencia histórica del trabajo anterior, no una repetición controlada dentro de esta auditoría. La diferencia de estado GPU entre arranques sigue siendo una variable que debe comprobarse.

## 15. Hipótesis de diseño para una corrección futura

Una dirección posible —no un parche aprobado— es separar:

- `max_rows`: límite funcional del camino de prompt y de los kernels;
- `scratch_rows`: filas para las que se reserva scratch;
- capacidad de prompt planificada: máximo de filas que el plan de ejecución permitirá utilizar.

El scratch podría dimensionarse según la capacidad real configurada, manteniendo el camino de 4096 filas en configuraciones y dispositivos que puedan aprovecharlo y admitirlo.

La propuesta del mantenedor de dimensionar activaciones según el límite real del prompt, por ejemplo `min(context, 4096)`, es un punto de partida. Debe comprobarse qué campo de configuración representa correctamente esa capacidad: contexto, prompt_rows, batch_rows y capacidad de ventana no son conceptos intercambiables.

Antes de cualquier cambio hay que auditar:

1. Todos los offsets y punteros tallados desde el arena.
2. Alineación y comprobaciones de límites.
3. Cada kernel que lee o escribe cada buffer escalado por filas.
4. Rutas prompt y no-prompt.
5. Reutilización de buffers entre capas.
6. Orden de ejecución asíncrona en el stream CUDA.
7. Captura y replay de CUDA Graphs.
8. Staging de prompts con imágenes y tablas adicionales.
9. Workspace INT8 opcional.
10. Tap ring, drafter y absorción en bloques de 128.
11. Multi-stream y layouts del pool.
12. Teardown y rutas de error.
13. Casos de 1, 16, 128, 256 y 4096 filas.
14. Tamaños no múltiplos del tile.
15. Rendimiento de prompts largos en hardware donde 4096 filas aporten una mejora.

No se propone reducir precisión numérica, alterar la política de reserve, eliminar comprobaciones ni revertir los kernels de prompt.

## 16. Plan de reproducción controlada

Para aislar la causa del rechazo temprano, repetir cada versión con las mismas condiciones:

1. Capturar `nvidia-smi` completo inmediatamente antes del arranque, incluida la lista de procesos.
2. Confirmar el mismo snapshot HF y comparar hashes/tamaños de todos los archivos.
3. Registrar comando y todas las variables de entorno.
4. Confirmar reserve efectivo.
5. Detener otros servidores/modelos y asegurar un estado GPU equivalente.
6. Capturar log completo desde el inicio hasta el error.
7. Distinguir si el fallo ocurre en la admisión de pesos, en la asignación del arena o en una asignación posterior.
8. Si el fallo es posterior a admisión, registrar `wbytes`, `scratch(.measure)` y memoria libre antes/después del arena.

Una comparación válida requiere mantener iguales checkpoint, comando, reserve, estado de GPU y procesos competidores.

## 17. Preguntas abiertas para el mantenedor

1. ¿Puede confirmarse el mensaje y la fase exacta del rechazo de 2.8 GiB de pesos frente a 2.6 GiB de presupuesto? ¿Es la comprobación previa a la creación del motor?
2. ¿Existe ya un campo/option que represente el máximo prompt chunk configurado, independiente del contexto o de la ventana?
3. ¿Se considera adecuado mantener `max_rows = 4096` para los kernels y usar una capacidad separada para reservar scratch?
4. ¿Qué batería de tests CUDA debe validar chunks parciales y el camino completo de 4096 filas?
5. ¿Qué otras asignaciones o cambios split-K entre 1.1.2 y la versión afectada deben entrar en una comparación byte a byte?

## 18. Trazabilidad y referencias

### Repositorio y commit

- [TensorFold upstream](https://github.com/ashhart/TensorFold)
- [Issue #1827](https://github.com/ashhart/TensorFold/issues/1827)
- [Commit de cambio de capacidad](https://github.com/ashhart/TensorFold/commit/c50b59a23418c3f8436db68827ab8fe45ea5c603)
- [Commit padre](https://github.com/ashhart/TensorFold/commit/184a938e3a5a96dda7692017eeaa2a3213b82b7c)

### Ficheros auditados

- `zig/src/families/qwen3_5/cuda_engine.zig` — arena, scratch, taps y capacidad.
- `zig/src/families/qwen3_5/cuda_round.zig` — límites de filas, verify, window y tablas.
- `zig/src/families/qwen3_5/cuda_cache.zig` — cache, tap ring, páginas y layouts de run.
- `zig/src/families/qwen3_5/cuda_geometry.zig` — geometría del modelo.
- `zig/src/families/qwen3_5/cuda_memory.zig` — reserve y presupuesto CUDA.
- `zig/src/families/qwen3_5/cuda_projection.zig` — proyecciones prompt.
- `zig/src/families/qwen3_5/cuda_prompt.zig` — launchers de prompt.
- `zig/src/families/qwen3_5/cuda_prompt_int8.zig` — workspace INT8 opcional.
- `zig/src/families/qwen3_5/cuda_forward.zig` — flujo forward.
- `zig/src/families/qwen3_5/cuda_pages.zig` — páginas CUDA.
- `zig/src/families/qwen3_5/cuda_recurrent.zig` — estado recurrente.
- `zig/src/families/qwen3_5/cuda_draft.zig` — drafter opcional.
- `zig/src/families/qwen3_5/cuda_mtp.zig` — MTP/MoE opcional.
- `zig/src/cuda/kernels/prefill_attention.cu` — kernel de atención prompt.
- `zig/src/cuda/kernels/prefill_attention_rows.cuh` — máscara de filas parciales.
- `zig/src/cuda/kernels/gdn_prefill.cu` — cadena GDN de prefill.

### Checkpoint

- [Hugging Face: Qwen3.5-4B-MLX-4bit](https://huggingface.co/mlx-community/Qwen3.5-4B-MLX-4bit)
- [Config del checkpoint](https://huggingface.co/mlx-community/Qwen3.5-4B-MLX-4bit/blob/main/config.json)

## 19. Estado final

**Conclusión de la auditoría:** existe una regresión cuantificable de reserva de scratch asociada al aumento de `max_rows` de 128 a 4096. Para el Qwen3.5-4B denso, las fórmulas reconstruidas indican aproximadamente 605 MiB más de scratch total.

**No está demostrado** que esa regresión sea la causa directa del rechazo temprano de pesos observado en el arranque fallido. Esa comprobación sucede antes de reservar el scratch y requiere comparar el estado real de GPU y el checkpoint en condiciones controladas.

**No se ha realizado** una nueva prueba GPU, compilación ni modificación de código. La dirección de corrección queda como hipótesis de diseño pendiente de revisión y acuerdo del mantenedor.

El resultado queda clasificado como **AUDITORÍA ESTÁTICA COMPLETADA / REPRODUCCIÓN FÍSICA PENDIENTE / CORRECCIÓN NO IMPLEMENTADA**.
