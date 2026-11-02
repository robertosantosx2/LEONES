# Qwen3.5-4B en TensorFold CUDA: geometría de scratch y admisión de memoria

**Fecha:** 2026-11-02  
**Estado:** análisis de código y corrección propuesta en PR; compilación y prueba GPU pendientes.  
**Restricción de ejecución:** este trabajo se ha realizado sobre GitHub y documentación. No se ha utilizado el Ubuntu físico del equipo.

## 1. Resultado histórico que sirve de referencia

LEONES ya contiene una ejecución física completada:

- **Motor:** TensorFold native 1.1.1, CUDA.
- **Modelo:** `mlx-community/Qwen3.5-4B-MLX-4bit`, revisión `32f3e8ecf65426fc3306969496342d504bfa13f3`.
- **GPU:** NVIDIA RTX 3050 Laptop, 4 GiB.
- **Contexto:** 512.
- **Carga:** 6,4 s.
- **Generación:** 53,64 tok/s (64 tokens) y 53,42 tok/s (128 tokens).
- **TTFT:** 193 ms y 212 ms.
- **VRAM:** 3.120 MiB asociadas al proceso; 3.143 / 4.096 MiB en la captura total.
- **Resultado:** inferencia real en español.

Registro original: [TensorFold local: pruebas Qwen3.5 en Ubuntu — 2026-10-19](https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/tensorfold-qwen35-local-results-2026-10-19.md). Inventario: [comparativa Qwen3.5, TensorFold y llama.cpp](./inventario-comparativo-qwen35-tensorfold-llamacpp-2026-10-20.md).

El registro también conserva un arranque rechazado con `TENSORFOLD_CUDA_MEMORY_LIMIT_GB=3.4` y reserva de 0,5 GiB: TensorFold informó de 1,3 GiB libres y solo 0,8 GiB de presupuesto frente a unos 2,8 GiB de pesos. **Ese rechazo concreto fue provocado por el límite configurado y la memoria libre de aquel momento; no demuestra por sí solo un error del estimador de scratch.** Después se completó la ejecución con contexto 512.

Por separado, `tensorfold-native info` estimaba 4,85 GiB (2,85 GiB de pesos más un margen genérico de 2 GiB). Esa estimación informativa tampoco impidió la ejecución posterior. La evidencia histórica demuestra que el modelo sí puede ejecutarse en esta GPU, pero no identifica por sí sola el motivo de cada rechazo de admisión en versiones posteriores.

## 2. Geometría real usada en el cálculo

La configuración de Qwen3.5-4B declara:

| Parámetro | Valor |
|---|---:|
| hidden_size | 2.560 |
| intermediate_size | 9.216 |
| num_hidden_layers | 32 |
| vocab_size | 248.320 |
| num_attention_heads | 16 |
| num_key_value_heads | 4 |
| linear_num_key_heads | 16 |
| linear_num_value_heads | 32 |
| head_dim | 256 |
| Cuantización MLX | 4 bits, group size 64 |
| Arquitectura | Dense, no MoE |

Fuente: [config.json del checkpoint Qwen3.5-4B](https://huggingface.co/mlx-community/Qwen3.5-4B-MLX-4bit/blob/32f3e8ecf65426fc3306969496342d504bfa13f3/config.json).

Derivaciones que utiliza `cuda_geometry.zig`:

- `valueWidth = 32 × 128 = 4.096`.
- `attnWidth = 16 × 256 = 4.096`.
- `convWidth = (2 × 16 + 32) × 128 = 8.192`.
- `wide = max(valueWidth, attnWidth, hidden) = 4.096`.
- `max(intermediate, wide) = 9.216`.
- `g.moe() = false`: no se reserva scratch de expertos enrutados.

## 3. Fórmula de scratch CUDA

Se ha reconstruido la suma desde las asignaciones de `Engine.scratch()`, respetando la alineación individual de 256 bytes que aplica TensorFold.

### Buffers fijos de verificación

| Buffer | Bytes |
|---|---:|
| `pm` | 524.288 |
| `pl` | 524.288 |
| `po` | 134.217.728 |
| `logits` | 63.569.920 |
| `amax` | 62.464 |
| `picks` | 1.048.576 |
| **Total fijo** | **199.947.264 bytes = 190,68457 MiB** |

### Buffers que crecen con las filas

La suma de las asignaciones por fila es **159.616 bytes = 155,875 KiB/fila**:

| Grupo | Bytes por fila antes de alineación |
|---|---:|
| `h/x/r` | 15.360 |
| `y/mix/z/v` | 32.768 |
| `q/k` | 8.192 |
| `qkv` | 16.384 |
| `gate/up/act` | 55.296 |
| `xs` | 576 |
| `a/b/beta` | 192 |
| `g_` | 128 |
| `qraw` | 16.384 |
| `qn` | 8.192 |
| `kraw/vraw/kn` | 6.144 |
| **Total** | **159.616** |

Para los tamaños de fila de esta tabla, la alineación de 256 bytes queda respetada en cada buffer. Por tanto:

`S(R) = 199.947.264 + 159.616 × R bytes`

Esta fórmula describe el scratch del motor Qwen3.5 denso; no incluye pesos, buffers de carga, módulos CUDA, cachés KV, memoria del driver ni otros procesos.

### Resultado por número de filas

| Filas | Scratch total | Ahorro frente a 4.096 filas |
|---:|---:|---:|
| 32 | 195,55566 MiB | 618,62891 MiB |
| 64 | 200,42676 MiB | 613,75781 MiB |
| 128 | 210,16895 MiB | 604,01562 MiB |
| 256 | 229,65332 MiB | 584,53125 MiB |
| 512 | 268,62207 MiB | 545,56250 MiB |
| 4.096 | 814,18457 MiB | 0 MiB |

**Matiz esencial para la prueba histórica:** el contexto servido fue 512. Si se limita correctamente el scratch al contexto configurado, 4.096 filas no son el techo relevante para esa ejecución; el techo es 512 filas. En ese escenario, la reducción del tamaño final de scratch respecto a 512 filas sería:

| Filas efectivas | Scratch | Ahorro frente a 512 filas |
|---:|---:|---:|
| 32 | 195,55566 MiB | 73,06641 MiB |
| 64 | 200,42676 MiB | 68,19531 MiB |
| 128 | 210,16895 MiB | 58,45312 MiB |
| 256 | 229,65332 MiB | 38,96875 MiB |
| 512 | 268,62207 MiB | 0 MiB |

No deben mezclarse los dos escenarios: el ahorro frente a 4.096 filas describe el techo global del kernel; el ahorro frente a 512 filas es la comparación pertinente para el contexto histórico 512.

### Workspace opcional de prompt INT8

Con `K = max(9.216, 4.096, 4.096, 2.560) = 9.216`, el código `cuda.w4a8.Kernels.scratch` reserva:

`I(R) = R × K + 2 × R × (K / 64) × 4 = 10.368 × R bytes`

| Filas | Workspace INT8 |
|---:|---:|
| 32 | 0,31641 MiB |
| 64 | 0,63281 MiB |
| 128 | 1,26563 MiB |
| 256 | 2,53125 MiB |
| 512 | 5,06250 MiB |

Este workspace solo se añade cuando `--prompt-precision int8` está activado. El indicador de excepción INT8 ocupa otros 4 bytes.

## 4. Problema de admisión detectado en PR #1879

PR: [fix(cuda): allocate Qwen3.5 scratch lazily](https://github.com/ashhart/TensorFold/pull/1879).

El parche separa el scratch del arena de pesos y crece bajo demanda. Las revisiones del PR identificaron que sumar `scratch_bytes` al modelo no era suficiente: `Pool.room()` ignora `held` cuando no hay `TENSORFOLD_CUDA_MEMORY_LIMIT_GB`. En consecuencia, la admisión podía asignar a streams/cachés una memoria que todavía no estaba físicamente ocupada, pero que el primer crecimiento de scratch necesitaría.

Había además que contar el pico de ampliación. `ensureScratch()` reserva el buffer nuevo antes de liberar el anterior para conservar el buffer activo si falla la asignación. Por tanto, durante el crecimiento coexisten temporalmente ambos buffers.

La corrección aplicada en la rama del PR sigue estas reglas:

1. **Límite de filas real:** pasar el contexto servido al constructor del motor y fijar `scratch_rows = min(context, 4096)` antes del warmup. El warmup ya no intenta reservar automáticamente el máximo global de 4.096 filas cuando el servidor solo admite 512.
2. **Reserva del reemplazo completo:** si la capacidad actual es menor que `scratch_rows`, reservar el tamaño completo del buffer de reemplazo. El buffer anterior ya está contabilizado en el uso CUDA vivo; no se debe restar de nuevo ni reservar solo la diferencia final, porque el pico es antiguo + nuevo.
3. **Admisión con y sin límite:** calcular el espacio como `Pool.room(actual_model) - pending_scratch`. Se aplica el descuento incluso si `TENSORFOLD_CUDA_MEMORY_LIMIT_GB` está sin configurar.
4. **INT8:** aplicar el mismo criterio al workspace INT8 opcional. Si ambos workspaces deben crecer, calcular el máximo pico según el orden real (scratch principal primero, INT8 después), descontando el scratch antiguo cuando ya se ha sustituido; no sumar ciegamente dos buffers de reemplazo completos.
5. **Compatibilidad de llamadas:** actualizar también el servidor, la herramienta de entrenamiento y los binarios de prueba CUDA para pasar el límite de filas al constructor.
5. **Mantenibilidad:** mover las funciones de cálculo y crecimiento a `cuda_scratch.zig`; las dos fuentes que habían superado el límite del proyecto quedan en 597 y 599 líneas; además, los 12 archivos modificados no presentan comentarios multilínea ni comentarios de más de 120 columnas según la regla de lean.

Código de la rama: [cuda_scratch.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/families/qwen3_5/cuda_scratch.zig), [cuda_engine.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/families/qwen3_5/cuda_engine.zig), [cuda_native.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/families/qwen3_5/cuda_native.zig), [native/cuda.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/native/cuda.zig), [native/cuda_memory.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/native/cuda_memory.zig), [cuda_family_host.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/build/cuda_family_host.zig), [qwen35_learn.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/cli/qwen35_learn.zig) y [qwen35_cuda_main.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/tests/qwen35_cuda_main.zig).

## 5. Estado de validación

- **Ejecución histórica 1.1.1:** medida en hardware físico y documentada en LEONES.
- **Geometría y cálculo:** reconstruidos a partir de las asignaciones del código y del config del checkpoint.
- **Cambios de código:** enviados a la rama `fix/qwen35-cuda-lazy-scratch`; PR #1879 sigue abierto y no está fusionado.
- **Pruebas host añadidas y conectadas a la build:** `test-cuda-memory-admission-host` comprueba el descuento de memoria pendiente con y sin límite CUDA; `test-qwen35-scratch-host` comprueba la reserva del buffer de reemplazo. Ambas quedan incluidas en `test-cuda-host`.
- **Build y pruebas automáticas de la nueva cabeza:** no ejecutados en esta fase. GitHub no informa de workflow runs ni de status checks para la cabeza consultada.
- **Prueba CUDA en RTX 3050:** pendiente. No se ha utilizado Ubuntu durante este análisis.

No presentar los cambios como compilados o validados por GPU. La siguiente fase será una prueba controlada en Ubuntu, aislada de la instalación estable y del servidor llama.cpp por defecto. Debe registrar memoria libre antes de carga, uso durante warmup, capacidad de scratch, pico de VRAM durante crecimiento, admisión de streams, inferencia, TTFT, tok/s y resultado de salida.

## Validación host comunicada el 2026-11-03

La primera ejecución local de `zig build test-cuda-host -Dtarget=x86_64-linux-gnu` terminó con varios `failed command`; por tanto, la suite global no puede declararse verde.

Distinción importante al interpretar el registro:

- `FAIL no-op projection` aparece en el test preexistente `zig/tests/cuda/projection_f32_host_tests.zig`, cuyo caso de prueba inyecta deliberadamente un lanzamiento CUDA que no escribe y comprueba `expectError(error.TestFailed, ...)`. Ese texto es parte de la prueba negativa, no prueba por sí solo un defecto de scratch.
- Los errores de `CPU reference comparison` proceden de pruebas cuantizadas existentes, no de los 12 archivos modificados por este PR. Hay recibos históricos del repositorio que contienen los mismos diagnósticos; aun así, el proceso de prueba devuelve fallo y no se debe ocultar.
- También aparecen salidas de pruebas de rechazo/errores simulados (topología GLM, contratos de kernels, carga de pesos y dependencias opcionales). Deben separarse de los dos tests nuevos antes de atribuir un fallo al parche.

El usuario confirmó que `nvcc` está disponible en `/usr/local/cuda-13.4/bin/nvcc`. Esto permite pasar a la compilación CUDA `sm_86` cuando los dos tests host específicos del parche estén aislados y aprobados.

**Pendiente inmediato:** registrar por separado el resultado de `test-qwen35-scratch-host` y `test-cuda-memory-admission-host`. La salida global de `test-cuda-host` no los sustituye. No se ha iniciado todavía la ejecución real en GPU con esta cabeza.


## Validación aislada y revisión de integración — 2026-11-03

El usuario ejecutó en el checkout aislado `~/tensorfold-pr1879-validation-20261102` los dos objetivos siguientes, ambos con `-Dtarget=x86_64-linux-gnu`:

- `zig build test-qwen35-scratch-host -Dtarget=x86_64-linux-gnu`: terminó sin salida de error.
- `zig build test-cuda-memory-admission-host -Dtarget=x86_64-linux-gnu`: terminó sin salida de error.

Se consideran **superados ambos tests host específicos**, según la salida comunicada. Esto no convierte en verde la suite global `test-cuda-host`, que había reportado otros fallos, ni valida la ejecución CUDA en GPU.

### Verificación del cableado del contador de scratch

La revisión directa de la rama `fix/qwen35-cuda-lazy-scratch` confirma que la estimación sí llega al punto genérico de admisión:

1. `zig/src/families/qwen3_5/cuda_native.zig` declara `Loaded.scratch_bytes`.
2. `Qwen3.5.open()` lo inicializa con `try e.unallocatedScratchBytes()`.
3. `zig/src/native/cuda.zig` lee el campo mediante `@hasField(L, "scratch_bytes")`, suma los bytes pendientes al consumo modelado y llama a `after.roomAfterPending(actual_model, unallocated_scratch)` antes de calcular el espacio para streams/cachés.

Por tanto, la sospecha previa de que el método del motor estuviera desconectado era incorrecta y queda retirada. La secuencia de inicialización también importa: `Engine.init()` ejecuta `finishWarm()`, que llama al warmup antes de que `Qwen3.5.open()` construya `Loaded`; el cálculo de `scratch_bytes` refleja así la capacidad ya conseguida y el crecimiento que todavía podría quedar pendiente. Con `--prompt-precision int8`, el workspace opcional se prepara antes de construir `Loaded` y el estimador contempla su capacidad pendiente.

### Estado actualizado

- Tests host específicos de scratch y admisión: **superados** según la ejecución local comunicada.
- Cableado `Engine.unallocatedScratchBytes() → Loaded.scratch_bytes → cuda.zig`: **verificado en código**.
- Suite host global: **no superada**; los fallos generales anteriores siguen separados de los dos tests nuevos.
- Compilación de kernels CUDA para sm_86: pendiente.
- Inferencia y medición en RTX 3050: pendiente; no se ha solicitado todavía una nueva ejecución GPU.

La salida silenciosa de los dos comandos no incluye contadores de tests, pero ambos procesos regresaron al prompt sin errores visibles.


## Compilación CUDA y validación host completadas — 2026-11-03

El usuario ejecutó en Ubuntu, dentro del checkout aislado `~/tensorfold-pr1879-validation-20261102`, con `/usr/local/cuda-13.4/bin` añadido a `PATH`, estos objetivos:

```sh
zig build test-qwen35-scratch-host -Dtarget=x86_64-linux-gnu
zig build test-cuda-memory-admission-host -Dtarget=x86_64-linux-gnu
zig build check-native-cuda-host compile-cuda-tests -Dtarget=x86_64-linux-gnu
```

Los cuatro objetivos terminaron regresando al prompt sin errores visibles. Se registran como **superados según la salida comunicada**. Los dos tests host específicos pasan y los objetivos de comprobación host nativa y compilación de tests CUDA también completaron sin fallo visible.

Límites: la salida no incluye un resumen explícito de tests ni identifica por sí sola todos los artefactos generados; tampoco demuestra que los kernels se ejecuten correctamente en la RTX 3050, ni que la admisión y el crecimiento de scratch funcionen bajo presión real de VRAM. La suite global `test-cuda-host` continúa registrada como fallida por otros objetivos ajenos a estas pruebas aisladas.

**Siguiente fase:** inspeccionar los artefactos/targets y realizar una prueba GPU controlada en el checkout aislado. Antes de inferencia, registrar VRAM libre y procesos, modelo/revisión, contexto 512 y configuración de memoria; no tocar la instalación estable ni el puerto 8080. Medir carga, warmup, VRAM máxima, scratch efectivo, admisión, TTFT, tok/s y salida. Detener si la memoria disponible no permite una carga segura.


## Ejecución física con PR #1879 en RTX 3050 — 2026-11-03

**Esta sección actualiza y sustituye las indicaciones anteriores que describían la prueba GPU como pendiente.** La ejecución se realizó en Ubuntu, en el checkout aislado `~/tensorfold-pr1879-validation-20261102`, sin sustituir la instalación estable ni utilizar el puerto habitual 8080.

### Identidad de la prueba

- Rama: `fix/qwen35-cuda-lazy-scratch`.
- Commit probado: `b880e52707780032c3bad1b3086657c41df89ffb`.
- Binario: `zig-out-pr1879/native/bin/tensorfold-native`, compilado para Linux x86-64, CUDA, SM 86, ReleaseFast.
- Modelo: `mlx-community/Qwen3.5-4B-MLX-4bit`.
- Revisión: `32f3e8ecf65426fc3306969496342d504bfa13f3`.
- GPU: NVIDIA GeForce RTX 3050 Laptop, 4.096 MiB.
- Servidor: `127.0.0.1:18083`, contexto 512, parallel 1, max-inflight 1.
- Entorno: `TENSORFOLD_MEMORY_RESERVE_GIB=0.5`, `HF_HUB_OFFLINE=1`.
- Arranque: pesos 2,81 GiB; un stream; scratch anunciado 0,21 GiB para ventana 512; reserva 0,5 GiB; carga completada en **10,4 s**.
- El intento inicial con la reserva predeterminada de 1 GiB fue rechazado por el presupuesto de admisión (3,6 GiB libres menos 1 GiB de reserva, frente a pesos de 2,8 GiB). Al reducir explícitamente la reserva a 0,5 GiB, el servidor cargó. El rechazo inicial no se debe presentar como fallo del parche.

### Inferencias reales

Las tres peticiones recibieron HTTP 200. Las dos primeras quedaron limitadas por `max_tokens`; la tercera finalizó normalmente con `finish_reason=stop`.

| Métrica | Thinking ON | Thinking OFF | Thinking OFF |
|---|---:|---:|---:|
| Archivo de evidencia | `pr1879-inference-128.json` | `pr1879-inference-no-thinking-192.json` | `pr1879-inference-no-thinking-256.json` |
| Tokens de entrada | 51 | 56 | 59 |
| Tokens generados | 128 | 192 | 133 |
| Velocidad | 56,05 tok/s | 54,32 tok/s | 55,92 tok/s |
| TTFT | 194,1 ms | 187,6 ms | 187,2 ms |
| Prefill | 188,1 ms | 184,1 ms | 183,5 ms |
| Tiempo de generación del motor | 2,266 s | 3,516 s | 2,360 s |
| Finalización | `length` | `length` | `stop` |
| Aceptación especulativa | 0/15 (0 %) | 1/99 (1,01 %) | 3/63 (4,76 %) |

La tercera solicitud pidió un máximo de 256 tokens, pero el modelo produjo 133 y terminó con `stop`; no fue truncada por el límite. Las velocidades son las comunicadas por el servidor en `tensorfold`, no una estimación a partir del tiempo total de curl.

La aceptación especulativa fue baja en las tres solicitudes. No hay evidencia de que speculative decoding explique la velocidad observada ni de una aceleración relevante por aceptación de borradores.

### VRAM observada

El registro `evidence/pr1879-gpu-monitor.csv` se tomó con `nvidia-smi` a intervalos de un segundo:

- Reposo inicial: 15 MiB usados y 3.754 MiB libres según la consulta de NVIDIA.
- Al cargar: 3.055 MiB usados.
- Tras completar la carga: 3.211–3.215 MiB usados.
- Durante la tercera inferencia: máximo observado de **3.227 MiB usados**, con **542 MiB libres** en la misma lectura; utilización GPU del 100 % durante varios segundos y temperatura máxima observada de 56 °C.
- En el muestreo correspondiente a las inferencias posteriores, el uso residente subió unos pocos MiB respecto al estado estable del servidor.

Estas cifras son lecturas globales de `nvidia-smi`, no un perfil de asignaciones por buffer ni una medida aislada del scratch. No permiten atribuir esos MiB adicionales a un buffer concreto ni demostrar por sí solas cuánto scratch se llegó a materializar. Sí documentan que el servidor permaneció residente y completó las tres inferencias en la GPU de 4 GiB sin OOM.

### Calidad de la respuesta: advertencia importante

La tercera respuesta explica incorrectamente que la asignación CUDA bajo demanda permite almacenar el modelo en RAM del host cuando la VRAM está llena. Esa no es la función del parche y no debe copiarse como explicación técnica válida.

La distinción correcta es:

- El parche difiere la asignación de los **buffers scratch CUDA** hasta que el motor los necesita y contabiliza el crecimiento pendiente al admitir streams y cachés.
- No traslada automáticamente los pesos a RAM, no convierte la RAM del host en VRAM y no permite superar la capacidad física de la GPU.
- El scratch que llegue a necesitar la inferencia activa debe caber en la memoria CUDA disponible. La ventaja buscada es evitar comprometer por adelantado capacidad que no se usa, no eliminar el requisito de que las asignaciones efectivas quepan.
- Por tanto, esta respuesta es una inferencia funcional correcta en términos de HTTP/generación, pero contiene una explicación factual equivocada. No se considera una validación semántica satisfactoria.

### Conclusión actualizada

**Resultado positivo de ejecución:** el binario de la rama no fusionada del PR #1879 cargó Qwen3.5-4B en la RTX 3050 de 4 GiB con reserva explícita de 0,5 GiB y completó tres inferencias reales a 54,32–56,05 tok/s, con TTFT de 187–194 ms. El pico global observado fue 3.227 MiB.

**Qué queda demostrado:** compilación del binario experimental, carga CUDA, servicio OpenAI-compatible e inferencia real repetida bajo la configuración indicada.

**Qué no queda demostrado:** ahorro exacto de VRAM atribuible al scratch lazy frente a la versión base, pico exacto de cada buffer, comportamiento bajo crecimiento forzado hasta el máximo de filas, robustez con otros contextos o concurrencia, ni mejora semántica del modelo. Para cuantificar el ahorro causal hace falta una comparación controlada con la versión base, misma revisión del modelo, contexto, reserva, estado de GPU y carga de peticiones.

**Estado de la suite:** los dos tests host específicos y los objetivos de compilación CUDA/host descritos anteriormente terminaron sin errores visibles según la salida comunicada. La suite global `test-cuda-host` sigue sin poder declararse superada por sus fallos en otros objetivos.

### Evidencias locales

Dentro de `~/tensorfold-pr1879-validation-20261102/evidence/`:

- `pr1879-server-startup-reserve-05.log`
- `pr1879-gpu-monitor.csv`
- `pr1879-inference-128.json`
- `pr1879-inference-no-thinking-192.json`
- `pr1879-inference-no-thinking-256.json`

La prueba es independiente de la ejecución histórica TensorFold 1.1.1 del 19-10-2026. No deben fusionarse sus cifras: son builds, fechas y condiciones de ejecución diferentes.


## Comparación física controlada: baseline frente a PR #1879 — 2026-11-03

**Resultado decisivo:** con la misma GPU, modelo, revisión, contexto, concurrencia y reserva de memoria, el baseline no consigue cargar Qwen3.5-4B; el binario del PR #1879 sí lo carga y completa inferencias reales. Esta prueba demuestra una diferencia funcional de admisión/carga en el equipo ensayado. No es una comparación de velocidad, porque el baseline no llegó a iniciar el servidor.

### Identidad y condiciones comunes

| Parámetro | Baseline | PR #1879 |
|---|---|---|
| Commit | `089a18dff289d4c58043c1957ad0d7fe73d814b3` | `b880e52707780032c3bad1b3086657c41df89ffb` |
| Binario | `zig-out-baseline/native/bin/tensorfold-native` | `zig-out-pr1879/native/bin/tensorfold-native` |
| Modelo | `mlx-community/Qwen3.5-4B-MLX-4bit` | Igual |
| Revisión HF | `32f3e8ecf65426fc3306969496342d504bfa13f3` | Igual |
| GPU | RTX 3050 Laptop, 4.096 MiB | Igual |
| Backend / contexto | CUDA / 512 | Igual |
| Concurrencia | parallel 1, max-inflight 1 | Igual |
| Reserva | `TENSORFOLD_MEMORY_RESERVE_GIB=0.5` | Igual |
| Modo HF | `HF_HUB_OFFLINE=1` | Igual |
| Puerto aislado | 18084 | 18083 |

Ambos binarios se compilaron localmente en Ubuntu para x86-64, CUDA SM 86 y ReleaseFast, en worktrees separados. No se utilizó ni modificó el servidor habitual del usuario en el puerto 8080.

### Resultado del baseline

El arranque del commit base terminó inmediatamente con:

```text
error: cuMemAlloc: CUDA_ERROR_OUT_OF_MEMORY (2) out of memory
tensorfold: the native CUDA engine cannot load
/home/ssantos/.cache/huggingface/hub/models--mlx-community--Qwen3.5-4B-MLX-4bit/snapshots/32f3e8ecf65426fc3306969496342d504bfa13f3
with its own glue kernels (OutOfDeviceMemory)
```

El proceso no abrió el puerto 18084. La petición de inferencia posterior devolvió `curl: (7) Failed to connect`, HTTP 000 y 0,000481 s; no se generó un JSON de respuesta. Esto es consecuencia de que el servidor no arrancó, no un fallo adicional de inferencia.

El monitor `baseline-gpu-monitor.csv` contiene 47 muestras de reposo entre 00:54:04 y 00:54:50 (hora local comunicada por el sistema). En esas muestras se observaron 15 MiB usados, 3.754 MiB libres y 0 % de utilización en la mayoría de lecturas. **El monitor no capturó el intento de asignación fallido**, por lo que no hay pico de VRAM del baseline ni perfil de la asignación que falló.

### Comparación de resultados

| Resultado | Baseline | PR #1879 |
|---|---|---|
| Carga del modelo | **OOM en `cuMemAlloc`** | Carga completada en 10,4 s |
| Servidor HTTP | No inicia | Inicia en 127.0.0.1:18083 |
| Inferencias HTTP 200 | 0 | 3 |
| Velocidad | No medible | 54,32–56,05 tok/s |
| TTFT | No medible | 187,2–194,1 ms |
| Pico global nvidia-smi | No capturado durante el intento | 3.227 MiB usados; 542 MiB libres |

Los valores de velocidad, TTFT y pico GPU de la columna PR proceden del registro de ejecución descrito en la sección anterior. No se deben interpretar como una mejora porcentual frente al baseline: el baseline no produjo una medición equivalente.

### Interpretación y límites

1. La prueba aporta evidencia directa de que el commit base falla al asignar memoria CUDA para cargar el motor Qwen3.5-4B bajo las condiciones especificadas.
2. El commit del PR #1879 supera esa barrera y realiza inferencia real en la misma GPU y con los mismos parámetros de contexto, concurrencia y reserva.
3. El resultado es consistente con la corrección de reservas anticipadas de scratch y de admisión de memoria pendiente descrita en el PR.
4. La prueba **no mide de forma aislada los bytes de scratch evitados** ni permite atribuir cada MiB de diferencia a un buffer concreto. Tampoco demuestra que el parche reduzca el pico de VRAM en todos los contextos.
5. No existe comparación válida de tokens/s, TTFT, calidad de salida o pico de memoria entre builds, porque el baseline no alcanzó la fase de servicio.
6. La inferencia PR #1879 sí tiene HTTP 200, pero una de las respuestas incluyó una explicación incorrecta sobre mover pesos a RAM. La advertencia semántica de la sección anterior sigue vigente.

### Veredicto experimental

**PR #1879: ventaja funcional confirmada para la carga de Qwen3.5-4B en la RTX 3050 de 4 GiB ensayada.** El baseline falla con `CUDA_ERROR_OUT_OF_MEMORY`; el PR carga y completa tres inferencias. El hallazgo justifica conservar la prueba como evidencia de regresión/corrección de admisión de memoria, sin exagerarlo como una medición exacta de ahorro de VRAM o de aceleración.

### Evidencias locales de la comparación

En `~/tensorfold-pr1879-baseline-20261103/evidence/`:

- `baseline-server-startup.log`: salida de arranque y error OOM.
- `baseline-gpu-monitor.csv`: muestreo GPU de reposo previo al arranque.
- `baseline-inference-no-thinking-256.json`: **no existe**, porque curl no pudo conectar y no se creó el fichero de salida. El comando `python3 -m json.tool` posterior falló por esa ausencia; no debe citarse como resultado de inferencia.

En `~/tensorfold-pr1879-validation-20261102/evidence/` permanecen el log de arranque, el monitor GPU y los tres JSON de inferencia PR enumerados en la sección anterior.
