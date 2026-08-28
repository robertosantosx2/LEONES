# JALÓN 6 — Gate de recomendación respaldada por evidencia

**Estado:** 🟠 CONTRATO EN CONSTRUCCIÓN
**Base:** `rc1-minimal-script-cleanup`

## 1. Propósito

JALÓN 6 conecta los contratos ya existentes sin crear un nuevo motor de scoring:

`JALÓN 5 → selector LEONES → recommendation gate → evidencia JALÓN 3 → Atlas`

La decisión final debe ser trazable y conservar la diferencia entre compatibilidad, estimación, observación y medición.

## 2. Piezas canónicas reutilizadas

- `scripts/selection_pipeline.py` — selección y runtime gate.
- `scripts/ods_magnitude_decision.py` — sobre de decisión externo.
- `scripts/validate_recommendation_gate.py` — gate estructural de recomendación.
- `scripts/validate_measured_benchmark.py` — frontera de evidencia física.
- `scripts/promote_measured_benchmark.py` — promoción explícita de mediciones válidas.
- `scripts/runtime_feedback_atlas.py` — retroalimentación medida hacia Atlas.

No se crea un segundo selector ni un segundo sistema de benchmark.

## 3. Autoridad

```text
ODS / Magnitude + LLMFit
          ↓
    señales externas
          ↓
     selector LEONES
          ↓
   recommendation gate
      ↙           ↘
  medir         rechazar/esperar
    ↓
JALÓN 3 evidence
    ↓
Atlas / recomendación
```

Una recomendación puede ser provisional cuando todavía no existe medición física. Una recomendación presentada como rendimiento observado exige evidencia local identificable y validada.

## 4. Reglas de cierre

1. El selector LEONES sigue siendo la autoridad de elegibilidad.
2. Las señales externas mantienen su procedencia.
3. LLMFit nunca se promociona automáticamente a `measured`.
4. ODS/Magnitude no sustituyen la evidencia física local.
5. `recommend` exige que el mínimo de evidencia declarado por el gate esté satisfecho.
6. Si falta evidencia física necesaria, la siguiente acción es `measure`, no inventar una cifra.
7. Una medición validada puede retroalimentar Atlas conservando `execution_id` y procedencia.
8. La promoción a Atlas es explícita; el gate no publica directamente.

## 5. Qué no hace JALÓN 6

- No crea nuevos benchmarks.
- No crea nuevos tiers de hardware.
- No inventa ponderaciones de ODS/Magnitude/LLMFit.
- No convierte `fit` en rendimiento.
- No reemplaza H10 ni JALÓN 5.

## 6. Criterio de cierre

El cierre operativo requiere tests del gate, integración con la frontera de medición y una ejecución reproducible del runner. La primera ejecución real de ODS/Magnitude continúa siendo una tarea de Ubuntu cuando sea necesaria.

**Frase de recuperación:**

> JALÓN 6 = recomendación trazable → evidencia válida → retroalimentación Atlas, sin fabricar rendimiento.
