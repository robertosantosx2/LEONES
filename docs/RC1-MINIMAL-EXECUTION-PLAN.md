# LEONES — RC1: plan mínimo operativo

> **Estado: PLAN ACTIVO — Release Candidate 1**
>
> Punto de partida: **JALÓN 3 cerrado**.
>
> Objetivo: construir la versión mínima de LEONES que pueda responder, sobre hardware de consumo real, **qué camino local conviene, qué modelo/configuración encaja y qué rendimiento se obtiene realmente**, y publicar después esa evidencia en MANADA.

## 1. Decisión arquitectónica congelada para RC1

LEONES no debe convertirse en otro servidor local, otro agente ni otro benchmark aislado.

```text
HARDWARE REAL
     ↓
LLMFit / FIT
     ↓
LEONES
     ↓
DECISIÓN: ODS / SOHO  ↔  Magnitude / ASISTENTE PERSONAL
     ↓
runtime / agente
     ↓
Hermes cuando lo aporte ODS
     ↓
TAREA REAL / A01
     ↓
MEDICIÓN LEONES
     ↓
EVIDENCIA
     ↓
RECOMENDACIÓN
     ↓
MANADA
```

### Regla esencial

**LLMFit ayuda a saber qué puede encajar; LEONES decide qué probar; ODS o Magnitude aportan la experiencia de ejecución que corresponda; LEONES mide; MANADA publica.**

No se copiarán dentro de LEONES las funciones que ya resuelven bien ODS, Magnitude o LLMFit.

| Pieza | Responsabilidad RC1 | No debe hacer |
|---|---|---|
| **LLMFit** | detección/normalización de hardware y primera estimación de fit | declarar rendimiento LEONES medido |
| **LEONES** | decisión, contratos, procedencia, selección, medición, validación y recomendación | convertirse en servidor AI generalista |
| **ODS** | opción de despliegue SOHO y capacidades ya aportadas, incluido Hermes cuando corresponda | sustituir la medición independiente de LEONES |
| **Magnitude** | opción orientada a asistente personal cuando sea el camino adecuado | convertirse en fuente de verdad del rendimiento |
| **Hermes de ODS** | harness/agente cuando ODS lo aporte de forma usable | duplicarse innecesariamente en LEONES |
| **llama.cpp** | ruta directa/control y fallback | desaparecer mientras siga siendo útil como referencia |
| **MANADA** | publicación del conocimiento y evidencia | recalcular o inventar métricas |

---

# 2. Por qué cambia el plan

JALÓN 3 ya demuestra que LEONES puede cerrar **ejecución → medición → evidencia**. El siguiente salto no es construir otro runtime, sino **integrar lo que ya existe y reservar a LEONES la decisión, la medición y la procedencia**.

ODS ya cubre una gran parte del problema de un servidor local: inferencia, UI, agentes, workflows, RAG, voz, búsqueda, observabilidad y gestión del stack. Su documentación actual también describe detección de hardware, tiers y selección de modelos por envolvente de memoria.

Por tanto, LEONES debe tratar ODS como **plataforma de ejecución integrable y medible**, no reconstruirla.

Magnitude queda después de la decisión de LEONES como alternativa para el escenario de **asistente personal**. La pregunta de RC1 será:

> **Para este hardware, tarea y perfil de uso, ¿conviene la ruta ODS/SOHO o la ruta Magnitude/asistente personal?**

Si ODS aporta Hermes de forma operativa, LEONES lo aprovechará. Se conserva el contrato de evaluación A01 y la correlación de evidencia, pero no se crea un segundo Hermes salvo necesidad demostrada.

---

# 3. Hardware de consumo: eje de RC1

RC1 prioriza hardware doméstico/prosumer:

- CPU-only;
- 8–16 GB RAM;
- 16–32 GB RAM;
- 32–64 GB RAM;
- GPU de consumo;
- 8 GB VRAM;
- 12 GB VRAM;
- 16 GB VRAM;
- 24 GB VRAM;
- memoria unificada cuando sea relevante.

Los tiers se expresarán por **capacidad**, no por catálogo de productos.

### Tiers iniciales

| Tier | Envolvente | Uso de referencia |
|---|---|---|
| C0 | CPU/memoria limitada | modelos pequeños |
| C1 | CPU doméstico, ~8–16 GB | inferencia local ligera |
| C2 | 16–32 GB RAM | modelos pequeños/medianos |
| C3 | 8–12 GB VRAM | GPU prosumer de entrada |
| C4 | 12–16 GB VRAM / equivalente | prosumer ampliado |
| C5 | 16–24 GB VRAM / 32–64+ GB unificada | consumo alto |
| C6 | 24 GB+ VRAM / memoria muy amplia | workstation doméstica |

Un tier **no afirma velocidad**. Describe una envolvente de capacidad. La velocidad real la obtiene LEONES.

---

# 4. Fases

## Fase 0 — Congelación de JALÓN 3

**CERRADA.** No se reabre salvo defecto que rompa el contrato.

Gate actual: 256 tests PASS, árbol limpio, contrato llama.cpp PASS, A01 real PASS y consistencia de hardware PASS.

**Ubuntu: NO.**

## Fase 1 — Núcleo mínimo de decisión

Construir solo:

- `hardware-profile.v1`;
- `llmfit-result.v1`;
- `model-candidate.v1`;
- `path-decision.v1`;
- `runtime-plan.v1`;
- `agent-plan.v1`;
- `measurement-plan.v1`;
- `evidence-reference.v1`;
- `recommendation.v1`.

Debe poder contestar: hardware → fit → restricciones de tarea → camino ODS/Magnitude → qué medir.

**GitHub/CI. Ubuntu: NO.**

## Fase 2 — LLMFit → LEONES

LLMFit será la primera capa hardware-aware de fit. LEONES conservará hardware, backend, memoria, candidatos, cuantización, contexto, estimaciones, runtime sugerido, versión, timestamp y referencia de salida.

LEONES no copiará su algoritmo ni su base de modelos.

```text
LLMFit → fit normalizado → LEONES → Atlas/evidencia/tarea/contexto → candidatos autorizables
```

**GitHub/CI. Ubuntu: NO para el adapter.**

## Fase 3 — Tiers de hardware de consumo

Formalizar C0–C6 como contrato de capacidades. Incluir RAM, VRAM/unified memory, CPU, backend, memoria utilizable y, cuando exista, ancho de banda. Separar siempre compatibilidad, estimación y medición.

**GitHub/CI. Ubuntu: NO.**

## Fase 4 — Decisión ODS vs Magnitude

Crear `path-decision.v1`.

### ODS / SOHO

Ruta preferente cuando el objetivo sea una máquina local de hogar/pequeña oficina con servicios integrados: inferencia, UI, agentes, Hermes, workflows, RAG, voz, observabilidad y gestión.

### Magnitude / asistente personal

Ruta preferente cuando la experiencia de asistente personal sea el objetivo principal y Magnitude resulte el camino más directo para ese hardware y tarea.

La decisión considera hardware, memoria, backend, tarea, contexto, modelo, instalación, complejidad, rendimiento esperado y evidencia.

**GitHub/CI. Ubuntu: NO.**

## Fase 5 — Adapter ODS + Hermes aportado por ODS

Adapter mínimo para identificar ODS/versionado, health, runtime, modelo, configuración, ejecución controlada y artefactos.

Si ODS aporta Hermes:

```text
ODS → Hermes → A01/tarea real → trayectoria/tool calls/errors/recovery → evidencia LEONES
```

No se duplica Hermes.

**GitHub/CI. Ubuntu: NO.**

## Fase 6 — Adapter Magnitude

Adapter fino para identidad/versionado, hardware, modelo/runtime, configuración, tarea, métricas, resultado, errores y artefactos. No se incorpora el motor de Magnitude al código de LEONES.

**GitHub/CI. Ubuntu: NO.**

## Fase 7 — E2E sintético

```text
hardware fixture → LLMFit fixture → LEONES → ODS path / Magnitude path → agent fixture → evidence → recommendation
```

Una prueba E2E mínima en CI debe demostrar que ambas rutas respetan el mismo contrato.

**Ubuntu: NO.**

## Fase 8 — Physical Run Manifest

Generar antes de tocar la máquina: host, CPU, RAM, GPU/VRAM, backend, OS, modelo, revisión, quant, contexto, runtime/version, ODS/Magnitude/Hermes version, tarea, warm-up, N, métricas, comandos, artefactos y PASS/FAIL.

Reutiliza el contrato de JALÓN 3.

**Ubuntu: NO.**

---

# 5. 🟡 Primera intervención imprescindible de Ubuntu

**No se pedirá Ubuntu antes de llegar aquí.**

La intervención será una única secuencia preparada:

1. perfilar hardware real;
2. validar el tier;
3. ejecutar LLMFit real y conservar su salida;
4. ejecutar la selección LEONES;
5. instalar/validar ODS **solo si es la ruta elegida**;
6. validar Hermes si ODS lo aporta y la tarea lo requiere;
7. validar Magnitude solo si la decisión corresponde a esa ruta;
8. ejecutar la medición física con LEONES;
9. comparar rutas solo si ambas se ejecutan bajo condiciones equivalentes;
10. conservar toda la evidencia.

**Aquí será cuando avise al usuario de que Ubuntu es imprescindible.**

No se diseñará arquitectura en Ubuntu.

---

# 6. Benchmark mínimo

Primero benchmark directo de runtime:

- TTFT si está disponible;
- generación tok/s;
- tokens entrada/salida;
- tiempo total;
- memoria;
- VRAM;
- consumo si es fiable.

Después benchmark agentivo:

- éxito/fallo;
- score de tarea;
- tool calls;
- errores;
- recovery;
- duración;
- tokens/coste si existe;
- artefactos.

No se mezclan throughput, TTFT, memoria, potencia y score agentivo en una única cifra.

---

# 7. Regla de comparación ODS ↔ Magnitude

Solo se comparan si se mantienen:

```text
misma máquina
misma familia/modelo
misma cuantización
mismo contexto
misma tarea
misma política de warm-up
mismo N
misma semántica de métricas
```

Los resultados externos o estimados no se transforman en mediciones LEONES.

---

# 8. Recomendador mínimo RC1

Debe responder:

1. qué camino recomienda — ODS o Magnitude;
2. qué modelo/configuración;
3. por qué encaja;
4. qué proviene de LLMFit;
5. qué proviene de fuentes externas;
6. qué ha medido LEONES;
7. qué está verificado;
8. qué alternativa fue descartada;
9. bajo qué condiciones es válida la recomendación.

---

# 9. Publicación en MANADA

MANADA presenta el conocimiento; no recalcula evidencia.

Registro mínimo:

- `execution_id`;
- hardware y tier;
- LLMFit/version;
- camino elegido;
- ODS/Magnitude version;
- runtime;
- Hermes si aplica;
- modelo/revisión/quant;
- contexto y tarea;
- benchmark y métricas;
- evidence type;
- measurement kind;
- timestamp UTC;
- hashes/referencias de artefactos;
- validación;
- recomendación.

---

# 10. Gate de RC1

RC1 pasa cuando exista al menos un caso real completo:

```text
REAL HARDWARE            PASS
LLMFIT                    PASS
LEONES SELECTION          PASS
ODS o MAGNITUDE           PASS
HERMES/A01 si corresponde PASS
LEONES MEASUREMENT        PASS
EVIDENCE                  PASS
RECOMMENDATION            PASS
MANADA                    PASS
```

No hace falta soportar todas las plataformas. Hace falta una cadena completa, reproducible y documentada.

---

# 11. Qué se aparca

Hasta después de RC1:

- segunda oleada completa de runtimes;
- multi-GPU exhaustivo;
- automatización multiplataforma extensa;
- dashboards propios complejos;
- catálogo exhaustivo;
- duplicación de Hermes;
- reimplementación de ODS, Magnitude o LLMFit;
- benchmarks masivos sin necesidad para el camino canónico;
- optimizaciones prematuras.

> **Si una pieza externa ya resuelve el problema y podemos integrarla con evidencia, no la reconstruimos.**

---

# 12. Deprecación

El repositorio ya dispone de superficie de deprecación previa a RC1:

- `deprecated/pre-rc1-legacy`;
- `deprecated/pre-rc1-legacy-2026-08-28`;
- [`docs/DEPRECATION-MAP.md`](DEPRECATION-MAP.md).

La limpieza continúa con:

```text
activo RC1
   ↓
contrato usado por el camino canónico
   ↓
referenciado por tests/documentación
   ↓
se conserva
```

Lo que no sea necesario para RC1 y no tenga valor documental/histórico se moverá a `deprecated` sin borrarlo prematuramente. La deprecación debe ser reversible y documentada.

---

# 13. Orden exacto desde ahora

```text
[1] congelar JALÓN 3
 ↓
[2] limpiar superficie RC1
 ↓
[3] LLMFit → LEONES
 ↓
[4] tiers de hardware de consumo
 ↓
[5] decisión ODS SOHO / Magnitude personal
 ↓
[6] adapter ODS + Hermes aportado por ODS
 ↓
[7] adapter Magnitude
 ↓
[8] E2E sintético
 ↓
[9] physical-run-manifest
 ↓
[10] 🟡 PEDIR UBUNTU
 ↓
[11] hardware real + LLMFit real
 ↓
[12] instalar/validar ruta elegida
 ↓
[13] benchmark runtime
 ↓
[14] benchmark Hermes/A01 si aplica
 ↓
[15] evidencia LEONES
 ↓
[16] recomendación
 ↓
[17] MANADA
 ↓
[18] RC1
```

---

# 14. Criterio de éxito

La RC1 no pretende demostrar que LEONES es el mejor runtime.

Pretende demostrar que LEONES puede:

> **partir del hardware real de una persona, reducir posibilidades con información externa, decidir de forma trazable entre caminos existentes, ejecutar una tarea real, medirla físicamente, conservar la evidencia y publicar una recomendación reproducible.**

Ese es el mínimo operativo que justifica LEONES.