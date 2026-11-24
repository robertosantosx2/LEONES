# Xiaomi Mi 9T Pro — llama.cpp CPU / Qwen2.5-Coder-3B-Instruct (24-11-2026)

**Estado:** tres inferencias completadas y medidas; cuarta inferencia funcional confirmada sin benchmark válido.  
**Plataforma:** Xiaomi Mi 9T Pro (raphael), Qualcomm Snapdragon 855 / SM8150, 8 núcleos ARM64, 6 GB RAM declarados, Android 10 / API 29, MIUI Global 12.0.5, Termux F-Droid 0.119.0-beta.3.  
**Fecha de campaña:** 24-11-2026 (CET).  
**Separación:** resultados exclusivos de este teléfono. No mezclar con LG-H930/Snapdragon 835 ni con MSI Thin 15/RTX 3050.

## 1. Motor y compilación

- Motor: llama.cpp, ejecutable `$HOME/src/llama.cpp/build/bin/llama-cli`.
- Versión: `1.0.0-dev`, build 1, commit `51831d47d0a47b8a7d07c9ff262ebe4b0a211790` (short `51831d4`).
- Compilador: Clang 21.1.8, Android aarch64.
- Configuración CMake: Release, `GGML_CPU=ON`; `GGML_VULKAN=OFF`, `GGML_OPENCL=OFF`, `GGML_CUDA=OFF`.
- **Backend realmente probado: CPU.** El runtime avisó `no usable GPU found, --gpu-layers option will be ignored`. No se ha validado Vulkan, OpenCL, Adreno 640 ni Hexagon/HTP.
- `llama-cli` ocupa 6,2 KB y utiliza bibliotecas dinámicas de `build/bin`; `ldd` no está instalado en Termux, no se instaló como parte de esta campaña.

## 2. Modelo

- Modelo: Qwen2.5-Coder-3B-Instruct GGUF, cuantización Q4_K_M.
- Repositorio: [Qwen/Qwen2.5-Coder-3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF).
- Archivo: `qwen2.5-coder-3b-instruct-q4_k_m.gguf`.
- Ruta local: `$HOME/models/llama.cpp/qwen2.5-coder-3b-instruct-q4_k_m.gguf`.
- Tamaño observado: aproximadamente 2,0 GB.
- SHA-256 verificado: `724fb256bec1ff062b2f65e4569e871ad2e95ab2a3989723d1769c54294730b7`.

## 3. Configuración de inferencia

Parámetros de las tres ejecuciones medidas y de la cuarta ejecución funcional:

- Contexto: 512.
- Hilos: 4; hilos de batch: 4.
- Batch: 64; ubatch: 32.
- Temperatura: 0,2; semilla: 42.
- Modo: `--single-turn --perf --no-display-prompt`.
- Prompt: `Write a C function that checks whether an integer is prime. Include a short explanation.`
- Límite de generación: 64 tokens en las ejecuciones 1 y 3; 160 tokens en la 2 y la 4.
- Prioridad reducida: `nice -n 10`.
- No se usó offload GPU.

## 4. Resultados medidos

| Ejecución | Hora local | Tokens máximos solicitados | Prefill | Generación | Resultado |
|---|---:|---:|---:|---:|---|
| 1 | 10:27:36 | 64 | 33,7 tok/s | 10,0 tok/s | Código 0; respuesta truncada por límite |
| 2 | — | 160 | 33,8 tok/s | 9,9 tok/s | Código 0; respuesta más extensa, truncada por límite |
| 3 | 10:33:00 | 64 | 33,4 tok/s | 8,3 tok/s | Código 0; respuesta truncada por límite |

**Media aritmética de las tres ejecuciones:** prefill **33,63 tok/s**; generación **9,40 tok/s**.  
**Rangos:** prefill 33,4–33,8 tok/s; generación 8,3–10,0 tok/s.

Son mediciones iniciales de tres ejecuciones, no un benchmark sostenido ni una prueba térmicamente estabilizada. La variación de la tercera ejecución no demuestra throttling: no hay temperatura correlacionada con la carga ni frecuencia sostenida capturada.

### Memoria y batería capturadas en las tres pruebas

- Ejecución 1: antes, MemAvailable 2.788.244 kB y SwapFree 1.574.772 kB; después, 3.360.140 kB y 750.312 kB. Batería 84 %, conectado a AC, 23,7 °C.
- Ejecución 2: antes, MemAvailable 3.306.828 kB y SwapFree 798.284 kB; después, 3.521.280 kB y 569.028 kB. Batería 84 %, conectado a AC, 24,0 °C.
- Ejecución 3: antes, MemAvailable 3.353.488 kB y SwapFree 1.177.780 kB; después, 3.610.264 kB y 854.900 kB. SwapCached 15.784 kB y Mlocked 159.016 kB. Batería 85 %, conectado a AC, 24,7 °C.

Las cifras de MemAvailable y SwapFree son instantáneas del sistema Android, no RSS atribuible a llama.cpp. No interpretar swap como RAM física ni atribuir todos sus cambios al modelo.

## 5. Cuarta ejecución — inferencia funcional, telemetría incompleta

- Inicio registrado: 24-11-2026 10:45:44 CET.
- Directorio de captura: `$HOME/benchmarks/qwen25-coder3b-monitor-20261124-104544`.
- Parámetros: los mismos de la sección 3, con `--n-predict 160`.
- El log inicial parecía contener únicamente el indicador animado `Loading model...`; el volcado completo posterior mostró metadatos del modelo, el prompt, una respuesta C coherente que empieza a implementar `isPrime` y el modo interactivo de llama.cpp.
- **Conclusión:** el modelo cargó y generó texto. No fue un fallo de carga.
- La supervisión con `nohup setsid nice ...` vigiló un PID wrapper y no capturó correctamente el proceso llama real. Solo quedó una muestra en `monitor.log`; no hay RSS/VmHWM, duración de inferencia ni tokens/s válidos para esta ejecución.
- El proceso ya no aparecía en `ps` al realizar el diagnóstico.
- Memoria al inicio: MemAvailable 3.302.244 kB; SwapFree 1.144.316 kB; SwapCached 28.108 kB; Mlocked 159.016 kB.
- Memoria al final de la comprobación (10:50:26): MemAvailable 1.634.304 kB; SwapFree 864.080 kB; SwapCached 17.256 kB; Mlocked 159.016 kB.
- Temperaturas de la única muestra del monitor: sensores CPU 28,7–29,8 °C, CPUSS 30,6–31,4 °C y otros sensores CPU hasta 40,7 °C. No hay serie temporal suficiente para atribuirlas a la inferencia.
- Batería al inicio: 85 %, UNPLUGGED/DISCHARGING, 25,0 °C, 4038 mV.
- La menor MemAvailable posterior merece una muestra de recuperación en reposo; no demuestra OOM ni permite atribuir el consumo a un proceso concreto.

## 6. Calidad y límites de la evidencia

**Confirmado**
- Binario llama.cpp funcional en Android ARM64.
- Modelo descargado y SHA-256 verificado.
- Tres inferencias CPU completadas con código de salida 0 y métricas de prefill/generación.
- Cuarta inferencia cargó el modelo y produjo salida textual.

**No medido o no validado**
- GPU Adreno 640, Vulkan, OpenCL, Hexagon/HTP.
- RSS máximo del proceso, duración total fiable de la cuarta ejecución y telemetría de memoria por proceso.
- Potencia, energía, autonomía, temperatura sostenida y throttling.
- Benchmark sostenido, contexto largo, concurrencia y calidad comparativa.

## 7. Próximos pasos

1. Capturar recuperación en reposo (MemAvailable, SwapFree, batería y sensores térmicos).
2. Corregir la supervisión del proceso hijo antes de otra ejecución monitorizada; no tomar el código de salida del wrapper como código de salida de llama-cli.
3. En una futura repetición, registrar PID real, `/proc/<pid>/status` (VmRSS/VmHWM/Threads), marcas de tiempo y salida íntegra de `--perf`.
4. Mantener la campaña CPU separada de cualquier investigación GPU hasta que exista una prueba específica reproducible.

**Clasificación final:** llama.cpp CPU + Qwen2.5-Coder-3B-Instruct Q4_K_M — **ejecutado y medido (3 repeticiones iniciales)**; cuarta ejecución **funcional, no medida**.
