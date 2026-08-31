# RC2-Q — Consentimiento de benchmark y handoff a RC1

**Estado:** 🟢 Contrato fijado

RC2 termina la preparación y deja que el usuario decida explícitamente si desea medir el modelo elegido. La instalación y el benchmark son consentimientos independientes.

## Decisión

```text
READY_FOR_BENCHMARK
        ↓
¿EJECUTAR BENCHMARK?
   ├── NO → READY_FOR_BENCHMARK
   └── SÍ → EXECUTION_AUTHORIZED
```

Si el usuario rechaza, no se ejecuta ningún runtime y no se genera autorización.

Si acepta, RC2 genera un único `rc1_handoff` con `execution_authorized=true`. Ese handoff es el puente hacia el runner validado de RC1; RC2 no duplica su lógica de ejecución, grader ni evidencia.

## Reglas

1. La instalación requiere consentimiento independiente.
2. El benchmark requiere consentimiento independiente.
3. `execution_authorized` solo aparece como verdadero después del consentimiento positivo y los estados previos completados.
4. El benchmark sigue siendo real cuando se ejecuta; ninguna evidencia histórica satisface una nueva medición.
5. El resultado de RC1 conserva su contrato de evidencia y se reincorpora a la sesión RC2 como resultado final.

## Trilingüe

La pregunta y sus opciones se presentan simultáneamente en Español, English y 中文. El valor técnico de la decisión permanece independiente del idioma.

```text
¿EJECUTAR EL BENCHMARK?
DO YOU WANT TO RUN THE BENCHMARK?
是否运行基准测试？

[1] Sí / Yes / 是
[2] No / No / 否
```

## Criterio de cierre

Con este bloque, RC2 tiene definido el recorrido lógico completo desde perfilado y selección hasta el punto exacto en que RC1 toma el control. La siguiente intervención física debe validar instalación y handoff sobre un host real; no se debe simular esa parte con una prueba de CI.
