# Pithos 0.5.1 + LFM3-1.7B Q4_K_M — campaña multiplataforma Ubuntu (2026-11-07)

**Fecha:** 7 de noviembre de 2026 (hora local, sesiones de benchmark).  
**Estado:** pruebas físicas completadas en CPU, Intel ADL GT2 Vulkan y NVIDIA RTX 3050 Vulkan. Incluye barridos de prefill hasta 16.384 tokens; las mediciones PP superiores al contexto predeterminado de 8.192 tokens se conservan como inválidas, no como rendimiento.  
**Equipo:** MSI Thin 15 B12UC · Intel Core i7-12650H · Intel ADL GT2 · NVIDIA RTX 3050 Laptop GPU 4 GiB.  
**Versión:** Pithos 0.5.1 (release Linux x86-64).  
**Modelo:** LFM3-1.7B Q4_K_M, GGUF, SHA-256 `3793e1e6e2266919d6e015287221b41100175a98eddaba92e111aed3b05c93c4`.  
**Informe anterior:** [Pithos 0.5.0 — campaña inicial del 6 de noviembre](PITHOS-LFM3-1.7B-RTX3050-2026-11-06.md).

## 1. Resumen ejecutivo

Pithos 0.5.1 se ha medido con el mismo modelo en tres rutas de ejecución del MSI:

- **NVIDIA RTX 3050 Vulkan:** 695,84 tok/s de prefill PP128 y 104,84 tok/s de generación TG64 (warm).
- **Intel ADL GT2 Vulkan optimizado:** 218,48 tok/s PP128 y 24,91 tok/s TG64 (warm), activando `PITHOS_VK_INTEL=1`.
- **Intel ADL GT2 Vulkan estándar:** 163,20 tok/s PP128 y 19,32 tok/s TG64 (warm).
- **CPU Intel Core i7-12650H:** 149,23 tok/s PP128 y 37,22 tok/s TG64 (warm).

En esta configuración y para LFM3-1.7B Q4_K_M, la RTX 3050 es la ruta más rápida en prefill y generación. Frente a Intel Vulkan optimizado, la NVIDIA obtiene 3,19× el PP128 y 4,21× el TG64. La optimización Intel de Pithos 0.5.1 mejora el resultado Intel estándar un 33,9% en PP y un 28,9% en TG.

La generación NVIDIA se mantiene alrededor de 101–105 tok/s en las pruebas TG256, incluso cuando se solicita un PP mayor. Sin embargo, los resultados de prefill solicitados por encima de 8.192 tokens devuelven tiempos cero y velocidades absurdas. El README de v0.5.1 documenta un contexto predeterminado de 8.192 tokens y máximo configurable de 131.072. Por tanto, esos PP no se consideran mediciones válidas y no se usan para inferir un límite del temporizador ni un fallo confirmado. La causa exacta requiere repetir con contexto explícito y revisar la inicialización del benchmark.

## 2. Hardware y software

| Campo | Valor |
|---|---|
| Equipo | MSI Thin 15 B12UC |
| Sistema | Ubuntu 26.04.1 LTS |
| CPU | Intel Core i7-12650H |
| CPU lógica | 16 hilos |
| iGPU | Intel ADL GT2 |
| GPU dedicada | NVIDIA GeForce RTX 3050 Laptop |
| VRAM NVIDIA | 4.096 MiB |
| Driver NVIDIA | 580.178.04 |
| CUDA reportada por NVIDIA | 13.0 |
| RAM detectada por Pithos | 14,8 GB (según salida de la aplicación) |
| Pithos | 0.5.1 Linux x86-64 |
| Backend probado | Vulkan y CPU |
| Dispositivo Vulkan | Intel índice 0; NVIDIA índice 1 |

No se capturó telemetría continua sincronizada con todos los benchmarks. No se atribuyen consumos, temperaturas ni picos de VRAM a una prueba concreta.

## 3. Modelo y artefacto

- Nombre: `LFM3-1.7B-Q4_K_M.gguf`.
- Origen: `LiquidAI/LFM3-1.7B-GGUF`.
- Tamaño aproximado: 1,02 GB.
- SHA-256: `3793e1e6e2266919d6e015287221b41100175a98eddaba92e111aed3b05c93c4`.
- Ruta usada en la release: `models/LFM3-1.7B-Q4_K_M.gguf`.
- Binario: `~/Pithos-0.5.1/pithos-0.5.1-linux-x64/pithos`.

El modelo se comparte mediante el directorio `models` enlazado a `~/Pithos/models`. No se incluye una copia del GGUF en este repositorio de documentación: el modelo es un artefacto externo de aproximadamente 1 GB y su SHA-256 permite verificar una copia descargada.

## 4. Resultados comparables PP128 / TG64

Se muestran los valores warm reportados por Pithos. PP = prompt processing/prefill; TG = token generation. No mezclar estos microbenchmarks con las pruebas de prompt largo.

| Plataforma / configuración | PP128 warm (tok/s) | TG64 warm (tok/s) | Working set |
|---|---:|---:|---:|
| NVIDIA RTX 3050 Vulkan | **695,84** | **104,84** | 1,19 GB |
| Intel ADL GT2 Vulkan optimizado | 218,48 | 24,91 | 1,18 GB |
| Intel ADL GT2 Vulkan estándar | 163,20 | 19,32 | 1,18 GB |
| Intel Core i7-12650H CPU | 149,23 | 37,22 | 1,06 GB |

### 4.1 Comparaciones derivadas

- RTX 3050 vs Intel Vulkan optimizado: 3,19× PP128 y 4,21× TG64.
- RTX 3050 vs CPU: 4,66× PP128 y 2,82× TG64.
- Intel Vulkan optimizado vs estándar: +33,9% PP128 y +28,9% TG64.
- CPU supera a Intel Vulkan estándar en TG64 (37,22 frente a 19,32 tok/s), aunque queda por debajo en PP128 (149,23 frente a 163,20 tok/s).

Estas comparaciones corresponden a los valores warm comunicados por las ejecuciones disponibles; no sustituyen una campaña estadística con múltiples repeticiones controladas.

## 5. NVIDIA RTX 3050 — barrido de prefill y generación

Configuración: Vulkan, dispositivo 1, modelo LFM3-1.7B Q4_K_M. Working set informado: 1,19 GB. El desglose de asignación observado fue 1.063 MB de pesos en GPU, 154 matrices aceleradas, 176 MB de KV y 8 MB de activaciones; Pithos informó que el forward completo estaba en GPU.

| Prueba | PP warm (tok/s) | TG256 warm (tok/s) | Tiempo PP | Tiempo TG256 | Estado |
|---|---:|---:|---:|---:|---|
| PP2048 / TG256 | 528,64 | 102,51 | 3,87 s | 2,50 s | Válida |
| PP4096 / TG256 | 424,99 | 101,18 | 9,64 s | 2,53 s | Válida |
| PP8192 / TG256 | 300,27 | 101,78 | 27,28 s | 2,52 s | Válida |
| PP8256 / TG256 | 550.289.039.701,66 | 102,45 | 0,00 s | — | **PP inválido** |
| PP8448 / TG256 | 528.005.583.870,60 | 102,56 | 0,00 s | — | **PP inválido** |
| PP8704 / TG256 | 544.005.753.078,80 | 102,27 | 0,00 s | — | **PP inválido** |
| PP9216 / TG256 | 341.319.696.900,55 | 102,52 | 0,00 s | — | **PP inválido** |
| PP10240 / TG256 | 640.006.768.328,00 | 102,50 | 0,00 s | — | **PP inválido** |
| PP12288 / TG256 | 722.966.549.770,52 | 102,20 | 0,00 s | — | **PP inválido** |
| PP16384 / TG256 | 215.565.748.964,70 | 102,46 | 0,00 s | — | **PP inválido** |

En todas las filas del barrido se comunicó un working set de 1,19 GB y una KV de 176 MB. Las cifras PP con tiempo cero son artefactos no utilizables como throughput. La generación TG256 sí se mantuvo estable alrededor de 102 tok/s, pero eso no valida el PP correspondiente.

## 6. Interpretación del límite de contexto

La documentación incluida en el tag `v0.5.1` declara:

- `-c N`: contexto en tokens.
- Valor predeterminado: 8.192.
- Máximo documentado: 131.072.
- `--bench [PP,TG]`: benchmark con perfil por operación.

El inicio de las mediciones PP inválidas (8.256) está inmediatamente por encima del contexto predeterminado documentado. Esto constituye una pista relevante, no una demostración de causalidad: no se ha confirmado todavía si la ruta `--bench` hereda `-c`, si reserva el contexto automáticamente o cómo gestiona una longitud PP superior al contexto efectivo.

La inspección de código realizada hasta ahora identificó el despacho del benchmark en `src/main.c` y el reloj monotónico Linux `clock_gettime(CLOCK_MONOTONIC)` en `src/platform.c`. No se ha completado la inspección del flujo de inicialización del contexto. Por tanto, este informe deja la causa abierta y no etiqueta el problema como bug del reloj.

## 7. Comandos de reproducción

Desde el directorio de la release:

**NVIDIA RTX 3050**
```bash
./pithos -m models/LFM3-1.7B-Q4_K_M.gguf --gpu vulkan --gpu-device 1 --bench
```

**Intel ADL GT2 optimizado**
```bash
PITHOS_VK_INTEL=1 ./pithos -m models/LFM3-1.7B-Q4_K_M.gguf --gpu vulkan --gpu-device 0 --bench
```

**Intel ADL GT2 estándar**
```bash
PITHOS_VK_INTEL=0 ./pithos -m models/LFM3-1.7B-Q4_K_M.gguf --gpu vulkan --gpu-device 0 --bench
```

**CPU**
```bash
./pithos -m models/LFM3-1.7B-Q4_K_M.gguf --cpu --bench
```

**Barrido NVIDIA PP/TG**
```bash
./pithos -m models/LFM3-1.7B-Q4_K_M.gguf --gpu vulkan --gpu-device 1 --bench 2048,256
./pithos -m models/LFM3-1.7B-Q4_K_M.gguf --gpu vulkan --gpu-device 1 --bench 4096,256
./pithos -m models/LFM3-1.7B-Q4_K_M.gguf --gpu vulkan --gpu-device 1 --bench 8192,256
```

No repetir PP mayores que 8.192 sin especificar y verificar primero el contexto efectivo. La documentación del CLI permite configurar `-c N`, pero esta campaña no confirmó el comportamiento de `--bench` con un contexto explícito mayor.

## 8. Inspección del código v0.5.1

Se comprobó el tag oficial `v0.5.1` en el clon local:

- `README.md`: documentación del contexto predeterminado 8.192 y máximo 131.072; opción `--bench [PP,TG]`.
- `src/main.c`: argumentos `bench`, `bench_pp`, `bench_tg`; valores por defecto PP128/TG64; rama de ejecución del benchmark alrededor de la línea 973.
- `src/platform.c`: `clock_gettime(CLOCK_MONOTONIC)` en Linux.

La inspección no fue una auditoría completa del código ni prueba concluyente del origen de los resultados PP anómalos.

## 9. Artefactos archivados

El directorio [`artifacts/pithos-0.5.1-2026-11-07/`](../artifacts/pithos-0.5.1-2026-11-07/) contiene:

- CSV de resultados PP/TG para análisis posterior.
- Registro consolidado de las salidas de benchmark y de las pruebas de contexto.
- Script con los comandos reproducibles.

**Nota sobre la procedencia de los logs:** los registros archivados son una transcripción estructurada de las salidas pegadas en la conversación de trabajo y de los valores conservados en el cuaderno de campaña. No son volcados stdout/stderr originales capturados a fichero en el equipo. Los logs originales completos, si existen en el MSI, no estuvieron disponibles como adjuntos para esta operación y no se afirma que se hayan copiado. El GGUF y el ejecutable tampoco se duplican en LEONES; se documentan sus rutas, versión y hash.

## 10. Limitaciones

- Una única sesión por ruta/configuración en los resultados resumidos; no se dispone de distribución estadística.
- Sin telemetría NVIDIA continua sincronizada con cada ejecución.
- Los valores PP superiores a 8.192 son inválidos y se conservan solo para trazabilidad.
- No se ha determinado todavía el comportamiento de `--bench` con `-c` explícito superior al default.
- No se evaluaron calidad, exactitud ni razonamiento del modelo.
- Las cifras son específicas de este equipo, esta versión, este modelo y esta cuantización.

## 11. Conclusión

Pithos 0.5.1 ofrece un resultado sólido en la RTX 3050 Laptop: **695,84 tok/s PP128 y 104,84 tok/s TG64 warm** con LFM3-1.7B Q4_K_M. La optimización Vulkan Intel aporta una mejora medible frente al camino Intel estándar, aunque en generación la CPU queda por encima de ambas rutas Intel Vulkan probadas.

El barrido confirma PP válido hasta 8.192 tokens en la configuración probada. Los resultados PP superiores son anómalos y deben permanecer excluidos hasta comprobar la interacción entre longitud PP y contexto efectivo. La campaña queda archivada como evidencia experimental de Pithos 0.5.1, sin elevar observaciones no verificadas a conclusiones.
