# Spark-X2.6-4B-abliterated-GGUF en Ubuntu — primera ejecución CUDA (2026-10-30)

## Estado

**Ejecución funcional confirmada con llama.cpp CUDA.** El modelo carga en el equipo local y genera una respuesta coherente en español. La prueba de 256 tokens terminó correctamente (código de salida 0).

Este documento conserva los resultados obtenidos hasta el 30 de octubre de 2026. No es todavía un benchmark exhaustivo ni una comparación controlada entre runtimes.

## Fuente y artefacto

- Repositorio: [FrostWolfAI/Spark-X2.6-4B-abliterated-GGUF](https://huggingface.co/FrostWolfAI/Spark-X2.6-4B-abliterated-GGUF)
- Archivo: `Spark-X2.6-4B-abliterated-Q4_K_M.gguf`
- Ruta local observada: `/home/ssantos/models/Spark-X2.6-4B-abliterated/Spark-X2.6-4B-abliterated-Q4_K_M.gguf`
- Tamaño: 2.600.225.408 bytes (aprox. 2,42 GiB / 2,5 GB decimales).
- Arquitectura GGUF detectada: `spark2_5`.
- Licencia indicada para el repositorio: Apache-2.0.
- Cuantización: Q4_K_M.

## Equipo y software

| Componente | Configuración observada |
|---|---|
| Sistema | Ubuntu nativo |
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H, 16 CPU lógicas |
| RAM | 14,8 GiB |
| GPU | NVIDIA GeForce RTX 3050 Laptop |
| VRAM | 4 GiB |
| Driver NVIDIA | 580.178.04 |
| CUDA reportada por el driver | 13.0 |
| Runtime | llama.cpp CUDA |
| Build | 0.7.0-dev, b11740, commit `6fa4f6cd3` |
| Binarios predeterminados | `/usr/local/bin/llama-cli` y `/usr/local/bin/llama-server`, enlazados a `~/llama.cpp-cuda/build-cuda/bin/` |

La compilación CUDA detecta la RTX 3050 mediante `llama-cli --list-devices`. La sustitución de los enlaces predeterminados no desinstaló el paquete anterior del sistema; se conservó `/usr/bin/llama-cli`.

## Resultados de inferencia

| Prueba | Parámetros principales | Resultado | Prompt | Generación |
|---|---|---|---:|---:|
| 1 | `-ngl 12 -c 1024 -t 6 -n 32 --temp 0.2` | Carga y genera; salida de razonamiento iniciada y respuesta truncada por el límite de tokens | 66,2 tok/s | 5,9 tok/s |
| 2 | `-ngl 12 -c 1024 -t 6 -n 128 --temp 0.2 --reasoning off` | Respuesta española coherente, pero truncada | 37,3 tok/s | 7,9 tok/s |
| 3 | `-ngl 12 -c 1024 -t 6 -n 256 --temp 0.2 --reasoning off` | **Respuesta completa y coherente**; código de salida 0 | 36,9 tok/s | **7,2 tok/s** |

La tercera prueba pidió explicar brevemente la IA y mencionar tres aplicaciones prácticas. La respuesta completó las tres aplicaciones (diagnóstico médico, gestión de producción y asistencia lingüística).

**Resultado funcional de referencia por ahora:** 7,2 tokens/s de generación para Spark Q4_K_M, con 12 capas GPU solicitadas, contexto 1024 y 6 hilos. El valor de `-ngl 12` es el parámetro solicitado; en estos registros no se ha confirmado de forma independiente el número efectivo de capas descargadas a GPU. Las pruebas usaron prompts y límites de generación distintos, por lo que no deben tratarse como una serie comparativa estrictamente homogénea.

## Comandos de ejecución

Primera prueba:

```bash
timeout 180s llama-cli \
  -m "$MODEL" \
  -ngl 12 -c 1024 -t 6 -n 32 --temp 0.2 \
  --single-turn \
  -p "Explica brevemente qué es la inteligencia artificial y menciona tres aplicaciones prácticas."
```

Segunda y tercera prueba añadieron `--reasoning off` y ampliaron `-n` a 128 y 256 respectivamente. La tercera terminó con respuesta completa.

## Registros locales

Los logs originales quedaron guardados en el equipo de pruebas:

- `~/spark-x26-cuda-test.log`
- `~/spark-x26-cuda-test-128.log`
- `~/spark-x26-cuda-test-256.log`

Los logs no se adjuntan a este commit; se conservan en la máquina local indicada. Las métricas de la tabla se transcriben de la salida de llama.cpp registrada durante esas ejecuciones.

## Incidencia del intento de benchmark repetido

Se inició posteriormente un intento de benchmark de tres pasadas con monitorización periódica de `nvidia-smi`. El intento quedó incompleto:

- El directorio creado fue `~/spark-x26-benchmark-20261030-215055`.
- `run-1.log` permaneció vacío y no apareció `run-1.exit`.
- El monitor `nvidia-smi` (PID 682027) quedó activo de forma huérfana y se detuvo finalmente con `sudo kill -9 682027`.
- En la misma sesión del sistema estaba ejecutándose LFM3-1.7B (PID 683912), utilizando aproximadamente 1.258 MiB de VRAM en la observación registrada. **Ese proceso no se interrumpió.**
- No había un proceso Spark activo cuando se inspeccionó la lista de procesos; por tanto, este intento fallido no demuestra que Spark se bloqueara ni que sufriera falta de memoria.
- El registro CSV de GPU solo refleja la observación disponible en ese intervalo (GPU 0 %, 1.281 MiB ocupados, 42–43 °C y 3,36 W en las últimas muestras). No es una medición de pico de Spark.

El monitor huérfano ya está detenido. La ejecución LFM3 seguía activa en la última comprobación, por lo que se decidió no lanzar otra inferencia Spark concurrente.

## Límites de la evidencia

- No se midió el pico de VRAM durante la carga/generación.
- No se midió de forma aislada el pico de RAM del proceso.
- No se ha ejecutado todavía una repetición controlada de tres o más pasadas con idéntico prompt y configuración.
- No se ha medido rendimiento con otros runtimes.
- No se debe inferir que la GPU usó exactamente 12 capas a partir del argumento `-ngl 12` sin revisar el log verbose de offload.
- El intento de monitorización fallido se registra como incidencia operativa, no como fallo de compatibilidad del modelo.

## Próxima fase de validación

Cuando no haya otra inferencia ocupando la GPU:

1. Repetir una sola ejecución Spark con registro directo a fichero y sin monitor de fondo.
2. Capturar el log verbose para verificar las capas realmente descargadas a CUDA.
3. Registrar tiempo de carga, prompt eval, generación, RSS máximo y snapshots de VRAM antes/después.
4. Después, realizar varias pasadas con prompt, contexto, hilos, temperatura y tokens idénticos.
5. Conservar por separado los logs originales y los datos agregados para que el resultado sea reproducible.

## Clasificación LEONES

- **Carga del modelo:** MEASURED — completada.
- **Generación funcional:** MEASURED — respuesta completa en la prueba de 256 tokens.
- **Velocidad:** MEASURED — 7,2 tok/s en la prueba funcional de referencia.
- **Compatibilidad básica Spark + llama.cpp CUDA b11740 + RTX 3050 Laptop:** MEASURED — ejecución satisfactoria.
- **Pico de VRAM/RAM y benchmark repetido:** PENDING — todavía no medidos.
