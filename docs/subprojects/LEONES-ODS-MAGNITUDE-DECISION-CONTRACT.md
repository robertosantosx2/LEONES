# Contrato de decisión LEONES → ODS | Magnitude

**Estado: fijado para implementación mínima.**

Este documento define la frontera de decisión entre LEONES y los subproyectos ODS y Magnitude. No crea un sistema de scoring paralelo ni sustituye los contratos de selección, ejecución o evidencia ya cerrados.

## 1. Principio

LEONES decide **qué camino debe seguir una solicitud**. ODS y Magnitude aportan capacidades concretas del stack que representan. LLMFit reduce el espacio de candidatos antes de ejecutar cuando dispone de señales útiles.

```text
intención + hardware
        ↓
      LLMFit
        ↓
 candidatos / fit
        ↓
 identidad + restricciones LEONES
        ↓
 decisión de stack
   ┌────┴───────────┐
   │                │
  ODS           Magnitude
   │                │
 despliegue     agente/runtime
   └────┬───────────┘
        ↓
 runner canónico
        ↓
 ejecución / benchmark
        ↓
 evidencia LEONES
        ↓
 recomendación
```

## 2. Responsabilidades

| Componente | Responsabilidad | No debe hacer |
|---|---|---|
| LEONES | identidad, restricciones, decisión, benchmark, evidencia y recomendación | delegar la verdad canónica a un subproyecto |
| LLMFit | fit modelo ↔ hardware y preselección | certificar rendimiento físico |
| ODS | despliegue, instalación, lifecycle, servicios y stack local | convertir sus estimaciones en mediciones LEONES |
| Magnitude | agente, CLI, perfilado, configuración e inferencia agentiva | sustituir el benchmark/grader LEONES |
| Runner | ejecutar el plan autorizado y conservar evidencia | inventar mediciones o crear una vía paralela |

## 3. Decisión mínima

La decisión LEONES debe producir una **selección autorizada**, no una cifra de rendimiento inventada.

Campos mínimos conceptuales:

- `intent`: tarea o workload solicitado;
- `hardware_profile`: capacidades conocidas del host;
- `candidate_models`: candidatos procedentes de Atlas/LLMFit;
- `model_id` y revisión cuando estén disponibles;
- `quantization` cuando esté determinada;
- `runtime`: runtime previsto;
- `stack`: `none`, `ods`, `magnitude` o combinación compatible;
- `constraints`: memoria, contexto, plataforma y demás restricciones;
- `selection_reason`: razón trazable de la elección;
- `confidence`: solo sobre la decisión, nunca sobre rendimiento no medido;
- `evidence_refs`: referencias a evidencia que sustenta la decisión.

Los campos ausentes permanecen `unknown`/`null`.

## 4. Regla ODS | Magnitude

### ODS

Seleccionar ODS cuando la necesidad principal sea **desplegar y operar un stack local de IA**: servicios, runtimes, modelos y componentes integrados del entorno.

### Magnitude

Seleccionar Magnitude cuando la necesidad principal sea **ejecutar una tarea agentiva**, especialmente coding, con su agente/CLI y motor de inferencia local.

### ODS + Magnitude

Seleccionar ambos únicamente cuando la arquitectura de la tarea necesite ODS como capa de despliegue/servicio y Magnitude como agente/ejecutor.

### Ninguno

No introducir ODS ni Magnitude si el workload puede resolverse directamente mediante un runtime ya soportado por LEONES. La integración no es obligatoria.

## 5. Prioridad de evidencia

Para resolver conflictos:

1. medición reproducible LEONES relevante para el mismo modelo/runtime/hardware/workload;
2. observación/evidencia LEONES del entorno;
3. evidencia externa identificada y fechada;
4. estimación de LLMFit u otra herramienta;
5. ausencia (`unknown`).

Una estimación no desplaza una medición relevante. Una afirmación externa no se convierte en `measured` por ser repetida por ODS, Magnitude o LLMFit.

## 6. Hardware tiers

Los tiers de hardware son una **capa de interpretación** sobre las capacidades observadas por las herramientas y la evidencia LEONES.

No contienen un catálogo alternativo de rendimiento.

```text
hardware observado
      +
fit LLMFit
      +
capacidad/runtime ODS o Magnitude
      +
mediciones LEONES disponibles
      ↓
 tier interpretado
```

Cuando no exista evidencia suficiente, el tier debe conservar la incertidumbre y no fabricar un tok/s esperado.

## 7. Runner y ejecución

La selección desemboca en el **runner canónico existente**. El contrato de decisión no crea otro ejecutor.

```text
selection.v1.1
      ↓
plan autorizado
      ↓
runner existente
      ↓
runtime real
      ↓
benchmark
      ↓
runtime-benchmark-evidence.v1.1
```

CI valida el contrato y los adaptadores. La medición física sigue perteneciendo al host Linux y al runner canónico.

## 8. Gates mínimos de integración

Una integración puede pasar a uso operativo solo si:

- la selección es determinista para las mismas entradas;
- la procedencia de LLMFit/ODS/Magnitude queda conservada;
- los estados `estimated`, `reported`, `observed` y `measured` permanecen separados;
- el plan generado es consumible por el runner existente;
- los tests unitarios funcionan sin instalar el stack externo;
- el benchmark físico queda fuera de CI salvo fixtures explícitos;
- ningún secreto aparece en la evidencia;
- el resultado canónico conserva modelo, runtime, hardware, configuración y procedencia.

## 9. Qué queda fuera

Este contrato no rediseña:

- `runtime-selection.v1.1`;
- `runtime-execution`;
- `runtime-benchmark-evidence.v1.1`;
- JALÓN 2;
- JALÓN 3;
- Atlas como identidad/evidencia;
- CABE/RULA como clasificación derivada.

Tampoco autoriza a crear un segundo sistema de scoring para modelos, hardware o rendimiento.

## 10. Siguiente implementación mínima

1. representar este contrato en estructuras/validación LEONES;
2. añadir adaptadores mínimos de ODS y Magnitude;
3. probar la decisión con fixtures, sin runtime externo;
4. conectar la salida al runner existente;
5. reservar la ejecución física para Ubuntu cuando el código esté listo.

**Criterio de cierre:** LEONES puede tomar una intención y un perfil de hardware, producir una selección trazable de `none`/`ods`/`magnitude`/`ods+magnitude`, y entregar esa selección al runner existente sin confundir estimación con medición.
