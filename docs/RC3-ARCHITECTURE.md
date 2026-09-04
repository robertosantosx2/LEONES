# LEONES RC3 — Hermes + native physical discovery architecture

**Estado:** 🟢 Arquitectura fijada · primer discovery físico Ubuntu observado · validación RC3 completa pendiente  
**Predecesor:** RC2  
**Decisión:** 4 de septiembre de 2026

## 1. Objetivo

RC3 desacopla el descubrimiento físico de cualquier proveedor externo. Hermes participa en el ecosistema local y puede aportar runtime/model-fit, pero LEONES no presupone que su CLI exponga una interfaz estable y machine-readable de hardware.

La primera ejecución física en Ubuntu ha confirmado que Hermes 0.21.0 está instalado y operativo a nivel de `doctor`, mientras que su CLI pública no ofrece un comando de hardware estructurado. Por tanto, RC3 usa una sonda nativa LEONES para producir el `hardware-profile.v1` autoritativo. La implementación observa además la lógica de hardware del runtime local de Hermes cuando corresponde, pero no acopla LEONES a módulos internos de Hermes.

La arquitectura queda:

```text
                         UBUNTU REAL
                              │
             ┌────────────────┴────────────────┐
             │                                 │
     LEONES native discovery              HERMES 0.21.0
             │                         runtime/model ecosystem
             │                                 │
             ▼                                 ▼
     hardware-profile.v1              candidate / runtime hints
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

La ejecución física de RC3 observó que `hermes --help` no ofrece un comando público de hardware/system discovery. Esto coincide con la limitación documentada aguas arriba sobre resource awareness en entornos de pocos recursos. citeturn0search2

### LEONES native discovery

La sonda `scripts/rc3_hardware_discovery.py` consulta directamente el Ubuntu real y genera `hardware-profile.v1`.

Puede observar:

- CPU, topología y flags;
- RAM total/disponible;
- GPU PCI visible y driver;
- VRAM NVIDIA si `nvidia-smi` está disponible;
- módulos de memoria cuando `dmidecode` está autorizado;
- backend/accelerators detectables.

Los datos ausentes se representan como `null`/lista vacía. No se inventan valores.

### Magnitude

Se activa **sólo si el usuario lo elige**. Recibe el resultado normalizado y aporta perfilado, estimación, tuning y ejecución según su interfaz canónica.

### ODS

Se activa **sólo si el usuario lo elige**. Recibe el resultado normalizado y aporta instalación, stack, runtime y operación según su interfaz canónica.

### LEONES

- Descubre y normaliza hardware físico.
- Conserva procedencia y versión/ref.
- Reconcilia declaraciones con datos detectados.
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

## 5. `candidate-set.v1`

Las propuestas de modelos/configuraciones permanecen separadas de la medición:

```json
{
  "source": "hermes-or-provider",
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

Una estimación externa nunca se transforma automáticamente en `MEASURED`.

## 6. Handoff

```text
Ubuntu
  ↓
LEONES native discovery
  ↓
hardware-profile.v1
  ↓
Hermes/runtime hints (si existen y son observables)
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

Más precisamente:

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

La primera pasada física ya ha confirmado el host real:

- Intel Core i5-1035G1, 4 núcleos / 8 hilos;
- 8 GiB DDR4, dos módulos de 4 GiB;
- Intel Iris Plus Graphics G1 visible por PCI, driver `i915`;
- ningún `nvidia-smi`, ROCm o Vulkan CLI disponible en la sesión;
- Hermes 0.21.0 instalado y `hermes doctor` ejecutado;
- OMH 2.0.0 con 46/46 comprobaciones OK.

Estos son **hechos de discovery**, no benchmarks.

La validación completa sigue abierta hasta ejecutar:

```text
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

Si fuentes observables discrepan en CPU, RAM, GPU, VRAM, backend o memoria, el flujo debe detenerse o marcar conflicto; nunca debe convertir la discrepancia en una medición válida.

## 10. Estado de RC3

- [x] Arquitectura Hermes + native discovery fijada.
- [x] LLMFit/FitLLM separado del camino canónico.
- [x] Magnitude y ODS definidos como handoffs alternativos elegidos por el usuario.
- [x] Hermes 0.21.0 observado en Ubuntu.
- [x] OMH 2.0.0 observado y `doctor` 46/46.
- [x] Primer discovery físico Ubuntu observado.
- [x] Adaptador `hardware-profile.v1` implementado.
- [ ] Artefacto `hardware-profile.v1` generado y conservado desde la máquina física.
- [ ] Reconciliación automática discovery ↔ perfil LEONES validada.
- [ ] Handoff real Hermes → Magnitude validado.
- [ ] Handoff real Hermes → ODS validado.
- [ ] Benchmark de tareas sobre ambos caminos.
- [ ] Evidencia comparativa.

Los últimos puntos requieren ejecución física real y no deben cerrarse por diseño documental.
