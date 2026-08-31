# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica libre/open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES) · [🤝 Contribuir](CONTRIBUTING.md)

---

## Qué es LEONES

LEONES construye una cadena reproducible para responder una pregunta práctica:

> **¿Qué modelo, runtime, hardware y configuración permiten realizar una tarea real de IA de forma razonable, reproducible, abierta y económicamente sostenible?**

No es otro catálogo de modelos ni otro chatbot. Es un sistema de **descubrimiento, selección, ejecución, medición, evidencia y decisión**.

Su principio rector es:

> **Una afirmación no se convierte en un hecho por repetición: se descubre, documenta, contrasta, mide cuando corresponde y conserva con su procedencia.**

---

## Cadena operativa

```text
DESCUBRIMIENTO
      ↓
ATLAS + EVIDENCIA + APERTURA
      ↓
HARDWARE + PRECIO / TCO
      ↓
LLMFIT / MODEL FIT
      ↓
SELECCIÓN DE MODELO + RUNTIME
      ↓
DECISIÓN DE STACK
      ↓
ODS / MAGNITUDE / RUNTIME DIRECTO
      ↓
ROUTER / AGENT / TAREA REAL
      ↓
BENCHMARK
      ↓
RUNNER CANÓNICO
      ↓
MEDICIÓN FÍSICA
      ↓
EVIDENCIA REPRODUCIBLE
      ↓
RECOMENDACIÓN
      ↓
CONOCIMIENTO COLECTIVO
```

### Regla de frontera

**GitHub/CI prepara y valida; el host Linux ejecuta y mide.**

CI valida contratos, esquemas, código, fixtures, tests y gates. No sustituye una medición realizada sobre el hardware y runtime reales.

El **runner existente es la vía canónica de ejecución medida**. No se crea un segundo runner paralelo ni se convierte el protocolo de medición en otra arquitectura de ejecución.

---

# Estado del proyecto

| Bloque | Estado | Resultado |
|---|---|---|
| V1 / A01 | 🟢 Cerrado | Cadena real de selección → ejecución → benchmark → evidencia |
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado | Contrato de medición real + auditoría física |
| JALÓN 4 | 🟢 **Cerrado** | Metodología AA + contrato LEONES → ODS/Magnitude + benchmark de tareas + tiers |
| RC1 | 🟢 **Validado** | Ejecución efectiva end-to-end: selección → gate → Ollama → A01 → medición → evidencia |
| RC2 | 🟡 **En preparación** | Flujo completo de usuario beta: hardware → perfilado → modelo → ODS/Magnitude → instalación → benchmark opcional |

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
INSTALAR
   ↓
DETECTAR / DECLARAR HARDWARE
   ↓
PERFILAR
   ↓
PROPONER MODELOS
   ↓
ELEGIR MODELO
   ↓
EXPLICAR TODAS LAS FUNCIONALIDADES DE ODS Y MAGNITUDE
   ↓
ELEGIR STACK
   ↓
INSTALAR / PREPARAR
   ↓
¿BENCHMARK REAL?
   ├─ NO → FIN
   └─ SÍ → RUNNER → MEDICIÓN → EVIDENCIA → RESULTADO
```

La elección ODS/Magnitude no será una caja de radio con dos nombres: LEONES deberá exponer antes de elegir las funcionalidades relevantes, componentes, requisitos, permisos, consumo, red, privacidad y limitaciones de cada alternativa, siempre vinculados a la versión/ref disponible. ODS y Magnitude siguen siendo las fuentes de sus propias capacidades; LEONES las orquesta y las valida.

**Plan RC2:** [`docs/RC2-BETA-USER-FLOW.md`](docs/RC2-BETA-USER-FLOW.md)

### Beta testers

Manual de instalación actual: [`docs/BETA-TESTER-INSTALL.md`](docs/BETA-TESTER-INSTALL.md).

Los resultados de cada máquina deben producir su propio `execution_id`, timestamp, métrica y procedencia. La evidencia de una máquina nunca se reutiliza como medición de otra.

---

# Componentes principales

## Prospector, Atlas, hardware y selección

Los componentes de descubrimiento, Atlas, hardware, precio/TCO, LLMFit, selección, router y recomendación mantienen las fronteras documentadas en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

LLMFit filtra candidatos cuando la evidencia disponible lo permite; la medición física prevalece sobre cualquier estimación.

## ODS y Magnitude

ODS se utiliza como integración de stack local y Magnitude como integración de agente/asistente. Sus contratos ya están fijados; RC2 añade una experiencia de elección informada que **expone sus funcionalidades antes de que el usuario elija**.

- [`docs/integrations/ODS.md`](docs/integrations/ODS.md)
- [`docs/integrations/Magnitude.md`](docs/integrations/Magnitude.md)
- [`docs/subprojects/LEONES-ODS-MAGNITUDE-DECISION-CONTRACT.md`](docs/subprojects/LEONES-ODS-MAGNITUDE-DECISION-CONTRACT.md)

## Runner y medición física

```text
selección autorizada → runner → runtime → modelo + hardware
                                      ↓
                                  benchmark
                                      ↓
                                  medición
                                      ↓
                                   evidence
```

El runner no inventa mediciones ni convierte fixtures en evidencia física.

---

# Estados de evidencia

| Estado | Significado |
|---|---|
| `estimated` | cálculo o estimación |
| `reported` | dato declarado por una fuente externa |
| `observed` | configuración observada en un entorno |
| `measured` | medición ejecutada por LEONES |
| `verified` | dato que superó el quality gate correspondiente |
| `unknown` | todavía no demostrado |

**Nunca se eleva un estado por inferencia, conveniencia o repetición.**

---

# Siguiente bloque lógico

**RC2 — LEONES Beta User Flow.**

El objetivo ya no es demostrar que la cadena técnica funciona —RC1 lo ha demostrado— sino que una persona pueda recorrerla de principio a fin:

**instalar → hardware → perfilado → candidatos → elección → ODS/Magnitude informado → instalación → benchmark opcional → evidencia → resultado.**

El alcance y los criterios de aceptación están fijados en [`docs/RC2-BETA-USER-FLOW.md`](docs/RC2-BETA-USER-FLOW.md).
