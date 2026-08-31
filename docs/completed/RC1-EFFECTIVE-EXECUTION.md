# RC1 — Cierre de ejecución efectiva

> **Estado: 🟢 VALIDADO**
>
> RC1 demuestra la transición efectiva desde una selección autorizada hasta una ejecución A01 real sobre Ollama y la producción de evidencia medida.

## 1. Qué queda cerrado

RC1 no se limita a validar código, tests o un preflight. La ejecución del 31 de agosto de 2026 demostró en el host Linux la cadena:

```text
selección
   ↓
runtime-selection gate
   ↓
execution_authorized=true
   ↓
comando runtime confiable
   ↓
Ollama
   ↓
modelo real
   ↓
A01
   ↓
grader
   ↓
medición real
   ↓
evidencia
```

La selección concreta fue:

- modelo: `qwen2.5:0.5b-instruct-q4_K_M`
- cuantización: `Q4_K_M`
- runtime: `ollama`
- estado de selección: `TOP_N`
- rango: `1`
- `execution_authorized`: `true`
- `measurement_required`: `true`

El comando confiable utilizado por el plan autorizado fue exactamente:

```text
python3 scripts/ollama_a01_runtime.py --model qwen2.5:0.5b-instruct-q4_K_M
```

## 2. Evidencia física de cierre

Ejecución efectiva RC1:

| Campo | Resultado |
|---|---|
| `execution_id` | `e07822d0-d991-4e9b-985b-b9afea0c13c0` |
| `measured_at` | `2026-08-31T06:46:37.464795+00:00` |
| `measurement_kind` | `real` |
| `evidence_type` | `measured` |
| A01 outcome | `success` |
| A01 score | `1.0` |
| grader | `passed` |
| tool calls | `2` |
| tool errors | `0` |
| recovery count | `0` |
| runtime wall time | `5.211607 s` |
| measured throughput | `53.3795 tok/s` |

El artefacto producido fue:

```text
artifacts/rc1-effective-execution.json
```

SHA-256 de la ejecución validada:

```text
b3c4807989d9a9c881ef963112675ff392949590428a6ca227cfc7ecb8a29884
```

## 3. Grading A01

El grader `A01-grader` v1.1 terminó con `passed` y `score=1.0`. Las comprobaciones fueron:

```text
tool_order=true
target_model=true
lookup_result=true
artifact_exists=true
artifact_contains_model=true
```

Esto demuestra que el resultado no fue solamente una llamada al runtime: la tarea A01 completó su trayectoria y su artefacto fue verificado.

## 4. Medición nueva, no reutilizada

La evidencia histórica anterior de este modelo/runtime registraba `40.7666 tok/s` y era del 27 de agosto de 2026.

RC1 se validó mediante una ejecución nueva el 31 de agosto de 2026. El resultado nuevo fue `53.3795 tok/s`.

La evidencia histórica no se sobrescribe ni se promociona retroactivamente. Las mediciones son observaciones independientes y conservan su procedencia.

## 5. Fronteras que permanecen intactas

RC1 no cambia las reglas de evidencia de LEONES:

- `estimated` no significa `measured`;
- una medición externa no se convierte en medición LEONES;
- la selección no equivale a rendimiento medido;
- la ejecución física es la fuente del dato `measured`;
- el runner no debe fabricar métricas;
- la evidencia histórica no se reescribe.

El artefacto RC1 también conserva algunos campos de hardware como `unknown`/`null`. Esto es deliberado: **RC1 no inventa información de hardware que no haya sido capturada**. El enriquecimiento de hardware es un trabajo distinto y no forma parte del cierre de esta ejecución.

## 6. Reproducción por beta testers

La guía pública para preparar un host Linux y ejecutar A01 está en:

[`docs/BETA-TESTER-INSTALL.md`](BETA-TESTER-INSTALL.md)

El beta tester debe generar su propia ejecución y su propio `execution_id`. No debe copiar la medición de este documento ni reutilizar `53.3795 tok/s` como si fuese suya.

## 7. Criterio de cierre

RC1 queda cerrado porque se han demostrado simultáneamente:

- selección consumible;
- gate de runtime;
- autorización explícita;
- comando confiable;
- runtime local real;
- modelo real;
- tarea A01 real;
- grader satisfactorio;
- medición nueva;
- evidencia estructurada;
- artefacto persistido;
- procedencia mediante `execution_id` y timestamp.

**RC1 EFFECTIVE EXECUTION = VALIDADO.**
