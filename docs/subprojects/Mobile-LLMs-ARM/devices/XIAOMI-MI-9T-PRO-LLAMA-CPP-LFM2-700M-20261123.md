# Xiaomi Mi 9T Pro — primera inferencia LFM2-700M con llama.cpp

**Fecha:** 2026-11-23  
**Proyecto:** LEONES / Mobile-LLMs-ARM  
**Estado:** `REPRODUCED` — primera inferencia funcional observada; benchmark sostenido pendiente.  
**Dispositivo:** Xiaomi Mi 9T Pro, 6 GB nominales, Snapdragon 855 (SM8150; identificación de plataforma registrada en la ficha del dispositivo).  
**Entorno:** Termux aarch64, Android 10; inferencia CPU sin root.  
**Alcance:** registrar fielmente una ejecución exploratoria. No equivale a aceptación del protocolo NEPENTHES de benchmark.

## 1. Resultado principal

Se cargó el modelo `LFM2-700M-Q4_K_M.gguf` con `llama-cli` y se generó una respuesta textual al prompt:

> Explain briefly what a local language model is and why running it on a smartphone is useful.

La salida observada fue coherente en su comienzo: describió un modelo de lenguaje local como un modelo de aprendizaje automático que entiende y genera texto, entrenado sobre un corpus. La respuesta quedó truncada/incompleta al finalizar la interacción; no se debe presentar como una evaluación completa de calidad.

| Métrica reportada por llama.cpp | Resultado |
|---|---:|
| Prompt / prefill throughput | **120.4 tokens/s** |
| Generation / decode throughput | **40.2 tokens/s** |
| GPU layers | 0 (CPU) |
| Contexto solicitado | 512 |
| Batch / ubatch | 64 / 32 |
| Hilos / batch threads | 4 / 4 |
| Máximo de tokens solicitado | 48 |
| Warmup | desactivado (`--no-warmup`) |
| Temperatura de muestreo | 0.2 |
| Estado de carga | modelo cargado y texto generado |
| Código de salida del proceso | 130, tras Ctrl+C |

**Interpretación del exit code:** 130 corresponde a la interrupción por teclado (`Ctrl+C`) al salir de la sesión interactiva; no es evidencia de un fallo de carga. La inferencia ya había generado texto y llama.cpp había impreso sus métricas. La ejecución no debe clasificarse como benchmark completo ni como generación terminada de forma natural.

## 2. Identidad del runtime

- Repositorio: [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
- Commit local: `51831d4`
- Versión mostrada: `1.0.0-dev` (build 1; banner CLI `b1-51831d4`)
- Compilación: Clang 21.1.8 para Android aarch64.
- Binario: `build/bin/llama-cli`
- Backend efectivo: CPU. La CLI mostró `warning: no usable GPU found`; `--gpu-layers` no se utilizó. No se ha demostrado Vulkan, OpenCL, Adreno, Hexagon/HTP ni QNN.
- Arquitectura LFM2 y dispatch correspondiente estaban presentes en el código fuente local (`src/llama-arch.cpp`, `src/models/lfm2.cpp`, `src/llama-model.cpp`).

## 3. Identidad e integridad del modelo

- Archivo: `LFM2-700M-Q4_K_M.gguf`
- Ruta utilizada: `$HOME/models/llama.cpp/LFM2-700M-Q4_K_M.gguf`
- Tamaño informado por `du -h`: 447 MiB.
- SHA-256: `684e8406dc13321452b3f6aeca432776e2a6a7e1ad6c23f7887b8fe3efbe2efa`
- Metadatos GGUF leídos con `gguf_dump.py --no-tensors`:
  - `general.architecture = lfm2`
  - `general.name = LFM2 700M`
  - `lfm2.block_count = 16`
  - `lfm2.context_length = 128000` (límite declarado en metadatos, no contexto probado)
  - `lfm2.embedding_length = 1536`
  - `lfm2.attention.head_count = 24`
  - `lfm2.vocab_size = 65536`
  - `general.quantization_version = 2`
  - `general.file_type = 15`, contrastado con `LLAMA_FTYPE_MOSTLY_Q4_K_M = 15` en `include/llama.h`.
- Modalidad anunciada por CLI: `text`.

La herramienta de inspección requirió Python 3.14, NumPy 2.5.5 y PyYAML 6.0.4 en Termux. Estas dependencias se instalaron para inspección estática; no forman parte del runtime de inferencia.

## 4. Memoria observada

Instantáneas de `/proc/meminfo`:

| Campo | Antes | Después |
|---|---:|---:|
| MemAvailable | 2,931,224 kB | 2,920,572 kB |
| SwapFree | 1,786,880 kB | 1,792,536 kB |

Diferencia entre instantáneas: MemAvailable −10,652 kB; SwapFree +5,656 kB. Son snapshots del sistema, no mediciones de RSS/peak del proceso ni atribución causal al modelo. No se observó presión de memoria evidente en esos dos puntos de muestreo.

## 5. Sensores térmicos

Lecturas capturadas inmediatamente antes y después de la ejecución:

| Zona | Tipo | Antes | Después |
|---:|---|---:|---:|
| 3 | cpu-0-2-usr | 32.900 °C | 33.700 °C |
| 33 | apc-0-max-step | 32.900 °C | 34.100 °C |
| 53 | pm8150_tz | 30.418 °C | 30.515 °C |
| 54 | pm8150b-wp-therm | 102.310 °C | 102.240 °C |
| 55 | pm8150b_tz | 28.504 °C | 28.796 °C |
| 65 | pm8150l_tz | 32.332 °C | 32.267 °C |
| 73 | xo_therm | 28.512 °C | 28.491 °C |
| 74 | quiet_therm | 28.661 °C | 28.432 °C |
| 79 | bms | 26.200 °C | 26.000 °C |
| 80 | battery | 26.200 °C | 26.000 °C |

**Limitación térmica importante:** la zona 54 (`pm8150b-wp-therm`) ya mostraba aproximadamente 102–103 °C en lecturas previas a esta inferencia y permaneció cerca de ese valor. Su correspondencia física no está identificada; no debe tratarse como temperatura confirmada de CPU/batería ni descartarse como lectura falsa. La pequeña variación de estas instantáneas no certifica seguridad térmica ni descarta throttling. No se dispone aquí de telemetría de frecuencia/thermal throttling sostenida.

## 6. Comando de referencia

Configuración ejecutada:

```bash
"$BIN" \
  -m "$MODEL" \
  -ngl 0 \
  -c 512 \
  -b 64 \
  -ub 32 \
  -t 4 \
  -tb 4 \
  -n 48 \
  --no-warmup \
  --temp 0.2 \
  --perf \
  -p "Explain briefly what a local language model is and why running it on a smartphone is useful."
```

El proceso se ejecutó en modo interactivo con `tee` para conservar salida en `$HOME/lfm2-700m-first-inference.log`. No se ha adjuntado ese log como artefacto del repositorio; los datos de este informe proceden de la salida compartida en la sesión.

## 7. Clasificación de evidencia

| Afirmación | Estado | Evidencia / límite |
|---|---|---|
| llama.cpp compila y arranca en Termux aarch64 | CONFIRMADO | versión y banner del binario |
| LFM2 está reconocido por la versión del código | CONFIRMADO | arquitectura/dispatch en código y carga del modelo |
| GGUF es Q4_K_M y su hash fue verificado | CONFIRMADO | metadatos, enum y SHA-256 |
| Inferencia CPU genera texto en Mi 9T Pro | REPRODUCED | salida CLI observada |
| Prefill 120.4 tokens/s | OBSERVADO, UNA EJECUCIÓN | cifra CLI; no repetida |
| Decode 40.2 tokens/s | OBSERVADO, UNA EJECUCIÓN | cifra CLI; no repetida |
| Rendimiento sostenido / estabilidad prolongada | NO MEDIDO | no se hizo prueba sostenida |
| TTFT, ITL, latencia por petición | NO MEDIDO | no hay timestamps de streaming |
| RSS máximo / memoria atribuible al proceso | NO MEDIDO | solo snapshots globales |
| GPU Adreno / Vulkan / DSP / NPU | NO DEMOSTRADO | CLI reporta que no hay GPU utilizable |
| Energía por token / consumo eléctrico | NO MEDIDO | sin medidor validado |
| Ausencia de throttling | NO DEMOSTRADA | faltan series temporales y frecuencias |
| Calidad comparativa del modelo | NO EVALUADA | una respuesta parcial, sin fixture de scoring |

## 8. Limitaciones y siguiente gate

Esta fue una prueba exploratoria única, con un solo prompt, sin warm-up y sin repeticiones. **No satisface** el protocolo de benchmark móvil NEPENTHES (warm-up, al menos cinco repeticiones medidas, artefactos completos, estadística y control térmico).

Siguiente trabajo, condicionado a revisar la anomalía de la zona 54 y a una condición térmica aceptable:
1. Preservar el log original y un inventario redactado del dispositivo.
2. Confirmar el estado térmico mediante sensores identificados y fuentes Android disponibles; no alterar thermal policy, trip points ni firmware.
3. Repetir solo una prueba corta controlada, con prompt y límites fijos, si el gate térmico lo permite.
4. Capturar número real de tokens, duración, TTFT/ITL si el runner los expone, RSS cuando sea accesible y series térmicas/frecuencias.
5. Comparar con Qwen2.5-0.5B solo después, manteniendo configuración y condiciones equivalentes.

No aumentar contexto, hilos ni duración por extrapolación de esta única muestra. No inferir que 128K de contexto GGUF sea utilizable en este dispositivo.

## 9. Conclusión

**Hito alcanzado:** primera inferencia local funcional de LFM2-700M-Q4_K_M mediante llama.cpp CPU en Xiaomi Mi 9T Pro / Snapdragon 855, con 120.4 tokens/s de prefill y 40.2 tokens/s de generación reportados por la CLI.

**Conclusión que no debe extraerse:** que esas cifras sean rendimiento sostenido, que el teléfono esté validado térmicamente, o que exista aceleración Adreno/Hexagon. La campaña permanece en caracterización inicial.
