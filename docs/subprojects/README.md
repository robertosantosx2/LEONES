# Subproyectos LEONES

Los subproyectos amplían LEONES sin convertirlos en dependencias obligatorias del núcleo.

## Mapa documental canónico

| Pieza | Papel | README / documentación | Integración LEONES |
|---|---|---|---|
| LLMFit | preselección hardware-aware | [`LLMFit/README.md`](LLMFit/README.md) | [`../integrations/LLMFIT/README.md`](../integrations/LLMFIT/README.md) |
| ODS | despliegue e instalación del stack local | [`ODS/README.md`](ODS/README.md) | [`../integrations/ODS/README.md`](../integrations/ODS/README.md) |
| Magnitude | runtime/agente local y coding | [`Magnitude/README.md`](Magnitude/README.md) | [`../integrations/Magnitude/README.md`](../integrations/Magnitude/README.md) |
| Buddy | harness/agente personal file-first | [`buddy/README.md`](buddy/README.md) | [`../AGENT_HARNESSES.md`](../AGENT_HARNESSES.md) |

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
