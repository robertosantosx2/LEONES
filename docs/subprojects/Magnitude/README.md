# Subproyecto Magnitude

## 1. Misión

Integrar Magnitude como **runtime/agente local opcional**, con prioridad para coding y evaluación agentiva.

Magnitude se documenta como agente de coding open source con inferencia local basada en llama.cpp, profiling de hardware, recomendación de modelos y ajuste de memoria/aceleración/placement/batching.

Fuente primaria del proyecto: `https://github.com/magnitudedev/magnitude`

## 2. Mapa documental

- [`../../integrations/Magnitude/README.md`](../../integrations/Magnitude/README.md) — contrato de integración LEONES.
- [`../../sources/MAGNITUDE.md`](../../sources/MAGNITUDE.md) — ficha de conocimiento.
- [`../ODS-Magnitude-INTEGRATION.md`](../ODS-Magnitude-INTEGRATION.md) — relación ODS ↔ Magnitude.
- [`../ODS-Magnitude-AUDIT.md`](../ODS-Magnitude-AUDIT.md) — auditoría conjunta.
- [`../buddy/MAGNITUDE-INTEGRATION.md`](../buddy/MAGNITUDE-INTEGRATION.md) — relación Buddy ↔ Magnitude.
- [`../../AGENT_HARNESSES.md`](../../AGENT_HARNESSES.md) — harnesses de referencia.
- [`../../EVALUACION_AGENTIC_TESTS.md`](../../EVALUACION_AGENTIC_TESTS.md) — evaluación agentiva.
- [`../../../benchmarks/agentic/README.md`](../../../benchmarks/agentic/README.md) — batería de benchmarks.
- [`../../../schemas/result.schema.json`](../../../schemas/result.schema.json) — contrato de resultados.
- [`../../../atlas/README.md`](../../../atlas/README.md) — conocimiento/evidencia canónica.

## 3. Frontera de responsabilidad

```text
Atlas → identidad/evidencia
   ↓
Recommender → modelo/hardware
   ↓
Magnitude adapter
   ↓
runtime + coding agent
   ↓
Agentic Benchmark
   ↓
result.schema.json
```

**Magnitude ejecuta. LEONES mide y valida.**

## 4. Prioridad benchmark

| Prioridad | Tarea | Motivo |
|---|---|---|
| 1 | A07 | coding agent y repositorios |
| 2 | A02 | operaciones dependientes |
| 3 | A03 | generación/verificación de artefactos |
| 4 | A04 | recuperación ante errores |
| 5 | A05 | sesiones largas |

## 5. Datos que debe conservar el adaptador

- versión del CLI;
- versión/revisión del runtime;
- modelo y cuantización;
- contexto;
- hardware detectado;
- aceleración/placement;
- batching;
- prefill/cache cuando sea observable;
- llamadas a herramientas;
- duración;
- tokens cuando estén disponibles;
- errores;
- recuperaciones.

Los valores no observables permanecen ausentes/`unknown`; nunca se rellenan con estimaciones sin marcar.

## 6. Instalación de referencia

La documentación revisada contempla:

```text
npm install -g @magnitudedev/cli
cd <proyecto>
magnitude
```

Para benchmarks LEONES la instalación debe fijar una versión y conservar el manifiesto del entorno. La instalación de producción no debe seguir automáticamente `main`.

## 7. Contrato de traza

Magnitude no crea un formato de benchmark paralelo. Su información debe transformarse al contrato canónico LEONES:

```text
model
  tool_call
  tool_result
  error
  recovery
  artifact
  grader
```

La traza es evidencia de ejecución; el `outcome` se calcula mediante un grader versionado.

## 8. Reproducibilidad

Registrar como mínimo:

- CLI/runtime;
- modelo/revisión/cuántización;
- hardware;
- configuración de contexto;
- placement/aceleración;
- herramientas;
- benchmark/task version;
- grader version;
- fecha de ejecución.

## 9. Validación mínima

- [ ] versión fijada;
- [ ] entorno reproducible;
- [ ] modelo identificado;
- [ ] runtime identificado;
- [ ] herramientas registradas;
- [ ] trazas completas;
- [ ] grader determinista cuando sea posible;
- [ ] resultado compatible con `schemas/result.schema.json`;
- [ ] repetición suficiente para estudiar variabilidad.

## 10. Relación con ODS y Buddy

ODS y Magnitude no compiten dentro de LEONES:

```text
ODS       = despliegue / stack
Magnitude = ejecución / agente
Buddy     = harness / memoria file-first
LEONES    = conocimiento / selección / medición / evidencia
```

Una instalación puede utilizar ODS, Magnitude, Buddy, varios de ellos o ninguno. La arquitectura del núcleo no debe depender de ninguno.

## 11. Estado

🟡 **DISEÑO LIMPIO Y CONGELADO.**

Siguiente fase: construir el adaptador ejecutable y realizar la primera campaña controlada sobre A07/A02/A03.

## 12. Referencias

- Magnitude: `https://github.com/magnitudedev/magnitude`
- Índice de subproyectos: [`../README.md`](../README.md)
- Agentic Benchmark: [`../../../benchmarks/agentic/README.md`](../../../benchmarks/agentic/README.md)
- Integración LEONES: [`../../integrations/Magnitude/README.md`](../../integrations/Magnitude/README.md)
- Ficha de conocimiento: [`../../sources/MAGNITUDE.md`](../../sources/MAGNITUDE.md)
- Contrato de resultados: [`../../../schemas/result.schema.json`](../../../schemas/result.schema.json)
