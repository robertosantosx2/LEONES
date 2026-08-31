# LEONES

## Estado del proyecto

| Bloque | Estado | Resultado |
|---|---|---|
| V1 / A01 | 🟢 Cerrado | Cadena real de selección → ejecución → benchmark → evidencia |
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado | Contrato de medición real + auditoría física |
| JALÓN 4 | 🟢 **Cerrado** | Metodología AA + contrato LEONES → ODS/Magnitude + benchmark de tareas + tiers |
| RC1 | 🟢 **Validado** | Ejecución efectiva end-to-end: selección → gate → Ollama → A01 → medición → evidencia |
| RC2 | 🟡 **En preparación** | Flujo beta: hardware → modelo → ODS/Magnitude → consentimiento → instalación → verificación → benchmark opcional |

## RC1 — ejecución efectiva validada

RC1 ha demostrado sobre un host Linux una ejecución nueva y real desde la selección autorizada hasta la evidencia A01.

```text
selección → gate → execution_authorized=true
        → Ollama → qwen2.5:0.5b-instruct-q4_K_M
        → A01 → grader=passed → measurement_kind=real
        → 53.3795 tok/s → evidencia
```

La ejecución cerrada corresponde al `execution_id` `e07822d0-d991-4e9b-985b-b9afea0c13c0`, con `A01=success`, `score=1.0`, `evidence=measured` y `measurement_kind=real`.

## RC2 — flujo de usuario beta

RC2 convierte la ejecución validada en RC1 en un recorrido que un usuario externo pueda completar sin conocer la arquitectura interna.

```text
INSTALAR → HARDWARE → PERFILAR → CANDIDATOS → ELEGIR MODELO
          → COMPARAR TODAS LAS FUNCIONALIDADES ODS/MAGNITUDE
          → ELEGIR STACK → PLAN → CONSENTIMIENTO
          → INSTALAR → VERIFICAR → ¿BENCHMARK?
          → SÍ: AUTORIZAR → RUNNER RC1 → MEDICIÓN → EVIDENCIA
          → NO: FIN
```

El wizard ASCII de RC2 ya orquesta la parte de decisión hasta el consentimiento de instalación. La instalación y la ejecución física siguen siendo efectos explícitos de adaptadores/runners; el wizard no los dispara por sorpresa.

Antes de elegir ODS o Magnitude, LEONES debe exponer las funcionalidades relevantes de cada opción, vinculadas a su versión/ref, junto con requisitos, componentes, permisos, red, almacenamiento, privacidad y limitaciones. ODS y Magnitude siguen siendo las fuentes de sus propias capacidades; LEONES las orquesta y valida.

**Plan:** [`docs/RC2-BETA-USER-FLOW.md`](docs/RC2-BETA-USER-FLOW.md)  
**Manual de usuario beta:** [`docs/RC2-USER-MANUAL.md`](docs/RC2-USER-MANUAL.md)  
**Manual de instalación:** [`docs/RC2-INSTALLATION-MANUAL.md`](docs/RC2-INSTALLATION-MANUAL.md)  
**Wizard:** [`scripts/rc2_wizard.py`](scripts/rc2_wizard.py)  
**Instalación/consentimiento:** [`docs/RC2-I-INSTALLATION-CONSENT.md`](docs/RC2-I-INSTALLATION-CONSENT.md)  
**Benchmark/hand-off:** [`docs/RC2-J-BENCHMARK-CONSENT.md`](docs/RC2-J-BENCHMARK-CONSENT.md)  
**LLMFit:** [`docs/integrations/LLMFIT.md`](docs/integrations/LLMFIT.md)

### Beta testers

El punto de entrada documental para un beta tester es el [manual de instalación de RC2](docs/RC2-INSTALLATION-MANUAL.md). Después puede consultar el [manual de usuario](docs/RC2-USER-MANUAL.md) y el [flujo canónico](docs/RC2-BETA-USER-FLOW.md).

Cada máquina debe producir su propia evidencia: nuevo `execution_id`, timestamp, métrica y procedencia. Una medición histórica nunca sustituye una ejecución actual.

## Componentes principales

### Prospector, Atlas, hardware y selección

Los componentes de descubrimiento, Atlas, hardware, precio/TCO, LLMFit, selección, router y recomendación mantienen las fronteras documentadas en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

**LLMFit es la fuente especializada de inteligencia hardware/model-fit.** LEONES no reimplementa sus heurísticas: consume su salida JSON, conserva la procedencia y normaliza candidatos. Sus estimaciones permanecen como `estimated`; una medición física de LEONES sólo nace de una ejecución real del runner/protocolo correspondiente.

## ODS y Magnitude

ODS se utiliza como integración de stack local y Magnitude como integración de agente/asistente. Sus contratos ya están fijados; RC2 añade una experiencia de elección informada que **expone sus funcionalidades antes de que el usuario elija**.
