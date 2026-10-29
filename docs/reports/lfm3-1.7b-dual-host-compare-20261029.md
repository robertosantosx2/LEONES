# LFM3-1.7B: comparación de compilaciones y diagnóstico de salida en dos equipos

**Fecha de registro:** 2026-10-29  
**Estado:** evaluación experimental; no se ha recompilado ningún motor como resultado de este análisis.  
**Modelo:** `LiquidAI/LFM3-1.7B-GGUF:Q4_K_M`  
**Formato:** GGUF Q4_K_M.

## Resumen ejecutivo

Se han contrastado las dos compilaciones recientes de `llama.cpp` utilizadas para probar LFM3-1.7B: una en el MSI con NVIDIA RTX 3050 de 4 GB y otra en un equipo Intel Core i7-5500U con Intel HD Graphics 5500. La comparación de historial confirma que la revisión Intel está 30 commits por delante de la revisión MSI. Ambas revisiones son posteriores a la incorporación del soporte base para LFM3-1.7B.

La ejecución en CPU Intel funciona, pero las pruebas muestran inconsistencias de formato en algunas respuestas: la capital aparece como `Berlin</think>Berlin`, mientras que la extracción exacta mejoró tras cambiar las opciones de razonamiento. No hay evidencia suficiente para atribuir el comportamiento a la diferencia entre commits. **No se recomienda recompilar todavía**: primero debe aislarse el efecto de la plantilla de chat, el formato de razonamiento y los límites de generación.

## 1. Equipos y revisiones

| Campo | MSI / CUDA | Equipo Intel / CPU |
|---|---|---|
| Sistema | Ubuntu; detalles en el informe CUDA vinculado | Ubuntu 26.04.1, kernel 7.0.0-38-generic |
| CPU | MSI Thin 15 B12UC, Intel i7-12650H | Intel Core i7-5500U, 2 núcleos / 4 hilos |
| GPU | NVIDIA RTX 3050 Laptop, 4 GB VRAM | Intel HD Graphics 5500 |
| Revisión llama.cpp | `c3df4b7e22a1ac38da663552d19e649dd97ca936` | `0893ec98f5eafad36a43a72cd1c3723d72b0d03a` |
| Fecha del trabajo | 2026-10-28 | 2026-10-29 |
| Evidencia de ejecución | Informe y artefactos del benchmark CUDA ya existentes en LEONES | Informes locales de batería y corrección de plantilla descritos más abajo |

- Informe MSI previo: [LFM3-1.7B RTX 3050 CUDA](lfm3-1.7b-rtx3050-cuda-20261028.md).
- Revisión MSI: [c3df4b7](https://github.com/ggml-org/llama.cpp/commit/c3df4b7e22a1ac38da663552d19e649dd97ca936).
- Revisión Intel: [0893ec9](https://github.com/ggml-org/llama.cpp/commit/0893ec98f5eafad36a43a72cd1c3723d72b0d03a).
- Comparación exacta: [c3df4b7...0893ec9](https://github.com/ggml-org/llama.cpp/compare/c3df4b7e22a1ac38da663552d19e649dd97ca936...0893ec98f5eafad36a43a72cd1c3723d72b0d03a).

La comparación de GitHub devuelve `ahead_by=30`, `behind_by=0`: la revisión Intel contiene 30 commits posteriores y no diverge de la revisión MSI en la historia comparada. El diff abarca varias áreas (incluidas carga/modelado, CUDA, OpenCL, SYCL, Metal y otros backends); el recuento por sí solo no demuestra que esos cambios mejoren la ejecución de LFM3-1.7B.

## 2. Confirmación de soporte de LFM3

El historial público contiene la incorporación de LFM3-1.7B y LFM3-VL-2B en [19cce691](https://github.com/ggml-org/llama.cpp/commit/19cce6919992fdffd92e0ac152caaf1e2b8f254e). El soporte base, por tanto, ya estaba presente antes de las dos revisiones comparadas. La incorporación posterior de LFM3-Audio-2B y LFM3-Omni-2B está registrada en [19ff817](https://github.com/ggml-org/llama.cpp/commit/19ff817fb25e9a1b838b1d7f9f4325f7bf9779c4); no debe confundirse ese soporte de modelos adicionales con una corrección demostrada para la salida de LFM3-1.7B.

## 3. Equipo Intel: entorno observado

- Repositorio de trabajo: `/home/roberto/lfm3-1.7b-llamacpp/llama.cpp`.
- Versión informada por el entorno: `0.8.0-dev`, build 1.
- Commit: `0893ec98f5eafad36a43a72cd1c3723d72b0d03a`.
- Configuración informada: CMake Release, `GGML_NATIVE=ON`, `GGML_OPENMP=ON`, `GGML_AVX2=OFF`.
- Servidor: `127.0.0.1:8080`, estado `ok`; RSS observado alrededor de 1,9 GB.
- Alias de modelo: `LiquidAI/LFM3-1.7B-GGUF:Q4_K_M`.
- Ruta del modelo resuelta por las propiedades del servidor: `/home/roberto/.cache/huggingface/hub/models--LiquidAI--LFM3-1.7B-GGUF/snapshots/bad5729bba61d076fff20d2548e62526665af215/LFM3-1.7B-Q4_K_M.gguf`.
- Opciones relevantes del lanzador tras la corrección: `--reasoning off`, `--no-reasoning-preserve`, `--reasoning-format deepseek`, contexto 2048, 4 hilos y temperatura 0,1.
- Se retiró el argumento obsoleto `--chat-template-kwargs '{"enable_thinking":false,"preserve_thinking":false}'`; se conserva una copia de seguridad del lanzador en el equipo Intel.

## 4. Batería inicial de 24 peticiones

Evidencia local registrada en el equipo Intel:
`/home/roberto/lfm3-1.7b-llamacpp/reports/battery-20261029-183727`.

La batería tenía 8 pruebas con 3 repeticiones cada una (24 peticiones API). Los resultados resumidos de esa ejecución fueron:

| Prueba | Observación registrada | Evaluación |
|---|---|---|
| Capital en español | `Berlín.</think>Berlín.` en las tres repeticiones | Respuesta duplicada / marcador de razonamiento visible |
| Capital en inglés | `Berlin</think>Berlin` en las tres repeticiones | Respuesta duplicada / marcador visible |
| Multiplicación 17 × 23 | Razonamiento largo, con cálculo incorrecto o confuso, truncado al límite de 64 tokens | No superar como prueba de exactitud |
| Extracción exacta | `rojo verde azul</think>rojo verde azul` | Contenido repetido |
| Resta 12 − 5 | `9` en las tres repeticiones | Incorrecta |
| Explicación RAM/SSD | Explicación razonable, seguida de `</think>` y repetición; truncada a 100 tokens | Contenido razonable, formato incorrecto |
| Resumen | Resumen de una frase, 35 tokens, consistente | Resultado funcional en esa tarea |
| Explicación AVX2 | Explicación razonable, truncada a 80 tokens | Resultado parcial por límite de generación |

Velocidades agregadas informadas para esta batería: generación media aproximada de 15 tokens/s y prefill de aproximadamente 33,56 tokens/s. Son valores observados en esta ejecución y no deben interpretarse como una comparación controlada entre hardware, revisiones o motores.

Propiedades del servidor guardadas localmente en:
`/home/roberto/lfm3-1.7b-llamacpp/reports/battery-20261029-183727/server-props.json`.

## 5. Prueba después del cambio de opciones de razonamiento

Resultados locales:
`/home/roberto/lfm3-1.7b-llamacpp/reports/template-fix-20261029-184239/results.json`.

| Prueba | Salida observada | Tiempo / tokens | Resultado |
|---|---|---|---|
| Capital de Alemania | `Berlin</think>Berlin` | 0,891 s; 4 tokens | Sigue duplicada |
| Extracción exacta | `rojo verde azul` | 1,013 s; 5 tokens | Correcta y limpia |
| 12 menos 5 | `12 - 5 = 7\n\n7` | 1,438 s; 10 tokens | Cálculo correcto, pero no respeta “solo el número” |
| 17 × 23 con explicación | Descomposición que empieza correctamente, truncada después de `17 × 20 =` | 5,738 s; límite 64 tokens | Inconclusa por truncación |

Tras el cambio se registró el aviso: `chat template supports preserving reasoning, consider enabling it via --reasoning-preserve`. No se debe asumir que habilitar esa opción resolverá el problema; debe probarse como variable independiente y con evidencia de salida completa.

## 6. Prueba directa con llama-cli

Se probó también el binario `llama-cli`, no solo el servidor API, con:
- `--reasoning off`
- `--no-reasoning-preserve`
- `--single-turn`
- semilla 42, temperatura 0,1 y límite de 64 tokens.

La salida de la pregunta por la capital fue `Berlin</think>Berlin`. La prueba informó aproximadamente 32,5 tokens/s de prompt y 16,0 tokens/s de generación. Esto confirma que el problema no parece exclusivo de la capa HTTP del servidor. No demuestra por sí solo si el origen está en la plantilla, el parser, el vocabulario/token especial o el comportamiento del modelo.

## 7. Conclusiones

1. **Las dos compilaciones reconocen LFM3-1.7B**; no hay evidencia de que falte soporte base en la revisión MSI.
2. **La revisión Intel es 30 commits posterior** a la revisión MSI. Eso no equivale a una mejora de calidad ni de rendimiento.
3. La ejecución CPU Intel funciona y ofrece una referencia útil, en torno a 15–16 tokens/s de generación en las pruebas registradas.
4. Las pruebas iniciales muestran errores aritméticos, respuestas repetidas y exposición de `</think>`; tras ajustar las opciones, la extracción exacta mejora, pero no todos los formatos quedan corregidos.
5. Las pruebas truncadas deben repetirse con límites suficientes; no se deben clasificar como fallo de razonamiento sin una salida completa.
6. No se ha ejecutado una prueba A/B idéntica en ambos equipos con el mismo prompt, modelo, parámetros, número de repeticiones y método de medición. Por ello, **no se deben comparar directamente las velocidades de ambos equipos**.
7. No se ha recompilado ni sustituido ningún binario como parte de este análisis.

## 8. Próximo protocolo experimental

- Mantener las compilaciones existentes y registrar sus hashes/binarios y configuración efectiva.
- Usar exactamente el mismo GGUF, prompts, semilla, temperatura, top-k, penalización, contexto y límite de salida cuando el hardware lo permita.
- Separar pruebas de CLI y API.
- Registrar tanto salida en bruto como salida parseada, motivo de finalización, tokens de prompt/generación, TTFT, prefill y velocidad de generación.
- Variar una sola opción cada vez: plantilla, `--reasoning off`, `--no-reasoning-preserve` y `--reasoning-preserve`; no combinar cambios sin identificar su efecto.
- Incluir pruebas de respuesta exacta (capital, extracción), aritmética con comprobación externa y tareas de explicación/resumen.
- Guardar logs completos, JSON originales, comandos exactos y SHA-256 en los artefactos del informe antes de extraer conclusiones de rendimiento.

## 9. Ubicación de evidencias

Los JSON y logs originales de la batería y del ajuste de plantilla están actualmente referenciados por rutas del equipo Intel en `/home/roberto/lfm3-1.7b-llamacpp/reports/`. Este informe conserva los resultados observados disponibles durante la revisión; los archivos originales del equipo remoto no se han copiado a este repositorio desde esta sesión. Cuando se incorporen al repositorio, conservar su contenido íntegro y generar `SHA256SUMS.txt`.

