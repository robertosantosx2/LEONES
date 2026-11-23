# NEPENTHES — protocolo de benchmark móvil para Xiaomi Mi 9T Pro

**Estado:** especificación de campaña PLANNED; no declara que NEPENTHES ya ejecute benchmarks Android.  
**Ámbito:** teléfono Android ARM64; captura externa mediante ADB/Termux y runner del runtime.  
**Relación con NEPENTHES:** adaptar y normalizar resultados en el esquema vigente tras inspeccionar el INDEX maestro y los contratos implementados. No crear una segunda fuente de prioridades ni asumir soporte de AIPerf/NVML en Android.

## 1. Principio

NEPENTHES conserva el protocolo, manifiesto, procedencia y análisis. El proceso de inferencia se ejecuta en el teléfono. ADB actúa como canal de control/recogida cuando está disponible; no se considera instrumentación interna del motor.

AIPerf es el runner primario NEPENTHES para endpoints OpenAI-compatible en el entorno donde esté soportado. No se declara AIPerf como runner móvil ni se presupone que pueda iniciar procesos Android. Para la primera campaña offline, usar el benchmark nativo del runtime (por ejemplo, llama-bench/llama-cli o harness Android) y un fixture fijo; importar después los resultados conservando originales y marcando la fuente.

## 2. Identidad de ejecución

Cada run debe registrar:
- schema_version, run_id, timestamp UTC y reloj monotónico si está disponible;
- device model, SoC confirmado/expected, RAM nominal y disponible;
- Android/API, ABI, kernel, build y root status (YES/NO/UNKNOWN);
- runtime, versión/commit, binario/APK SHA-256, backend y flags;
- modelo, revisión, formato, cuantización, tokenizer y SHA-256;
- contexto, batch, ubatch, threads, afinidad, GPU layers;
- prompt fixture ID/hash, input tokens, output tokens y stop condition;
- warm-up, repeticiones, duración y estado térmico;
- archivos de log, exit code y checksums.

Redactar seriales, IMEI, MAC, tokens, nombres de usuario y rutas personales. El device_id del benchmark será un alias estable definido por LEONES, no un identificador de hardware sensible.

## 3. Métricas y semántica

| Métrica | Unidad | Fuente / condición |
|---|---|---|
| TTFT | ms | Streaming con timestamp del primer token; si no, no reportar |
| Prefill throughput | tokens/s | tokens de entrada / tiempo prefill medido; documentar método |
| Decode throughput | tokens/s | tokens generados / tiempo de generación; separar warm-up |
| ITL | ms/token | timestamps por token; si no disponibles, omitir |
| Total latency | ms | reloj monotónico alrededor de petición |
| RSS peak | bytes/MiB | muestreo externo del proceso cuando sea accesible |
| Available RAM | bytes/MiB | snapshot antes/después; no confundir con RSS |
| Temperature | °C | sensor identificado; registrar ubicación/fuente |
| Thermal status | enum | Android thermal service cuando esté disponible |
| Battery delta | % | proxy grueso, nunca energía física |
| Energy | J / Wh | solo contador/medidor físico validado; documentar calibración |
| Errors | count | OOM, crash, timeout, throttling, exit code |

No rellenar campos no disponibles con cero. Usar null/unknown y describir limitación. No convertir porcentaje de batería en joules.

## 4. Diseño experimental mínimo

1. Confirmar dispositivo, estado de batería, temperatura y versión de runtime.
2. Cerrar apps prescindibles sin alterar políticas ni procesos del sistema.
3. Mantener brillo, conectividad, estado de carga y condiciones ambientales constantes; documentarlos.
4. Calentar el runtime/modelo con 3 ejecuciones no medidas.
5. Realizar al menos 5 repeticiones medidas por configuración.
6. Registrar cada petición y calcular mediana, media, desviación, MAD y P50/P95 cuando el tamaño de muestra lo permita.
7. Separar pruebas frías y sostenidas; repetir tras enfriamiento.
8. No ejecutar barridos paralelos ni cargas simultáneas.
9. Detener ante thermal status severo, OOM repetidos, reinicio, anomalía de batería o degradación del dispositivo.

## 5. Fixtures

Mantener prompts deterministas versionados en el repositorio, en español e inglés:
- generación corta de respuesta general;
- resumen de texto de longitud fija;
- extracción JSON con esquema;
- razonamiento aritmético sencillo con respuesta verificable.

Registrar hash del fixture, plantilla de chat, tokenizer y límites de salida. La comparación entre modelos distintos es de rendimiento y calidad, no solo tokens/s: incluir tasa de éxito de la tarea.

No almacenar contenido privado del usuario en fixtures.

## 6. Reglas de comparabilidad

Dos runs solo son comparables si se documentan diferencias de hardware, runtime, modelo, cuantización, tokenizer, prompt, longitudes, contexto, batch, concurrencia, estado térmico, energía y método de medición.

Para CPU vs GPU:
- mismo archivo de modelo/hash;
- mismo prompt y límites;
- misma versión del runtime;
- mismo contexto/batch;
- misma condición térmica inicial;
- backend efectivo demostrado en logs.

## 7. Artefactos

Paquete mínimo:
- manifest.json;
- device-inventory.txt redactado;
- runtime-version.txt;
- command.txt (sin secretos);
- model-metadata.json y SHA256SUMS;
- raw stdout/stderr;
- requests.jsonl o benchmark.jsonl;
- samples.csv;
- summary.json;
- thermal-and-battery.csv;
- checksums.sha256.

Conservar salida original además de cualquier normalización NEPENTHES. No declarar ausencia de eventos si la fuente no estaba disponible.

## 8. Integración futura

Antes de implementar un adaptador:
1. inspeccionar INDEX maestro NEPENTHES y contratos de datos existentes;
2. identificar formato de importación y CLI reales;
3. mapear unidades y semántica sin pérdida;
4. añadir fixtures y pruebas unitarias/contractuales;
5. documentar límites de telemetría Android y fuentes no disponibles;
6. mantener la ruta actual de escritorio sin regresiones.

No prometer NVML, Nsight Systems, CUPTI ni métricas GPU equivalentes en Android. Los datos móviles deben llevar su fuente (ADB, Android API, runtime o medidor externo).

## 9. Gate de aceptación de campaña

La campaña inicial se considera medida únicamente cuando:
- el hardware está identificado por salida del terminal;
- runtime y modelo están fijados por versión/hash;
- hay al menos cinco repeticiones válidas después de warm-up;
- logs y datos primarios están archivados y tienen checksums;
- las métricas tienen unidades y procedencia;
- fallos y límites están registrados;
- una revisión independiente puede reproducir la interpretación.

**Checkpoint actual:** documentación creada en rama de trabajo; falta inventario físico Android. No hay ejecución ni benchmark acreditado.
