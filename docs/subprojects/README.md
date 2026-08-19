# Subproyectos LEONES

Los subproyectos amplían LEONES sin convertirlos en dependencias obligatorias del núcleo.

## ODS

**Papel:** despliegue e instalación del stack local.

`docs/subprojects/ODS/README.md`

## Magnitude

**Papel:** runtime/agente local y ejecución de tareas agentivas, especialmente coding.

`docs/subprojects/Magnitude/README.md`

## Regla arquitectónica común

```text
LEONES = conocimiento + evidencia + recomendación + benchmark
ODS    = despliegue
Magnitude = ejecución agentiva/runtime
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
- documentación enlazada desde este índice.
