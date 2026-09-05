# LEONES RC3 — Arquitectura Hermes → Magnitude/ODS → Leo001…Leo010

**ESTADO: FIJADA**  
**Fecha:** 5 de septiembre de 2026

## Arquitectura canónica

```text
                         ┌──────────────────────┐
                         │ hardware_profile.py  │
                         └──────────┬───────────┘
                                    ↓
                         hardware-profile.v1
                                    ↓
                         candidate-set.v1
                                    ↓
                         ┌──────────────────────┐
                         │       HERMES         │
                         │ selección de modelo  │
                         └──────────┬───────────┘
                                    ↓
                         1 modelo de candidatos
                                    ↓
                         ┌──────────────────────┐
                         │    ELECCIÓN USUARIO  │
                         └──────────┬───────────┘
                                    ↓
                     ┌──────────────┼──────────────┐
                     ↓              ↓              ↓
                 MAGNITUDE         ODS           AMBOS
                     └──────────────┼──────────────┘
                                    ↓
                         handoff declarativo
                                    ↓
                     preparación / ejecución real
                                    ↓
                         verificación endpoint
                                    ↓
                 ┌────────────────────────────────────┐
                 │       SUITE BENCHMARK LEONES       │
                 │                                    │
                 │ Leo001  Tool use                   │
                 │ Leo002  Multi-step                 │
                 │ Leo003  Files / artifacts           │
                 │ Leo004  Recovery                    │
                 │ Leo005  Long horizon                │
                 │ Leo006  Research / evidence         │
                 │ Leo007  Coding                       │
                 │ Leo008  Local operations             │
                 │ Leo009  Safety                       │
                 │ Leo010  Cost / latency               │
                 └──────────────────┬─────────────────┘
                                    ↓
                    resultado MEDIDO por benchmark
                                    ↓
                 evidencia runtime-benchmark.v1.x
                                    ↓
                     comparación por tarea
                                    ↓
                         recomendación final

                    ↺ repetir: volver a HERMES
                      → nuevo modelo → Leo001…Leo010
```

## Nomenclatura FIJADA

Los benchmarks públicos de tareas de LEONES se denominan **Leo001, Leo002, …, Leo010**.

Los antiguos identificadores `A01-001`…`A10-001` dejan de ser nombres públicos. **Leo001…Leo010 son los identificadores canónicos e inmutables.**

## Principios fijados

1. **Hermes selecciona; LEONES valida.** Hermes sólo puede elegir entre los candidatos entregados por LEONES.
2. **El usuario decide el backend.** Puede seleccionar Magnitude, ODS o ambos.
3. **La selección no ejecuta.** El plan mantiene `execution_authorized=false`, `measurement_authorized=false` y `measured=false` hasta superar los gates físicos.
4. **El benchmark es común.** Magnitude y ODS terminan exponiendo el modelo seleccionado al mismo protocolo de medición de LEONES.
5. **El resultado es por tarea.** Se conserva Leo001…Leo010, sus ejecuciones, latencia y métricas disponibles.
6. **La recomendación llega después de medir.** Las cifras externas sirven para selección/evidencia, pero nunca se convierten en mediciones locales.
7. **La repetición es nativa.** Una nueva ejecución puede volver a Hermes, seleccionar otro candidato y repetir exactamente Leo001…Leo010.
8. **LLMFit/FitLLM queda fuera de RC3.** No es dependencia ni selector.

## Suite Leo

| ID | Familia | Qué mide |
|---|---|---|
| **Leo001** | Tool use | Selección y uso correcto de herramienta |
| **Leo002** | Multi-step | Operaciones dependientes en orden |
| **Leo003** | Files/artifacts | Creación y verificación de artefactos |
| **Leo004** | Recovery | Recuperación ante fallo |
| **Leo005** | Long horizon | Conservación del estado y requisitos |
| **Leo006** | Research | Reconciliación y trazabilidad de evidencia |
| **Leo007** | Coding | Inspección, parche y pruebas |
| **Leo008** | Local operations | Operación bajo permisos controlados |
| **Leo009** | Safety | Rechazo seguro + ejecución de la parte permitida |
| **Leo010** | Cost/latency | Cumplimiento de presupuesto |

El catálogo contiene actualmente estas diez tareas. fileciteturn37file0

## Ciclo de repetición

```text
Hermes → modelo X → backend → Leo001…Leo010 → resultados
                                      ↓
Hermes → modelo Y → backend → Leo001…Leo010 → resultados
                                      ↓
                           comparación tarea a tarea
```

No se crea otro benchmark para comparar modelos: **se reutiliza exactamente la misma suite Leo**.

## Comandos

Nuevo modelo elegido por Hermes:

```bash
python scripts/leones_task_benchmark.py \
  --base-url http://localhost:8080/v1 \
  --decision-json path/to/decision.json \
  --select-with-hermes
```

Candidato concreto:

```bash
python scripts/leones_task_benchmark.py \
  --base-url http://localhost:8080/v1 \
  --model <candidate-id>
```

El artefacto es `artifacts/task-benchmark-latest.json` y conserva los IDs Leo001…Leo010.

## Estado

**Arquitectura FIJADA en RC3.** La implementación queda en la rama de integración correspondiente y la validación física se mantiene separada: Hermes, Magnitude/ODS y las mediciones reales de Leo001…Leo010 sólo se declaran validadas después de ejecutarlas sobre Ubuntu.
