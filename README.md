# LEONES

## Estado del proyecto

| Bloque | Estado | Resultado |
|---|---|---|
| V1 / A01 | 🟢 Cerrado | Cadena real de selección → ejecución → benchmark → evidencia |
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado | Contrato de medición real + auditoría física |
| JALÓN 4 | 🟢 **Cerrado** | Metodología AA + contratos de integración + benchmark de tareas + tiers |
| RC1 | 🟢 **Validado** | Ejecución efectiva end-to-end |
| RC2 | 🟢 **Histórica** | Beta previa; no es el camino canónico RC3 |
| **RC3** | 🟢 **Implementación cerrada · 🟡 físico pendiente** | **`hardware_profile.py` → candidatos → Magnitude/ODS → medición LEONES** |

## RC3 — arquitectura canónica

RC3 simplifica deliberadamente el camino de instalación y selección. **La sonda física canónica es `scripts/hardware_profile.py`.** Hermes participa como ecosistema local de runtime/model-fit y Oh My Hermes (OMH) como capa operativa de routing, workflows, handoffs y gates. LEONES normaliza, reconcilia y conserva la autoridad sobre verificación física, ejecución, medición y evidencia.

```text
              scripts/hardware_profile.py
                 (sonda física canónica)
                           ↓
                  hardware-profile.v1
                           ↓
         HERMES runtime hints  +  OMH operación
                           ↓
                    LEONES normalize
                           ↓
                  candidate-set.v1
                           ↓
                ┌──────────┴──────────┐
                ↓                     ↓
           MAGNITUDE                  ODS
        profiling/tuning         install/stack
                ↓                     ↓
                └──────────┬──────────┘
                           ↓
                    selected runtime
                           ↓
                      LEONES tasks
                           ↓
                    real measurement
                           ↓
                       evidence
                           ↓
                     recommendation
```

### Regla de autoridad

**LEONES descubre el hardware. OMH organiza. El usuario elige. Magnitude u ODS preparan/ejecutan. LEONES verifica, mide y sentencia.**

Hermes aporta ecosistema runtime/model-fit; OMH no sustituye la sonda física ni los contratos de LEONES. Ninguna estimación externa se convierte automáticamente en evidencia LEONES. La validación física final de los handoffs queda pendiente en Ubuntu.

### FitLLM / LLMFit — fuera de RC3

FitLLM/LLMFit queda **fuera del camino canónico RC3**: no es dependencia, no se instala, no bloquea el arranque y no participa en la selección RC3. Se conserva como conocimiento histórico y como posible `CandidateProvider` futuro, completamente desacoplado de la instalación y del flujo físico.

### Handoff de usuario

Una vez descubierto y normalizado el equipo y construidos los candidatos, el usuario elige explícitamente un único camino:

- **Magnitude** → perfilado, estimación, tuning y ejecución mediante sus interfaces canónicas.
- **ODS** → instalación y stack local mediante sus interfaces canónicas.

LEONES no duplica instaladores ni runtimes. Antes de medir, verifica físicamente lo que realmente quedó instalado y ejecutable.

## Instalación RC3

La instalación canónica queda reducida a un bootstrap limpio:

```text
INSTALAR LEONES
      ↓
VERIFICAR / INSTALAR HERMES + OMH
      ↓
scripts/hardware_profile.py  (sonda física canónica)
      ↓
hardware-profile.v1
      ↓
RC3 adapter + Hermes runtime hints
      ↓
LEONES reconciliation → candidate-set.v1
      ↓
ELEGIR MODELO / CONFIGURACIÓN
      ↓
RESOLVER ARTEFACTO CONCRETO
      ↓
ELEGIR MAGNITUDE U ODS
      ↓
CONSENTIMIENTO
      ↓
PREPARAR / INSTALAR
      ↓
VERIFICAR FÍSICAMENTE
      ↓
TAREAS LEONES → MEDIR → EVIDENCIA
```

El instalador no descarga modelos ni stacks de usuario sin consentimiento. Las comprobaciones independientes son:

```bash
hermes doctor
omh doctor
```

El detalle contractual está en `docs/RC3-ARCHITECTURE.md`.

## Gate RC3

La implementación queda protegida por `scripts/rc3_release_gate.py` y `.github/workflows/rc3-release-gate.yml`. El gate valida contratos, evidencia, resolución de artefactos, selección explícita, frontera de ejecución y sonda física canónica, además de ejecutar la regresión Python.

El gate **no** declara como realizadas las operaciones que sólo pueden comprobarse en Ubuntu físico: handoff real Hermes → Magnitude, handoff real Hermes → ODS, instalación/preparación real, benchmark de tareas y evidencia comparativa.

## RC2

RC2 permanece como línea histórica de validación. Sus documentos y adaptadores pueden conservar integraciones anteriores, pero **no forman parte del camino canónico RC3**.

## Principio LEONES

> **Los proveedores pueden proponer. LEONES puede comprobar. Solo una ejecución controlada sobre el equipo real puede producir una medición LEONES.**

RC3 queda **cerrada a nivel de implementación y contratos**. El siguiente y último gate es físico: ejecutar la instalación en Ubuntu, observar el flujo real Hermes/OMH, capturar `hardware-profile.v1`, contrastarlo con las sondas LEONES y validar ambos handoffs antes de declarar RC3 físicamente validada.
