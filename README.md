
# Estado del proyecto

| Bloque | Estado | Resultado |
|---|---|---|
| V1 / A01 | 🟢 Cerrado | Cadena real de selección → ejecución → benchmark → evidencia |
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado | Contrato de medición real + auditoría física |
| JALÓN 4 | 🟢 **Cerrado** | Metodología AA + contrato LEONES → ODS/Magnitude + benchmark de tareas + tiers |
| RC1 | 🟢 **Validado** | Ejecución efectiva end-to-end: selección → gate → Ollama → A01 → medición → evidencia |
| RC2 | 🟡 **En preparación** | Flujo completo de usuario beta; **RC2-A implementado · RC2-B LLMFit fijado · RC2-C contrato de selección fijado** |

## RC1 — ejecución efectiva validada

RC1 ha demostrado sobre un host Linux una ejecución nueva y real desde la selección autorizada hasta la evidencia A01.

```text
selección → gate → execution_authorized=true
        → Ollama → qwen2.5:0.5b-instruct-q4_K_M
        → A01 → grader=passed → measurement_kind=real
        → 53.3795 tok/s → evidencia
```

La ejecución cerrada corresponde al `execution_id` `e07822d0-d991-4e9b-985b-b9afea0c13c0`, con `A01=success`, `score=1.0`, `evidence=measured` y `measurement_kind=real`.

La evidencia anterior de 40.7666 tok/s del 27 de agosto no fue reutilizada. RC1 generó una medición nueva el 31 de agosto de 2026.

**Cierre:** [`docs/completed/RC1-EFFECTIVE-EXECUTION.md`](docs/completed/RC1-EFFECTIVE-EXECUTION.md)

## RC2 — flujo de usuario beta

RC2 convierte la ejecución validada en RC1 en un recorrido que un usuario externo pueda completar sin conocer la arquitectura interna.

```text
INSTALAR → HARDWARE → PERFILAR → CANDIDATOS → ELEGIR MODELO
          → COMPARAR TODAS LAS FUNCIONALIDADES ODS/MAGNITUDE
          → ELEGIR STACK → PREPARAR → ¿BENCHMARK?
          → SÍ: RUNNER → MEDICIÓN → EVIDENCIA → RESULTADO
          → NO: FIN
```

Antes de elegir ODS o Magnitude, LEONES debe exponer las funcionalidades relevantes de cada opción, vinculadas a su versión/ref, junto con requisitos, componentes, permisos, red, almacenamiento, privacidad y limitaciones. ODS y Magnitude siguen siendo las fuentes de sus propias capacidades; LEONES las orquesta y valida.

**Plan:** [`docs/RC2-BETA-USER-FLOW.md`](docs/RC2-BETA-USER-FLOW.md)  
**RC2-A implementado:** [`docs/RC2-A-IMPLEMENTATION.md`](docs/RC2-A-IMPLEMENTATION.md)  
**RC2-B — LLMFit:** [`docs/RC2-B-LLMFIT-HARDWARE-INTELLIGENCE.md`](docs/RC2-B-LLMFIT-HARDWARE-INTELLIGENCE.md)  
**RC2-C — selección humana:** [`docs/RC2-C-MODEL-SELECTION.md`](docs/RC2-C-MODEL-SELECTION.md)  
**Integración LLMFit:** [`docs/integrations/LLMFIT.md`](docs/integrations/LLMFIT.md)  
**Entrada beta:** [`scripts/rc2_beta.py`](scripts/rc2_beta.py)

### Beta testers

Manual de instalación actual: [`docs/BETA-TESTER-INSTALL.md`](docs/BETA-TESTER-INSTALL.md).

Los resultados de cada máquina deben producir su propio `execution_id`, timestamp, métrica y procedencia. La evidencia de una máquina nunca se reutiliza como medición de otra.

---

# Componentes principales

## Prospector, Atlas, hardware y selección

Los componentes de descubrimiento, Atlas, hardware, precio/TCO, LLMFit, selección, router y recomendación mantienen las fronteras documentadas en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

**LLMFit es la fuente especializada de inteligencia hardware/model-fit.** LEONES no reimplementa sus heurísticas: consume su salida JSON, conserva la procedencia y normaliza candidatos. Sus estimaciones permanecen como `estimated`; una medición física de LEONES sólo nace de una ejecución real del runner/protocolo correspondiente.

LLMFit documenta detección de hardware, recomendaciones JSON, planificación de hardware y benchmarking local de runtimes. [`docs/integrations/LLMFIT.md`](docs/integrations/LLMFIT.md) fija la frontera de integración.

## ODS y Magnitude

ODS se utiliza como integración de stack local y Magnitude como integración de agente/asistente. Sus contratos ya están fijados; RC2 añade una experiencia de elección informada que **expone sus funcionalidades antes de que el usuario elija**.
