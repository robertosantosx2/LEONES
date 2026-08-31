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
| RC2-A | 🟢 **Validado** | Orquestación beta: hardware → candidatos → modelo → ODS/Magnitude → consentimiento |
| RC2-B → RC2-H | 🟡 **En validación física** | Instalación, verificación, benchmark opcional, resultado y piloto externo |

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
          → COMPARAR ODS/MAGNITUDE → ELEGIR STACK → PLAN
          → CONSENTIMIENTO → INSTALAR → VERIFICAR
          → ¿BENCHMARK? → SÍ: RUNNER RC1 → MEDICIÓN → EVIDENCIA
                         → NO: FIN
```

### RC2-A — validado

El wizard ASCII ya demuestra la capa de decisión y consentimiento. La suite local está verde: **334 tests passed**.

LLMFit aporta la inteligencia especializada de hardware/model-fit. Sus cifras de rendimiento permanecen marcadas como `estimated`; no son evidencia física.

### RC2-B y siguientes — siguiente gate

El siguiente paso ya no es añadir abstracciones: es validar el recorrido sobre una instalación real, invocar únicamente las interfaces soportadas por el stack elegido y comprobar instalación, health checks, ejecución y evidencia.

LEONES **no crea otro instalador de ODS ni otro instalador de Magnitude, ni otro runner RC2**. Reutiliza los proyectos y runners canónicos.

**Plan:** [`docs/RC2-BETA-USER-FLOW.md`](docs/RC2-BETA-USER-FLOW.md)  
**Manual de usuario beta:** [`docs/RC2-USER-MANUAL.md`](docs/RC2-USER-MANUAL.md)  
**Manual de instalación:** [`docs/RC2-INSTALLATION-MANUAL.md`](docs/RC2-INSTALLATION-MANUAL.md)  
**Wizard:** [`scripts/rc2_wizard.py`](scripts/rc2_wizard.py)  
**Instalación/consentimiento:** [`docs/RC2-I-INSTALLATION-CONSENT.md`](docs/RC2-I-INSTALLATION-CONSENT.md)  
**Benchmark/hand-off:** [`docs/RC2-J-BENCHMARK-CONSENT.md`](docs/RC2-J-BENCHMARK-CONSENT.md)  
**LLMFit:** [`docs/integrations/LLMFIT.md`](docs/integrations/LLMFIT.md)

### Beta testers

El punto de entrada documental para un beta tester es el [manual de instalación de RC2](docs/RC2-INSTALLATION-MANUAL.md). Cada máquina debe producir su propia evidencia: nuevo `execution_id`, timestamp, métrica y procedencia. Una medición histórica nunca sustituye una ejecución actual.

## Componentes principales

### Prospector, Atlas, hardware y selección

Los componentes de descubrimiento, Atlas, hardware, precio/TCO, LLMFit, selección, router y recomendación mantienen las fronteras documentadas en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

**LLMFit es la fuente especializada de inteligencia hardware/model-fit.** LEONES no reimplementa sus heurísticas: consume su salida JSON, conserva la procedencia y normaliza candidatos. Sus estimaciones permanecen como `estimated`; una medición física de LEONES sólo nace de una ejecución real del runner/protocolo correspondiente.

## ODS y Magnitude

ODS se utiliza como integración de stack local y Magnitude como integración de agente/asistente. RC2 presenta sus funcionalidades antes de la elección y mantiene separadas recomendación, instalación y benchmark.
