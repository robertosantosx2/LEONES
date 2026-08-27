# Evidencia real: Ollama → A01

**Estado: CERRADO**

Este documento fija la evidencia de la primera ejecución real de A01 mediante el runtime Ollama y conserva la separación entre selección, adaptación, ejecución, medición y evidencia.

## 1. Alcance

La prueba demuestra el camino real:

```text
runtime-selection.v1
        ↓
     ollama
        ↓
    ollama.v1
        ↓
 trusted://ollama/a01
        ↓
   Ollama real
        ↓
qwen2.5:0.5b-instruct-q4_K_M
        ↓
       A01
        ↓
    evidence
```

No es una simulación de GPU ni un modelo falso. La ejecución utiliza un servidor Ollama real y un modelo real instalado en el equipo de prueba.

## 2. Contrato A01

La trayectoria canónica contiene exactamente dos llamadas, en este orden:

```json
{"tool":"lookup_model","arguments":{"model_id":"qwen2.5:0.5b-instruct-q4_K_M"}}
{"tool":"write_report","arguments":{"path":"report.txt"}}
```

### `lookup_model`

Los argumentos válidos son exactamente:

```json
{"model_id":"qwen2.5:0.5b-instruct-q4_K_M"}
```

No se permiten propiedades adicionales. En particular, `output_path` es inválido.

### `write_report`

Los argumentos válidos son exactamente:

```json
{"path":"report.txt"}
```

Tampoco se permiten propiedades adicionales.

## 3. Fallo que permitió endurecer el contrato

Durante la prueba inicial el modelo produjo repetidamente:

```json
{"tool":"lookup_model","arguments":{"model_id":"qwen2.5:0.5b-instruct-q4_K_M","output_path":"report.txt"}}
```

El nombre de la herramienta y el modelo eran correctos, pero la llamada violaba el contrato porque `output_path` no pertenece a `lookup_model`.

LEONES rechazó deliberadamente la salida en lugar de corregirla silenciosamente. Esto establece una regla fundamental: **una salida que no cumple el contrato no se transforma en una salida aparentemente válida**.

Las definiciones de herramientas utilizan además `additionalProperties: false`, y el fallback estructurado expresa el `model_id` y el `path` concretos exigidos por A01.

## 4. Comportamiento de Ollama

La llamada directa mediante herramientas nativas de Ollama no produjo `message.tool_calls`; produjo contenido vacío con `done_reason=stop`.

Por ello el adaptador no inventa una trayectoria externa. Utiliza salida estructurada del mismo modelo para obtener la representación contractual y después aplica la validación canónica de LEONES.

La salida estructurada válida observada fue equivalente a:

```json
{
  "tool_calls": [
    {"tool":"lookup_model","arguments":{"model_id":"qwen2.5:0.5b-instruct-q4_K_M"}},
    {"tool":"write_report","arguments":{"path":"report.txt"}}
  ]
}
```

## 5. Ejecución real final

Comando:

```bash
python3 scripts/ollama_a01_runtime.py \
  --model qwen2.5:0.5b-instruct-q4_K_M \
  --timeout 600 \
  "Execute A01. Return only JSONL tool calls."
```

Resultado:

```text
EXIT=0
```

Artefacto observado:

```json
{"tool":"lookup_model","arguments":{"model_id":"qwen2.5:0.5b-instruct-q4_K_M"}}
{"tool":"write_report","arguments":{"path":"report.txt"}}
{"measured_tps":43.5952}
```

La medición procede de `eval_count/eval_duration` del runtime Ollama. Es una **medición empírica de esta ejecución**, no una estimación, recomendación ni garantía general de rendimiento.

## 6. Repetibilidad

Se realizaron cinco ejecuciones reales consecutivas:

| Run | Resultado | tok/s |
|---:|:---:|---:|
| 1 | PASS | 46.4259 |
| 2 | PASS | 31.9378 |
| 3 | PASS | 38.3947 |
| 4 | PASS | 38.1164 |
| 5 | PASS | 38.5249 |

Tasa de éxito contractual: **5/5 = 100 %**.

La dispersión de rendimiento se conserva como observación y no se convierte en una cifra normativa.

## 7. Frontera selector → adaptador

El registro de Ollama queda identificado como:

```text
runtime_id       = ollama
adapter_id       = ollama.v1
entrypoint_ref   = trusted://ollama/a01
```

La preparación del plan no expone `command`, `argv`, `shell`, `measured_tps` ni `tokens_per_second` como metadatos de ejecución del selector.

Esto preserva la separación entre:

1. **selección** — qué runtime/modelo se eligió;
2. **preparación** — qué adaptador queda autorizado;
3. **ejecución** — qué proceso confiable se ejecuta;
4. **medición** — qué observó el runtime;
5. **evidencia** — qué hechos pueden conservarse y verificarse.

## 8. Evidencia y procedencia

La evidencia real registrada contiene, como mínimo:

```text
runtime_id       ollama
adapter_id       ollama.v1
model_id         qwen2.5:0.5b-instruct-q4_K_M
task             A01
result           passed
measurement      measured_tps
source           ollama runtime eval_count/eval_duration
```

No se promociona automáticamente una medición a `verified`. La verificación independiente continúa siendo una capa distinta.

## 9. Regresión

En el cierre real se ejecutó la suite completa:

```text
205 passed
```

También se comprobó `git diff --check`, la sintaxis AST de los archivos afectados y la cadena selector → adaptador.

## 10. Commits

El cierre contractual quedó en:

```text
c5025fc test: close real Ollama A01 runtime contract
1ce52f2 feat(runtime): add Ollama V1.1 adapter boundary
c861745 fix(v1.1): reject non-positive benchmark observations
```

La ejecución documentada quedó capturada contra el commit completo:

```text
c5025fc0360e86334fb95a1d26c18ffea5ea3eee
```

## 11. Estado de cierre

```text
Contrato A01          CLOSED
Runtime                ollama
Adapter                ollama.v1
Modelo                 qwen2.5:0.5b-instruct-q4_K_M
Ejecución real         PASS
Repetibilidad          5/5 PASS
Suite Python           205 PASS
Selector → Adapter     PASS
Medición               43.5952 tok/s
Debug residual         NONE
Árbol local            CLEAN
```

## 12. Principio fijado

> **Construirlo. Medirlo. Explicarlo. Preservar la evidencia.**

Para futuros runtimes, el mismo estándar se aplica sin rebajar el contrato: los errores del modelo se rechazan; las mediciones se etiquetan como mediciones; y la evidencia conserva su procedencia.
