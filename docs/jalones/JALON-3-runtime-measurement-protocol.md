# JALÓN 3 — Protocolo de medición real

## Estado

**Contrato operativo V1 — listo para ejecución física.**

JALÓN 3 no mide todavía ningún runtime. Congela, antes de entrar en Ubuntu, las condiciones bajo las que una medición física será considerada comparable, reproducible y publicable como evidencia.

El contrato normativo es `schemas/runtime-measurement-protocol.v1.schema.json`.

## 1. Principio rector

La medición debe responder a una pregunta concreta y reproducible:

> ¿Qué rendimiento produce este modelo exacto, en este artefacto exacto, con esta cuantización, este runtime y esta configuración, sobre este hardware y bajo este protocolo?

Una cifra de rendimiento sin esa cadena de identidad no es evidencia comparable.

La documentación de trabajo aportada para el proyecto insiste además en separar capacidad de memoria, ancho de banda, runtime y forma de carga de trabajo, y en no comparar motores únicamente con una cifra de tokens/s. fileciteturn0file0L117-L120 fileciteturn0file0L250-L254

## 2. Qué queda congelado antes de ejecutar

1. **Modelo**: identificador, revisión, artefacto, cuantización y SHA-256 si está disponible.
2. **Entrada**: prompt/protocolo, identificador del prompt, hash y longitud de contexto objetivo.
3. **Generación**: máximo de tokens, política de parada y secuencias de parada.
4. **Decodificación**: temperatura, top-p, top-k y seed.
5. **Runtime**: nombre, versión, revisión/backend y comando exacto.
6. **Hardware**: CPU, RAM, GPU, VRAM y ancho de banda cuando estén disponibles.
7. **Sistema**: SO y condiciones de aislamiento.
8. **Ejecución**: warm-up, número de mediciones, orden, cooldown y política ante fallos.
9. **Métricas**: conjunto primario, obligatorio y opcional.
10. **Evidencia**: stdout/stderr sin alterar, código de salida, timestamps, artefacto y hashes.

No se permite cambiar una variable del protocolo durante una serie y seguir denominándola la misma serie.

## 3. Dos fases de inferencia

El protocolo conserva la distinción entre **prefill** y **decode**. El prefill procesa la entrada y condiciona TTFT; el decode genera tokens secuencialmente y suele estar condicionado por el movimiento de memoria. fileciteturn0file0L246-L249

Por ello:

- **TTFT** mide la experiencia inicial y debe conservarse separada.
- **generation_time_ms** mide el tiempo de generación.
- **decode_tokens_per_second** se calcula a partir de tokens generados y tiempo de generación.
- **total_time_ms** no debe sustituir silenciosamente a TTFT/TPS.
- Si el runtime no puede observar TTFT o prefill de forma fiable, el campo se conserva como `null` y se documenta la limitación; no se inventa.

## 4. Métrica primaria

El protocolo exige declarar una métrica primaria antes de ejecutar:

- `decode_tokens_per_second` para comparar capacidad de generación en una carga de usuario único;
- `end_to_end_tokens_per_second` cuando el objetivo sea el flujo completo;
- `ttft_ms` cuando el objetivo principal sea latencia inicial.

La métrica primaria no puede elegirse después de ver los resultados.

## 5. Repetición y warm-up

La secuencia normativa es:

```text
preparar entorno
  ↓
verificar identidad del artefacto
  ↓
warm-up N veces
  ↓
cooldown si el protocolo lo exige
  ↓
medición 1..M
  ↓
preservar stdout/stderr de cada ejecución
  ↓
agregar resultados
  ↓
generar evidence
```

Los warm-ups **no forman parte de las mediciones**.

Las mediciones fallidas no se convierten en ceros ni se eliminan silenciosamente. El runner debe conservarlas y el agregador debe marcar la serie como no válida si no alcanza `minimum_successful_runs`.

## 6. Determinismo

Cuando el objetivo sea comparar rendimiento, se recomienda `temperature=0` y seed fija siempre que el runtime/modelo lo permita. Si no es posible, la desviación se documenta.

El objetivo no es que todos los runtimes produzcan byte-identical output; el objetivo es que la carga y las condiciones de decodificación sean equivalentes y auditables.

La plantilla de chat/tokenización forma parte del contrato de ejecución: un formato incorrecto puede cambiar radicalmente el comportamiento del mismo peso. fileciteturn0file0L233-L234

## 7. Aislamiento

Cada serie debe declarar:

- política de red;
- política de procesos de fondo;
- perfil de energía/potencia;
- cooldown;
- límites temporales.

Cuando sea posible, la ejecución debe realizarse sin carga ajena relevante. Si no puede garantizarse, se conserva la condición real y la evidencia se etiqueta como tal.

## 8. Hardware y memoria

La evidencia debe registrar capacidad de memoria y, cuando sea posible, ancho de banda. No se debe inferir rendimiento únicamente desde la capacidad de VRAM: la documentación de referencia distingue explícitamente capacidad, ancho de banda y pila de software. fileciteturn0file0L117-L120

También debe conservarse la memoria pico observada. El modelo puede caber en memoria y aun así fallar o degradarse por caché KV, activaciones, batching, concurrencia o sobrecarga del runtime. fileciteturn0file0L36-L40

## 9. Comparabilidad

Dos resultados solo son comparables directamente si coinciden, como mínimo, en:

- modelo y revisión;
- artefacto/cuántización;
- prompt protocol;
- contexto objetivo;
- límite de salida;
- política de decodificación;
- definición de la métrica;
- warm-up y número de mediciones;
- hardware comparable y condiciones declaradas;
- versión exacta del runtime.

Si alguno cambia, se crea una nueva serie o un nuevo `protocol_id`/perfil de ejecución.

La guía de referencia recomienda medir el modelo exacto, cuantización, versión/flags, hardware, forma de carga y métricas como TTFT, TPOT, percentiles, tokens/s, solicitudes/s y memoria. fileciteturn0file0L250-L254

## 10. Evidencia mínima obligatoria

Cada ejecución física debe poder reconstruirse desde:

- `execution_id` único;
- timestamp UTC de inicio y fin;
- protocolo y hash del protocolo;
- modelo, revisión, cuantización y artefacto;
- runtime, versión y comando;
- hardware y SO;
- resultados por iteración;
- exit code;
- stdout bruto;
- stderr bruto;
- hash SHA-256 del artefacto;
- hash del prompt cuando proceda.

Esto alimenta el contrato existente `runtime-benchmark-evidence.v1.1`, que ya exige identidad del modelo, protocolo, runtime, hardware, mediciones, proceso y artefacto. fileciteturn14file0L2-L2

## 11. Estadística de la serie

El resultado agregado debe conservar al menos:

- número de ejecuciones intentadas;
- número de ejecuciones válidas;
- media;
- mediana cuando el tamaño de muestra lo permita;
- mínimo y máximo;
- desviación estándar cuando sea calculable;
- p50/p95/p99 cuando el número de muestras sea suficiente para que tenga sentido;
- dispersión de TPS y TTFT;
- cualquier fallo o anomalía.

No se debe presentar p95/p99 con una falsa precisión cuando la muestra sea demasiado pequeña.

## 12. Regla de publicación

Una medición puede promoverse a evidencia real solo si:

```text
protocolo válido
AND artefacto identificado
AND comando identificado
AND runtime identificado
AND hardware identificado
AND exit_code == 0
AND stdout/stderr preservados
AND hash del artefacto válido
AND successful_runs >= minimum_successful_runs
```

En cualquier otro caso: `failed`, `incomplete` o evidencia no comparable; nunca `measured` por conveniencia.

## 13. Separación entre estimación y medición

`estimated_tps` y `measured_tps` son conceptos distintos. La estimación puede servir para selección previa; únicamente la ejecución física puede producir evidencia medida.

La arquitectura existente ya separa el adaptador de selección de la medición: el adaptador llama.cpp emite una especificación de ejecución y no una medición. fileciteturn7file0L2-L2

## 14. Contaminación y protocolo congelado

El protocolo debe congelarse antes de la medición final. La fuente de estudio aportada para el proyecto establece como regla que el protocolo debe congelarse antes de la evaluación final y que la optimización contra el conjunto de prueba deja de ser una medición limpia. fileciteturn0file0L495-L499

Para benchmarking de runtime, esto se traduce en no cambiar prompt, flags, número de runs, warm-up o métrica después de observar los resultados y seguir presentando los resultados como una única serie.

## 15. Lo que queda para Ubuntu

**Nada arquitectónico.**

Antes de Ubuntu queda cerrado:

- contrato JSON Schema;
- semántica de medición;
- identidad del workload;
- protocolo de warm-up/medición;
- métricas;
- aislamiento;
- criterios de aceptación;
- evidencia mínima;
- separación estimación/medición;
- reglas de comparabilidad.

Ubuntu solo será imprescindible para la siguiente transición:

```text
protocolo congelado
    ↓
resolver modelo/artefacto real
    ↓
ejecutar runtime físico
    ↓
medir
    ↓
capturar stdout/stderr + hardware + timestamps
    ↓
producir runtime-execution.v1
    ↓
producir runtime-benchmark-evidence.v1.1
    ↓
validar evidencia
```

Ese punto es el **handoff físico de JALÓN 3**.
