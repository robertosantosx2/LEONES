# NEPENTHES · Tandem.cpp + Qwen3.5-35B-A3B · batería independiente completa · 2026-11-13

**ID:** `NEPENTHES_Tandem.cpp_Qwen3.5-35B-A3B-IQ2_XXS_20261113`  
**Tipo:** ejecución independiente de la batería NEPENTHES de 10 casos  
**Ejecución del runner:** 10/10 casos completados  
**Evidencia primaria:** completa para esta ejecución: manifiesto, diez respuestas originales, resumen y 255 muestras de recursos.

> **Criterio de lectura:** que el runner complete una petición no equivale a que la respuesta sea completa ni funcionalmente correcta. Cuatro casos terminaron con `finish_reason=length`; seis terminaron con `stop`. La revisión funcional de este informe es una inspección estática de las respuestas guardadas: no se ejecutó el código Python generado por el modelo.

## 1. Objetivo y alcance

Registrar una ejecución instrumentada de la batería de razonamiento de Qwen3.5-35B-A3B IQ2_XXS con **Tandem.cpp**, utilizando la metodología **Nepenthes**. La batería contiene diez casos secuenciales: tres preguntas aritméticas, cinco ejercicios `two_sum` y dos ejercicios `binary_search`, con distintos presupuestos solicitados y límites de generación.

Esta campaña es independiente. No es una comparación A/B controlada con `cafe-llama.cpp`; las diferencias de motor, caché, secuencia y estado del sistema impiden una comparación directa.

## 2. Motor y servidor

- **Motor:** `Tandem.cpp`
- **Repositorio local:** `~/Descargas/tandem-research/engines/tandem.cpp`
- **Build registrado:** `0.8.0-dev`, build `11962`; submódulo llama.cpp `f5222f25c18da062ab2b8a2dbbfbf4feae398566`.
- **Endpoint:** `http://127.0.0.1:18085`
- **PID monitorizado:** `10314`
- **Modelo servido:** `$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`

Argumentos de inicio registrados:

```bash
-m "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
--host 127.0.0.1 --port 18085 \
-c 2048 -b 128 -ub 64 -t 8 -tb 8 -ngl 99 \
--cpu-moe --moe-cache-mib 512 -np 1
```

El servidor ya estaba iniciado antes del runner. El runner no inicia, detiene ni reconfigura el servidor.

## 3. Modelo y plataforma

- **Modelo:** Qwen3.5-35B-A3B, arquitectura `qwen35moe`; 35B parámetros totales y aproximadamente 3B activos.
- **Expertos:** 256 totales; 8 activos por token.
- **Cuantización:** IQ2_XXS, 2,0625 bpw.
- **Archivo:** `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`, 10.665.148.928 bytes (aprox. 9,94 GiB).
- **SHA-256 del modelo:** no incluido en el manifiesto.

Plataforma: MSI Thin 15 B12UC; Ubuntu; Intel Core i7-12650H; 14 GiB RAM; 32 GiB swap; NVIDIA GeForce RTX 3050 Laptop con 4 GiB VRAM (sm_86); driver 580.178.04; CUDA runtime 13.0 y toolkit 13.4.92.

## 4. Protocolo y evidencia

- Diez peticiones secuenciales, un slot.
- Temperatura 0; streaming desactivado.
- `reasoning_format=deepseek`; `enable_thinking=true`.
- Presupuestos solicitados por caso: 64, 128 o 256 tokens; límites de salida entre 256 y 1.536 tokens.
- Runner: `run_battery.py`; `--server-pid 10314`, `--monitor-interval 1`, `--timeout 900`, pausa de 1 segundo.
- Inicio: `2026-11-13T23:50:38.027082+01:00`; fin: `2026-11-13T23:54:02.079131+01:00`.
- El manifiesto conserva `/health`, `/props`, configuración enviada y orden de casos.
- Evidencia primaria: diez JSON originales, `summary.jsonl`, `run_manifest.json`, `resources/resource_samples.jsonl` (255 muestras) y `SHA256SUMS`.

Enviar `reasoning_budget_tokens` no demuestra que el motor aplique un límite semántico efectivo al razonamiento. Se trata como parámetro solicitado, no como enforcement verificado.

## 5. Resultados cuantitativos de los diez casos

| Caso | Tarea | Budget | max_tokens | Prompt | Cacheados | Generados | Prefill tok/s | Generación tok/s | finish |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | arithmetic | 64 | 256 | 29 | 25 | 70 | 54,48 | 37,93 | `stop` |
| 2 | arithmetic | 128 | 384 | 29 | 25 | 384 | 56,45 | 31,92 | `length` |
| 3 | arithmetic | 256 | 512 | 29 | 25 | 262 | 56,35 | 36,66 | `stop` |
| 4 | two_sum | 128 | 512 | 93 | 0 | 512 | 97,53 | 35,26 | `length` |
| 5 | two_sum | 128 | 768 | 93 | 89 | 768 | 62,50 | 36,71 | `length` |
| 6 | two_sum | 256 | 1.024 | 93 | 89 | 1.024 | 50,81 | 36,67 | `length` |
| 7 | two_sum | 128 | 1.536 | 93 | 89 | 1.016 | 53,50 | 33,97 | `stop` |
| 8 | two_sum | 256 | 1.536 | 93 | 89 | 1.158 | 59,94 | 32,34 | `stop` |
| 9 | binary_search | 128 | 1.536 | 188 | 0 | 1.249 | 139,42 | 29,65 | `stop` |
| 10 | binary_search | 256 | 1.536 | 188 | 184 | 1.500 | 58,11 | 27,93 | `stop` |

Totales y agregados:
- **Tokens generados:** 7.943.
- **Tasa de generación media simple por petición:** 33,90 tok/s.
- **Mediana de las diez tasas por petición:** 34,61 tok/s.
- **Tasa agregada tokens/tiempo de generación** (suma de tokens dividida por suma de tiempos de generación): 32,30 tok/s.
- **Rango de tasas por petición:** 27,93–37,93 tok/s.
- **Finalización:** 6 `stop`; 4 `length` (casos 2, 4, 5 y 6).

Las tres medidas de tasa no son intercambiables: la media y mediana resumen tasas por petición; la tasa agregada pondera por tiempo de generación. Ninguna incorpora el prefill como si fuera tiempo de generación.

### Caché y prefill

Tokens cacheados por caso: 25/29 en casos 1–3; 0/93 en caso 4; 89/93 en casos 5–8; 0/188 en caso 9; 184/188 en caso 10. Los casos no son mediciones homogéneas de prefill frío. El caso 9 es el único prompt completo sin caché entre los dos casos de búsqueda binaria; el caso 10 es mayoritariamente cacheado. No se debe atribuir la diferencia de prefill exclusivamente al motor.

## 6. Inspección funcional de las respuestas originales

La siguiente clasificación procede de leer `response.choices[0].message.content` y `reasoning_content` de los diez JSON. No equivale a ejecutar las pruebas propuestas.

| Caso | Resultado de inspección | Evaluación |
|---:|---|---|
| 1 | Responde `391` a 17 × 23. | Correcto y breve. |
| 2 | Alcanza 384 tokens; `finish_reason=length`. El contenido queda mezclado con razonamiento y termina a mitad de una alternativa, aunque el razonamiento acaba calculando 391. | Incompleto; no cuenta como respuesta válida. |
| 3 | Responde `391` a 17 × 23. | Correcto; salida final concisa. |
| 4 | Código `two_sum` cortado durante la rama de almacenamiento del diccionario. | Truncado; no se puede validar la implementación completa. |
| 5 | Código y respuesta cortados al llegar a 768 tokens, durante la explicación de las pruebas. | Truncado; no se puede validar la entrega completa. |
| 6 | Código y explicación cortados al llegar a 1.024 tokens, antes de terminar la explicación/pruebas. | Truncado; no se puede validar la entrega completa. |
| 7 | Implementación completa con hash map, negativos, duplicados y caso sin solución; ejemplos coherentes. | Correcto por inspección estática; pruebas no ejecutadas. |
| 8 | Implementación completa de hash map y casos positivo, negativo, duplicados y sin solución. Un comentario inline da inicialmente una suma errónea y se corrige en el propio texto. | Código aparentemente correcto; defecto menor de calidad en el comentario de prueba. |
| 9 | Identifica `left = mid` como causa del bucle infinito y corrige a `left = mid + 1`; incluye casos límite. | Correcto por inspección estática; pruebas no ejecutadas. |
| 10 | Misma corrección, con implementación completa y pruebas para presente, ausente, lista vacía y un elemento. | Correcto por inspección estática; 1.500 tokens generados de 1.536, aunque terminó con `stop`. |

**Balance funcional prudente:** seis respuestas terminaron con `stop`; cinco de ellas son correctas en contenido/código por inspección y la sexta (caso 8) tiene un comentario de prueba contradictorio que se corrige en el texto. Los cuatro casos con `length` están truncados. No se declara un porcentaje de tests aprobados porque el código generado no se ejecutó en un entorno de pruebas independiente.

## 7. Monitorización de recursos

El monitor registró **255 muestras** en total (casos 1–10: 3, 13, 9, 17, 22, 29, 30, 36, 43 y 53). La tabla resume medias por petición. Los agregados siguientes son medias simples de las diez medias por caso, no medias ponderadas por número de muestras.

| Caso | CPU proceso % | RSS medio (GiB) | GPU % | VRAM (MiB) | Temp. GPU | Potencia |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 953,7 | 9,30 | 57,3 | 1.981 | 49,3 °C | 24,2 W |
| 2 | 888,5 | 9,41 | 78,6 | 2.020 | 54,6 °C | 28,5 W |
| 3 | 977,4 | 9,62 | 76,4 | 2.048 | 58,7 °C | 29,9 W |
| 4 | 948,9 | 9,88 | 74,2 | 2.058 | 61,8 °C | 31,9 W |
| 5 | 986,9 | 10,11 | 76,7 | 2.059 | 65,8 °C | 34,7 W |
| 6 | 989,0 | 10,22 | 81,0 | 2.059 | 69,4 °C | 36,5 W |
| 7 | 993,2 | 10,27 | 75,9 | 2.059 | 71,8 °C | 35,6 W |
| 8 | 978,2 | 10,23 | 74,6 | 2.068 | 73,6 °C | 35,3 W |
| 9 | 993,4 | 10,26 | 67,5 | 2.073 | 74,3 °C | 33,2 W |
| 10 | 996,6 | 10,28 | 64,6 | 2.073 | 75,1 °C | 32,6 W |

Medias simples de las diez medias por caso: **970,6 % CPU del proceso**, **9,96 GiB RSS**, **72,7 % GPU**, **2.050 MiB VRAM**, **65,4 °C** y **32,2 W**. CPU >100 % representa uso de varios núcleos según la convención de psutil.

La ocupación media de swap por caso aumenta a lo largo de la secuencia (aprox. 26,7 MiB en el caso 1 a 720,6 MiB en el caso 10). RAM usada/disponible, swap y E/S de disco son contadores del sistema; los deltas no se pueden atribuir solo al proceso. El crecimiento de swap ocupado no demuestra por sí solo thrashing.

Las muestras de los primeros casos son escasas (3–9) porque las respuestas fueron breves; sus medias son menos estables que las de peticiones largas. Por eso se publican los recuentos y se evita tratar cada media por caso como igualmente precisa.

## 8. Limitaciones y conclusiones

1. La batería ejecutó las diez peticiones, pero cuatro salidas quedaron truncadas por el límite de generación.
2. La calidad funcional se evaluó mediante inspección estática; no se ejecutaron los fragmentos Python ni sus asserts.
3. El presupuesto de razonamiento fue enviado por el cliente, pero no se ha demostrado que el servidor lo impusiera.
4. La caché de prompt varía sustancialmente; las tasas de prefill no son directamente comparables entre todos los casos.
5. Los agregados de recursos se basan en medias por petición y el número de muestras varía.
6. No se incluye SHA-256 del modelo ni log completo del servidor.

**Conclusión:** esta ejecución ofrece ahora evidencia primaria completa y auditable de los diez casos. El rendimiento agregado de generación fue 32,30 tok/s (tokens totales / tiempo total de generación), con una media simple por petición de 33,90 tok/s. El runner completó 10/10, pero solo seis respuestas terminaron con `stop`; cuatro quedaron truncadas. La inspección estática considera correctas cinco respuestas completas y señala un defecto menor de comentario en la sexta. No se declara validación funcional automatizada ni aprobación global de la batería.

## 9. Evidencia publicada

- [Directorio completo de la ejecución](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/full-run/)
- [Manifiesto](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/full-run/run_manifest.json)
- [Resumen de los diez casos](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/full-run/summary.jsonl)
- [Respuestas originales](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/full-run/responses/)
- [Muestras de recursos](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/full-run/resources/resource_samples.jsonl)
- [Inventario SHA-256](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/full-run/SHA256SUMS)
- [Metodología Nepenthes](tandem-qwen35-reasoning-budget-methodology-2026-11-12.md)
- [Plantilla de informe motor + modelo](NEPENTHES-engine-model-report-template.md)
