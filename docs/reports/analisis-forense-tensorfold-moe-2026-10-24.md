# Análisis forense TensorFold MoE — RTX 3050 Laptop 4 GiB

- **Fecha del expediente:** 2026-10-24
- **Repositorio:** robertosantosx2/LEONES
- **Estado:** rechazo de admisión de memoria previo a inferencia; no se obtuvieron tokens ni medidas de rendimiento.
- **Motor:** tensorfold-native 1.1.3
- **Equipo:** MSI Thin 15 B12UC, Ubuntu, NVIDIA GeForce RTX 3050 Laptop GPU de 4 GiB.
- **Naturaleza de la evidencia:** comandos y salidas reales compartidos desde el terminal, identificadores de logs locales y análisis de capacidades. Los logs originales permanecen en el host de prueba; este informe no afirma que los bytes originales de todos ellos se hayan adjuntado a GitHub.

## 1. Conclusión ejecutiva

Se capturaron dos intentos de arranque con TensorFold nativo 1.1.3:

1. **NVIDIA Nemotron 3.5 Lightning 30B-A3B**, modelo `TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit`. TensorFold informó 16,6 GiB de pesos y rechazó el arranque porque el presupuesto CUDA efectivo era de 2,6 GiB (3,6 GiB libres detectados menos una reserva de 1,0 GiB). Código de salida 1.
2. **Qwen3.6-35B-A3B**, modelo `TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP`. `tensorfold info` informó 19,47 GiB (20.904.564.068 bytes) de pesos y un suelo de memoria de 21,47 GiB. El comando `serve` mostró 19,0 GiB de pesos (redondeado) frente al mismo presupuesto CUDA de 2,6 GiB. Código de salida 1.

Los dos procesos terminaron por sí solos en unos segundos. Ninguno alcanzó una inferencia. El rechazo de memoria ocurre antes de servir una API y no es un resultado de velocidad ni una prueba de OOM durante generación.

**Conclusión estricta LEONES:** el resultado medido es un rechazo de admisión por presupuesto CUDA. No se ha demostrado una ejecución funcional de ninguno de los modelos en esta RTX 3050 de 4 GiB. Tampoco se ha demostrado que sean incompatibles con TensorFold en general o que el motor carezca de cualquier mecanismo interno de offload.

## 2. Identidad del entorno

| Campo | Valor observado |
|---|---|
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| CPU lógica | 16 |
| Sistema | Ubuntu |
| Kernel reportado en el inventario previo | `7.0.0-38-generic` |
| RAM física | 14 GiB |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| VRAM | 4096 MiB / 4 GiB |
| Driver NVIDIA | 580.178.04 |
| CUDA mostrada por nvidia-smi | 13.0 |
| TensorFold | tensorfold-native 1.1.3 |
| SHA-256 del binario | `a51ec99fa4f87ab12bd48261e1c1cbeb1e7b51f72755a71d4a7eda89712ff671` |
| Ejecutable | `/home/ssantos/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native` |
| Proceso gráfico | Xorg, PID 5911 |
| VRAM usada antes del intento Qwen | 15 MiB; Xorg figura con 4 MiB en tabla de procesos |
| RAM disponible antes de Qwen serve | 2,3 GiB |
| Swap/intercambio usado antes de Qwen serve | 7,7 GiB de 31 GiB |

El hash y la versión coinciden en los registros compartidos para Nemotron, Qwen info, Qwen serve y la auditoría de capacidades.

### 2.1 Memoria del host antes y después de Qwen serve

Salida literal de `free -h` antes del intento:

    total       usado       libre  compartido   búf/caché  disponible
    Mem:            14Gi        12Gi       463Mi       874Mi       3,1Gi       2,3Gi
    Inter:          31Gi       7,7Gi        24Gi

Salida literal después:

    total       usado       libre  compartido   búf/caché  disponible
    Mem:            14Gi        12Gi       738Mi       887Mi       3,1Gi       2,6Gi
    Inter:          31Gi       7,7Gi        24Gi

La etiqueta «Inter» se conserva tal como apareció en la consola. El proceso terminó rápidamente y no hay evidencia de que cargara de forma sostenida los pesos.

### 2.2 Ruta incorrecta descartada

Un intento anterior apuntó a `$HOME/.local/opt/tensorfold-1.1.3-check.aOKPG0/...`, ruta que no existía. Fue un error de ruta, no un fallo de TensorFold ni del checkpoint. Las pruebas documentadas aquí utilizaron la ruta correcta bajo `$HOME/tensorfold-1.1.3-check.aOKPG0/`.

## 3. Evidencia A — Nemotron 3.5 Lightning 30B-A3B

### 3.1 Identidad, configuración y tiempos

- Modelo: `TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit`
- Servicio: `nemotron-forensic`
- Host: `127.0.0.1`
- Puerto: `18089`
- Backend solicitado: `auto`
- Paralelismo: 1
- Contexto: 512
- Temperatura: 0
- Thinking: desactivado mediante `--no-thinking`
- Inicio: `2026-10-24T21:45:53,499655019+02:00`
- Fin: `2026-10-24T21:45:58,572657071+02:00`
- Duración aproximada: 5,073 segundos
- Código de salida registrado: 1
- Log de preflight: `/home/ssantos/tensorfold-forensic-20261024/nemotron-1.1.3-preflight.log`
- Log de arranque: `/home/ssantos/tensorfold-forensic-20261024/nemotron-1.1.3-context512.log`

El script registró la etiqueta `timeout_exit_code=1`. Aunque el comando se envolvió en timeout, no agotó el plazo: el programa terminó por sí solo con código 1.

### 3.2 Comando exacto de arranque

    /home/ssantos/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native serve \
      TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit \
      --name nemotron-forensic \
      --host 127.0.0.1 \
      --port 18089 \
      --backend auto \
      --parallel 1 \
      --context 512 \
      --temperature 0 \
      --no-thinking

### 3.3 Error literal capturado

    tensorfold: the checkpoint's 16.6 GiB of weights do not fit the 2.6 GiB the CUDA memory budget grants (3.6 GiB free less a 1.0 GiB reserve); free device memory or adjust TENSORFOLD_MEMORY_RESERVE_GIB / TENSORFOLD_CUDA_MEMORY_LIMIT_GB

### 3.4 Interpretación

El mensaje declara:
- Pesos: 16,6 GiB.
- Memoria CUDA libre detectada: 3,6 GiB.
- Reserva: 1,0 GiB.
- Presupuesto resultante: 2,6 GiB.
- Déficit respecto a los pesos mostrados: aproximadamente 14,0 GiB.

El servidor no llegó a estar disponible; no se registraron peticiones HTTP, tokens, tok/s, TTFT ni calidad de generación.

### 3.5 Otros comandos históricos de Nemotron

También aparecieron en el historial estos comandos anteriores:

    "$TF" serve TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit --name nemotron-moe --parallel 1 --context 2048 --temperature 0 --no-thinking

    "$TF" serve TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit \
      --name nemotron-moe-113 --host 127.0.0.1 --port 18089 --backend auto \
      --parallel 1 --context 512 --temperature 0 --no-thinking

No se dispone aquí del error original completo de esos intentos previos. No deben confundirse con la captura controlada de 21:45:53.

## 4. Evidencia B — Qwen3.6-35B-A3B: inspección del checkpoint

### 4.1 Identidad y comando info

- Modelo: `TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP`
- Fecha: `2026-10-24T21:48:59,552050510+02:00`
- Versión: `tensorfold-native 1.1.3`
- SHA-256: `a51ec99fa4f87ab12bd48261e1c1cbeb1e7b51f72755a71d4a7eda89712ff671`
- Log: `/home/ssantos/tensorfold-forensic-20261024/qwen36-info-1.1.3.log`
- Código de salida de info: 0.

Comando registrado:

    TF="$HOME/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native"
    OUT="$HOME/tensorfold-forensic-20261024"
    MODEL="TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP"
    "$TF" info "$MODEL"

### 4.2 Resultado de info

    family: qwen3_5_moe (qwen3_5_moe)
    format: 4-bit, group 64
    weights: 19.47 GiB (20904564068 bytes)
    memory floor: 21.47 GiB (weights plus a 2.00 GiB runtime margin)
    info_exit_code=0

Ruta del snapshot local reportada en el inventario previo:

    /home/ssantos/.cache/huggingface/hub/models--TensorFold--Qwen3.6-35B-A3B-MLX-4bit-MTP/snapshots/f84b054c5677b6e59bdb969ae61915b0983d68bb

El inventario previo estimó unos 20 GiB en caché y reportó cuatro shards safetensors más `mtp-4bit.safetensors`, configuración, tokenizer e índice. No se guardaron en este expediente hashes individuales de los shards; por tanto, no se afirma verificación criptográfica de cada fichero.

Un `info_exit_code=0` confirma que se pudo inspeccionar la información del checkpoint, no que se hayan cargado los pesos o que la inferencia funcione.

## 5. Evidencia C — Qwen3.6-35B-A3B: arranque controlado

### 5.1 Parámetros y tiempos

- Inicio: `2026-10-24T21:50:01,153166636+02:00`
- Fin: `2026-10-24T21:50:03,917760790+02:00`
- Duración aproximada: 2,765 segundos
- Servicio: `qwen36-forensic`
- Host: `127.0.0.1`
- Puerto: `18090`
- Backend: `auto`
- Paralelismo: 1
- Contexto: 256
- Temperatura: 0
- Thinking: desactivado
- Código de salida: 1
- Log: `/home/ssantos/tensorfold-forensic-20261024/qwen36-1.1.3-serve-context256.log`

### 5.2 Comando exacto

    /home/ssantos/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native serve TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP --name qwen36-forensic --host 127.0.0.1 --port 18090 --backend auto --parallel 1 --context 256 --temperature 0 --no-thinking

La ejecución estuvo envuelta por:

    timeout --signal=INT --kill-after=5s 30s \
      "$TF" serve "$MODEL" \
      --name qwen36-forensic \
      --host 127.0.0.1 \
      --port 18090 \
      --backend auto \
      --parallel 1 \
      --context 256 \
      --temperature 0 \
      --no-thinking

Resultado:

    serve_exit_code=1

El proceso terminó en aproximadamente 2,76 segundos; no fue un timeout de 30 segundos.

### 5.3 Error literal completo

    tensorfold: the checkpoint's 19.0 GiB of weights do not fit the 2.6 GiB the CUDA memory budget grants (3.6 GiB free less a 1.0 GiB reserve); free device memory or adjust TENSORFOLD_MEMORY_RESERVE_GIB / TENSORFOLD_CUDA_MEMORY_LIMIT_GB

El mensaje de serve redondea los pesos a 19,0 GiB; info había informado 19,47 GiB. La diferencia es precisión de presentación, no evidencia de dos checkpoints distintos.

### 5.4 GPU antes y después

Antes:
- NVIDIA-SMI 580.178.04; driver 580.178.04; CUDA 13.0.
- RTX 3050, 4096 MiB totales.
- 15 MiB usados; GPU-Util 9%; 44 °C.
- Xorg PID 5911: 4 MiB.

Después:
- NVIDIA-SMI 580.178.04; driver 580.178.04; CUDA 13.0.
- RTX 3050, 4096 MiB totales.
- 15 MiB usados; GPU-Util 0%; 44 °C.
- Xorg PID 5911: 4 MiB.

Esto concuerda con un rechazo temprano y no con una carga sostenida de pesos.

## 6. Evidencia D — auditoría de TensorFold 1.1.3

### 6.1 Fecha, fichero y comando

- Fecha: `2026-10-24T21:51:22,680971026+02:00`
- Log local: `/home/ssantos/tensorfold-forensic-20261024/offload-capability-audit.log`

Comando:

    TF="$HOME/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native"
    OUT="$HOME/tensorfold-forensic-20261024"
    {
      echo "===== FECHA ====="
      date --iso-8601=ns
      echo "===== HELP SERVE ====="
      "$TF" serve --help 2>&1
      echo "===== CAPACIDADES ====="
      "$TF" capabilities --json 2>&1
      echo "===== OPCIONES DE MEMORIA Y OFFLOAD EN EL BINARIO ====="
      strings "$TF" |
        grep -Ei 'offload|cpu.?memory|host.?memory|memory.?budget|TENSORFOLD_MEMORY_RESERVE_GIB|TENSORFOLD_CUDA_MEMORY_LIMIT_GB|TF_CUDA_SEGMENTS|segments' |
        sort -u
    } 2>&1 | tee "$OUT/offload-capability-audit.log"

### 6.2 Ayuda de serve observada

    usage: tensorfold serve [-h] [--host HOST] [--port PORT] [--name NAME] [--chat-template FILE] [--alias ALIAS] [--allowed-host NAME] [--allowed-origin ORIGIN] [--api-key API_KEY] [--api-key-file API_KEY_FILE] [--metrics-open] [--dashboard] [--context CONTEXT] [--speed-up SETTINGS] [--prompt-cache-gib PROMPT_CACHE_GIB] [--prompt-cache-over-cap] [--learn] [--learn-dir LEARN_DIR] [--learn-gib LEARN_GIB] [--learn-conversations] [--learn-daily-gib LEARN_DAILY_GIB] [--recall] [--recall-dir RECALL_DIR] [--recall-gib RECALL_GIB] [--recall-read-only] [--max-tokens MAX_TOKENS] [--temperature TEMPERATURE] [--top-p TOP_P] [--top-k TOP_K] [--min-p MIN_P] [--prompt-seed] [--thinking | --no-thinking] [--reasoning-effort {low,medium,high,xhigh}] [--thinking-budget THINKING_BUDGET] [--thinking-reserve THINKING_RESERVE] [--loop-guard] [--no-drafts] [--drafter DRAFTER] [--drafter-bits {0,4}] [--record RECORD] [--keep-warm SECONDS] [--compact-at COMPACT_AT] [--compact-keep COMPACT_KEEP] [--compact-memory COMPACT_MEMORY] [--slide] [--slide-graph SLIDE_GRAPH] [--parallel PARALLEL] [--cortheon] [--no-update-check] [--backend {auto,mlx,cuda}] [--device DEVICE] [--segments SEGMENTS] model

La ayuda no muestra un flag general obvio `--cpu-offload` o `--offload` para los pesos principales. Esta observación no basta para probar la ausencia de toda implementación interna.

### 6.3 Capacidades JSON: campos relevantes

La salida informó motor Zig, versión 1.1.3, chip `nvidia-sm86`, backends `["cuda"]` y estas familias/formats relevantes:

    {
      "schema": 1,
      "engine": "zig",
      "version": "1.1.3",
      "chip": "nvidia-sm86",
      "backends": ["cuda"],
      "families": {
        "nemotron_h": ["mlx-q4g64", "modelopt-nvfp4", "modelopt-ggml"],
        "nemotron_h_omni": ["mlx-q4g64", "modelopt-nvfp4", "modelopt-ggml"],
        "qwen3_5": ["mlx-q4g64"],
        "qwen3_5_moe": ["mlx-q4g64"]
      },
      "env": [
        "TENSORFOLD_API_KEY",
        "TENSORFOLD_NO_LIVE",
        "TENSORFOLD_SEED_SALT",
        "TENSORFOLD_REQUEST_LOG",
        "TENSORFOLD_NO_UPDATE_CHECK",
        "HF_HOME",
        "HF_HUB_CACHE",
        "HF_HUB_OFFLINE",
        "BRAVE_SEARCH_API_KEY",
        "TF_CUDA_DEVICE",
        "TF_CUDA_SEGMENTS",
        "TENSORFOLD_CUDA_KERNELS",
        "TENSORFOLD_MEMORY_RESERVE_GIB",
        "TENSORFOLD_CUDA_MEMORY_LIMIT_GB"
      ]
    }

El JSON completo enumeraba otras familias, flags y bibliotecas opcionales. Para esta investigación son importantes la familia Nemotron-H, la familia Qwen3.5 MoE y las variables de memoria. Que una familia/formato aparezca en las capacidades no demuestra que un checkpoint concreto quepa en la GPU ni que su carga vaya a terminar.

La salida también informaba:
- cuBLASLt y cuBLAS encontrados, uso aún no determinado.
- NCCL no encontrado.
- RDMA verbs encontrado.
- TensorFold video / libtfvideo.so no encontrado.
- libjpeg-turbo encontrado, pero marcado no usable por el resolvedor de libturbojpeg.so.0.
- libwebp no encontrado.
- TensorFold grammar / libtfgrammar.so encontrado, uso no determinado.
- RCCL no encontrado.
- MCDMA RPC y MCDMA fabric no encontrados.

No hay evidencia que vincule esas bibliotecas opcionales con los errores de presupuesto de pesos observados.

### 6.4 Variables de memoria

Los mensajes nombran:
- `TENSORFOLD_MEMORY_RESERVE_GIB`
- `TENSORFOLD_CUDA_MEMORY_LIMIT_GB`

La auditoría anterior registró que estas variables estaban vacías/no definidas en el entorno examinado. El error informa una reserva efectiva de 1,0 GiB.

Cambiar esas variables altera el presupuesto lógico calculado por el programa; no aumenta la VRAM física. No se recomienda establecer un límite CUDA superior a la VRAM real ni retirar la reserva sin justificarlo: pasar la comprobación inicial no garantiza que quepan los pesos, la KV cache, buffers y workspace en la asignación real.

### 6.5 Cadenas internas de strings relevantes

Entre las cadenas copiadas desde el resultado de `strings` aparecen:

    HostMemoryUnavailable
    BadSegments
    InvalidQwenSegments
    --segments
    TF_CUDA_SEGMENTS=
    TENSORFOLD_MEMORY_RESERVE_GIB
    TENSORFOLD_CUDA_MEMORY_LIMIT_GB
    the checkpoint's  GiB of weights do not fit the  GiB the CUDA memory budget grants
    the CUDA memory budget fits no stream beside the model
    the CUDA memory budget fits no stream
    Pinned host memory the engine holds now: staging buffers and windows; only where the backend counts it (CUDA).
    --slide runs a prompt one chunk at a time, its change's scratch shared by every layer: serve it without --segments or TF_CUDA_SEGMENTS
    --vision-offload

Cautelas:
- `strings` extrae cadenas internas; no es una especificación completa de interfaz ni demuestra que cada código se ejecute.
- `HostMemoryUnavailable` no permite inferir exactamente qué funciones de memoria host están disponibles.
- `--segments` no debe interpretarse como offload de pesos. La cadena relativa a `--slide` habla de procesar el prompt por chunks y de memoria scratch.
- `--vision-offload` apareció en cadenas, pero no en la ayuda normal de serve copiada; no debe tratarse como descarga de los pesos de lenguaje.
- No se encontró en la ayuda mostrada una opción general documentada de offload CPU para los pesos principales.

### 6.6 Referencia a un motor Python antiguo

Otra cadena interna decía:

    is not served by the native engine; the Python engine 0.6.6 serves it:
    python -m pip install git+https://github.com/ashhart/TensorFold.git@v0.6.6

Es un mensaje genérico interno. No demuestra que estos checkpoints deban usarse con esa versión ni que el motor Python pueda ejecutarlos con 14 GiB de RAM y 4 GiB de VRAM. No se instaló ni probó el motor Python en esta sesión.

## 7. Comparación cuantitativa

| Métrica | Nemotron 3.5 Lightning | Qwen3.6 |
|---|---:|---:|
| Pesos informados por serve | 16,6 GiB | 19,0 GiB |
| Pesos de info | no conservado en la salida compartida | 19,47 GiB |
| Suelo de memoria de info | no conservado en la salida compartida | 21,47 GiB |
| VRAM física | 4 GiB | 4 GiB |
| VRAM libre detectada | 3,6 GiB | 3,6 GiB |
| Reserva | 1,0 GiB | 1,0 GiB |
| Presupuesto CUDA | 2,6 GiB | 2,6 GiB |
| Déficit aproximado según serve | 14,0 GiB | 16,4 GiB |
| Código de salida | 1 | 1 |
| API lista confirmada | No | No |
| Inferencia completada | No | No |
| Tokens generados | No | No |
| tok/s / TTFT | No medidos | No medidos |

Las cifras de serve están redondeadas; los déficits derivados también son aproximados.

## 8. Hechos demostrados y cuestiones abiertas

### Demostrado
- Los dos comandos serve terminan con código 1 tras un mensaje explícito de presupuesto CUDA insuficiente.
- Los pesos declarados superan ampliamente el presupuesto CUDA de 2,6 GiB.
- Qwen info inspecciona el checkpoint y devuelve 19,47 GiB de pesos y un suelo de 21,47 GiB.
- En el intento Qwen, nvidia-smi muestra 15 MiB usados antes y después.
- El intento Qwen no agotó el timeout de 30 segundos.
- La ayuda de serve observada no documenta un flag general obvio de CPU offload.

### No demostrado
- Incompatibilidad general de ambos modelos con TensorFold.
- Ausencia absoluta de cualquier mecanismo interno de offload.
- Que --segments distribuya pesos entre CPU y GPU.
- Que bajar la reserva haga posible la ejecución.
- Que TensorFold Python 0.6.6 funcione para estos modelos.
- OOM de RAM/GPU durante generación.
- Rendimiento, calidad o tokens generados.
- Integridad criptográfica de cada shard del checkpoint.
- Que todos los logs locales estén adjuntos como archivos raw en este commit.

## 9. Recomendaciones y siguientes pasos seguros

1. No repetir el mismo arranque: el rechazo ya está demostrado.
2. No elevar artificialmente `TENSORFOLD_CUDA_MEMORY_LIMIT_GB` por encima de la VRAM física. Eso no crea memoria y puede desplazar el fallo a una asignación posterior.
3. No asumir que `--segments` es offload; verificar su semántica en el código/documentación exactos de 1.1.3.
4. Auditar el código fuente/tag exacto para localizar el cálculo de pesos, presupuesto de memoria, `HostMemoryUnavailable`, `BadSegments` y carga de tensores. Registrar tag/commit y hashes de los archivos examinados.
5. Tratar el motor Python 0.6.6 como un experimento separado, en entorno aislado y con versiones/hashes fijados.
6. Para inferencia práctica en este hardware, usar un checkpoint cuyo tamaño de pesos y memoria de runtime quepan o investigar un runtime con CPU offload documentado. No clasificar una estimación como MEASURED.
7. Antes de cualquier ensayo futuro, guardar hora con zona horaria, versión y SHA-256 del ejecutable, modelo exacto, comando completo, RAM/swap, procesos GPU, stdout/stderr y código de salida.

## 10. Comandos reproducibles

### Qwen info (inspección, no inferencia)

    TF="$HOME/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native"
    "$TF" info "TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP"

### Qwen serve (comando que produjo el rechazo; no es necesario repetirlo)

    TF="$HOME/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native"
    MODEL="TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP"
    timeout --signal=INT --kill-after=5s 30s \
      "$TF" serve "$MODEL" \
      --name qwen36-forensic \
      --host 127.0.0.1 \
      --port 18090 \
      --backend auto \
      --parallel 1 \
      --context 256 \
      --temperature 0 \
      --no-thinking

### Auditoría de capacidades (no carga el modelo)

    "$TF" serve --help
    "$TF" capabilities --json
    strings "$TF" | grep -Ei 'offload|cpu.?memory|host.?memory|memory.?budget|TENSORFOLD_MEMORY_RESERVE_GIB|TENSORFOLD_CUDA_MEMORY_LIMIT_GB|TF_CUDA_SEGMENTS|segments' | sort -u

## 11. Índice de artefactos locales

Los ficheros que se registraron en el host bajo `/home/ssantos/tensorfold-forensic-20261024/` son:

| Fichero | Contenido |
|---|---|
| `nemotron-1.1.3-preflight.log` | Preflight de Nemotron; entorno/hash y recursos previos según el script original |
| `nemotron-1.1.3-context512.log` | Arranque y error de Nemotron |
| `qwen36-info-1.1.3.log` | Inspección del checkpoint Qwen y recursos |
| `qwen36-1.1.3-serve-context256.log` | Comando, error, código de salida y recursos finales de Qwen |
| `offload-capability-audit.log` | Ayuda, capacidades y cadenas filtradas del binario |
| `tensorfold-1.1.3-memory-options.log` | Auditoría previa de opciones de memoria, variables y cadenas |
| `preflight.log` | Nombre observado en el inventario inicial; confirmar si es copia/alias del preflight anterior antes de contarlo como evidencia independiente |

La publicación de este Markdown no modifica los logs originales del host. Este documento conserva los resultados compartidos, pero no certifica la identidad byte a byte de los ficheros locales. Para una cadena de custodia más fuerte, copiar los logs originales a un directorio de artefactos de LEONES y calcular SHA-256 de cada fichero antes de publicarlos.

## 12. Declaración final LEONES

Este informe registra un resultado observado y reproducible de admisión de memoria para dos modelos MoE en una RTX 3050 Laptop de 4 GiB con TensorFold nativo 1.1.3. No es un benchmark de velocidad ni una prueba de calidad de generación.

Se conserva la distinción LEONES entre ESTIMATED y MEASURED: tamaños, recursos y mensajes de error proceden de ejecuciones reales; cualquier hipótesis sobre offload, compatibilidad en otra GPU o rendimiento futuro permanece sin validar.


## 13. Artefactos de consola añadidos al repositorio

Se añadieron archivos de texto bajo docs/reports/artifacts/tensorfold-moe-forensic-2026-10-24/ para conservar las salidas disponibles en esta sesión:

- qwen36-1.1.3-serve-context256.console.log
- nemotron-1.1.3-context512.console.log
- qwen36-info-1.1.3.console.log
- offload-capability-audit.console.log
- tensorfold-1.1.3-memory-options.console.log

**Limitación de procedencia:** son transcripciones de consola elaboradas a partir de las salidas compartidas en la conversación. Para Qwen serve se conserva la salida mostrada completa; los registros de Nemotron, info y auditorías se identifican expresamente como transcripción, extracto o reconstrucción cuando no se compartió el archivo original íntegro. No son copias binarias certificadas de los logs del equipo. Los originales continúan en las rutas locales indicadas en la sección 11 y deben copiarse desde Ubuntu para completar una cadena de custodia byte a byte.


## 14. Logs originales publicados y SHA-256

Los siete logs originales del host se han añadido a este repositorio. Los enlaces siguientes apuntan a los ficheros originales, no a las transcripciones `.console.log` de la sección 13. El manifiesto se calculó en Ubuntu con `sha256sum` y se verificó con `sha256sum -c` antes del commit.

| Log original | Contenido | SHA-256 |
|---|---|---|
| [`nemotron-1.1.3-preflight.log`](artifacts/tensorfold-moe-forensic-2026-10-24/nemotron-1.1.3-preflight.log) | Preflight de Nemotron | `a14bbc3ab48e01181b5c1643f68faed80aa99ca339b1f2296e774e445400fa4c` |
| [`nemotron-1.1.3-context512.log`](artifacts/tensorfold-moe-forensic-2026-10-24/nemotron-1.1.3-context512.log) | Arranque y error de Nemotron | `75f6246d9b132155f65a1f499d5f391dfe65f6b553f0f566b30630d2abc6b47b` |
| [`offload-capability-audit.log`](artifacts/tensorfold-moe-forensic-2026-10-24/offload-capability-audit.log) | Auditoría de capacidades/offload | `b83f80846b0b29643cf8ac405057fd9657bf5dc31b7c2babfa58080c1009f2ab` |
| [`preflight.log`](artifacts/tensorfold-moe-forensic-2026-10-24/preflight.log) | Preflight adicional; verificar posible duplicado antes de tratarlo como evidencia independiente | `9c27f6c5c00a14732ab55eb14b3948d5e79873d03f7a3aba67f33bba1b727447` |
| [`qwen36-1.1.3-serve-context256.log`](artifacts/tensorfold-moe-forensic-2026-10-24/qwen36-1.1.3-serve-context256.log) | Comando y error de arranque Qwen | `cb232b183b75689310e20f940c1334e45faf23a61d2ce48ae7a677c47feae1f4` |
| [`qwen36-info-1.1.3.log`](artifacts/tensorfold-moe-forensic-2026-10-24/qwen36-info-1.1.3.log) | Inspección del checkpoint Qwen | `09ccbbfc4222d230c95f2dd00738f83fe9ede965d695cb412c86d449c2165438` |
| [`tensorfold-1.1.3-memory-options.log`](artifacts/tensorfold-moe-forensic-2026-10-24/tensorfold-1.1.3-memory-options.log) | Auditoría de opciones de memoria | `b54561e0d88c675ea0f87b2a85356864317d254511bfcaf95d80f53fe2405bc3` |

Manifiesto: [`SHA256SUMS-originals.txt`](artifacts/tensorfold-moe-forensic-2026-10-24/SHA256SUMS-originals.txt).

**Procedencia:** los hashes se calcularon sobre los archivos copiados en Ubuntu y se verificaron localmente. Esto permite comprobar que los ficheros publicados coinciden con el manifiesto; no constituye por sí solo una certificación independiente de la fecha o del método de generación de cada log.

### Informe en inglés

La traducción inglesa de este informe, con enlaces a los logs originales y sus SHA-256, está disponible en [TensorFold MoE Forensic Analysis — RTX 3050 Laptop 4 GiB](analisis-forense-tensorfold-moe-2026-10-24-en.md).
