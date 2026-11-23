# Xiaomi Mi 9T Pro — plataforma móvil de referencia

**Estado:** plataforma de referencia declarada; caracterización física pendiente.  
**Campaña:** [plan de pruebas](../docs/subprojects/Mobile-LLMs-ARM/devices/XIAOMI-MI-9T-PRO-TEST-PLAN.md) · [matriz de runtimes](../docs/subprojects/Mobile-LLMs-ARM/devices/XIAOMI-MI-9T-PRO-RUNTIME-MATRIX.md) · [protocolo de benchmark](../docs/subprojects/Mobile-LLMs-ARM/devices/XIAOMI-MI-9T-PRO-BENCHMARK-PROTOCOL.md)

## Identidad y datos comunicados

| Campo | Valor | Procedencia / estado |
|---|---|---|
| Dispositivo | Xiaomi Mi 9T Pro | Declarado por el usuario |
| RAM nominal | 6 GB | Declarado por el usuario |
| CPU | Octa-core, hasta 2,84 GHz | Declarado por el usuario; pendiente de lectura del dispositivo |
| SoC esperado | Qualcomm Snapdragon 855 | Identificación del modelo comercial; confirmar con Android |
| GPU esperada | Qualcomm Adreno 640 | Identificación del SoC; confirmar driver y capacidades |
| DSP/AI | Qualcomm Hexagon 690 | Identificación de plataforma; no implica soporte LLM |
| Almacenamiento | 128 GB total; 55,2 GB ocupados; ≈72,8 GB libres | Captura «Sobre el teléfono», 2026-11-23; libre calculado como total menos ocupado |
| MIUI | Global 12.0.5 Estable (`12.0.5.0(QFKEUXM)`) | Captura «Sobre el teléfono», 2026-11-23 |
| Android/API | Android 10; API level pendiente | Captura «Sobre el teléfono»; API no visible |
| Root | Desconocido | Inventario pendiente |
| Parche de seguridad Android | 2021-04-01 | Captura «Sobre el teléfono», 2026-11-23 |
| ABI / kernel / firmware | Desconocidos | Inventario pendiente |
| Estado térmico/batería | Desconocido | Inventario pendiente |

Los elementos marcados como esperados son hipótesis de identificación de la variante comercial, no una lectura de hardware obtenida del terminal. No publicar capacidades de aceleración como verificadas hasta capturar la salida del dispositivo.

## Propósito en LEONES

Plataforma ARM64 de referencia para Mobile-LLMs-ARM, complementaria a la estación Ubuntu MSI. La campaña caracterizará inferencia local de modelos compactos y comparará CPU, GPU y, si la plataforma de software lo permite, DSP/HTP.

La primera ruta será **Android sin root**, sin desbloquear bootloader, cambiar ROM, instalar firmware ni modificar particiones. Root se registrará como capacidad opcional y solo se utilizará en experimentos posteriores que lo requieran y cuenten con autorización explícita.

## Perfil esperado del SoC (pendiente de confirmar)

- Snapdragon 855 / familia SM8150.
- CPU Kryo 485: configuración heterogénea de núcleos basada en Cortex-A76/A55; no tratar los ocho núcleos como equivalentes.
- GPU Adreno 640.
- DSP Hexagon 690 / plataforma Qualcomm AI de esa generación.

La presencia de Hexagon no demuestra que QNN, HTP, FastRPC o un runtime moderno puedan ejecutar modelos LLM en este dispositivo. Cada combinación requiere una prueba de compatibilidad y ejecución efectiva.

## Inventario físico pendiente

Recopilar mediante ADB y/o Termux sin root:

- fabricante, modelo, producto, SoC y board;
- Android release, API level, build fingerprint y kernel;
- ABI primaria/secundarias y características CPU visibles;
- memoria total/disponible y almacenamiento libre;
- versión Vulkan, extensiones y driver GPU si están expuestos;
- estado de batería, temperatura y thermal status cuando Android lo permita;
- restricciones de batería, procesos y ahorro energético.

Comandos iniciales y campos esperados están en el plan de pruebas. No recopilar IMEI, número de serie, MAC, cuentas ni otros identificadores personales. Redactar identificadores únicos de las salidas antes de archivarlas.

## Límites y evidencia

- **Declarado:** datos facilitados por el usuario.
- **EXPECTED:** especificación inferida del modelo comercial, pendiente de confirmación.
- **DISCOVERED:** capacidad detectada, sin prueba de ejecución.
- **COMPATIBLE:** runtime/modelo preparado y compatible según evidencia concreta.
- **REPRODUCED:** inferencia funcional repetida en el dispositivo identificado.
- **MEASURED:** benchmark con protocolo, versiones, configuración y artefactos verificables.
- **VERIFIED:** evidencia revisada y reproducible; no equivale automáticamente a aceptación.

No hay benchmarks físicos LEONES acreditados para este teléfono en este perfil. Ninguna cifra de terceros se atribuirá al dispositivo. Mantener separados rendimiento pico, sostenido, térmico y eficiencia energética.

## Inventario físico capturado por SSH/Termux — 2026-11-23

**Estado de caracterización:** DISCOVERED para identidad de sistema, ABI, topología CPU, memoria, almacenamiento, sensores y disponibilidad de bibliotecas gráficas. Vulkan GPU Qualcomm: UNVERIFIED. Inferencia: NOT TESTED.

### Sistema y software

| Campo | Valor observado | Estado |
|---|---|---|
| Fabricante / modelo | Xiaomi / Mi 9T Pro | DISCOVERED |
| SoC / plataforma | Qualcomm; `ro.board.platform=msmnile`; `ro.hardware=qcom`; `ro.boot.hardware=qcom` | DISCOVERED |
| Android | 10 | DISCOVERED |
| API level | 29 | DISCOVERED |
| Kernel | `4.14.117-perf-g0f2347b`; build 2021-04-14 | DISCOVERED |
| Arquitectura | AArch64 | DISCOVERED |
| ABI primaria | `arm64-v8a` | DISCOVERED |
| ABI adicionales | `armeabi-v7a`, `armeabi` | DISCOVERED |
| Termux | 0.119.0-beta.3, paquete F-Droid, target SDK 28 | DISCOVERED |
| Gestor de paquetes | apt; repositorio Termux main (`packages-cf.termux.dev`) | DISCOVERED |
| termux-tools | 1.45.0 | DISCOVERED |
| Acceso remoto | SSH desde MSI confirmado; servidor Termux en puerto 8022 | REPRODUCED (conexión SSH) |
| Root | No determinado; no se ha comprobado ni requerido | UNKNOWN |

### CPU

La salida de `lscpu` identifica ocho CPU lógicas y dos clústeres:

| Clúster informado | Núcleos | Frecuencia máxima informada |
|---|---:|---:|
| Kryo-4XX-Gold | 4 | 2.841,6 MHz |
| Kryo-4XX-Silver | 4 | 1.785,6 MHz |

Las frecuencias instantáneas capturadas durante el inventario fueron 1.708–1.785,6 MHz en CPU 0–3 y 710,4–825,6 MHz en CPU 4–7. El governor visible en CPU 0 es `schedutil`; `scaling_max_freq` visible en esa política fue 1.785.600 kHz. No interpretar las frecuencias instantáneas como rendimiento sostenido ni como máximo efectivo de todos los clústeres.

### Memoria y almacenamiento

| Campo | Valor observado | Estado / contexto |
|---|---:|---|
| RAM total detectada | 5.636.076 kB (≈5,37 GiB) | DISCOVERED |
| RAM disponible | 2.467.628 kB (≈2,35 GiB) | DISCOVERED; instantánea |
| RAM libre inmediata | 103.928 kB | DISCOVERED; no equivale a memoria disponible |
| Swap total | 2.621.436 kB (≈2,50 GiB) | DISCOVERED |
| Swap libre | 1.699.036 kB | DISCOVERED |
| Swap usada | ≈922.400 kB (≈0,88 GiB) | Calculada de total menos libre; instantánea |
| Almacenamiento Android comunicado anteriormente | 128 GB nominales; ≈72,8 GB libres | Captura «Sobre el teléfono», 2026-11-23 |
| Partición `/data` vista desde Termux | 109G total, 44G usados, 65G disponibles | `df -h`, 2026-11-23 |
| Espacio ocupado por HOME de Termux | 48K | `du -sh $HOME`, 2026-11-23 |

Las cifras de almacenamiento proceden de vistas y unidades distintas (pantalla de almacenamiento Android y sistema de archivos `/data`); conservar ambas sin asumir que son mediciones idénticas.

### GPU, Vulkan y aceleradores

| Campo | Resultado | Estado |
|---|---|---|
| GPU de la plataforma | Adreno 640, correspondiente al Snapdragon 855 | EXPECTED; no enumerada por Vulkan desde Termux |
| Driver Android Qualcomm | `/vendor/lib64/hw/vulkan.msmnile.so` presente; también ruta espejo bajo `/system/vendor/lib64` | DISCOVERED (archivo presente) |
| Bibliotecas Qualcomm | EGL/GLES Adreno y `libadreno_utils.so` presentes en `/vendor/lib64` | DISCOVERED |
| Interfaz KGSL | `/sys/class/kgsl/kgsl-3d0` y rutas consultadas no visibles desde Termux | UNAVAILABLE from current app context |
| Nodos de dispositivo | No se observaron `/dev/kgsl*` ni `/dev/dri/*` en la consulta | UNAVAILABLE from current app context |
| Vulkan Tools | `vulkan-tools 1.4.369` instalado en Termux | DISCOVERED |
| Loader / ICD de Termux | `vulkan-loader-generic 1.4.369`; `mesa-vulkan-icd-swrast 26.3.1` | DISCOVERED |
| Dispositivo enumerado por `vulkaninfo --summary` | `llvmpipe (LLVM 21.1.8, 128 bits)`, tipo `PHYSICAL_DEVICE_TYPE_CPU` | DISCOVERED |
| Versión Vulkan de instancia | 1.4.369 | DISCOVERED |
| Driver Vulkan enumerado | Mesa 26.3.1 / LLVM 21.1.8; `DRIVER_ID_MESA_LLVMPIPE` | DISCOVERED |
| Aceleración Vulkan Adreno | No demostrada; la enumeración actual usa rasterizador software CPU | UNVERIFIED / NOT AVAILABLE in current test |

**Interpretación:** que el driver Qualcomm exista en la partición Android no significa que el loader Vulkan de Termux lo esté cargando. La salida actual identifica únicamente llvmpipe, por lo que no atribuir ninguna operación Vulkan a la Adreno 640. No copiar bibliotecas del sistema ni alterar variables/paths de carga para forzar una detección sin un procedimiento específico y reversible.

### Temperatura y estado térmico — instantánea en reposo

| Sensor | Valor | Interpretación |
|---|---:|---|
| Sensores CPU `cpu-*` | aproximadamente 34,9–38,4 °C | Lecturas observadas |
| Sensores GPU `gpuss-*` | aproximadamente 34,9–36,4 °C | Lecturas observadas |
| DDR | 36,4 °C | Lectura observada |
| Batería (`battery`) | 30,2 °C | Lectura observada |
| `pm8150b_tz` | 34,0 °C | Lectura observada |
| `pm8150b-wp-therm` | 103,862 °C según el valor sysfs | Sensor auxiliar; significado físico no confirmado |
| `soc` | 274 °C según el valor sysfs | Valor incoherente; tratar como lectura inválida/no interpretable |
| `lmh-dcvs-00/01` | 75 °C | Sensor/umbral con semántica no confirmada |

Las temperaturas son una instantánea y no caracterizan carga sostenida, throttling ni temperatura de carcasa. Los sensores con valores incoherentes, negativos o cero no se usan para conclusiones térmicas sin identificar su semántica.

### Evidencia y límites de la campaña

- Inventario obtenido mediante comandos de solo lectura desde Termux por SSH el 2026-11-23.
- `free -h`, `/proc/meminfo`, `lscpu`, `getprop`, `termux-info`, `df`, sysfs térmico y `vulkaninfo --summary` aportan la evidencia descrita.
- La lectura de `/proc/swaps` fue denegada por permisos; el total y libre de swap sí se obtuvieron de `/proc/meminfo`.
- No se ha instalado ni ejecutado todavía ningún motor LLM ni modelo en el teléfono.
- No hay benchmark de tokens/s, prefill, latencia, consumo energético ni throttling.
- No se ha verificado acceso a Vulkan Qualcomm, OpenCL, Hexagon/HTP, QNN o NPU desde Termux.
- La instalación de Vulkan Tools añadió el loader genérico y el ICD software Mesa; no sustituye ni demuestra el uso del driver Adreno del sistema.
- Mantener la campaña inicial sin root y sin modificar bootloader, ROM, kernel, firmware o particiones.
