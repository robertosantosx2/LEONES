# Falcon3 I2_S — revisión del tokenizer y metadatos GGUF

**Fecha:** 2026-11-18  
**Repositorio de evidencia:** [LEONES](https://github.com/robertosantosx2/LEONES)  
**Rama:** `research/falcon3-i2s-avx2-overflow-2026-11-18`  
**Alcance:** inspección de código y metadatos; no modifica el GGUF, el conversor ni llama.cpp.

## 1. Evidencia observada del modelo

El GGUF local inspeccionado por el usuario declara:

| Clave | Valor |
|---|---|
| `general.architecture` | `llama` |
| `tokenizer.ggml.model` | `gpt2` |
| `tokenizer.ggml.pre` | `falcon3` |
| `llama.vocab_size` | 131072 |
| `tokenizer.ggml.eos_token_id` | 11 |
| `tokenizer.ggml.padding_token_id` | 2023 |
| `tokenizer.ggml.bos_token_id` | ausente |
| `tokenizer.ggml.tokens` | 131072 entradas |
| `tokenizer.ggml.merges` | 128810 entradas |

El tokenizer HF inspeccionado por el usuario declara `bos_token=null`, EOS `<|endoftext|>` y PAD `<|pad|>`. Su vocabulario asigna `Ċ` (representación GPT-2 del salto de línea) al ID 12, `<|endoftext|>` al ID 11 y `<|pad|>` al ID 2023.

La correspondencia EOS/PAD entre HF y GGUF es consistente. Esto no demuestra todavía que la entrada 12 del array serializado `tokenizer.ggml.tokens` sea idéntica a la del tokenizer HF: el volcado disponible mostró el array truncado.

## 2. Hallazgo de código: comportamiento BOS de llama.cpp

En el commit público del submódulo fijado por BitNet, `390c307752ab78fd8189f359d6954c9ba1be74af`, `src/llama-vocab.cpp` contiene esta secuencia:

1. Para `tokenizer.ggml.model = gpt2`, los valores por defecto son `special_bos_id = 11`, `special_eos_id = 11` y `special_pad_id = LLAMA_TOKEN_NULL` ([código, líneas 2010–2017](https://github.com/isHuangXin/llama.cpp/blob/390c307752ab78fd8189f359d6954c9ba1be74af/src/llama-vocab.cpp#L2010-L2017)).
2. Para `tokenizer.ggml.pre = falcon3`, la rama compartida con Llama 3 asigna `pre_type = LLAMA_VOCAB_PRE_TYPE_LLAMA3`, `ignore_merges = true` y `add_bos = true` ([código, líneas 2129–2138](https://github.com/isHuangXin/llama.cpp/blob/390c307752ab78fd8189f359d6954c9ba1be74af/src/llama-vocab.cpp#L2129-L2138)).
3. El tokenizer BPE añade `vocab.token_bos()` cuando la llamada permite tokens especiales ([código, línea 3375 y siguientes](https://github.com/isHuangXin/llama.cpp/blob/390c307752ab78fd8189f359d6954c9ba1be74af/src/llama-vocab.cpp#L3370-L3385)).

Como el GGUF examinado no contiene `tokenizer.ggml.bos_token_id`, el valor por defecto 11 permanece activo. En consecuencia, en este commit, una tokenización BPE con tokens especiales puede anteponer el ID 11 como BOS; ese mismo ID es el EOS declarado por el modelo. Esto es una **incompatibilidad potencial de metadatos/selección BOS**, no una prueba de que explique por sí sola la generación incoherente.

La campaña ya contiene una inferencia con BOS desactivado que siguió generando texto incoherente. Por tanto, corregir o desactivar BOS no debe presentarse como solución suficiente sin una prueba diferencial adicional.

## 3. Hallazgo de código: advertencia de newline

La advertencia:

`model vocab missing newline token, using special_pad_id instead`

se emite cuando `src/llama-vocab.cpp` ejecuta `tokenize("\\n", false)` y obtiene un vector vacío ([código, líneas 2485–2494](https://github.com/isHuangXin/llama.cpp/blob/390c307752ab78fd8189f359d6954c9ba1be74af/src/llama-vocab.cpp#L2485-L2494)).

Por tanto, la advertencia demuestra que **el tokenizador interno de esa build no consiguió tokenizar el texto newline durante la inicialización**. No demuestra que el tokenizer HF carezca de representación newline: el tokenizer original sí asigna `Ċ` al ID 12.

Hay además un detalle de orden de inicialización que requiere atención: para el modelo BPE GPT-2, `special_pad_id` comienza como `LLAMA_TOKEN_NULL`; la lectura de metadatos especiales —incluido `tokenizer.ggml.padding_token_id`— aparece después del cálculo de `linefeed_id` ([inicialización BPE y defaults](https://github.com/isHuangXin/llama.cpp/blob/390c307752ab78fd8189f359d6954c9ba1be74af/src/llama-vocab.cpp#L1967-L2017), [cálculo de newline y lectura posterior de tokens especiales](https://github.com/isHuangXin/llama.cpp/blob/390c307752ab78fd8189f359d6954c9ba1be74af/src/llama-vocab.cpp#L2485-L2525)). Si se activa ese fallback, `linefeed_id` puede quedar asignado al valor nulo inicial, no al PAD 2023 leído posteriormente. Debe verificarse el efecto real de este campo antes de atribuirle consecuencias sobre la generación.

## 4. Conversor BitNet

El conversor público de BitNet:

- construye el array de tokens por ID a partir de `tokenizer.vocab`;
- conserva las entradas añadidas con su tipo CONTROL/USER_DEFINED;
- asigna el pretokenizer `falcon3` cuando coincide el hash de la secuencia de comprobación;
- escribe `tokenizer.ggml.model = gpt2`, el pretokenizer, tokens, tipos y vocabulario especial.

Referencias: [construcción del vocabulario, líneas 260–290](https://github.com/microsoft/BitNet/blob/0b341e582afbf9e1011f24744b554c96a3477eb5/utils/convert-hf-to-gguf-bitnet.py#L260-L290), [detección del pretokenizer Falcon3, líneas 340–352](https://github.com/microsoft/BitNet/blob/0b341e582afbf9e1011f24744b554c96a3477eb5/utils/convert-hf-to-gguf-bitnet.py#L340-L352), [escritura del vocabulario GPT-2, líneas 370–380](https://github.com/microsoft/BitNet/blob/0b341e582afbf9e1011f24744b554c96a3477eb5/utils/convert-hf-to-gguf-bitnet.py#L370-L380).

La inspección estática no ha demostrado todavía que el conversor escriba mal el token 12 ni que el pretokenizer `falcon3` sea incorrecto. No se debe modificar manualmente el vocabulario ni cambiar el hash del pretokenizer sin una reproducción diferencial.

## 5. Conclusiones y próximos pasos

**Confirmado por los metadatos aportados:**
- HF y GGUF coinciden en EOS 11 y PAD 2023.
- HF no declara BOS.
- HF representa newline mediante el token GPT-2 `Ċ` con ID 12.
- El GGUF declara GPT-2 BPE con pretokenizer `falcon3` y no declara BOS explícito.

**Confirmado por inspección del código público `390c307`:**
- La rama `falcon3` activa `add_bos=true`.
- El default BOS de GPT-2 en esa revisión es ID 11, que coincide con EOS del GGUF.
- La advertencia de newline se emite porque la tokenización interna de `\\n` devuelve cero tokens.
- El fallback de newline se calcula antes de leer el PAD especial del GGUF.

**Pendiente:**
1. Verificar el valor real de `tokenizer.ggml.tokens[12]` y `tokenizer.ggml.token_type[12]` en el GGUF completo.
2. Reproducir con el mismo commit la tokenización de `\\n`, `Ċ`, tabulador y texto ordinario; registrar IDs y piezas.
3. Registrar explícitamente `llama_vocab_bos()`, `llama_vocab_eos()`, `llama_vocab_nl()`, `llama_vocab_pad()` y el comportamiento con/sin `add_special`.
4. Comparar los IDs de prompt y tokens generados con el tokenizer HF original.
5. Solo después, decidir si procede corregir metadatos en el conversor o comportamiento en llama.cpp.

La prueba previa con `--no-bos` siguió produciendo salida incoherente; el hallazgo BOS es una anomalía concreta que debe corregirse/aislar, pero no cierra la causa E2E. Tampoco se atribuye causalidad al kernel AVX2: el runtime de control no-AVX2 reproduce el síntoma.

**No se ha modificado el conversor, el GGUF ni llama.cpp; no se ha abierto ningún PR upstream.**


## 6. Evidencia adicional aportada por la inspección local (segunda revisión)

El usuario inspeccionó el checkout BitNet y confirmó el origen exacto de la advertencia en `src/llama-vocab.cpp`:

- La rama `LLAMA_VOCAB_TYPE_RWKV` contiene un `GGML_ASSERT` si no se tokeniza newline.
- La rama general (que incluye el BPE GPT-2 del GGUF) llama a `tokenize("\\n", false)`; si el resultado está vacío, emite la advertencia y asigna `linefeed_id = special_pad_id`.
- La advertencia, por tanto, **no demuestra que falte el token newline en el vocabulario serializado**. Demuestra que esa ruta de tokenización de llama.cpp no pudo obtener un ID para el carácter LF en la inicialización.

La inspección HF adicional confirmó:

| Token | ID HF |
|---|---:|
| `<|startoftext|>` | 10 |
| `<|endoftext|>` | 11 |
| `Ċ` (símbolo GPT-2 para LF) | 12 |
| `ĉ` (símbolo GPT-2 para TAB) | 13 |
| `<|pad|>` | 2023 |

Los IDs 10, 11 y 2023 aparecen en `added_tokens`; los IDs 12 y 13 proceden del vocabulario base. El conversor BitNet recorre `tokenizer.vocab` por ID y, para tokens añadidos, aplica encode/decode para preservar caracteres especiales; el resto se copia desde el vocabulario base. El comentario del conversor sobre newline/tab añadidos manualmente no prueba que LF/TAB sean added tokens en este modelo concreto.

El GGUF completo vuelve a confirmar `tokenizer.ggml.model=gpt2`, `tokenizer.ggml.pre=falcon3`, EOS 11 y PAD 2023; no contiene BOS explícito. El volcado corto no muestra los valores completos de `tokens[12]` ni `token_type[12]`, por lo que no se afirma que la serialización de esos slots sea correcta o incorrecta.

La generación válida con `llama-completion` en el control no-AVX2 produjo exactamente seis bytes de whitespace (LF, TAB, TAB, LF, LF, LF), con 31 pasos de generación, sin texto visible. Esto confirma que el proceso de completion ejecutó decodificación, pero no permite conocer los IDs muestreados; es imprescindible registrar IDs y piezas, no solo el texto decodificado.

### 6.1. Corrección de interpretación del hallazgo newline

La hipótesis inicial de que el fallback se calculaba antes de leer PAD debe mantenerse como detalle de orden de inicialización del código, pero **no debe elevarse a causa raíz**. La observación clave ahora es la discrepancia entre el vocabulario HF (LF representado por `Ċ`, ID 12) y el hecho de que el tokenizer BPE de llama.cpp devuelve cero IDs para el carácter LF en esa build. Debe aislarse si la causa es el pretokenizer `falcon3`, la implementación de tokenización, los tipos/strings GGUF o una diferencia entre los checkouts usados.

### 6.2. Sonda remota añadida

Se añade un workflow de GitHub Actions que compila el `llama-tokenize` de la revisión fijada y empaqueta el ejecutable con sus bibliotecas. El objetivo es ejecutar, contra el GGUF real del usuario, comparaciones reproducibles de:

- LF literal (archivo de entrada, no una secuencia de dos caracteres backslash+n);
- el símbolo visible `Ċ`;
- TAB literal y texto ordinario;
- tokenización con BOS por defecto y con `--no-bos`;
- IDs numéricos y piezas decodificadas.

El workflow no altera ni convierte el modelo. Tampoco cambia el comportamiento de inferencia. Los resultados de esta sonda deben acompañarse del SHA256 del GGUF y de la versión exacta del runtime.

**Criterio de decisión:** si LF literal no se tokeniza pero `Ċ` sí, investigar el mapeo byte-level/pretokenizer; si ambos fallan, inspeccionar arrays `tokenizer.ggml.tokens` y `token_type` del GGUF; si ambos funcionan, la advertencia debe reproducirse en el build exacto antes de atribuirle relevancia. Para BOS, comparar las secuencias con y sin `--no-bos` y comprobar explícitamente que el ID 11 no se antepone como BOS en el flujo de prompt.

## 7. Estado actualizado

- **Confirmado:** HF newline visible `Ċ` ID 12; HF tab visible `ĉ` ID 13; EOS 11; PAD 2023.
- **Confirmado:** el mensaje de warning se genera en la ruta general cuando `tokenize("\\n", false)` devuelve vacío.
- **Confirmado:** la ejecución completion no-AVX2 produjo whitespace, no texto legible.
- **Pendiente:** IDs/piezas efectivos de LF, TAB, `Ċ`, BOS y prompt en el mismo commit y contra el GGUF real.
- **No demostrado:** que el warning newline o la anomalía BOS expliquen por sí solos la generación incoherente.
- **Sin cambios:** no se ha modificado el GGUF, el conversor ni el código de llama.cpp; no se ha abierto PR upstream.
