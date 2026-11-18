# Falcon3-10B I2_S — investigación de inferencia incoherente y overflow AVX2

**Proyecto:** LEONES · **Fecha de corte:** 2026-11-18  
**Estado:** defecto aritmético reproducido en el kernel AVX2 para entradas válidas; dispatch efectivo e impacto E2E sobre Falcon3 todavía pendientes.  
**Repositorio bajo investigación:** [microsoft/BitNet](https://github.com/microsoft/BitNet)  
**Submódulo:** [llama.cpp](https://github.com/ggml-org/llama.cpp) (incluido en BitNet como `3rdparty/llama.cpp`).

> Este documento separa hechos reproducidos, interpretación del código y cuestiones todavía abiertas. No se debe presentar la causa E2E de las generaciones incoherentes como cerrada hasta contrastar activaciones reales o una ruta escalar de referencia.

## 1. Resumen ejecutivo

Se convirtió `tiiuae/Falcon3-10B-Instruct-1.58bit` a GGUF F32 y después a GGUF I2_S. El archivo I2_S carga correctamente en llama.cpp y el runtime genera tokens, pero las cinco primeras pruebas de generación produjeron texto incoherente. Una de las rutas CLI también terminó con una excepción del parser PEG; sin embargo, `llama-completion`, que no necesita esa ruta de conversación, reprodujo la generación incoherente.

La investigación aisló un defecto en `ggml_vec_dot_i2_i8_s_1x1()` cuando se compila con AVX2:

- El kernel acumula productos parciales en lanes de 16 bits mediante `_mm256_add_epi16`.
- La acumulación puede exceder el rango de `int16_t` y envuelve módulo 65.536.
- Una prueba diferencial que llama al símbolo SIMD del binario compilado reprodujo un resultado incorrecto para entradas válidas.
- El llamador GGML resta después la suma de activaciones (`act_sums`) para convertir los códigos empaquetados 0/1/2 a la representación ternaria -1/0/+1. Esa compensación no puede reparar el overflow previo.

**Conclusión demostrada:** el kernel SIMD AVX2 no es aritméticamente correcto para todo el dominio válido de entrada.  
**Conclusión aún no demostrada:** que este defecto sea la única causa —o la causa dominante— de todas las salidas incoherentes de Falcon3. Hace falta probar con activaciones reales del modelo o comparar una inferencia con el kernel SIMD y otra con una implementación corregida/escalar.

## 2. Entorno y procedencia

### Hardware y sistema

- MSI Thin 15 B12UC.
- Intel Core i7-12650H, con AVX2 y AVX-VNNI.
- 14 GiB RAM.
- NVIDIA RTX 3050 Laptop, 4 GiB VRAM.
- Ubuntu; kernel registrado durante la campaña: `7.0.0-43-generic`.
- La compilación analizada es **CPU-only**; no atribuir estos resultados a CUDA/GPU.

### Repositorios y commits

| Componente | Procedencia |
|---|---|
| BitNet | `microsoft/BitNet`, HEAD `0b341e582afbf9e1011f24744b554c96a3477eb5` |
| llama.cpp incluido | `3rdparty/llama.cpp`, commit `5f76dc3871407df2ac3411e00e971fb454cd0429` |
| Build local | `b9919-5f76dc387` |
| Clang | 21.1.8 |
| CMake | 4.2.3 |
| Python | 3.12.15 en `.venv` |
| PyTorch | 2.11.0+cpu |
| Transformers | 4.57.6 |
| gguf Python | 0.19.0 |

El submódulo incorpora el soporte CLI de I2_S necesario para esta campaña: registro del tipo en `ggml_validate_row_data()`, mapeo de `LLAMA_FTYPE_MOSTLY_I2_S` y opción `I2_S` en `llama-quantize`. Commit local del submódulo: `5f76dc3871407df2ac3411e00e971fb454cd0429`.

### Modelo y artefactos

- HF: [tiiuae/Falcon3-10B-Instruct-1.58bit](https://huggingface.co/tiiuae/Falcon3-10B-Instruct-1.58bit).
- Revisión HF: `4b61e8876b19bf7a4b271b757a1bd2974bf38913`.
- `model.safetensors`: 3.986.209.008 bytes.
- GGUF F32: `ggml-model-f32.gguf`, aproximadamente 39 GiB.
- GGUF I2_S: `ggml-model-i2_s.gguf`, 2.811.745.952 bytes (2,62 GiB).
- SHA-256 I2_S: `61abe7e2f9ec1aad4d4916859fa609d6967f34f69c034cd4459a275bfd8ffe7b`.
- Conversión I2_S: 363 tensores; 281 tensores de tipo GGML I2_S; tiempo de cuantización 59.546,31 ms.
- Conservar el F32 y los temporales de conversión hasta cerrar validación. No se adjunta aquí el binario GGUF de varios GiB.

## 3. Conversión y validación estática

### Conversión

La conversión HF → F32 necesitó `--use-temp-file` para evitar que el conversor consumiera más RAM de la disponible. Se exportaron 363 tensores; el GGUF F32 resultante ocupa aproximadamente 39 GiB.

Después se cuantizó a **I2_S** (no IQ2_S):

```text
model size  = 39312.95 MiB (32.00 BPW)
quant size  =  2676.96 MiB (2.18 BPW)
quantize time = 59546.31 ms
```

### Integridad GGUF

Inspección con `gguf.GGUFReader`:

- 363 tensores.
- `general.architecture=llama`.
- `general.name=Falcon3-10B-Instruct-1.58bit`.
- `general.quantization_version=2`.
- `general.file_type=41` (I2_S).
- Distribución: 281 tensores GGML I2_S (tipo 36), 81 F32 (tipo 0), uno de tipo 14.
- Config HF declara `LlamaForCausalLM`, `model_type=llama`, coherente con la arquitectura GGUF.

Esto demuestra que el archivo es reconocible y que contiene tensores I2_S; no demuestra por sí solo que la inferencia sea numéricamente correcta.

### Conversión de pesos y escalas

El conversor extrae `weight_scale` y para I2_S pasa el valor original como `override_scale` a `quantize_to_i2_s()`. El kernel BitNet de referencia usa la escala de pesos como factor multiplicativo (`... * ws[ws_idx]`). Por tanto, la escala directa preservada en I2_S es coherente con esa convención.

Se identificó además una discrepancia en la ruta F32 del conversor: divide por `weight_scale`, mientras que la implementación de referencia reconstruye el peso ternario multiplicando por ese valor. Ejemplo observado en `model.layers.0.mlp.gate_proj.weight`: `weight_scale=23.875`; dividir produce 0,0418848 para un peso +1, mientras que la reconstrucción esperada es +23,875. Este hallazgo afecta a la ruta F32 y debe tratarse por separado; no demuestra que el GGUF I2_S tenga la misma equivocación de escala.

En esa matriz original:
- Shape `(5760, 3072)`, dtype `torch.uint8`.
- Códigos 0: 34,459%; 1: 31,061%; 2: 34,480%; 3: 0%.
- Mapeo del conversor: 0 → -1, 1 → 0, 2 → +1.

El empaquetado CUDA del repositorio de origen aplica permutación WMMA e interleave. No se debe asumir que ese layout está presente en los tensores safetensors; el GGUF I2_S se empaqueta en el layout lineal que consume el kernel GGML CPU.

## 4. Síntoma de inferencia

Cinco intentos de inferencia con el GGUF I2_S cargaron el modelo y generaron tokens, pero no respuestas semánticamente coherentes:

1. `llama-cli` interactivo: salida incoherente; carga I2_S y generación aproximada de 15,1 tok/s.
2. `llama-cli --conversation --single-turn`: salida incoherente y excepción PEG al procesar el resultado.
3. `llama-cli --no-conversation` con prompt manual: salida incoherente y la misma ruta PEG.
4. `llama-completion` con prompt manual HF y `-no-cnv`: salida incoherente, exit code 0; descarta que PEG sea la explicación suficiente.
5. `llama-completion` con `tokenizer.ggml.add_bos_token=false`: salida incoherente repetitiva; desactivar BOS no resolvió el síntoma.

El build mostró avisos de GPU no utilizable, esperado para el build CPU-only. Las métricas de tiempo de evaluación reportadas como 0 ms / infinito no son utilizables como benchmark.

## 5. Tokenizador: comprobaciones realizadas

El tokenizer HF local informa:

- Vocabulario: 131.072.
- BOS: no definido.
- EOS: `<|endoftext|>`, ID 11.
- PAD: `<|pad|>`, ID 2023.
- `\n` → ID 12.
- El prompt manual `<|user|>...<|assistant|>` produce 19 IDs.

El GGUF no contiene `tokenizer.ggml.bos_token_id`; llama.cpp infería BOS=11 y añadía ese ID por defecto. Se verificó que `llama-tokenize --no-bos --no-parse-special --ids` reproduce los 19 IDs HF. Desactivar BOS en generación no arregló la incoherencia, por lo que no es una explicación suficiente.

El aviso `model vocab missing newline token` puede estar relacionado con la diferencia entre el token literal newline esperado por llama.cpp y el token BPE `Ċ`; no se ha demostrado que cause el problema.

## 6. Hallazgo principal: overflow en el kernel AVX2

### Código afectado

Archivo:

`3rdparty/llama.cpp/ggml/src/ggml-cpu/quants.c`

Función:

`ggml_vec_dot_i2_i8_s_1x1()`

Ruta AVX2 compilada cuando `__AVX2__` está definido. Su ejecución efectiva depende del dispatch de GEMM/GEMV y de si `llamafile_sgemm_i2s()` resuelve la operación antes.

En los bucles de acumulación se ejecuta:

```c
accu32 = _mm256_add_epi16(
    accu32, _mm256_add_epi16(xq8_0, xq8_1));
accu32 = _mm256_add_epi16(
    accu32, _mm256_add_epi16(xq8_2, xq8_3));
```

y, en el bucle residual:

```c
accula = _mm256_add_epi16(
    accula, _mm256_add_epi16(xq8_0, xq8_1));
accula = _mm256_add_epi16(
    accula, _mm256_add_epi16(xq8_2, xq8_3));
```

La reducción a 32 bits se realiza después del bucle:

```c
accu = _mm256_add_epi32(
    accu, _mm256_madd_epi16(accula, one16));
```

La ampliación posterior no puede recuperar los bits ya perdidos por overflow en los lanes de 16 bits.

### Dominio de activaciones

`quantize_row_i8_s()` escala cada fila para que el máximo absoluto alcance 127 y limita los valores a [-128, 127]. No existe una restricción que impida una fila válida con activaciones positivas elevadas.

### Prueba diferencial reproducida

Se cargó la biblioteca CPU compilada `build/bin/libggml-cpu.so.0.15.3` mediante `dlopen()` y se resolvió `ggml_vec_dot_i2_i8_s` con `dlsym()`. La firma y los argumentos se contrastaron con el wrapper y los llamadores de GGML.

Entrada:
- K = 3072.
- Pesos empaquetados: todos los bytes `0xAA`, es decir, cuatro códigos 2 por byte.
- Activaciones: todos los elementos `int8_t=127`.
- Una fila (`nrc=1`).
- El kernel lee los bytes empaquetados y las activaciones I8_S sin necesitar la cola de escala del tensor.

Resultados:

| Magnitud | Valor |
|---|---:|
| Producto bruto esperado (código 2 × 127 × 3072) | 780.288 |
| Suma de activaciones | 390.144 |
| Producto ternario esperado (+1 × 127 × 3072) | 390.144 |
| Resultado SIMD observado | -268.288 |
| Resultado SIMD tras compensación `tmp - act_sum` | -658.432 |
| Error final frente al resultado esperado | **-1.048.576** |

El error es exactamente (-16 	imes 65.536), coherente con el wrap-around de acumuladores de 16 bits.

Para K=3072 hay 24 bloques de 128. En este patrón, cada iteración suma 2.032 por lane de 16 bits:

[
24 	imes 2032 = 48768 > 32767
]

El valor envuelve en el acumulador de 16 bits antes de convertirse a 32 bits.

**Corrección de la prueba:** una primera salida de diagnóstico restaba `act_sums` dos veces al calcular una columna «centrada». Esa columna y su diferencia no son válidas. Los valores de referencia correctos son los de la tabla anterior: producto bruto esperado 780.288; SIMD -268.288; diferencia bruta -1.048.576. Después de la compensación GGML, el error final sigue siendo -1.048.576.

### Por qué la compensación GGML no lo repara

El llamador de GGML, en `ggml-cpu.c`, prepara:

- `act_scales` y `act_sums`.
- `ws = *scale` para la escala I2_S.
- `post_scale = ws / act_scales[col]`.

Y finaliza el producto mediante:

```c
dst_row[row] = (tmp[row] - asum) * post_scale;
```

La resta `tmp - asum` es necesaria para convertir los códigos sin signo 0/1/2 al producto ternario -1/0/+1. Pero `tmp` ya está corrupto cuando el acumulador de 16 bits desborda. Restar la suma correcta de activaciones no restaura el valor perdido.

### Impacto y alcance

- **Confirmado:** la función AVX2 devuelve un producto incorrecto para una entrada válida y la diferencia se propaga por el postprocesado GGML.
- **Confirmado:** el binario CPU analizado compila la ruta AVX2; el objeto desensamblado contiene `vpmaddubsw`, `vpaddw` y `vpaddd`, sin `vpdpbusd` en este símbolo.
- **No confirmado:** frecuencia del overflow con activaciones reales de Falcon3.
- **No confirmado:** que este defecto explique por sí solo todos los tokens incoherentes observados.
- **No confirmado:** que la inferencia de Falcon3 en la configuración investigada llegue realmente a este símbolo.
- El dispatcher de `ggml-cpu.c`, cuando `GGML_USE_LLAMAFILE` está habilitado, intenta primero `llamafile_sgemm_i2s()`. En AVX2 esta función llama a `tinyBLAS_I2S_AVX::matmul()` y devuelve éxito; no llega al vec-dot. La clase mantiene acumuladores int32 y pliega una suma int16 por bloque de 128 elementos.
- Si LLAMAFILE está deshabilitado, el fast path I2_S propio procesa bloques de cuatro columnas con `ggml_gemm_i2_i8_s()` y las columnas restantes con `ggml_gemv_i2_i8_s()`; para generación de una columna, GEMV llama al vec-dot AVX2 investigado.
- El CMake de ggml deja `GGML_LLAMAFILE_DEFAULT=OFF` cuando el proyecto padre no lo define. El `setup_env.py` público de BitNet no pasa una opción para activarlo. Esto hace plausible que la ruta vec-dot sea la usada en una build estándar de BitNet, pero la configuración efectiva del build local de Falcon3 sigue sin estar verificada.
- El GEMM propio `ggml_gemm_i2_i8_s()` tiene una rama AVX-VNNI que acumula en 32 bits; la rama AVX2 no-VNNI calcula una suma int16 por bloque y la pliega inmediatamente a int32. El `tinyBLAS_I2S_AVX::gemm` de LLAMAFILE hace lo mismo en cuanto a acumulación por bloque; #628 analiza el coste de ese pliegue frecuente, no el overflow prolongado del vec-dot.

## 7. Antecedentes upstream: defecto ya reportado en BitNet

La consulta del historial y de los informes públicos de GitHub ha encontrado dos incidencias directamente relacionadas. Por tanto, esta investigación **no debe abrir un reporte duplicado** del mismo overflow.

### Microsoft BitNet #629 — mismo kernel AVX2

[Issue #629: Latent int16 overflow in ggml_vec_dot_i2_i8_s_1x1](https://github.com/microsoft/BitNet/issues/629) (abierta, creada el 13-09-2026) describe el mismo patrón en `ggml/src/ggml-cpu/quants.c`:

- El kernel acumula 128 resultados `vpmaddubsw` por lane de 16 bits antes de reducir a 32 bits.
- El límite conservador derivado de la máscara 0..3 es 97.536 por lane; incluso los códigos realmente emitidos 0..2 permiten 65.024, ambos por encima de 32.767.
- El autor midió con pesos reales de BitNet-b1.58-2B-4T y activaciones fijadas a +127: 11.998 de 12.000 filas diferían de la referencia int64.
- Con activaciones ordinarias de su muestra no observó wraps (0/12.000).

**Matiz de dispatch importante:** el autor indica que, en su build, `llamafile_sgemm` atiende esas formas y el kernel `ggml_vec_dot_i2_i8_s_1x1` no se invoca (`calls=0`, `sgemm=52068`). Esto depende de compilar con `GGML_USE_LLAMAFILE`; no es universal para todas las builds.

La revisión del código público aclara ambos caminos:

- Con `GGML_USE_LLAMAFILE` y AVX2, `ggml-cpu.c` llama a `llamafile_sgemm_i2s()`. En `sgemm.cpp`, esa función construye `tinyBLAS_I2S_AVX`, ejecuta `matmul()` y devuelve `true`; el dispatcher retorna sin llegar a GEMV ni al vec-dot.
- Ese GEMM tinyBLAS mantiene acumuladores `int32` y convierte cada suma parcial de 128 elementos desde `int16` a `int32` dentro del bucle. El máximo absoluto conservador de la suma por bloque, con códigos 0..3 y activaciones [-128,127], es 3.072, inferior a 32.767. No presenta la misma acumulación int16 prolongada del vec-dot.
- Sin `GGML_USE_LLAMAFILE`, el fast path I2_S propio de `ggml-cpu.c` procesa lotes de cuatro columnas con `ggml_gemm_i2_i8_s()` y las columnas restantes con `ggml_gemv_i2_i8_s()`. En generación de una columna, GEMV llama al vec-dot AVX2 investigado.
- En `ggml/CMakeLists.txt`, `GGML_LLAMAFILE_DEFAULT` queda en OFF si el proyecto padre no lo define; `GGML_LLAMAFILE` hereda ese valor. El `setup_env.py` público de BitNet no pasa `-DGGML_LLAMAFILE=ON` ni define `GGML_LLAMAFILE_DEFAULT`. Por tanto, la ruta habitual de ese script apunta a LLAMAFILE desactivado, salvo configuración externa/cache previa.

Así, la observación de #629 sobre `calls=0` no debe extrapolarse a la build de Falcon3. La configuración exacta de la build local no está almacenada en GitHub y no se puede dar por verificada todavía. El overflow del vec-dot puede ser alcanzable si LLAMAFILE está desactivado, pero aún hay que demostrar que ocurre con activaciones reales de Falcon3.

Nuestra prueba independiente con K=3072, códigos 2 y activaciones +127 confirma el mismo wrap en el símbolo AVX2: error bruto -1.048.576 y error idéntico tras la compensación `tmp - act_sum`. No constituye un segundo defecto; es corroboración adicional para una longitud K relevante en Falcon3.

### Microsoft BitNet #628 — acumulación en el GEMM AVX2

[Issue #628: i2_s AVX2 GEMM folds the int16 accumulator 10x more often than its own bound requires](https://github.com/microsoft/BitNet/issues/628) analiza otro punto de acumulación, `tinyBLAS_I2S_AVX::gemm`, en `ggml-cpu/llamafile/sgemm.cpp`. Documenta que el camino GEMM activo pliega la suma int16 en cada bloque, aunque el límite derivado permite agrupar varios bloques, y mide una mejora del 7,5% al reducir pliegues sin cambiar perplexity. También señala un segundo punto en `ggml-cpu-i2s.c`.

#628 y #629 son problemas relacionados por el ancho de acumulación, pero **no son el mismo kernel ni deben fusionarse en una sola corrección sin analizar ambos caminos**.

### Procedencia GitHub de la implementación

El `.gitmodules` público de [microsoft/BitNet](https://github.com/microsoft/BitNet/blob/main/.gitmodules) fija `3rdparty/llama.cpp` a la rama `release-bitnet-embedding-0.6b-270m`, cuyo commit observado es `390c307752ab78fd8189f359d6954c9ba1be74af`. El kernel AVX2 afectado ya está presente en ese commit.

El commit `5f76dc3871407df2ac3411e00e971fb454cd0429` usado por el checkout de reproducción local no está disponible como commit público en el fork consultado mediante GitHub; no debe tratarse como una revisión publicada ni como base de un PR hasta localizar/publicar su procedencia. El análisis y la corrección deberán partir de la revisión pública realmente fijada por BitNet o de una rama upstream posterior verificada.

### Implicación para el plan

- No crear un issue duplicado en Microsoft BitNet: #629 ya registra el overflow del vec-dot AVX2.
- No asumir que la ruta por defecto invoca ese vec-dot: comprobar el dispatch de la build concreta.
- Investigar por separado el GEMM tinyBLAS de #628 y el fallback vec-dot de #629.
- Aportar la reproducción Falcon3 como evidencia complementaria en el seguimiento existente, si el acceso GitHub permite comentar; si no, conservar el enlace y la evidencia en LEONES.

## 8. Trabajo pendiente y plan de validación

### P0 — cuantificar el defecto

1. Crear una prueba diferencial reproducible y versionada que compare el símbolo AVX2 con una referencia escalar correcta para:
   - patrones extremos positivos/negativos;
   - activaciones mixtas deterministas;
   - rangos de amplitud crecientes;
   - longitudes K representativas y alineadas.
2. Comprobar explícitamente la semántica de la compensación `act_sums` y la escala de salida.
3. Ejecutar sanitización/validación de memoria si procede; el defecto observado es aritmético, no un acceso fuera de límites.

### P1 — confirmar impacto en el modelo

1. Capturar o instrumentar estadísticas de las activaciones I8_S reales durante una operación GEMV de Falcon3.
2. Calcular por lane/bloque el máximo acumulado y contar los overflows potenciales.
3. Comparar salidas intermedias con referencia escalar o con una implementación AVX2 corregida.
4. Repetir una inferencia corta de Falcon3 únicamente después de tener una ruta diferencial validada.

### P2 — corregir y preparar PR upstream

Evaluar una de estas estrategias, sin decidir antes de medir:
- ensanchar/acumular parcialmente en 32 bits antes de que un lane de 16 bits pueda desbordar;
- reorganizar la reducción para evitar acumulación prolongada en 16 bits;
- añadir una ruta AVX-VNNI con acumulación de 32 bits cuando esté disponible, conservando fallback portable.

Cualquier parche deberá incluir pruebas que cubran el patrón que reproduce el fallo y patrones mixtos. El cambio se desarrollará primero en GitHub, mediante rama y PR; el checkout local se sincronizará después para compilar y validar. No modificar directamente el checkout de trabajo sin autorización expresa.

## 9. Comandos y ubicaciones locales de referencia

Repositorio local de trabajo:

```text
~/bitnet-falcon3-10b
```

Fuentes principales:

```text
3rdparty/llama.cpp/ggml/src/ggml-cpu/quants.c
3rdparty/llama.cpp/ggml/src/ggml-cpu/ggml-cpu.c
3rdparty/llama.cpp/ggml/src/ggml-cpu/ggml-cpu-i2s.c
```

Build:

```text
build/bin/llama-cli
build/bin/llama-completion
build/bin/libggml-cpu.so.0.15.3
```

Logs de inferencia conservados localmente:

```text
logs/first_inference_i2_s.log
logs/fourth_inference_completion.log
logs/fifth_inference_no_bos.log
```

Otros intentos y salida de depuración se documentaron en la sesión de trabajo. La primera prueba C de `dlopen/dlsym` se ejecutó desde `/tmp/test_i2s_overflow.c`. Se ha versionado en GitHub un harness ampliado en `research/bitnet/reproducers/repro_i2s_avx2_dot.c`, con cuatro patrones: todos +127, 90% positivos, bloques alternos de signo y todos +64. **El nuevo harness todavía no se ha compilado ni ejecutado**; queda como siguiente validación local después de sincronizar la rama. No se presenta como resultado medido. Los artefactos binarios grandes (F32, I2_S y pesos HF) permanecen fuera del repositorio LEONES.

## 10. Referencias de código y repositorios

- [BitNet — repositorio Microsoft](https://github.com/microsoft/BitNet).
- [llama.cpp — repositorio upstream](https://github.com/ggml-org/llama.cpp).
- [Falcon3-10B-Instruct-1.58bit — Hugging Face](https://huggingface.co/tiiuae/Falcon3-10B-Instruct-1.58bit).
- `ggml-cpu/quants.c`: `quantize_row_i8_s()`, `dequantize_row_i2_s()`, `quantize_i2_s()`, `ggml_vec_dot_i2_i8_s_1x1()`.
- `ggml-cpu/ggml-cpu.c`: tipo I2_S, cuantización de activaciones y postprocesado GEMV/GEMM.
- `ggml-cpu/ggml-cpu-i2s.c`: rutas especializadas GEMV/GEMM.
- `gpu/convert_checkpoint.py`: cuantización de pesos y convención de escala de referencia.
- `gpu/pack_weight.py`: permutación/interleave del layout CUDA de origen.

---

**Estado LEONES:** investigación reproducible documentada; defecto del kernel AVX2 confirmado para entradas válidas; validación con activaciones reales y corrección upstream pendientes.
