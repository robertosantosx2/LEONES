# LEONES RC3 — Hermes-first discovery architecture

**Estado:** 🟢 Arquitectura fijada · implementación física pendiente de validación Ubuntu  
**Predecesor:** RC2  
**Decisión:** 4 de septiembre de 2026

## 1. Objetivo

RC3 elimina la dependencia estructural de LLMFit/FitLLM para el descubrimiento de hardware y la preselección inicial.

Hermes pasa a ser el **bootstrap de descubrimiento y fit local**. LEONES conserva la autoridad sobre la verificación física, la ejecución, la medición y la evidencia.

La selección de stack queda bajo decisión explícita del usuario:

```text
                         HERMES
                 discovery + initial fit
                           │
                           ▼
                  hardware-profile.v1
                           │
                           ▼
                  LEONES normalization
                           │
                 candidate set / fit
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
             MAGNITUDE               ODS
           profiling/tuning      install/stack
                 │                   │
                 └─────────┬─────────┘
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

- Descubrir el hardware y backend local.
- Evaluar memoria/fit de modelos locales.
- Seleccionar build/cuántización/contexto compatible cuando corresponda.
- Servir como bootstrap del runtime local.
- Entregar el conjunto inicial de modelos/configuraciones compatibles.

Hermes no es autoridad de rendimiento LEONES.

### Magnitude

Se activa **sólo si el usuario lo elige**. Recibe el resultado normalizado de Hermes/LEONES y aporta su perfilado, estimación, tuning y ejecución según su propia interfaz canónica.

### ODS

Se activa **sólo si el usuario lo elige**. Recibe el resultado normalizado de Hermes/LEONES y aporta instalación, stack, runtime y operación según su interfaz canónica.

### LEONES

- Normaliza el descubrimiento.
- Conserva procedencia y versión/ref.
- Presenta/ejecuta la decisión del usuario.
- Verifica físicamente los datos críticos.
- Ejecuta tareas controladas.
- Registra mediciones reales.
- Produce evidencia reproducible.
- Decide la recomendación final.

## 3. FitLLM / LLMFit queda fuera de RC3

LLMFit/FitLLM deja de ser dependencia dura, selector obligatorio o camino de ejecución de RC3.

No se elimina su conocimiento histórico ni su documentación de frontera: queda **desacoplado y diferido** como posible proveedor externo futuro, sin participar en el flujo canónico RC3.

No debe instalarse, invocarse ni bloquear el arranque de LEONES RC3.

La regla es:

```text
RC2: LLMFit → hardware/candidatos → LEONES
RC3: Hermes → hardware/candidatos → LEONES
```

## 4. Contrato conceptual

RC3 usa dos contratos separados:

### `hardware-profile.v1`

Describe lo observado por Hermes:

```json
{
  "source": "hermes",
  "source_version": "...",
  "cpu": {},
  "ram": {},
  "gpu": [],
  "backend": "...",
  "available_memory": {},
  "discovery_timestamp": "..."
}
```

### `candidate-set.v1`

Normaliza las propuestas sin convertirlas en mediciones:

```json
{
  "source": "hermes",
  "model": {},
  "quantization": "...",
  "runtime": "...",
  "hardware_fit": "...",
  "memory_estimate": {},
  "context": {},
  "speed_estimate": null,
  "confidence": "external",
  "evidence_level": "estimated"
}
```

Los nombres exactos de campos pueden evolucionar durante la implementación; el principio contractual no.

## 5. Handoff

El usuario selecciona uno de dos caminos:

```text
HERMES
   ↓
LEONES discovery artifact
   ↓
usuario elige
   ├── MAGNITUDE
   │      ↓
   │   profiling/tuning
   │      ↓
   │   runtime
   │
   └── ODS
          ↓
       install/stack
          ↓
       runtime

ambos
   ↓
LEONES task benchmark
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
- versión/ref de Hermes y del stack seleccionado;
- timestamp;
- estado `estimated` hasta que exista medición real.

## 6. Regla de autoridad

```text
Hermes descubre
Magnitude/ODS ejecutan y optimizan
LEONES verifica y mide
```

Más precisamente:

> Una recomendación externa puede decir que una configuración debería funcionar. Sólo una ejecución física controlada por LEONES puede producir una medición LEONES.

## 7. Instalación RC3

El orden operativo previsto es:

```text
1. instalar LEONES
2. instalar/verificar Hermes
3. Hermes descubre hardware
4. LEONES registra hardware-profile.v1
5. Hermes propone modelos/configuraciones compatibles
6. usuario elige modelo/configuración
7. usuario elige Magnitude u ODS
8. consentimiento
9. instalar/preparar el stack elegido
10. verificar físicamente
11. ejecutar tareas LEONES
12. medir
13. registrar evidencia
```

LEONES no crea un instalador alternativo de Magnitude ni de ODS.

## 8. Gate físico de RC3

La implementación completa no se declara validada hasta ejecutar en Ubuntu una máquina no previamente descrita al flujo:

```text
máquina desconocida
      ↓
Hermes discovery
      ↓
hardware-profile.v1
      ↓
LEONES cross-check
      ↓
model fit
      ↓
Magnitude / ODS
      ↓
real task
      ↓
measured
      ↓
evidence
```

Si Hermes y las sondas LEONES discrepan en CPU, RAM, GPU, VRAM, backend o memoria disponible, el flujo debe detenerse o marcar conflicto; nunca debe convertir la discrepancia en una medición válida.

## 9. Estado de RC3

- [x] Arquitectura Hermes-first fijada.
- [x] LLMFit/FitLLM separado conceptualmente del camino canónico.
- [x] Magnitude y ODS definidos como handoffs alternativos elegidos por el usuario.
- [x] Medición y evidencia siguen siendo propiedad de LEONES.
- [ ] Adaptador machine-readable de discovery Hermes validado físicamente.
- [ ] Handoff real Hermes → Magnitude validado.
- [ ] Handoff real Hermes → ODS validado.
- [ ] Benchmark de tareas sobre ambos caminos.
- [ ] Evidencia comparativa.

Los últimos puntos requieren ejecución física real y no deben cerrarse por diseño documental.
