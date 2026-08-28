# JALÓN 3 — contrato operativo de medición real V1

## Estado

Este documento fija el contrato operativo antes de la siguiente captura física. JALÓN 3 no se considera cerrado hasta que una ejecución real cumpla este contrato y su evidencia sea conservada sin ambigüedades.

## Unidad de evidencia

Una evidencia representa una ejecución de un protocolo concreto sobre:

- modelo y artefacto identificados por SHA-256;
- cuantización;
- contexto;
- runtime, versión y revisión;
- backend;
- hardware identificado;
- comando exacto;
- prompt y protocolo de prompt;
- warm-up;
- al menos 5 mediciones válidas;
- cooldown;
- timestamps UTC;
- `execution_id` único.

## Reglas de aceptación

Una ejecución sólo puede ser `valid` si:

1. hay al menos 5 mediciones;
2. todas las mediciones terminan con código 0;
3. el warm-up termina correctamente;
4. todas las mediciones contienen throughput;
5. todas las mediciones producen exactamente el límite de tokens solicitado por el comando;
6. el tiempo de generación se deriva del throughput reportado por el runtime y del número de tokens solicitado, no de una resta que mezcle carga del modelo y generación;
7. el artefacto existe y su SHA-256 queda registrado;
8. el runtime queda identificado por versión y, cuando la versión lo expone, por commit/revisión;
9. el hardware tiene una identidad de CPU no vacía y RAM total registrada;
10. no se presentan resultados parciales como válidos.

## Semántica temporal

`first_output_ms` significa únicamente el instante en que el proceso produjo su primera salida no vacía. **No es TTFT.** `llama-cli` puede producir texto de arranque, eco del prompt o información de interfaz antes de generar el primer token; por ello ese instante no puede usarse como TTFT.

`ttft_ms` queda `null` cuando el adaptador no dispone de una señal fiable del primer token. El campo no debe ser rellenado con una aproximación basada en la primera línea de stdout.

`generation_time_ms` se obtiene de `output_tokens / tokens_per_second`, cuando ambos datos son fiables. `total_time_ms` mide la duración completa del proceso y puede incluir carga del modelo, preparación del prompt y generación.

Para obtener TTFT físico comparable en una futura versión del adaptador será necesario instrumentar el runtime o utilizar una ruta de benchmark que exponga explícitamente el tiempo de procesamiento del prompt. No se infiere TTFT desde stdout genérico.

## Datos opcionales

`peak_vram_mb` y `power_w` pueden ser `null` cuando la plataforma o el backend no proporcionan una fuente fiable. La ausencia de esos datos no invalida por sí sola una medición.

## Resultado observado en RUN-001

La primera medición física de JALÓN 3 demostró que el pipeline completo funciona, pero también reveló que el cálculo anterior de `ttft_ms` estaba capturando salida temprana del proceso, no necesariamente el primer token. Por eso RUN-001 se conserva como evidencia histórica, pero no debe convertirse en la referencia canónica del contrato endurecido.
