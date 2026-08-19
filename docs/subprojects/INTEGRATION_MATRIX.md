# Matriz de integración de subproyectos

| Capacidad | LEONES | ODS | Magnitude |
|---|---|---|---|
| Identidad/evidencia | **canónica** | consume | consume |
| Recomendación | **canónica** | consume | consume |
| Instalación/stack | especifica | **principal** | secundaria |
| Runtime | mide | proporciona servicios | **proporciona agente/runtime** |
| Herramientas | benchmark | expone según stack | **ejecuta** |
| Benchmark | **canónico** | huésped | huésped |
| Grading | **canónico** | no sustituye | no sustituye |
| Resultado | **canónico** | aporta datos | aporta datos |
| Hardware | **registro/medición** | detecta | perfila |
| Evidencia externa | **valida** | declara | declara |

## Regla de oro

Ningún subproyecto puede convertir una afirmación propia en una medición LEONES sin ejecución instrumentada.

## Combinaciones soportadas

### LEONES + ODS

Despliegue local y medición del stack.

### LEONES + Magnitude

Ejecución agentiva y medición de tareas.

### LEONES + ODS + Magnitude

ODS despliega; Magnitude ejecuta; LEONES mide y valida.

### LEONES sin subproyectos

El núcleo continúa siendo plenamente válido y debe poder ejecutar benchmarks con otros runtimes.

## Criterio de cierre

Una integración se considera operativa únicamente cuando puede recorrer:

`detect → select → pin → install/start → verify → measure → report → cleanup`

con versiones identificables y resultado compatible con el contrato canónico.
