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
| llmfit | [`LLMFIT.md`](LLMFIT.md) | 🟢 Activa / 🟡 integración funcional | Revisar versiones, catálogo y metodología |
| Infraestructura de IA local 2026 | [`LOCAL-INFERENCE-2026.md`](LOCAL-INFERENCE-2026.md) | 🟢 Activa / 🟡 verificación pendiente | Revisar proyectos, licencias, claims y benchmarks |

## Evidencia local de referencia

- [`LLMFIT-REAL-HARDWARE-2026-08-20.md`](LLMFIT-REAL-HARDWARE-2026-08-20.md) — primera observación real de LLMFit sobre un Intel i5-1035G1 con 8 núcleos, 7 GB de RAM y GPU Intel Iris Plus integrada. Se conserva separada de los benchmarks propios.

## Pipeline de incorporación

```text
FUENTE EXTERNA → ANÁLISIS INDEPENDIENTE → CANDIDATOS → IDENTIDAD + EVIDENCIA → QUALITY GATE → CONOCIMIENTO VERIFICADO → ATLAS / RECOMENDADOR
```

## Regla de independencia

Una fuente estratégica puede aportar taxonomías, entidades, proyectos, hipótesis y señales de mercado. No puede alterar por sí sola las clasificaciones congeladas de LEONES ni convertir una estimación externa en medición propia.

En el caso de llmfit, su papel es el de **preselector hardware-aware**: reduce el espacio de candidatos antes de que el Router de LEONES aplique evidencia, tarea, licencia/JGB, CABE/RULA, rendimiento medido, runtime y demás criterios propios.

El informe de infraestructura local 2026 se utiliza como **radar de prospección**. Los proyectos y claims incluidos deben verificarse individualmente contra sus repositorios o documentación primaria antes de entrar en Atlas como hechos verificados.

## Mantenimiento

Ante una nueva edición: comparar con la anterior, identificar cambios, revisar entidades/proyectos/hipótesis, conservar histórico, actualizar documentación y ejecutar validaciones.
