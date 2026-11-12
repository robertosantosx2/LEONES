# NEPENTHES : Metodología reproducible · Tandem.cpp / Qwen3.5-35B-A3B · 2026-11-12

**Estado:** documentación y scripts publicados. Los logs binarios/JSON originales y la captura integral del host se incorporarán cuando se ejecute el recolector en el MSI.

## Objetivo

Separar dos variables en experimentos comparables:

1. **Mismo motor, modelo diferente:** conservar el motor, build, parámetros del servidor y host; cambiar solo el modelo.
2. **Mismo modelo, motor diferente:** conservar exactamente el GGUF y el host; cambiar el motor. Configurar el motor alternativo con el mismo contexto, plantilla, cuantización y parámetros equivalentes.

El runner no arranca, detiene ni reconfigura procesos. Solo envía peticiones a un endpoint OpenAI-compatible ya iniciado.

## Batería fija

Las peticiones usan temperature 0, stream false, reasoning_format deepseek y enable_thinking true.

| Tarea | Presupuesto | max_tokens |
|---|---:|---:|
| Aritmética 17 × 23 | 64 | 256 |
| Aritmética 17 × 23 | 128 | 384 |
| Aritmética 17 × 23 | 256 | 512 |
| two_sum | 128 | 512 |
| two_sum | 128 | 768 |
| two_sum | 256 | 1024 |
| two_sum | 128 | 1536 |
| two_sum | 256 | 1536 |
| binary_search | 128 | 1536 |
| binary_search | 256 | 1536 |

Los prompts literales están embebidos en run_battery.py. La matriz reproduce las combinaciones distintas registradas en la campaña; las repeticiones que devolvieron el mismo ID no se cuentan como muestras independientes.

## Scripts

Todos están en el directorio repro de este archivo de experimento:

- [run_battery.py](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_battery.py): cliente común. Guarda el JSON completo de cada petición/respuesta, summary.jsonl, run_manifest.json y captura /health y /props.
- [repeat_same_engine_new_model.sh](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/repeat_same_engine_new_model.sh): cambia el modelo manteniendo el endpoint/motor.
- [repeat_same_model_new_engine.sh](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/repeat_same_model_new_engine.sh): cambia el motor manteniendo el GGUF.
- [collect_evidence.sh](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/collect_evidence.sh): copia logs y metadatos existentes y captura sistema, GPU, CUDA, proceso y commits. Genera tar.gz y SHA256SUMS.

## Requisitos

- Ubuntu/Linux.
- Python 3.10 o posterior (solo biblioteca estándar).
- curl, tar, sha256sum, lscpu, free, swapon; nvidia-smi y nvcc cuando estén instalados.
- Servidor ya iniciado con API compatible OpenAI.
- El modelo debe estar cargado antes de ejecutar la batería.

## A. Repetir con el mismo motor y otro modelo

Ejemplo para un modelo diferente servido por Tandem.cpp en el endpoint existente:

~~~bash
cd /ruta/al/directorio/repro

MODEL_ID='alias-del-modelo-en-la-API' \
MODEL_PATH="$HOME/models/otro-modelo.gguf" \
BASE_URL='http://127.0.0.1:18086' \
ENGINE_LABEL='tandem.cpp' \
bash repeat_same_engine_new_model.sh
~~~

No se debe cambiar el build, la configuración del servidor ni el entorno durante la comparación. Registrar cualquier diferencia inevitable (contexto máximo admitido, plantilla, offload, cuantización o caché).

## B. Repetir con el mismo modelo y otro motor

Primero, iniciar manualmente el motor alternativo y cargar el mismo archivo GGUF. Después:

~~~bash
cd /ruta/al/directorio/repro

BASE_URL='http://127.0.0.1:PUERTO' \
ENGINE_LABEL='nombre-y-version-del-otro-motor' \
MODEL_ID='alias-del-modelo-en-la-API' \
MODEL_PATH="$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
bash repeat_same_model_new_engine.sh
~~~

El servidor alternativo debe aceptar las extensiones de la API usadas por la batería: reasoning_format, reasoning_budget_tokens y chat_template_kwargs.enable_thinking. Si no las implementa, el script registrará el error; no se debe considerar una comparación equivalente.

## Captura de evidencia local

Ejecutar en el MSI:

~~~bash
bash collect_evidence.sh
~~~

El recolector guarda los logs qwen35 existentes, logs de build, estado del sistema, nvidia-smi, nvcc, versiones, estado del endpoint y commits. No copia pesos GGUF ni detiene servicios. Para calcular también SHA-256 del GGUF (lectura completa del fichero, aproximadamente 10 GiB):

~~~bash
HASH_MODEL=1 bash collect_evidence.sh
~~~

El resultado es un directorio, un archivo .tar.gz y su checksum. Adjuntar el .tar.gz a la conversación para incorporar los artefactos binarios originales a LEONES. No reemplazar archivos ausentes con ficheros vacíos.

## Métricas a comparar

Por cada respuesta: prompt_tokens, completion_tokens, cached_tokens, prompt_ms, predicted_ms, prompt_per_second, predicted_per_second, finish_reason, contenido final, longitud de reasoning_content, ID de respuesta y errores HTTP. Mantener por separado el prefill frío y caliente; no mezclar cache hits con muestras independientes.

Para resultados robustos, ejecutar al menos tres repeticiones independientes por caso, con IDs diferentes, y publicar mediana, rango y desviación. Esta recomendación de repetición es para futuras campañas; los resultados originales de 2026-11-12 no se deben presentar como tres repeticiones si no lo fueron.

## Control de variables

- Fijar modelo y SHA-256 (cuando se calcule), motor/commit/build y argumentos.
- Fijar temperatura, prompt, presupuesto de razonamiento y max_tokens.
- Fijar contexto, batch, ubatch, threads, GPU layers, CPU-MoE, caché y plantilla.
- Registrar RAM, swap, VRAM, temperatura, driver, CUDA, kernel y procesos competidores.
- No ejecutar ambas pruebas simultáneamente.
- No comparar salidas truncadas como respuestas completas.
- No inferir hit rate de caché de expertos a partir del tamaño configurado.

## Seguridad y límites

Los scripts solo interactúan con servidores que el operador ya ha iniciado. No contienen lógica para matar procesos, descargar modelos ni cambiar parámetros del servidor. Los pesos del modelo no se suben al repositorio.

## Ejecución independiente adicional: cafe-llama.cpp · 2026-11-13

Se añadió una ejecución exploratoria del mismo GGUF Qwen3.5-35B-A3B-IQ2_XXS mediante **cafe-llama.cpp**, usando la metodología Nepenthes. Esta ejecución se registra como una prueba independiente y no como una comparación controlada de motores: el prefill tuvo 89/93 tokens en caché y la configuración/extensiones de API no están demostradas como equivalentes a Tandem.cpp.

### Scripts específicos

- [run_cafe_independent_two_sum.py](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_cafe_independent_two_sum.py): ejecuta una única petición two_sum contra un servidor cafe-llama.cpp ya iniciado. Captura /health, /props, identidad del proceso, petición y respuesta completas, y monitorización mediante el resource_monitor compartido. No inicia, detiene ni reconfigura el servidor. Requiere indicar --pid y proporciona opciones para endpoint, modelo y directorio de salida.
- [inspect_cafe_independent_run.py](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_cafe_independent_run.py): inspecciona un resultado ya guardado sin realizar peticiones al servidor; puede mostrar el contenido final y el razonamiento con --show-content.

Ejemplo de ejecución (adaptar PID, endpoint y rutas al servidor ya iniciado):

~~~bash
python3 run_cafe_independent_two_sum.py \
  --pid 21313 \
  --base-url http://127.0.0.1:18086 \
  --port 18086 \
  --model "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
  --output "$HOME/cafe-llama.cpp-qwen35-independent-YYYYMMDD"
~~~

Inspección posterior:

~~~bash
python3 inspect_cafe_independent_run.py \
  "$HOME/cafe-llama.cpp-qwen35-independent-YYYYMMDD" \
  --show-content
~~~

### Resultado registrado (ejecución 2026-11-13)

- Estado: HTTP correcto, `finish_reason=stop`, sin error de petición.
- Entrada/salida: 93 tokens de prompt, 1.060 tokens generados; 89 tokens de prompt reportados como caché.
- Velocidad reportada: 26,62 tok/s de prompt y 31,03 tok/s de generación. El valor de prompt no es una medición fría: la mayoría de los tokens estaban en caché.
- GPU: utilización media 89,8 %, VRAM estable 2.001 MiB, temperatura media 55,86 °C y potencia media 32,21 W.
- CPU del proceso: media 99,74 %; CPU del sistema: media 6,97 %.
- Swap-in del sistema: 90.112 bytes; swap-out: 0 bytes. Los contadores de swap y disco son de sistema y no se atribuyen exclusivamente al proceso.
- Calidad: implementación two_sum con hash map correcta en O(n), negativos, duplicados y separación de índices. La respuesta contiene dos errores editoriales en las pruebas: el caso rotulado como duplicados usa [3, 2, 4], y un comentario de la prueba negativa muestra primero una suma incorrecta antes de explicar el resultado correcto.
- `reasoning_budget_tokens=128` fue enviado en la petición; la aceptación del campo no demuestra que el servidor aplicase ese límite.

Los datos originales de esta ejecución deben permanecer en su directorio de evidencia y añadirse al repositorio como artefactos, junto con manifest, respuesta íntegra, muestras de recursos, logs y hashes. Los scripts anteriores permiten repetir y revisar el experimento; no sustituyen esos datos originales.

### Interpretación comparativa

Los resultados de Tandem.cpp y cafe-llama.cpp se mantienen como campañas separadas. No calcular una clasificación de rendimiento ni atribuir diferencias al motor hasta disponer de repeticiones independientes y condiciones equiparadas, especialmente caché de prompt, plantilla, extensiones de razonamiento, contexto y parámetros de ejecución.
