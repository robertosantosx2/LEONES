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
| **RC3** | 🟢 **Arquitectura fijada · implementación cerrada · 🟡 validación física pendiente** | **hardware → candidatos → HERMES → elección usuario → Magnitude/ODS → Leo001…Leo010 → medición → evidencia → recomendación** |

## RC3 — arquitectura canónica FIJADA

La decisión arquitectónica de RC3 queda fijada: **Hermes es el único selector de modelos de RC3**. LEONES conserva la autoridad sobre hardware, contratos, consentimiento, ejecución, medición y evidencia. Magnitude y ODS son caminos de ejecución elegidos explícitamente por el usuario; no son selectores de modelos.

```text
                 UBUNTU / EQUIPO REAL
                         ↓
              hardware_profile.py
             sonda física canónica
                         ↓
                hardware-profile.v1
                         ↓
                 candidate-set.v1
                         ↓
                      HERMES
                selección de modelo
                         ↓
                  1 modelo candidato
                         ↓
                 ELECCIÓN USUARIO
                         ↓
              ┌──────────┴──────────┐
              ↓                     ↓
         MAGNITUDE                 ODS
       profiling/tuning        install/stack
              ↓                     ↓
              └──────────┬──────────┘
                         ↓
              consentimiento explícito
                         ↓
                preparación/ejecución
                         ↓
                 verificación física
                         ↓
                Leo001 … Leo010
                         ↓
                medición por tarea
                         ↓
                     evidencia
                         ↓
               recomendación final
                         ↺
              Hermes → nuevo modelo
              → misma suite de tareas
```

### Reglas fijadas

1. **Hermes selecciona; LEONES valida.** Hermes es el único selector activo en RC3.
2. **El candidate set sólo contiene propuestas.** No contiene ejecución ni medición y conserva la procedencia.
3. **El usuario elige el modelo/configuración.** Una recomendación de Hermes no autoriza por sí misma ninguna ejecución.
4. **El usuario elige Magnitude, ODS o ambos.** La elección de stack es independiente de la selección del modelo.
5. **Seleccionar no equivale a consentir ejecutar.** El consentimiento y el execution gate permanecen separados.
6. **La misma suite Leo001…Leo010 se utiliza para cada modelo/backend**, para permitir comparación tarea a tarea.
7. **Los resultados se conservan por tarea.** No se colapsan inicialmente en una única puntuación que oculte fortalezas y debilidades.
8. **La evidencia externa no es evidencia medida local.** Datos de Hugging Face, Artificial Analysis u otras fuentes sólo informan/explican la selección.
9. **La medición LEONES sólo nace de una ejecución física controlada y reproducible.**
10. **La repetición es parte del diseño.** Tras medir un modelo se puede volver a Hermes, seleccionar otro candidato y repetir exactamente la misma suite.
11. **LLMFit/FitLLM queda fuera de RC3.** No participa en la ruta canónica ni es dependencia de instalación o selección.

## Responsabilidad de cada capa

```text
hardware_profile.py  → descubre hechos físicos
candidate-set.v1     → normaliza candidatos y procedencia
HERMES               → selecciona un modelo candidato
usuario              → elige modelo/configuración y stack
Magnitude / ODS      → preparan y ejecutan el camino elegido
LEONES               → verifica, mide, conserva evidencia y recomienda
```

**Regla de autoridad:** los proveedores pueden proponer; Hermes selecciona dentro del universo de candidatos; el usuario decide qué ejecutar; sólo LEONES puede convertir una ejecución física controlada en medición y evidencia LEONES.

## Suite canónica de tareas

La suite pública queda fijada con identificadores inmutables:

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

Los IDs son identificadores públicos estables; las especificaciones de tarea, entorno y grader deben versionarse antes de declarar resultados oficiales.

## Repetición del benchmark

El ciclo de evaluación es deliberadamente repetible:

```text
HERMES
  ↓
modelo A
  ↓
Magnitude / ODS / ambos
  ↓
Leo001…Leo010
  ↓
resultados por tarea
  ↓
comparación
  ↺
HERMES → modelo B → misma suite
```

El runner de tareas permite seleccionar un nuevo modelo mediante Hermes y repetir la suite sin cambiar el protocolo de tareas. Los resultados deben permanecer identificados por modelo, runtime/backend, stack, ejecución y tarea.

## Instalación RC3

La instalación canónica queda reducida a un bootstrap limpio:

```text
INSTALAR LEONES
      ↓
VERIFICAR / INSTALAR HERMES + OMH
      ↓
scripts/hardware_profile.py
      ↓
hardware-profile.v1
      ↓
candidate-set.v1
      ↓
HERMES → selección de modelo
      ↓
ELEGIR MODELO / CONFIGURACIÓN
      ↓
RESOLVER ARTEFACTO CONCRETO
      ↓
ELEGIR MAGNITUDE / ODS / ambos
      ↓
CONSENTIMIENTO
      ↓
PREPARAR / INSTALAR
      ↓
VERIFICAR FÍSICAMENTE
      ↓
Leo001…Leo010 → MEDIR → EVIDENCIA
```

El instalador no descarga modelos ni stacks de usuario sin consentimiento. Las comprobaciones independientes son:

```bash
hermes doctor
omh doctor
```

El detalle contractual está en `docs/RC3-ARCHITECTURE.md` y `docs/RC3-HERMES-TASK-BENCHMARKS.md`.

## Gate RC3

La implementación queda protegida por `scripts/rc3_release_gate.py` y `.github/workflows/rc3-release-gate.yml`. El gate valida contratos, evidencia, resolución de artefactos, selección explícita, frontera de ejecución, sonda física canónica y la suite Leo001…Leo010.

El gate **no** declara como realizadas las operaciones que sólo pueden comprobarse en Ubuntu físico: handoff real Hermes → Magnitude, handoff real Hermes → ODS, preparación/ejecución real, benchmark completo de tareas y evidencia comparativa MEASURED.

## FitLLM / LLMFit — fuera de RC3

FitLLM/LLMFit queda **fuera del camino canónico RC3**: no es dependencia, no se instala, no bloquea el arranque y no participa en la selección RC3. Se conserva como conocimiento histórico y como posible proveedor futuro, completamente desacoplado de la instalación y del flujo físico.

## RC2

RC2 permanece como línea histórica de validación. Sus documentos y adaptadores pueden conservar integraciones anteriores, pero **no forman parte del camino canónico RC3**.

## Principio LEONES

> **Los proveedores pueden proponer. Hermes selecciona. El usuario elige. Solo una ejecución controlada sobre el equipo real puede producir una medición LEONES.**

RC3 queda **cerrada a nivel de arquitectura, implementación y contratos**. La validación física final sigue abierta hasta completar los handoffs reales y el benchmark Leo001…Leo010 bajo autoridad LEONES. La observación física existente no se reutiliza como evidencia MEASURED de RC3.
