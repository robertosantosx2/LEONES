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

```text
GitHub / CI
  ├─ contratos
  ├─ esquemas
  ├─ validadores
  ├─ tests
  └─ runner / auditoría
          │
          ▼
HOST LINUX
  ├─ runtime real
  ├─ modelo real
  ├─ hardware real
  ├─ benchmark real
  └─ evidencia
```

---

# Estado del proyecto

| Bloque | Estado | Resultado |
|---|---|---|
| V1 / A01 | 🟢 Cerrado | Cadena real de selección → ejecución → benchmark → evidencia |
| RC1 | 🟢 **Validado** | Ejecución efectiva end-to-end: selección → gate → Ollama → A01 → medición → evidencia |
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado operativamente | Contrato `runtime-benchmark-evidence.v1.1` + auditoría física |
| Decisión ODS | Magnitude | 🟢 Contrato fijado | Selección de stack sin scoring paralelo |
| Tiers de hardware | 🔵 Preparado | Capa de interpretación sobre ODS, Magnitude, LLMFit y evidencia LEONES |

## RC1 — ejecución efectiva validada

RC1 ha demostrado sobre un host Linux una ejecución nueva y real desde la selección autorizada hasta la evidencia A01.

```text
selección
   ↓
runtime-selection gate
   ↓
execution_authorized=true
   ↓
comando confiable
   ↓
Ollama
   ↓
qwen2.5:0.5b-instruct-q4_K_M
   ↓
A01
   ↓
grader=passed
   ↓
measurement_kind=real
   ↓
53.3795 tok/s
   ↓
artifacts/rc1-effective-execution.json
```

La ejecución cerrada corresponde al `execution_id` `e07822d0-d991-4e9b-985b-b9afea0c13c0`, con `A01=success`, `score=1.0`, `evidence=measured` y `measurement_kind=real`.

La evidencia anterior de 40.7666 tok/s del 27 de agosto no fue reutilizada. RC1 generó una medición nueva el 31 de agosto de 2026.

**Cierre completo:** [`docs/completed/RC1-EFFECTIVE-EXECUTION.md`](docs/completed/RC1-EFFECTIVE-EXECUTION.md)

### Beta testers

La primera ejecución de usuarios externos se puede realizar siguiendo el manual reproducible de instalación y ejecución:

**[`docs/BETA-TESTER-INSTALL.md`](docs/BETA-TESTER-INSTALL.md)**

El repositorio incluye además el plan mínimo de selección y el comando confiable utilizados por la beta en [`examples/rc1/`](examples/rc1/).

Cada beta tester debe producir su propio `execution_id`, timestamp, métrica y SHA-256. La medición de referencia de RC1 no se reutiliza como resultado de otra máquina.

## JALÓN 2 — referencia histórica

```text
llama.cpp
Qwen3 0.6B · Q4_K_M
CPU · 4 threads
5 ejecuciones
43.6 tok/s de media
```

Esta evidencia es histórica e inmutable. Los resultados posteriores no deben reescribirla.

## JALÓN 3 — cierre operativo

JALÓN 3 quedó **cerrado operativamente el 2026-08-28**. El contrato de medición dejó de ser solo diseño: una ejecución física real lo satisfizo y el runner canónico produjo todos los gates de cierre.

Runner canónico:

```text
scripts/run_jalon3_audit.sh
```

Gates:

```text
CONTRACT_GATE=PASS
TESTS_GATE=PASS
DIFF_GATE=PASS
REAL_RUNTIME_EVIDENCE_GATE=PASS
REPRODUCIBILITY_GATE=PASS
JALON3_OPERATIONAL_CLOSE=PASS
AUDIT_EXIT_CODE=0
```

La evidencia de cierre registra identidad del modelo y artefacto, cuantización, runtime y versión, protocolo de workload, warm-up, cinco mediciones, entorno, códigos de salida, stdout/stderr, timestamps y hashes.

**JALÓN 3 no se rediseña y su evidencia no se modifica retroactivamente.**

---

# Componentes principales

## 1. Prospector

Descubre modelos, repositorios, benchmarks, runtimes, datasets y herramientas. Filtra candidatos y alimenta el Atlas.

**No convierte candidatos en conocimiento canónico.**

Docs: [`docs/phases/2026-08-daily-prospection/`](docs/phases/2026-08-daily-prospection/) · [`docs/SOURCE-DISCOVERY.md`](docs/SOURCE-DISCOVERY.md)

## 2. Open LLM Atlas

Mantiene la identidad canónica de modelos y familias y conserva la evidencia que respalda sus atributos.

**Atlas es fuente de identidad y evidencia, no un ranking arbitrario.**

Docs: [`atlas/README.md`](atlas/README.md) · [`docs/phases/2026-08-atlas-expanded/`](docs/phases/2026-08-atlas-expanded/)

## 3. JGB / apertura

Clasifica la apertura mediante dimensiones explícitas y evidencia primaria. Apertura, velocidad, precio y calidad de tarea son dimensiones distintas.

Docs: [`web/proyectos/atlas/openness/JGB-INDEX.md`](web/proyectos/atlas/openness/JGB-INDEX.md)

## 4. Hardware

Relaciona modelos con CPU, RAM, GPU/VRAM, almacenamiento y otras capacidades relevantes.

**Compatibilidad estimada no equivale a rendimiento medido.**

Docs: [`docs/phases/2026-08-hardware-matrix/`](docs/phases/2026-08-hardware-matrix/) · [`docs/completed/H08-HARDWARE-MATRIX.md`](docs/completed/H08-HARDWARE-MATRIX.md)

## 5. Precio / TCO

Conserva observaciones de precio y las combina con capacidad y rendimiento para estudiar el coste de una solución completa.

Docs: [`docs/phases/2026-08-hardware-pricing/`](docs/phases/2026-08-hardware-pricing/) · [`docs/phases/2026-08-economic-ranking-v1/`](docs/phases/2026-08-economic-ranking-v1/)

## 6. LLMFit

Aporta una primera estimación de encaje **modelo ↔ máquina** para reducir candidatos antes de ejecutar o descargar modelos cuando la evidencia disponible lo permite.

LLMFit **no es fuente de verdad** y nunca convierte una estimación en `measured`.

Docs: [`docs/integrations/LLMFIT/`](docs/integrations/LLMFIT/) · [`docs/phases/2026-08-atlas-recommendation-pipeline/`](docs/phases/2026-08-atlas-recommendation-pipeline/)

## 7. CABE / RULA

Conserva `tokens_per_second` como dato primario y deriva una clasificación operativa. La clasificación nunca sustituye a la medición.

Docs: [`docs/phases/2026-08-cabe-rula/`](docs/phases/2026-08-cabe-rula/) · [`docs/completed/H09-CABE-RULA.md`](docs/completed/H09-CABE-RULA.md)

## 8. Selección, Router y recomendación

LEONES separa la decisión declarativa de la ejecución.

Una ejecución queda determinada por:

`modelo + cuantización + runtime + hardware + configuración`

LLMFit puede filtrar candidatos; la medición física prevalece sobre la estimación cuando ambas existen.

La decisión de stack ODS/Magnitude está fijada en [`docs/subprojects/LEONES-ODS-MAGNITUDE-DECISION-CONTRACT.md`](docs/subprojects/LEONES-ODS-MAGNITUDE-DECISION-CONTRACT.md).

Docs: [`docs/PILLARS.md`](docs/PILLARS.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## 9. Agentes y evaluación

LEONES evalúa tareas agentivas mediante tareas reproducibles, herramientas, trayectoria, resultado, grading, tiempo, coste, seguridad y artefactos.

Los benchmarks orientados a tareas complementan los benchmarks externos: el objetivo final es conocer **qué tareas se completan en qué condiciones**, no reducir todo el sistema a una única cifra.

Docs: [`docs/EVALUACION_AGENTIC_TESTS.md`](docs/EVALUACION_AGENTIC_TESTS.md) · [`docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`](docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md)

## 10. Runner y medición física

```text
selección autorizada
        ↓
runner
        ↓
runtime
        ↓
modelo + hardware
        ↓
benchmark
        ↓
medición
        ↓
evidence
```

El runner ejecuta la configuración autorizada y conserva los datos necesarios para validar la ejecución. **No inventa mediciones ni convierte fixtures en evidencia física.**

El runner canónico de auditoría de JALÓN 3 es `scripts/run_jalon3_audit.sh`.

Docs: [`docs/completed/JALON-3.md`](docs/completed/JALON-3.md) · [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md)

## 11. ODS, Magnitude, FreeToken, AirLLM, Ollama y llama.cpp

LEONES puede utilizar herramientas externas para descubrimiento, profiling, estimación, ejecución o comparación.

La frontera es explícita:

- **evidencia externa** sigue siendo evidencia externa;
- **estimación** sigue siendo estimación;
- **medición LEONES** requiere una ejecución LEONES reproducible;
- una herramienta externa no se convierte automáticamente en verdad canónica.

ODS se reserva para despliegue/stack local; Magnitude para ejecución agentiva/runtime. Cuando ambos son necesarios pueden combinarse. Si un runtime directo resuelve el workload, no se añade una capa innecesaria.

Docs: [`docs/subprojects/README.md`](docs/subprojects/README.md) · [`docs/subprojects/ODS-Magnitude-INTEGRATION.md`](docs/subprojects/ODS-Magnitude-INTEGRATION.md) · [`docs/subprojects/ODS-Magnitude-AUDIT.md`](docs/subprojects/ODS-Magnitude-AUDIT.md)

---

# Contratos y evidencia

LEONES utiliza contratos versionados para mantener separadas selección, ejecución, medición y evidencia.

`runtime-selection.v1.1` es declarativo: identifica runtime, adaptador, modelo, compatibilidad, restricciones y razón de selección. No es rendimiento medido ni una orden de ejecución.

El contrato de decisión ODS/Magnitude define `none`, `ods`, `magnitude` y `ods+magnitude` como opciones de stack, sin crear un scoring paralelo.

El contrato de evidencia de JALÓN 3 es `runtime-benchmark-evidence.v1.1`.

```text
runtime-selection
      ↓
plan validado
      ↓
decisión de stack
      ↓
adapter / runner
      ↓
runtime-execution
      ↓
benchmark
      ↓
evidence
```

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

# Calidad y reproducibilidad

La CI forma parte del contrato del proyecto.

Principios:

- contratos explícitos y versionados;
- cambios mínimos antes que reescrituras innecesarias;
- separación estricta entre fixtures y evidencia;
- procedencia conservada;
- mediciones repetibles;
- ningún dato físico inventado;
- documentación alineada con el código real;
- una única vía canónica de ejecución medida: el runner existente.

Para contribuir: [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

# Siguiente bloque lógico

Con JALÓN 3 cerrado, RC1 validado y el contrato de decisión ODS/Magnitude fijado, el siguiente bloque es **continuar la implementación mínima sobre las piezas existentes**.

Los tiers serán una **capa de interpretación** sobre ODS, Magnitude, LLMFit y evidencia LEONES; no una segunda base de datos paralela de modelos y rendimiento.

---

# Documentación clave

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura general.
- [`docs/PILLARS.md`](docs/PILLARS.md) — pilares del sistema.
- [`PIPELINE_E2E.md`](PIPELINE_E2E.md) — recorrido integral.
- [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) — resultados y evidencia.
- [`docs/subprojects/LEONES-ODS-MAGNITUDE-DECISION-CONTRACT.md`](docs/subprojects/LEONES-ODS-MAGNITUDE-DECISION-CONTRACT.md) — contrato de decisión.
- [`docs/completed/JALON-1.md`](docs/completed/JALON-1.md) — cierre del JALÓN 1.
- [`docs/completed/JALON-3.md`](docs/completed/JALON-3.md) — cierre operativo del JALÓN 3.
- [`docs/completed/RC1-EFFECTIVE-EXECUTION.md`](docs/completed/RC1-EFFECTIVE-EXECUTION.md) — cierre efectivo de RC1.
- [`docs/BETA-TESTER-INSTALL.md`](docs/BETA-TESTER-INSTALL.md) — instalación y ejecución para beta testers.
- [`docs/V1-A01-REAL-RUNTIME.md`](docs/V1-A01-REAL-RUNTIME.md) — A01 con runtime real.
- [`docs/V1-CLEAN-ROOM.md`](docs/V1-CLEAN-ROOM.md) — limpieza, versionado y evidencia.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribución.

---

# Licencia

Consulta [`LICENSE`](LICENSE) y la documentación específica de cada subproyecto o dependencia externa. Las licencias de terceros no deben interpretarse como licencia de LEONES.
