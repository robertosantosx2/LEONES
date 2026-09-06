# LEONES RC4 — physical handoff, task measurement and evidence

**Estado:** 🟡 **RC4 EN DESARROLLO**  
**Predecesor:** RC3 (fase cerrada el 5 de septiembre de 2026)  
**Decisión:** 6 de septiembre de 2026

## 1. Objetivo

RC4 no rediseña la arquitectura de RC3. Convierte en ejecución real el backlog que RC3 dejó explícitamente fuera de su cierre:

- handoff real Hermes → Magnitude;
- handoff real Hermes → ODS;
- gate de consentimiento y preparación física;
- ejecución de la suite canónica Leo001…Leo010;
- medición LEONES reproducible;
- evidencia MEASURED;
- comparación de caminos cuando ambos estén medidos.

La regla de continuidad es estricta: **RC3 sigue siendo la frontera contractual; RC4 añade la capa física de ejecución y medición sin mover la autoridad de LEONES.**

## 2. Arquitectura canónica RC4

```text
                         UBUNTU / EQUIPO REAL
                                  ↓
                     hardware_profile.py
                                  ↓
                       hardware-profile.v1
                                  ↓
                         candidate-set.v1
                                  ↓
                              HERMES
                         recomendación
                                  ↓
                         elección usuario
                                  ↓
                    selección/configuración.v1
                                  ↓
                        artifact-resolution
                                  ↓
                         CONSENTIMIENTO
                                  ↓
                  ┌───────────────┴───────────────┐
                  ↓                               ↓
             MAGNITUDE                           ODS
          profile / tune                    install / stack
                  ↓                               ↓
                  └───────────────┬───────────────┘
                                  ↓
                       verificación física
                                  ↓
                         Leo001 … Leo010
                                  ↓
                             MEDICIÓN
                                  ↓
                     runtime-benchmark-evidence
                                  ↓
                         evidencia MEASURED
                                  ↓
                         recomendación final
```

### Regla de autoridad

**Hermes propone. El usuario elige. Magnitude/ODS ejecutan. LEONES autoriza, verifica, mide y sentencia.**

Ningún `estimated`, `hosted`, `observed` o resultado de un proveedor externo puede convertirse por sí mismo en `measured`.

## 3. Frontera de interfaz

RC4 debe conservar interfaces estables y sustituibles. LEONES no duplica instaladores ni runtimes.

La interfaz de usuario debe expresar **funciones y estados**, no nombres internos de herramientas. Un usuario debe poder distinguir como mínimo:

1. **DESCUBRIR** — qué tiene físicamente el equipo;
2. **ELEGIR** — qué modelo/configuración quiere probar;
3. **PREPARAR** — qué camino de ejecución ha elegido;
4. **AUTORIZAR** — qué acción física va a realizarse;
5. **PROBAR** — qué tarea se está ejecutando;
6. **MEDIR** — qué se ha medido realmente;
7. **RESULTADO** — qué evidencia ha quedado registrada.

Los estados deben ser inequívocos y no deben presentar una estimación como resultado físico. La interfaz debe mantener navegación y terminología coherentes con el resto de la web de LEONES y no introducir nomenclatura histórica de RC2/LOTB como si fuese el camino canónico RC4.

## 4. Contrato de ejecución

Antes de ejecutar debe existir, como mínimo:

- `hardware-profile.v1`;
- candidato elegido;
- `user-selection.v1`;
- artefacto concreto resuelto;
- runtime/backend y stack;
- consentimiento explícito;
- identidad de ejecución.

La ejecución debe conservar procedencia suficiente para reconstruir:

- hardware;
- modelo y revisión;
- cuantización/formato;
- artefacto y SHA-256;
- runtime/backend y versión;
- stack y versiones relevantes;
- configuración de contexto y generación;
- tarea Leo;
- timestamps UTC;
- `execution_id`;
- métricas reales.

## 5. Suite canónica

RC4 adopta los identificadores públicos ya fijados por RC3:

| ID | Tarea |
|---|---|
| Leo001 | Tool use |
| Leo002 | Multi-step |
| Leo003 | Files / artifacts |
| Leo004 | Recovery |
| Leo005 | Long horizon |
| Leo006 | Research / evidence |
| Leo007 | Coding |
| Leo008 | Local operations |
| Leo009 | Safety |
| Leo010 | Cost / latency |

Los IDs son estables. Las especificaciones de tarea, entorno y grader deben estar versionadas antes de declarar resultados oficiales.

Cada resultado debe permanecer identificado por **modelo + runtime/backend + stack + ejecución + tarea**.

## 6. Medición

RC4 no reduce el benchmark a tokens/segundo. Para las ejecuciones compatibles se registrarán, cuando estén disponibles:

- TTFT;
- TPOT;
- tokens/s;
- tiempo total;
- p50/p95/p99 cuando exista una serie suficiente;
- memoria utilizada;
- errores/timeout;
- resultado de tarea;
- recursos relevantes.

La comparación debe respetar el protocolo congelado. El principio de evaluación limpia exige separar desarrollo/validación de la medición final y no optimizar contra un conjunto de prueba que ya se presenta como limpio.

## 7. Estados de evidencia

```text
DECLARED
   ↓
ESTIMATED
   ↓
OBSERVED
   ↓
MEASURED
```

Solo una ejecución controlada sobre el equipo real puede producir `MEASURED`.

`OBSERVED` no equivale a `VALIDATED` y `VALIDATED` no debe usarse como sinónimo de `MEASURED` si el contrato no lo define así.

## 8. Primera implementación RC4

Orden de trabajo mínimo:

1. congelar contratos de ejecución/medición;
2. implementar el execution gate con consentimiento explícito;
3. implementar adaptador de handoff Hermes → Magnitude;
4. implementar adaptador de handoff Hermes → ODS;
5. implementar runner Leo001…Leo010;
6. conectar resultados al evidence bridge existente;
7. crear gate RC4 estático/CI;
8. ejecutar validación física en Ubuntu;
9. repetir la misma suite sobre el segundo camino cuando proceda;
10. publicar evidencia y recomendación comparativa.

## 9. No objetivos de RC4

RC4 no debe:

- reabrir RC3;
- sustituir `hardware_profile.py`;
- convertir Hermes en autoridad física;
- introducir otro selector de modelos;
- convertir Magnitude u ODS en selectores;
- reinstalar o duplicar runtimes ya proporcionados por sus caminos canónicos;
- recuperar FitLLM/LLMFit como dependencia;
- usar LOTB como nombre del benchmark canónico de LEONES;
- usar velocidad de Artificial Analysis u otro proveedor como `measured_tps` local.

## 10. Criterio de cierre RC4

RC4 podrá declararse cerrada cuando exista evidencia reproducible de extremo a extremo para los caminos físicos que se hayan incluido en el alcance:

```text
hardware → candidate → Hermes → user selection
→ artifact → consent → handoff → physical verification
→ Leo001…Leo010 → measurement → MEASURED evidence
→ final recommendation
```

La evidencia debe ser trazable, reproducible y distinguible de estimaciones y observaciones externas.
