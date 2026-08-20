# Fuentes de conocimiento — LEONES

Este directorio contiene fuentes externas convertidas en conocimiento documental independiente para LEONES.

## Principios

1. La fuente externa conserva su procedencia, versión y fecha.
2. El análisis LEONES no sustituye la evidencia original.
3. Una fuente no publica automáticamente datos en el Atlas canónico.
4. Las mediciones propias permanecen separadas de las observaciones externas.
5. Cada actualización importante debe dejar trazabilidad.
6. Las herramientas externas de estimación no sustituyen los contratos ni las métricas canónicas de LEONES.

## Fuentes activas

| Fuente | Documento | Estado | Revisión |
|---|---|---|---|
| Mozilla / SlashData | [`MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md`](MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md) | 🟢 Activa | Mensual / nueva edición |
| LLMFit | [`LLMFIT.md`](LLMFIT.md) | 🟢 Activa / 🟡 integración funcional | Revisar versiones, catálogo y metodología |
| AirLLM | [`AIRLLM.md`](AIRLLM.md) | 🟢 Activa / 🟡 integración funcional | Revisar compatibilidad, runtimes y benchmarks |
| Infraestructura de IA local 2026 | [`LOCAL-INFERENCE-2026.md`](LOCAL-INFERENCE-2026.md) | 🟢 Activa / 🟢 verificación documental completada | Revisar nuevas ediciones, proyectos y claims |

## Derivados de la fuente de infraestructura local

- [`LOCAL-INFERENCE-2026-CANDIDATES.md`](LOCAL-INFERENCE-2026-CANDIDATES.md) — radar de candidatos y decisión de promoción.
- [`LOCAL-INFERENCE-2026-VERIFICATION.md`](LOCAL-INFERENCE-2026-VERIFICATION.md) — verificación uno a uno contra fuentes primarias.

### Resultado actual

**23 proyectos de infraestructura:** 18 `verified-primary`, 3 archivados y 2 `unresolved`.

**10 modelos/familias:** 7 `verified-primary`, 2 con licencia diferenciada/no-OSI y 1 `unresolved`.

Los `verified-primary` quedan pendientes únicamente de benchmark LEONES para obtener estado `measured`. Los archivados se conservan por trazabilidad histórica y los `unresolved` no generan recomendaciones ni registros canónicos verificados.

## Evidencia local de referencia

- [`LLMFIT-REAL-HARDWARE-2026-08-20.md`](LLMFIT-REAL-HARDWARE-2026-08-20.md) — observación de LLMFit sobre un Intel i5-1035G1 con 8 núcleos, 7 GB de RAM y GPU Intel Iris Plus integrada. Se conserva separada de los benchmarks propios.

## Pipeline de incorporación

```text
FUENTE EXTERNA
      ↓
ANÁLISIS INDEPENDIENTE
      ↓
CANDIDATOS
      ↓
IDENTIDAD + EVIDENCIA PRIMARIA
      ↓
QUALITY GATE
      ↓
verified-primary
      ↓
LLMFIT / FIT
      ↓
RUNTIME SELECTOR
      ↓
BENCHMARK LEONES
      ↓
measured
      ↓
ATLAS / RECOMENDADOR
```

## Regla de independencia

Una fuente estratégica puede aportar taxonomías, entidades, proyectos, hipótesis y señales de mercado. No puede alterar por sí sola las clasificaciones congeladas de LEONES ni convertir una estimación externa en medición propia.

LLMFit actúa como **preselector hardware-aware**: reduce el espacio de candidatos antes de que el Router de LEONES aplique evidencia, tarea, licencia/JGB, CABE/RULA, rendimiento medido, runtime y demás criterios propios.

AirLLM actúa como **runtime candidato memory-constrained**: puede ampliar el conjunto de modelos ejecutables cuando la VRAM es el cuello de botella, pero sus claims de memoria/rendimiento deben reproducirse con benchmarks LEONES antes de alimentar recomendaciones como evidencia medida.

El informe de infraestructura local 2026 actúa como **radar de prospección**. Sus claims se contrastan individualmente y el resultado de esa comprobación queda en los documentos derivados indicados arriba.

## Mantenimiento

Ante una nueva edición: comparar con la anterior, identificar cambios, revisar entidades/proyectos/hipótesis, conservar histórico, actualizar documentación y ejecutar validaciones. Un proyecto archivado no se elimina del conocimiento: se marca como histórico. Una referencia no resoluble no se promociona por inferencia.
