# LEONES

## Estado del proyecto

| Bloque | Estado | Resultado |
|---|---|---|
| V1 / A01 | 🟢 Cerrado | Cadena real de selección → ejecución → benchmark → evidencia |
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado | Contrato de medición real + auditoría física |
| JALÓN 4 | 🟢 Cerrado | Metodología AA + contratos de integración + benchmark de tareas + tiers |
| RC1 | 🟢 Validado | Ejecución efectiva end-to-end |
| RC2 | 🟢 Histórica | Beta previa; no es el camino canónico RC3/RC4 |
| **RC3** | 🟢 Cerrada | Arquitectura canónica y contratos de fase cerrados |
| **RC4** | 🟡 En validación física | TUI integrada + intención obligatoria + evidencia HF/AA + recomendador LLMFit endurecido; frontera MEASURED pendiente de validación física Ubuntu |

## RC4 — estado fijado

**La TUI RC4 ya está integrada en `main`.** Presenta el flujo canónico sin cambiar su semántica: idioma al inicio, estado de máquina, intención múltiple obligatoria, recomendación, elección humana, stack, runtime y medición.

**Regla de autoridad RC4:** LEONES descubre el hardware. Hugging Face y Artificial Analysis aportan evidencia externa. LLMFit puede preseleccionar desde su catálogo propio. LEONES cruza identidades y presenta candidatos `ESTIMATED`. El usuario elige. Solo la ejecución física protocolizada en Ubuntu produce `MEASURED`.

- FitLLM/LLMFit es opcional; no es dependencia dura de arranque.
- La intención `user_intent[]` es obligatoria, múltiple y no vacía antes de recomendar.
- El feed externo está limitado a 100 modelos; no se inventan candidatos por padding.
- Menos de tres coincidencias válidas produce `insufficient`.
- Ninguna recomendación autoriza instalación, ejecución o medición.
- Hermes y OMH no son selectores canónicos de RC4.
- La TUI es presentación y no altera contratos de recomendación, autorización, runtime o evidencia.

### Frontera pendiente

```text
TUI + recomendación + CI
          ↓
     SELECCIÓN HUMANA
          ↓
   RUNTIME FÍSICO UBUNTU
          ↓
      MEDICIÓN REAL
          ↓
    EVIDENCIA MEASURED
```

Esta frontera **no se declara cerrada** hasta completar la validación física correspondiente. JA (`ja`) queda deliberadamente fuera de alcance de esta fase de limpieza.

## Cadena canónica RC4

```text
HARDWARE DETECTADO
      ↓
USER_INTENT[] · obligatorio · múltiple · no vacío
      ↓
RESOURCE PREFLIGHT
      ↓
HUGGING FACE + ARTIFICIAL ANALYSIS
      ↓
FEED LEONES · ≤100
      ↓
LLMFit · catálogo propio · ≤100
      ↓
INTERSECCIÓN POR IDENTIDAD
      ↓
hasta 3 ESTIMATED
      ↓
SELECCIÓN HUMANA
      ↓
ARTIFACT RESOLUTION
      ↓
RUNTIME FÍSICO UBUNTU
      ↓
BENCHMARK
      ↓
MEASURED EVIDENCE
```

## Interfaz de usuario

Norma fijada de proyecto: [`docs/LEONES-INTERFACE-RULES.md`](docs/LEONES-INTERFACE-RULES.md).

La TUI RC4 es `scripts/rc4_tui.py`. La interfaz debe conservar la separación entre `ESTIMATED`, `OBSERVED`, `MEASURED`, `UNKNOWN` y `BLOQUEADO`, además de los consentimientos separados de instalación, ejecución y medición.

## Evidencia y JALÓN 2

JALÓN 2 permanece cerrado e inmutable como evidencia histórica. La integración de la TUI y la limpieza documental no modifica sus artifacts ni su resultado.

## Principio LEONES

> **Los proveedores pueden proponer. FitLLM puede recomendar. El usuario elige. Solo una ejecución controlada sobre el equipo real puede producir una medición LEONES.**

RC3 está cerrada como fase. RC4 tiene la capa TUI/recomendación integrada y endurecida; queda abierta únicamente la frontera de validación física Ubuntu y la posterior declaración de cierre.