# LEONES RC3 — Hermes + native physical discovery architecture

**Estado:** 🟢 Arquitectura fijada · discovery físico Ubuntu validado · candidate-set.v1 · evidencia externa · decisión determinista · selección explícita de usuario  
**Predecesor:** RC2  
**Decisión:** 4 de septiembre de 2026

## 1. Objetivo

RC3 desacopla el descubrimiento físico de cualquier proveedor externo. Hermes participa en el ecosistema local y puede aportar runtime/model-fit, pero LEONES no presupone que su CLI exponga una interfaz estable y machine-readable de hardware.

La ejecución física en Ubuntu confirmó que Hermes 0.21.0 está instalado y operativo a nivel de `doctor`, mientras que su CLI pública no ofrece un comando de hardware estructurado. Por tanto, RC3 usa una sonda nativa LEONES para producir el `hardware-profile.v1` autoritativo.

La decisión de implementación queda fijada: **`scripts/hardware_profile.py` es la única sonda física canónica**. `scripts/rc3_hardware_discovery.py` es únicamente un adaptador de contrato RC3 y no debe contener un segundo parser de CPU/GPU/RAM.

La arquitectura queda:

```text
                         UBUNTU REAL
                              │
                              ▼
                 scripts/hardware_profile.py
                    CANONICAL PHYSICAL PROBE
                              │
                              ▼
                     hardware-profile.v1
                              │
             ┌────────────────┴────────────────┐
             │                                 │
             ▼                                 ▼
     RC3 discovery adapter              HERMES 0.21.0
   (contract mapping only)          runtime/model ecosystem
             │                                 │
             └────────────────┬────────────────┘
                              ▼
                     LEONES reconciliation
                              │
                     candidate-set.v1
                              │
                 HF + Artificial Analysis
                              │
                    deterministic ranking
                              │
                 recomendación (no selección)
                              │
                     usuario elige modelo
                              │
                  selección/configuración.v1
                              │
                     usuario elige stack
                       ┌──────┴──────┐
                       ▼             ▼
                   MAGNITUDE        ODS
                  profile/tune   install/stack
                       │             │
                       └──────┬──────┘
                              ▼
                    consentimiento explícito
                              │
                              ▼
                       selected runtime
                              │
                              ▼
                         LEONES tasks
                              │
                              ▼
                      real measurement
                              │
                              ▼
                           evidence
                              │
                              ▼
                        recommendation
```

## 2. Responsabilidades

### Hermes

- Aportar el agente, herramientas y runtime local que correspondan.
- Evaluar modelos/configuraciones dentro de las capacidades que realmente exponga su interfaz.
- Servir como bootstrap operativo cuando el flujo lo requiera.
- No se considera fuente autoritativa de hardware si no entrega un artefacto machine-readable verificable.

### LEONES canonical physical probe

`scripts/hardware_profile.py` es la fuente única de hechos físicos de bajo nivel. Usa `/proc/cpuinfo`, la topología machine-readable de `lscpu`, sysfs PCI y herramientas estándar cuando están disponibles, evitando depender de etiquetas localizadas de `lscpu`.

Puede observar CPU, topología y flags; RAM visible/disponible; GPU PCI, identificador y driver; discos, red y herramientas aceleradoras. Los datos ausentes se representan como `null`/lista vacía. No se inventan valores.

### RC3 discovery adapter

`scripts/rc3_hardware_discovery.py` **no vuelve a descubrir hardware**. Importa `profile()` desde `scripts/hardware_profile.py` y transforma su salida al contrato RC3 `hardware-profile.v1`, añadiendo únicamente metadatos RC3 y el estado de Hermes.

### Candidate set

`runtime_selection/candidate_set.py` implementa la frontera `candidate-set.v1`. Normaliza propuestas de modelos/configuraciones, conserva procedencia y distingue explícitamente `estimated` de cualquier medición. Un candidate set nunca autoriza ejecución y exige elección explícita del usuario.

### Evidencia externa para la decisión

`runtime_selection/model_evidence.py` añade una segunda capa, **después del candidate set y antes de la elección del usuario**. Combina señales de Hugging Face y Artificial Analysis cuando existen:

- disponibilidad de pesos, licencia, descargas y likes en Hugging Face;
- parámetros y contexto;
- Artificial Analysis Intelligence Index y benchmarks externos;
- velocidad de proveedor externo, cuando exista, etiquetada como `hosted_output_tps`;
- estimación conservadora de memoria local a partir de parámetros/cuanti­zación.

Estas señales sirven para **ordenar y explicar candidatos**, no para crear mediciones LEONES. La salida contiene `recommended_model_id`, pero mantiene `user_choice_required: true`, `execution_authorized: false` y `measured: false`.

La instantánea inicial está en `runtime_selection/data/model-evidence.rc3.json`. Es un catálogo curado y fechado, no una base de datos viva: debe poder renovarse sin cambiar el contrato de decisión.

### Selección explícita del usuario

`runtime_selection/user_selection.py` implementa `user-selection.v1` y cierra la frontera entre recomendación y ejecución. Recibe únicamente un candidato ya presente en la decisión, registra modelo, revisión, cuantización y runtime elegidos, y exige una elección explícita de **Magnitude u ODS**.

La selección conserva deliberadamente:

- `execution_authorized: false`;
- `measurement_authorized: false`;
- `measured: false`;
- `consent_required_before_execution: true`.

Por tanto, **elegir no equivale a autorizar ejecutar**. El consentimiento/autoridad de ejecución será un gate posterior, justo antes de la preparación y ejecución física.

### Magnitude

Se activa **sólo si el usuario lo elige**. Recibe el resultado normalizado y aporta perfilado, estimación, tuning y ejecución según su interfaz canónica.

### ODS

Se activa **sólo si el usuario lo elige**. Recibe el resultado normalizado y aporta instalación, stack, runtime y operación según su interfaz canónica.

### LEONES

- Descubre y normaliza hardware físico.
- Conserva procedencia y versión/ref.
- Reconcilia declaraciones con datos detectados.
- Construye el candidate set sin convertir estimaciones en mediciones.
- Enriquece candidatos con evidencia externa trazable.
- Presenta una recomendación determinista, sin sustituir la elección del usuario.
- Registra explícitamente la elección de modelo/configuración y stack.
- Mantiene separado el consentimiento de ejecución.
- Verifica físicamente los datos críticos.
- Ejecuta tareas controladas.
- Registra mediciones reales.
- Produce evidencia reproducible.
- Decide la recomendación final.

## 3. Regla de evidencia externa

```text
Hugging Face / Artificial Analysis
             ↓
     evidencia EXTERNA
             ↓
   ranking / explicación
             ↓
     decisión del usuario
             ↓
      selección v1
             ↓
   consentimiento explícito
             ↓
      ejecución física
             ↓
     benchmark LEONES
             ↓
   evidencia MEASURED
```

**Nunca:** `Artificial Analysis speed → LEONES measured_tps`.

Una velocidad publicada por Artificial Analysis es útil para comparar proveedores/modelos, pero no predice automáticamente la velocidad de llama.cpp, Magnitude u ODS sobre el hardware del usuario. La medición local debe seguir siendo independiente.

## 4. Candidate set y evidencia

`candidate-set.v1` es una capa de **propuesta**, no de ejecución ni medición. Su construcción canónica está en `runtime_selection/candidate_set.py`.

Cada candidato puede conservar `model_id`, nombre, revisión, rank/fit, cuantización, parámetros, parámetros activos, runtime, `estimated_tps`, procedencia y `evidence_level`. El validador rechaza fugas de ejecución o medición (`command`, `argv`, `measured_tps`, `tokens_per_second`, etc.).

La capa `model-evidence.v1` añade información externa sin modificar esa frontera. La velocidad externa se conserva con semántica explícita de proveedor (`hosted_output_tps`) y no como throughput local.

## 5. Handoff

```text
Ubuntu
  ↓
canonical hardware_profile.py
  ↓
hardware-profile.v1
  ↓
RC3 adapter / Hermes runtime hints
  ↓
LEONES reconciliation
  ↓
candidate-set.v1
  ↓
HF + Artificial Analysis evidence
  ↓
deterministic ranking
  ↓
recommended_model_id + explicación
  ↓
usuario elige modelo/configuración
  ↓
user-selection.v1
  ├── MAGNITUDE → profiling/tuning → runtime
  └── ODS       → install/stack   → runtime
                              ↓
                  consentimiento / execution gate
                              ↓
                         LEONES task
                              ↓
                         measurement
                              ↓
                           evidence
```

El handoff debe conservar como mínimo hardware profile, modelo elegido, cuantización/build, contexto, runtime/backend, stack elegido, origen de cada decisión, versión/ref, timestamp y estado `estimated` hasta que exista medición real.

## 6. FitLLM / LLMFit queda fuera de RC3

LLMFit/FitLLM queda desacoplado y diferido como posible proveedor externo futuro, sin participar en el flujo canónico RC3.

No debe instalarse, invocarse ni bloquear el arranque de LEONES RC3.

## 7. Regla de autoridad

```text
Hermes propone / opera
Fuentes externas informan
Usuario elige
Magnitude/ODS ejecutan y optimizan
LEONES descubre físicamente, verifica y mide
```

> Una recomendación externa puede decir qué candidato parece mejor. El usuario decide qué quiere probar. Sólo una ejecución física controlada por LEONES puede producir una medición LEONES.

## 8. Estado de RC3

- [x] Arquitectura Hermes + native discovery fijada.
- [x] LLMFit/FitLLM separado del camino canónico.
- [x] Magnitude y ODS definidos como handoffs alternativos elegidos por el usuario.
- [x] Hermes 0.21.0 observado en Ubuntu.
- [x] OMH 2.0.0 observado y `doctor` 46/46.
- [x] Discovery físico Ubuntu validado.
- [x] `scripts/hardware_profile.py` fijado como sonda física canónica.
- [x] `scripts/rc3_hardware_discovery.py` reducido a adaptador de contrato.
- [x] Reconciliación física canonical ↔ RC3 validada.
- [x] `candidate-set.v1` implementado y protegido contra medición/ejecución prematuras.
- [x] Tests de candidate set añadidos.
- [x] Capa `model-evidence.v1` implementada.
- [x] Catálogo inicial HF + Artificial Analysis incorporado como snapshot fechado.
- [x] Ranking determinista separado de la selección del usuario.
- [x] `user-selection.v1` implementado y protegido contra autorización/medición prematuras.
- [x] Tests de selección y elección de stack añadidos.
- [ ] Renovación automática de fuentes externas.
- [ ] Handoff real Hermes → Magnitude validado.
- [ ] Handoff real Hermes → ODS validado.
- [ ] Gate de consentimiento y preparación física validado.
- [ ] Benchmark de tareas sobre ambos caminos.
- [ ] Evidencia comparativa.

Los últimos puntos requieren ejecución física real y no deben cerrarse por diseño documental.
