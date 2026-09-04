# LEONES RC3 — Hermes + native physical discovery architecture

**Estado:** 🟢 Arquitectura fijada · discovery físico Ubuntu validado · candidate-set.v1 implementado  
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
                     usuario elige modelo
                              │
                     usuario elige stack
                       ┌──────┴──────┐
                       ▼             ▼
                   MAGNITUDE        ODS
                  profile/tune   install/stack
                       │             │
                       └──────┬──────┘
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

Puede observar:

- CPU, topología y flags;
- RAM visible/disponible para el sistema operativo;
- GPU PCI visible, identificador y driver;
- discos y red;
- presencia de herramientas aceleradoras.

Los datos ausentes se representan como `null`/lista vacía. No se inventan valores.

### RC3 discovery adapter

`scripts/rc3_hardware_discovery.py` **no vuelve a descubrir hardware**. Importa `profile()` desde `scripts/hardware_profile.py` y transforma su salida al contrato RC3 `hardware-profile.v1`, añadiendo únicamente metadatos RC3 y el estado de Hermes.

Esta separación evita que una corrección física se aplique en un parser pero no en el otro.

### Candidate set

`runtime_selection/candidate_set.py` implementa la frontera `candidate-set.v1`. Normaliza propuestas de modelos/configuraciones, conserva procedencia y distingue explícitamente `estimated` de cualquier medición. Un candidate set nunca autoriza ejecución y exige elección explícita del usuario.

### Magnitude

Se activa **sólo si el usuario lo elige**. Recibe el resultado normalizado y aporta perfilado, estimación, tuning y ejecución según su interfaz canónica.

### ODS

Se activa **sólo si el usuario lo elige**. Recibe el resultado normalizado y aporta instalación, stack, runtime y operación según su interfaz canónica.

### LEONES

- Descubre y normaliza hardware físico.
- Conserva procedencia y versión/ref.
- Reconcilia declaraciones con datos detectados.
- Construye el candidate set sin convertir estimaciones en mediciones.
- Presenta/ejecuta la decisión del usuario.
- Verifica físicamente los datos críticos.
- Ejecuta tareas controladas.
- Registra mediciones reales.
- Produce evidencia reproducible.
- Decide la recomendación final.

## 3. FitLLM / LLMFit queda fuera de RC3

LLMFit/FitLLM queda desacoplado y diferido como posible proveedor externo futuro, sin participar en el flujo canónico RC3.

No debe instalarse, invocarse ni bloquear el arranque de LEONES RC3.

```text
RC2: LLMFit → hardware/candidatos → LEONES
RC3: native physical discovery + Hermes/runtime hints → LEONES
```

## 4. Contrato `hardware-profile.v1`

El artefacto físico RC3 tiene como fuente autoritativa `leones-native-ubuntu`:

```json
{
  "schema": "hardware-profile.v1",
  "source": "leones-native-ubuntu",
  "verification": "detected",
  "cpu": {},
  "ram": {},
  "gpu": [],
  "backend": [],
  "accelerators": [],
  "discovery_timestamp": "...",
  "hermes": {
    "discovery_cli": "not-exposed"
  }
}
```

El campo `hermes` conserva el estado de la integración sin fingir que Hermes ha emitido un perfil físico.

## 5. Contrato `candidate-set.v1`

`candidate-set.v1` es una capa de **propuesta**, no de ejecución ni medición. Su construcción canónica está en `runtime_selection/candidate_set.py`.

Cada candidato puede conservar:

- `model_id`, nombre y revisión;
- rank/fit aportados por la fuente;
- cuantización, parámetros y parámetros activos cuando estén disponibles;
- runtime propuesto;
- `estimated_tps` como estimación externa, nunca como medición;
- `source`, `source_version` y `evidence_level`;
- `selection_status: CANDIDATE`;
- `execution_authorized: false`;
- `measurement_required: true`.

El contenedor añade:

```json
{
  "schema_version": "candidate-set.v1",
  "hardware": {},
  "candidates": [],
  "candidate_count": 0,
  "selection": {
    "user_choice_required": true,
    "selected_model_id": null,
    "execution_authorized": false
  },
  "measurement": {
    "measured": false,
    "runtime_benchmark_required": true
  }
}
```

El validador rechaza fugas de ejecución o medición (`command`, `argv`, `measured_tps`, `tokens_per_second`, etc.). Una estimación externa nunca se transforma automáticamente en `MEASURED`.

## 6. Handoff

```text
Ubuntu
  ↓
canonical hardware_profile.py
  ↓
hardware-profile.v1
  ↓
RC3 adapter / Hermes runtime hints (si existen y son observables)
  ↓
LEONES reconciliation
  ↓
candidate-set.v1
  ↓
usuario elige
  ├── MAGNITUDE → profiling/tuning → runtime
  └── ODS       → install/stack   → runtime
                              ↓
                         LEONES task
                              ↓
                         measurement
                              ↓
                           evidence
```

El handoff debe conservar como mínimo:

- hardware profile;
- modelo seleccionado;
- cuantización/build;
- contexto;
- runtime/backend;
- origen de cada decisión;
- versión/ref del componente;
- timestamp;
- estado `estimated` hasta que exista medición real.

## 7. Regla de autoridad

```text
Hermes propone / opera
Magnitude/ODS ejecutan y optimizan
LEONES descubre físicamente, verifica y mide
```

> Una recomendación externa puede decir que una configuración debería funcionar. Sólo una ejecución física controlada por LEONES puede producir una medición LEONES.

## 8. Instalación RC3

```text
1. instalar LEONES
2. instalar/verificar Hermes
3. verificar/activar OMH
4. LEONES descubre hardware físico
5. registrar hardware-profile.v1
6. consumir hints de Hermes sólo si son observables y trazables
7. construir candidate-set.v1
8. usuario elige modelo/configuración
9. usuario elige Magnitude u ODS
10. consentimiento
11. instalar/preparar el stack elegido
12. verificar físicamente
13. ejecutar tareas LEONES
14. medir
15. registrar evidencia
```

## 9. Gate físico de RC3

La pasada física de Ubuntu observó y reconcilió correctamente:

- Intel Core i5-1035G1, 4 núcleos físicos / 8 hilos;
- Intel Iris Plus Graphics G1, PCI `8086:8a56`, driver `i915`;
- `vram_gb: null`, porque no se dispone de una fuente fiable que permita atribuir VRAM dedicada a esta GPU integrada;
- `memory_modules: []` y `vendor_probe: null` en esta sesión: son campos opcionales no observados, no discrepancias físicas;
- Hermes 0.21.0 instalado y `hermes doctor` ejecutado;
- OMH 2.0.0 con 46/46 comprobaciones OK.

La reconciliación física ejecutada el 4 de septiembre de 2026 produjo:

```text
CANONICAL: Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz
CANONICAL: 4 cores / 8 threads
GPU: 0000:00:02.0 / 8086:8a56 / i915
RC3 ADAPTER: mismos valores críticos
RC3 CANONICAL RECONCILIATION: PASS
```

Estos son **hechos de discovery**, no benchmarks. Además, `i915` es el driver Linux observado: no se debe interpretar por sí solo como confirmación de un backend de inferencia GPU utilizable por el runtime elegido.

## 10. Estado de RC3

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
- [ ] Test físico de normalización → candidate-set.v1.
- [ ] Handoff real Hermes → Magnitude validado.
- [ ] Handoff real Hermes → ODS validado.
- [ ] Benchmark de tareas sobre ambos caminos.
- [ ] Evidencia comparativa.

Los últimos puntos requieren ejecución física real y no deben cerrarse por diseño documental.
