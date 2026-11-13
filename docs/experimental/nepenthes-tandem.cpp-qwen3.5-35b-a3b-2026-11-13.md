# NEPENTHES · Tandem.cpp + Qwen3.5-35B-A3B · batería independiente · 2026-11-13

**ID:** `NEPENTHES_Tandem.cpp_Qwen3.5-35B-A3B-IQ2_XXS_20261113`  
**Tipo:** ejecución independiente de la batería NEPENTHES de 10 casos  
**Estado de ejecución:** 10/10 según la salida final del runner  
**Estado de publicación:** evidencia parcial; el fragmento de terminal disponible conserva los registros detallados de los casos 6–10.

> **Alcance de esta publicación.** El archivo primario recibido contiene los registros completos impresos para los casos 6–10 y la confirmación final de la ruta de resultados. No incluye los registros de los casos 1–5, el manifiesto completo, los JSON originales de respuestas ni el fichero bruto de muestras de recursos. Este informe no reconstruye esos datos ausentes y no presenta los cinco casos publicados como si fueran toda la batería.

## 1. Objetivo y alcance

Registrar una ejecución instrumentada de la batería de razonamiento de Qwen3.5-35B-A3B IQ2_XXS con **Tandem.cpp**, utilizando la metodología **Nepenthes**. La batería ejecutó diez casos secuenciales: operaciones aritméticas, `two_sum` y `binary_search`, con distintos presupuestos de razonamiento y límites de generación.

Esta campaña es una ejecución independiente. No es una comparación A/B controlada con `cafe-llama.cpp`. Las diferencias de motor, caché, secuencia de ejecución y estado del sistema impiden tratar los resultados como una comparación directa.

## 2. Motor y servidor

- **Motor:** `Tandem.cpp`
- **Repositorio local:** `~/Descargas/tandem-research/engines/tandem.cpp`
- **Build registrado en la campaña de referencia:** `0.8.0-dev`, build `11962`; submódulo llama.cpp `f5222f25c18da062ab2b8a2dbbfbf4feae398566`.
- **Endpoint:** `http://127.0.0.1:18085`
- **PID:** `10314`
- **Modelo servido:** `$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`

Argumentos de inicio del servidor confirmados en la sesión:

```bash
-m "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
--host 127.0.0.1 --port 18085 \
-c 2048 -b 128 -ub 64 -t 8 -tb 8 -ngl 99 \
--cpu-moe --moe-cache-mib 512 -np 1
```

El servidor ya estaba iniciado antes de ejecutar el runner. El runner no inicia, detiene ni reconfigura el servidor.

## 3. Modelo

- **Familia:** Qwen3.5-35B-A3B
- **Archivo:** `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`
- **Arquitectura:** `qwen35moe`
- **Parámetros:** 35B totales; aproximadamente 3B activos
- **Expertos:** 256 totales; 8 activados por token
- **Cuantización:** IQ2_XXS, 2,0625 bpw
- **Tamaño local comunicado:** 10.665.148.928 bytes (aprox. 9,94 GiB)
- **SHA-256 del modelo:** no incluido en la evidencia de esta ejecución.

## 4. Plataforma

- **Host:** MSI Thin 15 B12UC
- **Sistema operativo:** Ubuntu
- **CPU:** Intel Core i7-12650H
- **RAM:** 14 GiB
- **Swap configurada:** 32 GiB
- **GPU:** NVIDIA GeForce RTX 3050 Laptop, 4 GiB VRAM, arquitectura sm_86
- **Driver:** 580.178.04
- **CUDA runtime:** 13.0
- **CUDA toolkit:** 13.4.92

## 5. Protocolo

- **Casos:** 10 en la batería completa; los registros publicados aquí corresponden a 6–10.
- **Ejecución:** secuencial, un slot.
- **Temperatura de generación:** 0.
- **Streaming:** desactivado.
- **Formato de razonamiento solicitado:** `deepseek`.
- **Thinking:** habilitado mediante `chat_template_kwargs.enable_thinking=true`.
- **Presupuesto de razonamiento enviado:** variable por caso (128 o 256 en los registros publicados).
- **Monitorización:** intervalo nominal de 1 segundo; 29–53 muestras por petición en los casos publicados.
- **Runner:** `run_battery.py`, con `--server-pid 10314`, `--monitor-interval 1` y `--timeout 900`.
- **Directorio de salida confirmado por el runner:** `~/NEPENTHES_TANDEM_QWEN35_20261113_full`.

Enviar `reasoning_budget_tokens` o seleccionar un formato de razonamiento no demuestra por sí solo que el servidor imponga un límite semántico de razonamiento. Se registra como parámetro solicitado, no como límite efectivo verificado.

## 6. Resultados de los casos con evidencia disponible

| Caso | Tarea | Budget enviado | max_tokens | Prompt | Cacheados | Generados | Prefill tok/s | Generación tok/s | finish |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 6 | two_sum | 256 | 1.024 | 93 | 89 | 1.024 | 50,81 | 36,67 | `length` |
| 7 | two_sum | 128 | 1.536 | 93 | 89 | 1.016 | 53,50 | 33,97 | `stop` |
| 8 | two_sum | 256 | 1.536 | 93 | 89 | 1.158 | 59,94 | 32,34 | `stop` |
| 9 | binary_search | 128 | 1.536 | 188 | 0 | 1.249 | 139,42 | 29,65 | `stop` |
| 10 | binary_search | 256 | 1.536 | 188 | 184 | 1.500 | 58,11 | 27,93 | `stop` |

En estos cinco casos se generaron 5.947 tokens. La media simple de las cinco tasas de generación por petición fue **32,11 tok/s**; mediana **32,34 tok/s**; rango **27,93–36,67 tok/s**. No es la media de la batería completa.

### Interpretación de caché

- Casos 6–8: 89 de 93 tokens de entrada aparecen como cacheados.
- Caso 9: 0 de 188 tokens cacheados; es el único de estos cinco con prompt completamente no cacheado.
- Caso 10: 184 de 188 tokens aparecen como cacheados.

Por tanto, no se debe comparar el prefill de estos casos como si todos fueran mediciones frías homogéneas. La tasa de prefill del caso 9 no es directamente comparable con las de los casos 6–8 y 10.

### Finalización y truncamiento

El caso 6 alcanzó exactamente su límite de 1.024 tokens y terminó con `finish_reason=length`: es una generación truncada por límite. Los casos 7–10 terminaron con `stop`. Un `stop` acredita la terminación de la generación, no la corrección del algoritmo producido.

El caso 10 generó 1.500 de los 1.536 tokens permitidos, aunque terminó con `stop`. Su proximidad al límite merece revisión de la respuesta original.

## 7. Monitorización de recursos (casos 6–10)

Las cifras siguientes son medias por petición obtenidas por el monitor. Para las medias globales se usa la media simple de las cinco medias por caso, no una media ponderada por muestras.

| Caso | CPU proceso % | RSS proceso (GB) | GPU % | VRAM media (MiB) | Temperatura media | Potencia media |
|---:|---:|---:|---:|---:|---:|---:|
| 6 | 989,0 | 10,97 | 81,0 | 2.059 | 69,4 °C | 36,5 W |
| 7 | 993,2 | 11,03 | 75,9 | 2.059 | 71,8 °C | 35,6 W |
| 8 | 978,2 | 10,98 | 74,6 | 2.068 | 73,6 °C | 35,3 W |
| 9 | 993,4 | 11,01 | 67,5 | 2.073 | 74,3 °C | 33,2 W |
| 10 | 996,6 | 11,03 | 64,6 | 2.073 | 75,1 °C | 32,6 W |

Resumen de las medias por caso:

- **CPU del proceso:** 990,1 % (aprox. 9,9 núcleos equivalentes según la convención de `psutil`).
- **RSS del proceso:** alrededor de 11,0 GB.
- **Utilización GPU:** 72,7 %.
- **VRAM:** 2.059–2.073 MiB; media de las cinco medias: 2.066 MiB.
- **Temperatura GPU:** media de las cinco medias: 72,8 °C; media máxima por caso: 75,1 °C.
- **Potencia GPU:** media de las cinco medias: 34,7 W.
- **Muestras:** 191 en total (29 + 30 + 36 + 43 + 53).

La RAM usada, RAM disponible, swap y E/S de disco son contadores del sistema; no deben atribuirse exclusivamente al proceso. En los casos publicados, la media por caso de RAM disponible se mantuvo alrededor de 11,33 GB. La media por caso de swap ocupado creció desde unos 589 MB (caso 6) hasta unos 756 MB (caso 10). El incremento de swap ocupado no demuestra por sí solo thrashing ni permite atribuir todo el intercambio al servidor. Los deltas de swap y disco son globales.

## 8. Calidad funcional

**No evaluada con la evidencia publicada.** El fragmento conserva contadores de caracteres de razonamiento y contenido, pero no las respuestas textuales originales. No es posible verificar aquí:

- si la implementación de `two_sum` es correcta;
- si `binary_search` devuelve índices correctos en los casos límite;
- si las explicaciones son coherentes;
- si los casos 7–10 terminan con soluciones completas;
- si el caso 6 quedó truncado antes de cerrar la solución.

No se asigna una puntuación funcional ni se declara aprobada la batería.

## 9. Límites y acciones necesarias para cerrar la campaña

1. Incorporar los registros de los casos 1–5.
2. Publicar `run_manifest.json`, `summary.jsonl`, los diez JSON originales de `responses/` y `resources/resource_samples.jsonl`.
3. Añadir logs del servidor y SHA-256 del modelo y del paquete de evidencia.
4. Inspeccionar las respuestas completas y ejecutar pruebas de corrección para `two_sum` y `binary_search`.
5. Verificar si el servidor aplicó el presupuesto de razonamiento, en lugar de inferirlo del valor enviado.
6. Mantener separadas las mediciones de prefill frío y caliente.

## 10. Evidencia publicada

- [Fragmento original de terminal: casos 6–10](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/evidence/terminal-tail-cases-06-10.txt)
- [SHA-256 del fragmento](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/evidence/terminal-tail-cases-06-10.txt.sha256)
- [Metodología NEPENTHES](tandem-qwen35-reasoning-budget-methodology-2026-11-12.md)
- [Plantilla de informe motor + modelo](NEPENTHES-engine-model-report-template.md)

**Conclusión:** la evidencia disponible confirma que el runner completó la batería de diez casos y permite cuantificar el rendimiento y la monitorización de los casos 6–10. No permite certificar la calidad funcional ni publicar estadísticas completas de los diez casos. La campaña queda documentada como ejecución completada con evidencia primaria parcial, pendiente de incorporar el directorio de resultados íntegro.
