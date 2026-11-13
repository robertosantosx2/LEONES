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

### Scripts específicos y procedimiento de uso

Los dos scripts están en el directorio `repro/`:

- [`run_NEPENTHES_cafe_independent_two_sum.py`](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_NEPENTHES_cafe_independent_two_sum.py): lanza una petición de prueba y registra la respuesta junto con la telemetría del host. **No arranca, detiene ni reconfigura el servidor**.
- [`inspect_NEPENTHES_cafe_independent_run.py`](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_NEPENTHES_cafe_independent_run.py): lee los ficheros guardados por el runner. No necesita que el servidor siga activo y no vuelve a ejecutar el modelo.

#### 1. Preparar el entorno

Clonar el repositorio (o actualizar la copia existente) y situarse en la rama que contiene este experimento:

~~~bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
git checkout benchmarks/tandem-qwen35-reasoning-battery-2026-11-12
git pull --ff-only
~~~

En una copia ya clonada, basta con:

~~~bash
cd /ruta/a/LEONES
git fetch origin
git switch benchmarks/tandem-qwen35-reasoning-battery-2026-11-12
git pull --ff-only
~~~

El runner requiere Python 3 y el monitor compartido `resource_monitor.py`, que debe existir en:

~~~text
artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/resource_monitor.py
~~~

Usa la biblioteca estándar de Python; no requiere instalar paquetes con pip.

#### 2. Comprobar el servidor existente

Antes de ejecutar el runner, inicia manualmente `cafe-llama.cpp` con el modelo y los parámetros que quieras evaluar. El script no lo inicia por ti. Comprueba que el endpoint responde:

~~~bash
curl -fsS http://127.0.0.1:18086/health
~~~

Localiza el PID del servidor:

~~~bash
pgrep -af 'llama-server.*18086'
~~~

Identifica el PID correcto y verifica que corresponde al ejecutable esperado:

~~~bash
PID=21313
readlink -f "/proc/$PID/exe"
tr '\0' ' ' < "/proc/$PID/cmdline"
echo
~~~

Sustituye `21313` por el PID real. No uses un PID antiguo sin comprobarlo: puede haber sido reutilizado por otro proceso.

#### 3. Ejecutar la prueba Nepenthes

Desde el directorio `repro/`, ejecuta:

~~~bash
cd artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro

python3 run_NEPENTHES_cafe_independent_two_sum.py \
  --pid "$PID" \
  --base-url http://127.0.0.1:18086 \
  --port 18086 \
  --model "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
  --output "$HOME/cafe-llama.cpp-qwen35-nepenthes-$(date +%Y%m%d-%H%M%S)"
~~~

Parámetros:

- `--pid`: obligatorio; PID del proceso `llama-server` que ya está atendiendo la petición.
- `--base-url`: URL base de la API OpenAI-compatible. Por defecto, `http://127.0.0.1:18086`.
- `--port`: puerto que utiliza el monitor de recursos; debe corresponder al servidor probado.
- `--model`: ruta del GGUF; por defecto apunta al Qwen3.5-35B-A3B IQ2_XXS indicado en este informe.
- `--output`: directorio nuevo para esta ejecución. No reutilices un directorio con contenido: el runner se niega a sobrescribir evidencias.
- `--max-tokens`, `--reasoning-budget-tokens` y `--timeout`: permiten cambiar el máximo de generación, el campo de presupuesto enviado y el tiempo límite. El valor predeterminado de presupuesto es 128; enviarlo no demuestra que el servidor lo aplique.
- `--monitor-script`: opcional; permite indicar otra ruta al `resource_monitor.py` si no está en la ubicación del repositorio documentada arriba.

La tarea enviada es una implementación de `two_sum` en Python con complejidad O(n), números negativos, duplicados, índices distintos y resultado `None` cuando no hay solución. El runner usa temperatura 0, `reasoning_format=deepseek`, `enable_thinking=true` y `stream=false`.

#### 4. Inspeccionar los resultados

Copia la ruta exacta que imprimió el runner y pásala al inspector:

~~~bash
python3 inspect_NEPENTHES_cafe_independent_run.py \
  "$HOME/cafe-llama.cpp-qwen35-nepenthes-AAAAMMDD-HHMMSS"
~~~

Para mostrar también el texto final generado y el razonamiento que la API exponga por separado:

~~~bash
python3 inspect_NEPENTHES_cafe_independent_run.py \
  "$HOME/cafe-llama.cpp-qwen35-nepenthes-AAAAMMDD-HHMMSS" \
  --show-content
~~~

El inspector no modifica los datos. Informa de identidad de ejecución, build, modelo, tiempos, tokens, métricas de recursos y número de muestras de monitorización.

#### 5. Ficheros que produce el runner

Dentro del directorio indicado con `--output`:

- `manifest.json`: configuración, identidad del proceso, `/health`, `/props`, petición enviada y notas de interpretación.
- `responses/independent-two-sum.json`: respuesta íntegra, métricas derivadas, errores si los hubiera y resumen de recursos.
- `resources/resource_samples.jsonl`: muestras temporales de monitorización.

Conserva el directorio completo para reproducibilidad. No edites manualmente los JSON originales; si necesitas anotaciones, guárdalas en un fichero separado. El script de inspección requiere los tres ficheros anteriores.

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


## Estructura reutilizable de Nepenthes: motor + modelo

Nepenthes identifica la **metodología de ensayo**. Cada ejecución queda identificada por el par concreto **motor + modelo**; el motor es el runtime evaluado (por ejemplo, `cafe-llama.cpp` o `Tandem.cpp`) y el modelo es el artefacto exacto (familia, tamaño, cuantización y hash cuando esté disponible).

La documentación se organiza en tres niveles:

1. **Metodología:** este documento define el protocolo común, las variables, los controles, la telemetría y el uso de los scripts.
2. **Plantilla motor + modelo:** [NEPENTHES-engine-model-report-template.md](NEPENTHES-engine-model-report-template.md). Se copia para cada nueva combinación y obliga a registrar identidad del motor, identidad del modelo, configuración, ejecución, resultados, calidad y limitaciones.
3. **Informe de ejecución:** un documento concreto por combinación y campaña. Como primer ejemplo, [cafe-llama.cpp + Qwen3.5-35B-A3B · 2026-11-13](nepenthes-cafe-llama.cpp-qwen3.5-35b-a3b-2026-11-13.md).

### Convención de identificación

Usar siempre el formato:

`NEPENTHES_<MOTOR>_<MODELO>_<AAAAMMDD>`

El nombre legible del informe debe expresar ambos componentes, por ejemplo: **cafe-llama.cpp + Qwen3.5-35B-A3B**. No crear un informe llamado únicamente por el modelo o únicamente por el motor.

### Scripts y flujo operativo

- `run_NEPENTHES_*.py`: ejecuta la petición o batería contra un servidor ya iniciado, recoge respuesta y telemetría, y crea un directorio de evidencia nuevo. Nunca inicia, detiene ni reconfigura el motor.
- `inspect_NEPENTHES_*.py`: lee el directorio de evidencia creado por el runner, presenta métricas y permite mostrar el contenido. No vuelve a consultar el servidor ni modifica los resultados.
- Los scripts específicos del motor pueden variar en argumentos y tareas. La plantilla y el informe deben documentar siempre el comando exacto empleado, incluyendo PID/endpoint, ruta del modelo, directorio de salida y versión del script.
- Antes de repetir una prueba, usar un directorio de salida nuevo. No sobrescribir ni editar los JSON originales.

Ejemplo para esta campaña cafe-llama.cpp:

```bash
python3 run_NEPENTHES_cafe_independent_two_sum.py \
  --pid "$PID" \
  --base-url http://127.0.0.1:18086 \
  --port 18086 \
  --model "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
  --output "$HOME/cafe-llama.cpp-qwen35-nepenthes-$(date +%Y%m%d-%H%M%S)"
```

Inspección del resultado:

```bash
python3 inspect_NEPENTHES_cafe_independent_run.py \
  "$HOME/cafe-llama.cpp-qwen35-nepenthes-AAAAMMDD-HHMMSS" \
  --show-content
```

El informe de cada par debe enlazar el script runner, el inspector y el directorio/archivo de evidencia preservado. No se deben trasladar cifras de una combinación motor/modelo a otra ni presentar campañas independientes como comparación controlada.
