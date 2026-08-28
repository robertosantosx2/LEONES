# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web de LEONES](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES) · [🤝 Contribuir](CONTRIBUTING.md)

---

# 🟢 RC1 — objetivo y estado

**LEONES está reorientado hacia una V1 mínima, operativa y medible para hardware de consumo.**

La prioridad ya no es construir otro gran sistema de inferencia ni duplicar capacidades que ya existen en proyectos especializados. LEONES debe ser la **capa de conocimiento, decisión, integración y medición** que los conecta.

La pregunta central de LEONES es:

> **Dado un usuario, una tarea y un hardware de consumo, ¿qué solución abierta tiene sentido ejecutar y qué evidencia real demuestra que funciona?**

RC1 persigue una cadena corta y verificable:

```text
conocimiento / Atlas
        ↓
perfil de hardware
        ↓
LLMFit — primera estimación de encaje
        ↓
LEONES — decisión y orquestación
        ↓
ODS / SOHO        Magnitude / asistente personal
        ↓
runtime realmente disponible
        ↓
medición LEONES
        ↓
benchmark de tarea real
        ↓
evidencia reproducible
        ↓
MANADA — conocimiento colectivo
```

**Principio:** LEONES reutiliza antes de reinventar.

- Atlas conserva conocimiento e identidad.
- Prospector descubre conocimiento nuevo.
- LLMFit aporta el primer filtro de encaje modelo ↔ hardware.
- ODS aporta su propio motor, agentes, herramientas y experiencia cuando encaje en el escenario SOHO.
- Magnitude aporta su experiencia y capacidades cuando el objetivo sea un asistente personal.
- LEONES decide, integra, mide y conserva evidencia.
- AirLLM y FreeToken se evaluarán como aportaciones a ODS/Magnitude; se intentará upstream antes de crear conectores propios.
- MANADA recibe resultados suficientemente documentados para convertir mediciones individuales en conocimiento colectivo.

---

# 🎯 Qué es LEONES

LEONES no pretende ser otro catálogo de modelos, otro chatbot ni otro runtime de inferencia.

Es una **capa abierta de conocimiento y decisión para IA local**, especialmente orientada al hardware de consumo, que conecta:

1. descubrimiento de modelos, runtimes, benchmarks y herramientas;
2. investigación y conocimiento estructurado;
3. identidad y evidencia mediante Open LLM Atlas;
4. análisis de apertura;
5. análisis y perfilado de hardware;
6. estimación de encaje mediante LLMFit;
7. selección de una solución apropiada;
8. integración con sistemas especializados como ODS y Magnitude;
9. ejecución real;
10. benchmark de tareas reales;
11. evidencia física reproducible;
12. publicación y aprendizaje colectivo mediante MANADA.

La regla fundacional sigue siendo:

> **No convertir una afirmación en un hecho por repetición. Descubrir, documentar, verificar, medir y conservar la procedencia.**

LEONES distingue siempre entre:

- `estimated` — cálculo o estimación;
- `reported` — dato declarado por una fuente externa;
- `observed` — configuración observada;
- `measured` — medición ejecutada por LEONES;
- `verified` — dato que supera el quality gate correspondiente;
- `unknown` — información todavía no demostrada.

---

# 🧭 Arquitectura RC1

```text
                         CONOCIMIENTO
                              │
             ┌────────────────┼────────────────┐
             ↓                ↓                ↓
        PROSPECTOR          ATLAS          INVESTIGACIÓN
             │                │                │
             └────────────────┼────────────────┘
                              ↓
                     HARDWARE DEL USUARIO
                              ↓
                           LLMFit
                    "¿qué puede encajar?"
                              ↓
                           LEONES
                   "¿qué debemos probar?"
                              │
                 ┌────────────┴────────────┐
                 ↓                         ↓
              ODS / SOHO            MAGNITUDE / PERSONAL
                 │                         │
              Hermes                 capacidades propias
                 └────────────┬────────────┘
                              ↓
                     RUNTIME DE INFERENCIA
                              ↓
                       TAREA REAL / AGENTE
                              ↓
                    BENCHMARK LEONES
                              ↓
                       MEDICIÓN FÍSICA
                              ↓
                         EVIDENCIA
                              ↓
                           MANADA
                              ↓
                    CONOCIMIENTO COLECTIVO
```

La arquitectura evita crear una segunda implementación paralela de aquello que los proyectos integrados ya hacen bien.

---

# 🧠 Investigación y conocimiento

La investigación sigue siendo una parte esencial del proyecto. La reducción de alcance de RC1 afecta a la **ejecución y al producto mínimo**, no al patrimonio de conocimiento.

LEONES conserva y continúa desarrollando:

- investigación sobre modelos abiertos;
- familias, variantes, checkpoints y cuantizaciones;
- benchmarks públicos;
- runtimes y motores de inferencia;
- agentes y herramientas;
- datasets;
- licencias y grados de apertura;
- hardware y aceleradores;
- memoria, VRAM y ancho de banda;
- precios y TCO;
- rendimiento publicado por terceros;
- evidencia física obtenida por LEONES;
- relaciones entre modelo, tarea, runtime y hardware;
- conocimiento histórico y procedencia.

La investigación alimenta Atlas y las decisiones de LEONES, pero **no se confunde con una medición física**.

---

# 1. 🔎 Prospector / prospección

Prospector descubre candidatos nuevos en el ecosistema abierto: modelos, repositorios, runtimes, benchmarks, datasets y herramientas.

Su función es **descubrir**, no decidir por sí mismo qué debe entrar en el catálogo ni qué debe recomendarse.

Flujo:

```text
fuentes
  → descubrimiento
  → filtros de apertura/licencia
  → identidad
  → enriquecimiento
  → deduplicación
  → feed
  → Atlas / evidencia
```

La prospección no convierte automáticamente un candidato en conocimiento canónico.

Documentación: [`docs/SOURCE-DISCOVERY.md`](docs/SOURCE-DISCOVERY.md) y [`docs/phases/2026-08-daily-prospection/`](docs/phases/2026-08-daily-prospection/).

---

# 2. 📚 Open LLM Atlas

Atlas continúa siendo una pieza central de LEONES.

Su misión es mantener una base canónica de **identidad, características y evidencia de modelos y familias**, evitando mezclar nombres, variantes, checkpoints o afirmaciones de terceros.

Flujo:

```text
Prospector
   ↓
identidad
   ↓
evidencia
   ↓
quality gate
   ↓
verified-only cuando corresponda
   ↓
Atlas
```

Atlas es **fuente de conocimiento e identidad**, no un ranking arbitrario ni un benchmark físico.

Documentación: [`atlas/README.md`](atlas/README.md) y [`docs/phases/2026-08-atlas-expanded/`](docs/phases/2026-08-atlas-expanded/).

---

# 3. 🔓 Apertura / JGB

LEONES conserva el análisis sistemático de apertura.

Open weights, open source, open research y otros grados de apertura no deben reducirse a una única etiqueta sin evidencia.

JGB documenta dimensiones de apertura y procedencia separadamente del rendimiento, precio y velocidad.

Documentación: [`web/proyectos/atlas/openness/JGB-INDEX.md`](web/proyectos/atlas/openness/JGB-INDEX.md).

---

# 4. 🖥️ Hardware

El hardware de consumo es el foco práctico de RC1.

LEONES conserva el conocimiento de hardware y evoluciona hacia tiers operativos basados en capacidades reales:

- CPU;
- RAM;
- GPU;
- VRAM;
- arquitectura;
- ancho de banda cuando esté disponible;
- almacenamiento y restricciones relevantes;
- sistema operativo y runtime;
- características que condicionen la inferencia.

La matriz de hardware **no es un benchmark**. Sirve para reducir el espacio de búsqueda y contextualizar resultados.

Documentación: [`docs/completed/H08-HARDWARE-MATRIX.md`](docs/completed/H08-HARDWARE-MATRIX.md).

Los tiers de consumo de RC1 se documentan en [`docs/RC1-HARDWARE-CONSUMER-TIERS.md`](docs/RC1-HARDWARE-CONSUMER-TIERS.md).

---

# 5. ⚡ LLMFit — primera capa de encaje

LLMFit se utiliza como **estimador previo de model fit**.

```text
hardware
   ↓
LLMFit
   ↓
candidatos
   ↓
LEONES
   ↓
validación / ejecución / medición
```

LLMFit reduce el coste de explorar candidatos, pero su resultado no se promociona automáticamente a medición real.

La frontera es explícita:

> **LLMFit estima si algo puede encajar; LEONES comprueba qué ocurre al ejecutarlo.**

Documentación: [`docs/integrations/LLMFIT-RC1.md`](docs/integrations/LLMFIT-RC1.md).

---

# 6. 🦁 LEONES — capa de decisión mínima

La responsabilidad propia de LEONES se concentra en cuatro funciones:

### 6.1 Conocer

Utilizar investigación, Atlas, evidencia externa y perfil de hardware.

### 6.2 Filtrar

Utilizar LLMFit, requisitos, cuantización, contexto, runtime y restricciones del usuario para reducir candidatos.

### 6.3 Decidir qué probar

LEONES no necesita ejecutar todo. Selecciona la combinación que merece una prueba real.

### 6.4 Medir y conservar

Una vez ejecutado el sistema, LEONES captura las condiciones y transforma la ejecución en evidencia reproducible.

---

# 7. 🤖 ODS / SOHO y Magnitude / asistente personal

RC1 adopta una decisión arquitectónica deliberada: **LEONES no sustituye a ODS ni a Magnitude**.

Después de LLMFit → LEONES se decide qué ecosistema especializado resulta apropiado:

| Escenario | Camino previsto |
|---|---|
| SOHO / entorno doméstico-servidor | **ODS** |
| Asistente personal | **Magnitude** |
| Otros casos | El sistema que aporte mejor cobertura, sujeto a evidencia |

ODS conserva sus capacidades propias, incluido Hermes y su motor de inferencia. Magnitude conserva sus propias capacidades de agente/asistente.

LEONES aporta la capa que falta entre conocimiento/hardware y medición comparativa: **decidir, ejecutar de forma controlada y medir**.

La integración no debe duplicar componentes que ya existan aguas abajo.

---

# 8. 🚀 AirLLM y FreeToken

AirLLM y FreeToken forman parte del conocimiento técnico que LEONES puede investigar y aprovechar, pero no se convierten automáticamente en nuevos subsistemas propios.

La regla congelada para RC1 es:

```text
AirLLM / FreeToken
        ↓
 análisis de utilidad
        ↓
 aportación a ODS / Magnitude
        ↓
 intentar upstream
        ↓
 si upstream no es viable → conector mínimo
```

El objetivo es que sus mejoras lleguen al ecosistema que realmente ejecuta la tarea, evitando mantener forks o arquitecturas paralelas innecesarias.

---

# 9. 🧪 Benchmarks: LEONES mide lo que realmente ocurre

Los benchmarks externos siguen siendo importantes como **conocimiento y referencia**.

Pero la medición que decide una recomendación física debe distinguirse de:

- cifras del fabricante;
- benchmarks de terceros;
- estimaciones de LLMFit;
- resultados de otro hardware;
- resultados de otro runtime;
- resultados de otra cuantización.

La medición LEONES conserva como mínimo:

- modelo e identidad;
- revisión cuando esté disponible;
- cuantización;
- runtime y versión;
- hardware;
- contexto;
- prompt/protocolo;
- warm-up;
- número de mediciones;
- ejecución concreta;
- timestamps;
- métricas observadas;
- artefactos y procedencia.

JALÓN 3 dejó cerrado el contrato operativo de medición real: [`docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md`](docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md).

---

# 10. 🧰 Evaluación agentiva

LEONES conserva la evaluación de tareas reales y agentes.

No basta con medir tokens/segundo. Una tarea agentiva puede depender de:

- llamadas a herramientas;
- éxito de la trayectoria;
- errores;
- recuperación;
- tiempo total;
- coste;
- artefactos generados;
- seguridad;
- cumplimiento de la tarea.

La cadena A01 ya proporciona una referencia de extremo a extremo y sirve como base para ampliar la evaluación sin convertir RC1 en un proyecto de infraestructura gigantesco.

---

# 11. 📊 CABE / RULA

CABE/RULA conserva una función interpretativa: transformar rendimiento observado en categorías operativas sin destruir el dato original.

La métrica primaria sigue siendo el rendimiento medido; la clasificación es derivada.

Documentación: [`docs/completed/H09-CABE-RULA.md`](docs/completed/H09-CABE-RULA.md).

---

# 12. 💶 Precio y TCO

El precio y el coste total de propiedad siguen formando parte del conocimiento de LEONES.

No se mezclan artificialmente con rendimiento ni apertura:

```text
modelo
hardware
rendimiento
apertura
precio / TCO
        ↓
 decisión informada
```

Esto permite responder no solo "¿qué funciona?", sino también "¿qué tiene sentido para este usuario?".

Documentación: [`docs/phases/2026-08-hardware-pricing/`](docs/phases/2026-08-hardware-pricing/) y [`docs/phases/2026-08-economic-ranking-v1/`](docs/phases/2026-08-economic-ranking-v1/).

---

# 13. 🤝 MANADA — conocimiento colectivo

MANADA es el destino del conocimiento validado que LEONES produce o consolida.

La cadena objetivo es:

```text
usuario / máquina
      ↓
LEONES
      ↓
medición
      ↓
evidencia
      ↓
validación
      ↓
MANADA
      ↓
conocimiento colectivo
```

MANADA no debe recibir estimaciones disfrazadas de hechos. La procedencia y el nivel de evidencia viajan con el dato.

---

# 🧱 Qué NO hará RC1

Para proteger el minimalismo:

- no construirá un nuevo motor de inferencia si ODS/Magnitude/otros ya proporcionan uno adecuado;
- no duplicará Hermes;
- no convertirá LLMFit en un fork interno;
- no mantendrá una segunda matriz paralela de hardware sin necesidad;
- no tratará benchmarks publicados como mediciones propias;
- no mezclará `estimated`, `reported` y `measured`;
- no incorporará AirLLM o FreeToken como infraestructura permanente antes de probar su utilidad;
- no ampliará el número de runtimes por completar una lista si no existe una necesidad real;
- no sacrificará documentación y procedencia para ganar velocidad aparente.

---

# 🧊 Contratos congelados

RC1 parte de los siguientes contratos:

1. **Investigación y Atlas permanecen.**
2. **LLMFit es estimación, no verdad física.**
3. **LEONES es capa de decisión e integración, no runtime monolítico.**
4. **ODS es la vía SOHO cuando resulte apropiada.**
5. **Magnitude es la vía de asistente personal cuando resulte apropiada.**
6. **Hermes se aprovecha donde lo aporte ODS.**
7. **AirLLM y FreeToken se intentarán llevar upstream a ODS/Magnitude antes de crear conectores.**
8. **LEONES realiza los benchmarks y mediciones finales que necesite para sus decisiones.**
9. **Los resultados válidos alimentan MANADA.**
10. **Toda cifra conserva su procedencia y nivel de evidencia.**

---

# 🛠️ Plan RC1

El plan completo está en [`docs/RC1-MINIMAL-CORE-PLAN.md`](docs/RC1-MINIMAL-CORE-PLAN.md).

Orden de trabajo:

```text
1. congelar arquitectura y reglas
        ↓
2. adelgazar / limpiar el código heredado
        ↓
3. fijar LLMFit como entrada de model fit
        ↓
4. consolidar tiers de hardware de consumo
        ↓
5. definir contrato mínimo LEONES ↔ ODS/Magnitude
        ↓
6. preparar instalación y ejecución real
        ↓
7. benchmark de tareas reales
        ↓
8. evidencia reproducible
        ↓
9. publicación en MANADA
        ↓
10. RC1 operativo
```

La primera ejecución física de ODS/Magnitude será el punto en el que Ubuntu resulte imprescindible.

---

# 📖 Documentación

### Arquitectura y reglas

- [`docs/LEONES-RULES.md`](docs/LEONES-RULES.md) — reglas de trabajo congeladas.
- [`docs/RC1-MINIMAL-CORE-PLAN.md`](docs/RC1-MINIMAL-CORE-PLAN.md) — plan operativo de RC1.
- [`docs/RC1-HARDWARE-CONSUMER-TIERS.md`](docs/RC1-HARDWARE-CONSUMER-TIERS.md) — tiers de hardware.
- [`docs/integrations/LLMFIT-RC1.md`](docs/integrations/LLMFIT-RC1.md) — integración LLMFit.

### Medición y evidencia

- [`docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md`](docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md) — contrato de medición real.
- [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) — esquema de resultados.
- [`docs/completed/BENCHMARK-MEASURED-EVIDENCE.md`](docs/completed/BENCHMARK-MEASURED-EVIDENCE.md) — evidencia medida.
- [`docs/completed/PHYSICAL-BENCHMARK-VALIDATION.md`](docs/completed/PHYSICAL-BENCHMARK-VALIDATION.md) — validación física.

### Conocimiento

- [`atlas/README.md`](atlas/README.md) — Open LLM Atlas.
- [`docs/SOURCE-DISCOVERY.md`](docs/SOURCE-DISCOVERY.md) — descubrimiento de fuentes.
- [`web/proyectos/atlas/openness/JGB-INDEX.md`](web/proyectos/atlas/openness/JGB-INDEX.md) — apertura.
- [`docs/phases/2026-08-daily-prospection/`](docs/phases/2026-08-daily-prospection/) — prospección.
- [`docs/phases/2026-08-atlas-expanded/`](docs/phases/2026-08-atlas-expanded/) — expansión de Atlas.
- [`docs/phases/2026-08-hardware-matrix/`](docs/phases/2026-08-hardware-matrix/) — hardware.
- [`docs/phases/2026-08-hardware-pricing/`](docs/phases/2026-08-hardware-pricing/) — precios.
- [`docs/phases/2026-08-economic-ranking-v1/`](docs/phases/2026-08-economic-ranking-v1/) — economía/TCO.

### Proyecto

- [`PIPELINE_E2E.md`](PIPELINE_E2E.md) — pipeline integral.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contrato de contribución.

---

# 🤝 Contribuir

Las contribuciones son bienvenidas. Antes de abrir un issue o pull request, consulta [`CONTRIBUTING.md`](CONTRIBUTING.md) y [`docs/LEONES-RULES.md`](docs/LEONES-RULES.md).

Las contribuciones deben respetar especialmente:

- procedencia de los datos;
- separación entre fuente, estimación, observación y medición;
- contratos de CI y pruebas;
- minimalismo arquitectónico;
- documentación de decisiones;
- compatibilidad con la cadena de conocimiento colectivo.

---

# 🦁 Principio final

> **LEONES no necesita hacerlo todo. Necesita saber qué ya existe, elegir bien, demostrarlo en el hardware real y devolver el conocimiento al colectivo.**
