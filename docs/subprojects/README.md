# Subproyectos LEONES

Los subproyectos amplían LEONES sin convertirlos en dependencias obligatorias del núcleo.

## Mapa documental canónico

| Pieza | Papel | README / documentación | Integración LEONES |
|---|---|---|---|
| LLMFit | preselección hardware-aware | [`LLMFit/README.md`](LLMFit/README.md) | [`../integrations/LLMFIT/README.md`](../integrations/LLMFIT/README.md) |
| ODS | despliegue e instalación del stack local | [`ODS/README.md`](ODS/README.md) | [`../integrations/ODS/README.md`](../integrations/ODS/README.md) |
| Magnitude | runtime/agente local y coding | [`Magnitude/README.md`](Magnitude/README.md) | [`../integrations/Magnitude/README.md`](../integrations/Magnitude/README.md) |
| Buddy | harness/agente personal file-first | [`buddy/README.md`](buddy/README.md) | [`../AGENT_HARNESSES.md`](../AGENT_HARNESSES.md) |
| Open-dCoder | modelo de difusión de texto y evaluación local | [`Open-dCoder/README.md`](Open-dCoder/README.md) · [`Open-dCoder/EXECUTIVE-SUMMARY.md`](Open-dCoder/EXECUTIVE-SUMMARY.md) | V1/V2 single-sequence + V3 batch real en RTX 3050 |
| LEONES Lab Agent | agente local autocontenido en Rust para diagnóstico, inventario y asistencia sobre LLM local | [`leones-lab-agent/README.md`](leones-lab-agent/README.md) | v0.3.0: inventario de hardware/modelos/herramientas; API Chat Completions solo en loopback; herramientas de solo lectura; JSON; compilación estática musl |
| TensorFold | runtime de inferencia local y auditoría de memoria CUDA | [`TensorFold/README.md`](TensorFold/README.md) · [`TensorFold/CUDA-MEMORY-REGRESSION-2026-11-01.md`](TensorFold/CUDA-MEMORY-REGRESSION-2026-11-01.md) | Qwen3.5-4B; regresión de scratch 128→4096 filas; reproducción física pendiente |

### Piezas relacionadas

- [`INTEGRATION_MATRIX.md`](INTEGRATION_MATRIX.md) — matriz global de subproyectos e integraciones.
- [`ODS-Magnitude-INTEGRATION.md`](ODS-Magnitude-INTEGRATION.md) — integración conjunta ODS + Magnitude.
- [`ODS-Magnitude-AUDIT.md`](ODS-Magnitude-AUDIT.md) — auditoría de esa integración.
- [`buddy/HARNESS-CONTRACT.md`](buddy/HARNESS-CONTRACT.md) — contrato específico de Buddy.
- [`buddy/ODS-INTEGRATION.md`](buddy/ODS-INTEGRATION.md) — Buddy ↔ ODS.
- [`buddy/MAGNITUDE-INTEGRATION.md`](buddy/MAGNITUDE-INTEGRATION.md) — Buddy ↔ Magnitude.
- [`buddy/LICENSING-INTEGRATION.md`](buddy/LICENSING-INTEGRATION.md) — licencia y frontera de integración.
- [`../AGENT_HARNESSES.md`](../AGENT_HARNESSES.md) — DSH, Buddy y Hermes como harnesses de referencia.
- [`../EVALUACION_AGENTIC_TESTS.md`](../EVALUACION_AGENTIC_TESTS.md) — evaluación común.
- [`../../benchmarks/agentic/README.md`](../../benchmarks/agentic/README.md) — batería agentiva.
- [`../../schemas/result.schema.json`](../../schemas/result.schema.json) — contrato de resultado.

## LLMFit

**Papel:** preselector hardware-aware y estimador inicial de encaje modelo ↔ máquina.

[`LLMFit/README.md`](LLMFit/README.md) → [`../integrations/LLMFIT/README.md`](../integrations/LLMFIT/README.md) → [`../sources/LLMFIT.md`](../sources/LLMFIT.md) → benchmark LEONES.

LLMFit nunca se considera una medición propia: sus resultados permanecen como `reported`/`estimated` hasta que LEONES los contraste y mida.

## ODS

**Papel:** despliegue e instalación del stack local.

[`ODS/README.md`](ODS/README.md) → [`../integrations/ODS/README.md`](../integrations/ODS/README.md) → [`../sources/ODS.md`](../sources/ODS.md).

## Magnitude

**Papel:** runtime/agente local y ejecución de tareas agentivas, especialmente coding.

[`Magnitude/README.md`](Magnitude/README.md) → [`../integrations/Magnitude/README.md`](../integrations/Magnitude/README.md) → [`../sources/MAGNITUDE.md`](../sources/MAGNITUDE.md).

## Open-dCoder

**Papel:** ejecución y evaluación local de modelos de difusión de texto, diferenciando posiciones de salida/s de tokens/s autoregresivos.

[`Open-dCoder/EXECUTIVE-SUMMARY.md`](Open-dCoder/EXECUTIVE-SUMMARY.md) → [`Open-dCoder/README.md`](Open-dCoder/README.md) → [`Open-dCoder/EXPERIMENT-2026-10-31.md`](Open-dCoder/EXPERIMENT-2026-10-31.md) (V1/V2) → [`Open-dCoder/EXPERIMENT-V3-BATCH-2026-10-31.md`](Open-dCoder/EXPERIMENT-V3-BATCH-2026-10-31.md) (batch real).

La evidencia actual incluye un benchmark repetido V2 de secuencia única y nueve configuraciones V3 de batching real, todas medidas en RTX 3050 Laptop. Son resultados de una tarea factorial, no una puntuación de inteligencia general. Los artefactos originales V3 CSV/JSONL/JSON, el log y el runner permanecen identificados en el informe como archivos locales pendientes de incorporación íntegra al repositorio.

## TensorFold

**Papel:** runtime de inferencia local y objeto de auditoría de compatibilidad/memoria en hardware limitado.

[`TensorFold/README.md`](TensorFold/README.md) → [auditoría CUDA Qwen3.5-4B](TensorFold/CUDA-MEMORY-REGRESSION-2026-11-01.md) → [issue upstream #1827](https://github.com/ashhart/TensorFold/issues/1827).

La auditoría estática reconstruye un incremento aproximado de 605 MiB en el scratch reservado al pasar de 128 a 4096 filas. Distingue esa reserva posterior a la admisión del rechazo temprano de pesos, cuya causa aún requiere una reproducción controlada. Las cifras son cálculos de código fuente, no nuevas mediciones físicas.

## Buddy

**Papel:** harness de referencia para evaluación agentiva, con memoria Git/Markdown y herramientas file-first.

[`buddy/README.md`](buddy/README.md) → [`../AGENT_HARNESSES.md`](../AGENT_HARNESSES.md) → [`buddy/HARNESS-CONTRACT.md`](buddy/HARNESS-CONTRACT.md) → benchmark agentivo.

## Regla arquitectónica común

```text
LEONES = conocimiento + evidencia + recomendación + benchmark
LLMFit = preselección / estimación
ODS    = despliegue
Magnitude = ejecución agentiva / runtime
Buddy  = harness de evaluación
```

Las capacidades declaradas por un subproyecto son evidencia externa. Solo una ejecución reproducible puede convertirse en medición LEONES.

## Ciclo común

```text
DETECT → SELECT → PIN → INSTALL/START → VERIFY → MEASURE → REPORT → CLEANUP
```

Toda integración debe fijar versiones, conservar el manifiesto del entorno y producir resultados mediante el contrato canónico de `schemas/result.schema.json`.

## Criterios de calidad

- integración opcional;
- interfaces mínimas y versionables;
- ningún secreto en resultados;
- ningún dato externo presentado como medición propia;
- posibilidad de reproducir el entorno;
- recuperación limpia tras fallo;
- documentación enlazada desde este índice y desde el README de cada pieza;
- contratos, tests, workflows, benchmarks y evidencia navegables desde el subsistema correspondiente.

## Regla de cierre documental

Una integración no se considera documentalmente cerrada mientras su README no permita navegar, como mínimo, hacia:

```text
README de la pieza
   ↓
contrato / adaptador
   ↓
fuente de conocimiento
   ↓
implementación / subproyecto
   ↓
tests / workflow
   ↓
benchmark / grader
   ↓
resultado / evidencia
   ↓
Atlas / Router / Web cuando corresponda
```


## LEONES Lab Agent

**Papel:** agente local en Rust para diagnóstico del equipo, inventario de motores/modelos y ejecución futura de experimentos reproducibles bajo supervisión.

[leones-lab-agent/README.md](leones-lab-agent/README.md) → [código Rust](../../projects/leones-lab-agent/) → fase 1.

La primera fase es deliberadamente de solo lectura: no instala paquetes, no descarga modelos, no inicia ni detiene servicios y no ejecuta benchmarks. La detección de herramientas se limita a ejecutables en PATH y la detección de modelos a la caché Hugging Face estándar. Los informes distinguen inventario de resultados MEASURED.
