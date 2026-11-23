# Xiaomi Mi 9T Pro — experimento LFM2-2.6B con llama.cpp

**Fecha:** 2026-11-23  
**Proyecto:** LEONES / Mobile-LLMs-ARM  
**Estado:** `REPRODUCED` — carga y generación CPU repetidas; caracterización exploratoria, no benchmark NEPENTHES.  
**Dispositivo:** Xiaomi Mi 9T Pro, 6 GB nominales, Snapdragon 855 (SM8150).  
**Entorno:** Termux aarch64, Android 10, sin root.  
**Runtime:** llama.cpp `1.0.0-dev`, build 1, commit `51831d4`, Clang 21.1.8 Android aarch64.  
**Backend:** CPU (`-ngl 0`); la CLI indicó `no usable GPU found`. No se demostró aceleración Adreno/Vulkan/OpenCL/Hexagon/QNN.

## 1. Identidad e integridad del modelo

- Archivo: `LFM2-2.6B-Q4_K_M.gguf`
- Ruta: `$HOME/models/llama.cpp/LFM2-2.6B-Q4_K_M.gguf`
- Tamaño observado: aproximadamente 1.5 GiB.
- SHA-256 verificado: `384bc877b6c37064982f96885bef69e4475919f5969218ed4e3b9399ae0340df`
- Repositorio de origen: [LiquidAI/LFM2-2.6B-GGUF](https://huggingface.co/LiquidAI/LFM2-2.6B-GGUF)
- Inspección estática mediante `gguf_dump.py --no-tensors`:
  - `general.architecture = lfm2`
  - `lfm2.block_count = 30`
  - `lfm2.context_length = 128000` (metadato declarado, no contexto probado)
  - `lfm2.embedding_length = 2048`
  - `lfm2.attention.head_count = 32`
  - `lfm2.attention.head_count_kv` es un vector de 30 valores; configuración KV variable por bloque.
  - `lfm2.vocab_size = 65536`
  - `tokenizer.ggml.eos_token_id = 7`
  - `general.quantization_version = 2`
  - `general.file_type = 15` (Q4_K_M según enum de llama.cpp)
  - Chat template presente.
- Nombre GGUF informado: `Bd63F69Daf9378770Be9430369E1D68F3Fe34282`; se conserva literalmente, sin reinterpretarlo como nombre comercial.

## 2. Configuración común de inferencia

Ambas ejecuciones usaron el mismo prompt y configuración:

| Parámetro | Valor |
|---|---:|
| Backend | CPU, `-ngl 0` |
| Contexto | 512 |
| Batch / ubatch | 32 / 16 |
| Hilos / batch threads | 2 / 2 |
| Máximo de tokens | 32 |
| Warmup | desactivado (`--no-warmup`) |
| Temperatura | 0.2 |
| Métricas | `--perf` |
| Prompt | `Explain briefly what a local language model is and why running it on a smartphone is useful.` |

Comando de referencia:

```bash
"$BIN" \
  -m "$MODEL" \
  -ngl 0 \
  -c 512 \
  -b 32 \
  -ub 16 \
  -t 2 \
  -tb 2 \
  -n 32 \
  --no-warmup \
  --temp 0.2 \
  --perf \
  -p "Explain briefly what a local language model is and why running it on a smartphone is useful."
```

## 3. Resultados observados

| Ejecución | Prompt throughput | Generation throughput | Terminación |
|---|---:|---:|---|
| 1 | 21.6 tokens/s | 11.4 tokens/s | La CLI imprimió texto y métricas; la sesión SSH se cerró. Código de salida no recuperado. |
| 2 (repetición) | 22.1 tokens/s | 11.3 tokens/s | `/exit` explícito; `LLAMA_EXIT_CODE=0`. |

Variación entre las dos cifras observadas:
- Prompt: +2.3 % en la segunda ejecución.
- Generación: −0.9 % en la segunda ejecución.

Las velocidades son las reportadas por llama.cpp. Dos ejecuciones exploratorias con un único prompt no constituyen estadística de rendimiento ni demuestran rendimiento sostenido.

### Salida textual

Primera ejecución:
> A local language model is an artificial intelligence model that runs directly on a device's hardware—such as a smartphone—without relying on cloud-based servers.

Segunda ejecución:
> A local language model is an artificial intelligence model that processes and generates natural language directly on a device, such as a smartphone, without relying on cloud-based

Ambas salidas son coherentes en el fragmento observado, pero quedaron incompletas/truncadas al límite de generación o interacción. No se realizó evaluación sistemática de calidad.

### Logs

- Primera ejecución: `$HOME/lfm2-2.6b-first-inference.log` fue sobrescrito por un intento posterior y solo conserva las advertencias iniciales de GPU; no sirve como log íntegro de la inferencia.
- Repetición limpia: `$HOME/lfm2-2.6b-repeat-20261123-222650.log`. La salida compartida incluye el resultado y `LLAMA_EXIT_CODE=0`. El archivo permanece en el teléfono; no se ha adjuntado como artefacto a GitHub.

## 4. Memoria y sensores

Snapshots de memoria disponibles antes/después de la primera ejecución:

| Campo | Antes | Después |
|---|---:|---:|
| MemAvailable | 2,852,524 kB | 2,856,980 kB |
| SwapFree | 1,720,636 kB | 1,720,636 kB |

Tras reconectar por SSH se observó:
- MemAvailable: 3,182,692 kB.
- SwapFree: 1,267,212 kB.
- `ps` no mostró proceso `llama-cli` activo.

Antes de la repetición:
- MemAvailable: 3,163,488 kB.
- SwapFree: 1,278,032 kB.

No se capturó snapshot de memoria inmediatamente después de la repetición. Estas cifras son snapshots globales de Android, no RSS ni peak RSS atribuible al proceso; no permiten cuantificar memoria máxima del modelo.

Lecturas térmicas disponibles antes de la primera ejecución y después del primer intento fallido por argumento inválido (no inferencia):

| Zona | Tipo | Antes de intento | Después de intento |
|---:|---|---:|---:|
| 3 | cpu-0-2-usr | 33.700 °C | 34.500 °C |
| 33 | apc-0-max-step | 34.100 °C | 33.300 °C |
| 53 | pm8150_tz | 30.742 °C | 30.840 °C |
| 54 | pm8150b-wp-therm | 102.008 °C | 101.939 °C |
| 55 | pm8150b_tz | 29.055 °C | 29.055 °C |
| 65 | pm8150l_tz | 32.526 °C | 32.526 °C |
| 73 | xo_therm | 28.756 °C | 28.756 °C |
| 74 | quiet_therm | 28.834 °C | 28.831 °C |
| 79 | bms | 26.500 °C | 26.500 °C |
| 80 | battery | 26.500 °C | 26.500 °C |

Tras finalizar la primera inferencia y reconectar por SSH se observaron:
- CPU zone 3: 33.700 °C.
- APC zone 33: 33.700 °C.
- PM8150 zone 53: 30.742 °C.
- Zona 54 (`pm8150b-wp-therm`): 102.008 °C.
- PM8150B zone 55: 29.218 °C.
- PM8150L zone 65: 32.689 °C.
- XO zone 73: 28.944 °C.
- Quiet zone 74: 29.015 °C.
- BMS y batería zones 79/80: 26.500 °C.

**Limitación térmica:** no se capturó una serie temporal durante la inferencia ni una lectura posterior a la repetición limpia. La zona 54 ya mostraba aproximadamente 102 °C antes de la inferencia y su correspondencia física sigue sin identificarse. No debe interpretarse como temperatura confirmada de CPU/batería ni descartarse como lectura falsa. Las instantáneas no certifican seguridad térmica ni ausencia de throttling.

## 5. Clasificación de evidencia

| Afirmación | Estado | Límite |
|---|---|---|
| GGUF íntegro y metadatos leídos | CONFIRMADO | SHA-256 y dump estático |
| llama.cpp reconoce y carga LFM2-2.6B | REPRODUCIDO | Dos cargas observadas |
| Generación textual CPU en Snapdragon 855 | REPRODUCIDO | Dos ejecuciones, un prompt |
| Prompt 21.6 / 22.1 tokens/s | OBSERVADO | Dos muestras |
| Decode 11.4 / 11.3 tokens/s | OBSERVADO | Dos muestras |
| Segunda ejecución termina con código 0 | CONFIRMADO | `/exit` y `LLAMA_EXIT_CODE=0` |
| Rendimiento sostenido / throttling | NO MEDIDO | Sin test prolongado ni serie de frecuencias |
| TTFT / ITL | NO MEDIDO | No se capturaron timestamps por token |
| RSS máximo | NO MEDIDO | Sin telemetría de proceso |
| Energía por token | NO MEDIDO | Sin instrumentación eléctrica |
| Aceleración Adreno / DSP / NPU | NO DEMOSTRADA | CLI reporta GPU no utilizable |
| Calidad comparativa | NO EVALUADA | Dos respuestas parciales, sin scoring |

## 6. Conclusión y próximos gates

**Hito alcanzado:** LFM2-2.6B Q4_K_M carga y genera texto en el Xiaomi Mi 9T Pro / Snapdragon 855 con llama.cpp CPU, a aproximadamente 11.3–11.4 tokens/s de generación en dos ejecuciones exploratorias con configuración idéntica.

No declarar benchmark NEPENTHES completo, rendimiento sostenido, calidad validada, aceleración GPU ni estabilidad térmica.

Antes de ampliar duración, contexto, hilos o tamaño de modelo, mantener los gates de caracterización del dispositivo y telemetría térmica. El contexto GGUF de 128K es un metadato del modelo, no una capacidad demostrada en este teléfono.
