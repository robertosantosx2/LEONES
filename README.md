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
ROUTER
      ↓
AGENT / TAREA REAL
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
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado operativamente | Contrato `runtime-benchmark-evidence.v1.1` + auditoría física |
| Siguiente bloque | 🔵 Preparado | Decisión **LEONES → ODS | Magnitude** + tiers de hardware |

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

Conserva `tokens_per_second` como dato primario y deriva una clasificación operativa:

```text
<1 tok/s       → No CABE
1–<10 tok/s    → CABE
10–100 tok/s   → RULA
>100 tok/s     → RULA+
```

La clasificación nunca sustituye a la medición.

Docs: [`docs/phases/2026-08-cabe-rula/`](docs/phases/2026-08-cabe-rula/) · [`docs/completed/H09-CABE-RULA.md`](docs/completed/H09-CABE-RULA.md)

## 8. Selección, Router y recomendación

LEONES separa la decisión declarativa de la ejecución.

Una ejecución queda determinada por:

`modelo + cuantización + runtime + hardware + configuración`

LLMFit puede filtrar candidatos; la medición física prevalece sobre la estimación cuando ambas existen.

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

Cuando una herramienta se integra, se documentan función, procedencia, supuestos y límites. Se reutiliza su arquitectura cuando es adecuada; **no se crea innecesariamente un sistema paralelo**.

Docs: [`docs/subprojects/ods/`](docs/subprojects/ods/) · [`docs/subprojects/magnitude/`](docs/subprojects/magnitude/)

---

# Contratos y evidencia

LEONES utiliza contratos versionados para mantener separadas selección, ejecución, medición y evidencia.

`runtime-selection.v1.1` es declarativo: identifica runtime, adaptador, modelo, compatibilidad, restricciones y razón de selección. No es rendimiento medido ni una orden de ejecución.

El contrato de evidencia de JALÓN 3 es `runtime-benchmark-evidence.v1.1`.

```text
runtime-selection
      ↓
plan validado
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

Con JALÓN 3 cerrado, el siguiente bloque es **consumir el contrato**, no rediseñar la medición.

La prioridad es cerrar el contrato de decisión **LEONES → ODS | Magnitude**, utilizar **LLMFit** como fuente de ajuste/fit cuando corresponda y derivar los tiers de hardware de consumo a partir de las capacidades reales de esas herramientas.

Los tiers de LEONES serán una **capa de interpretación** sobre ODS, Magnitude y LLMFit, no una segunda base de datos paralela de modelos y rendimiento.

---

# Documentación clave

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura general.
- [`docs/PILLARS.md`](docs/PILLARS.md) — pilares del sistema.
- [`PIPELINE_E2E.md`](PIPELINE_E2E.md) — recorrido integral.
- [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) — resultados y evidencia.
- [`docs/completed/JALON-1.md`](docs/completed/JALON-1.md) — cierre del JALÓN 1.
- [`docs/completed/JALON-3.md`](docs/completed/JALON-3.md) — cierre operativo del JALÓN 3.
- [`docs/V1-A01-REAL-RUNTIME.md`](docs/V1-A01-REAL-RUNTIME.md) — A01 con runtime real.
- [`docs/V1-CLEAN-ROOM.md`](docs/V1-CLEAN-ROOM.md) — limpieza, versionado y evidencia.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribución.

---

# Licencia

Consulta [`LICENSE`](LICENSE) y la documentación específica de cada subproyecto o dependencia externa. Las licencias de terceros no deben interpretarse como licencia de LEONES.
