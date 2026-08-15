# Open LLM Atlas

**Subproyecto de LEONES para construir una base de conocimiento verificable sobre modelos LLM abiertos/open-weight y convertir ese conocimiento en recomendaciones de IA local explicables.**

> **Principio central:** `modelo × variante × cuantización × runtime × hardware × workload × restricciones`

El Atlas no pretende responder cuál es «el mejor modelo» en abstracto. Su objetivo es responder **qué configuración es adecuada para una necesidad concreta, en un hardware concreto, bajo unas restricciones concretas y con evidencia trazable**.

---

## 1. Por qué existe el Atlas

El ecosistema de LLM cambia demasiado deprisa para que una lista estática de modelos sea útil durante mucho tiempo. Un mismo modelo puede ser una excelente elección en una GPU y una mala elección en CPU; puede funcionar bien con una cuantización y mal con otra; puede ser técnicamente ejecutable pero demasiado lento para un agente; y puede declararse «open» sin que eso signifique el mismo grado de libertad que otro proyecto.

Por eso el Atlas separa deliberadamente:

- **identidad del modelo**;
- **familia y organización**;
- **arquitectura y capacidades**;
- **benchmarks y calidad observada**;
- **apertura/libertad**;
- **self-hostability**;
- **hardware**;
- **runtime**;
- **formato y cuantización**;
- **workload**;
- **observaciones empíricas de rendimiento**;
- **evidencia y confianza**.

Esta separación es la condición necesaria para que LEONES pueda recomendar sin convertir todos los datos en una única puntuación opaca.

---

# 2. El Índice JGB: pieza fundamental del Atlas

## 2.1 Qué problema resuelve

El Atlas utiliza el **Índice JGB** como marco específico para describir el grado de apertura/libertad de un modelo. Se basa en la documentación de Jesús M. Gonzalez-Barahona, *Generative AI in your own infrastructure* (6 de julio de 2026).

Su importancia para LEONES es estratégica: **«open», «open weights», «self-hostable» y «reproducible» no son sinónimos**. Si el recomendador no distingue estas situaciones, puede recomendar como equivalente un modelo que simplemente puede consultarse mediante una aplicación, uno cuyos pesos pueden descargarse y otro cuyo software, datos y proceso pueden estudiarse y reproducirse.

El JGB permite conservar esa diferencia como conocimiento estructurado y auditable.

## 2.2 Las seis clases

El marco establece seis categorías:

| Nivel | Clase JGB | Interpretación en el Atlas |
|---:|---|---|
| **0** | Behind-app model | El usuario accede a una aplicación; el modelo está detrás del servicio. |
| **1** | Directly accessible model | Acceso directo, pero condicionado por las restricciones del proveedor/API. |
| **2** | Available weights model | Los pesos están disponibles, pero permanecen condiciones o limitaciones relevantes. |
| **3** | Open weight model | Los pesos son utilizables con un grado mayor de libertad según los requisitos del marco. |
| **4** | Open source model | Se amplía la libertad para estudiar, modificar y utilizar el sistema, con los requisitos correspondientes. |
| **5** | Reproducible (libre) model | Máximo grado del marco: permite la reproducción/libertad completa exigida por la categoría. |

**La escala no es un ranking de inteligencia.** JGB 5 no significa «mejor modelo» que JGB 2. Significa un grado diferente de libertad/apertura.

## 2.3 Las cinco dimensiones son más importantes que el número

El Atlas no almacenará únicamente `jgb_level`. Conservaremos las dimensiones que sustentan la clasificación:

1. **Access** — cómo se puede acceder al modelo.
2. **Model control** — qué capacidad existe para controlar, estudiar o modificar el modelo.
3. **Data control** — qué control existe sobre los datos relacionados con el sistema.
4. **Autonomy** — hasta qué punto el usuario puede operar sin depender del proveedor.
5. **Trust** — hasta qué punto pueden estudiarse y verificarse los elementos necesarios para confiar/reproducir el sistema.

Por tanto:

```text
JGB
 │
 ├── Access
 ├── Model control
 ├── Data control
 ├── Autonomy
 └── Trust
       │
       ▼
   JGB class 0–5
```

El nivel es una síntesis; **las dimensiones y sus evidencias son los datos auditables**.

## 2.4 JGB no es self-hostability

Esta distinción es crítica para el recomendador:

```text
JGB / libertad
      ≠
self-hostability
      ≠
performance
      ≠
quality
      ≠
cost
```

Un modelo puede tener pesos disponibles y ser ejecutable localmente, pero no cumplir los requisitos de una categoría JGB superior. También puede existir un modelo con un alto grado de apertura que no sea una buena elección para el hardware concreto del usuario.

Por ello el Atlas registra por separado:

- **JGB:** grado de apertura/libertad.
- **Self-hostability:** posibilidad práctica de ejecutar el sistema en infraestructura propia.
- **Performance:** comportamiento medido en una configuración concreta.
- **Quality:** capacidades y resultados de benchmarks/tareas.

## 2.5 JGB y Barahona no se sustituyen

El Atlas conserva la clasificación de **Jesús Rodríguez Barahona** como taxonomía independiente.

```text
                 OPENNESS
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
      BARAHONA               JGB
      taxonomía          libertad/control
      existente
```

No se debe sustituir una por otra, ni transformar ninguna en un score universal de calidad. Tener dos marcos permite comparar sus resultados y detectar dónde difieren sus criterios.

---

# 3. Regla de evidencia JGB

La clasificación JGB debe ser **demostrable**, no una etiqueta heredada.

Una fuente que diga `open weights` no se convierte automáticamente en `JGB 3`. El Atlas exige comprobar la evidencia pertinente y registrar:

- fuente;
- URL cuando exista;
- fecha de verificación;
- evidencia concreta;
- dimensión JGB afectada;
- nivel/categoría resultante;
- confianza;
- estado de verificación.

Si no hay evidencia suficiente:

```text
jgb_level       = unknown
jgb_class       = unknown
verification    = needs_verification
confidence      = low
```

**`unknown` es un resultado correcto. Inventar una clasificación no lo es.**

Los cambios de licencia, condiciones de uso, disponibilidad de pesos, código, datasets o documentación relevante deben poder provocar una nueva verificación.

---

# 4. El Atlas como base del recomendador

El Atlas se estructura para que el recomendador no tenga que adivinar relaciones que deberían estar en los datos.

```text
                     OPEN LLM ATLAS
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
    MODELOS             APERTURA            EVIDENCIA
       │              JGB + Barahona             │
       │                   │                     │
       └───────────────────┼─────────────────────┘
                           ▼
                    DEPLOYMENT LAYER
                           │
             modelo × quant × runtime × hardware
                           │
                           ▼
                     OBSERVACIONES
                  MSA / benchmarks / local
                           │
                           ▼
                RECOMMENDATION ENGINE
                           │
                           ▼
                RECOMENDACIÓN EXPLICABLE
                           │
                           ▼
                         LEONES
```

La unidad real de recomendación es, por tanto:

**modelo × variante × cuantización × runtime × hardware × workload × restricciones**.

---

# 5. MSA y rendimiento: observaciones, no propiedades universales

Las mediciones de **Model Speed Arena (MSA)** se incorporan como observaciones empíricas. Una medición no significa que «el modelo tenga X tokens/s» universalmente.

Debe conservarse el contexto:

```text
modelo
 + hardware
 + runtime
 + cuantización/formato
 + contexto
 + workload
       ↓
observación de rendimiento
```

Siempre que sea posible se conserva:

- fuente y URL;
- fecha;
- hardware;
- runtime;
- formato/cuanti­zación;
- contexto/carga;
- tokens/s, TTFT, TPOT u otras métricas disponibles;
- metodología;
- confianza.

Una observación externa nunca debe sobrescribir los metadatos intrínsecos del modelo.

---

# 6. El recomendador: cómo toma decisiones

El motor v0.1 será deliberadamente **determinista y explicable** antes de incorporar técnicas de aprendizaje automático.

## Fase A — filtros duros

Primero se eliminan configuraciones que no pueden cumplir la petición:

1. ¿Cabe en memoria?
2. ¿El hardware es compatible?
3. ¿Existe un runtime adecuado?
4. ¿El formato/cuanti­zación es compatible?
5. ¿Soporta el contexto requerido?
6. ¿Soporta la modalidad/workload solicitada?

Una configuración que falla un requisito obligatorio no debe quedar primera simplemente porque tenga mejores benchmarks.

## Fase B — ajuste al workload

Después se compara la adecuación a:

- chat;
- coding;
- reasoning;
- RAG;
- agents;
- batch.

El mismo modelo puede tener distinta utilidad según la carga.

## Fase C — evidencia de calidad y rendimiento

Se incorporan, sin mezclarlos de forma irreversible:

- benchmarks de calidad;
- observaciones de rendimiento;
- memoria utilizada;
- latencia;
- fiabilidad.

## Fase D — preferencias del usuario

El usuario puede establecer prioridades como:

- máxima privacidad/localidad;
- mayor velocidad;
- mayor calidad;
- menor consumo de memoria;
- mayor apertura JGB;
- compatibilidad con un runtime concreto.

## Fase E — explicación

Cada recomendación debe poder contestar:

> **Por qué este modelo/configuración está aquí y por qué otro quedó por debajo.**

La explicación debe señalar las evidencias y las incertidumbres, no limitarse a mostrar un número.

---

# 7. JGB dentro del recomendador

JGB **puede ser una restricción o una preferencia**, según la petición.

Ejemplo:

```text
«Quiero ejecutar un LLM localmente»
```

No implica automáticamente `JGB >= 3`.

En cambio:

```text
«Quiero un modelo Open Weight según JGB»
```

sí puede convertirse en una condición explícita del filtro.

Otro caso:

```text
«Prefiero más libertad, pero no es obligatorio»
```

convierte JGB en una preferencia ponderable, sin contaminar el score de calidad.

Así evitamos que el recomendador imponga una definición de «mejor» que el usuario no ha solicitado.

---

# 8. Hardware y runtime

Los primeros perfiles de referencia incluyen:

- Intel i5 + 16 GB RAM sin GPU;
- Intel i7 + 32 GB RAM sin GPU;
- Intel i7 + 64 GB RAM sin GPU;
- sistema CPU con 128 GB RAM;
- RTX 4060 8 GB + 32 GB RAM.

Los primeros runtimes de referencia son:

- llama.cpp;
- Ollama;
- vLLM;
- Hugging Face Transformers;
- KoboldCpp.

Estos perfiles son puntos de partida, no límites universales. Las recomendaciones deben poder incorporar nuevos hardware y runtimes conforme la prospección los detecte.

---

# 9. Prospección diaria → Atlas → recomendador

El Atlas no es una base de datos que se actualiza manualmente de vez en cuando. Forma parte del ciclo operativo de LEONES.

```text
                 PROSPECCIÓN DIARIA
                         │
                         ▼
                 nuevo/actualizado
                      modelo
                         │
                         ▼
                       ATLAS
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       ¿JGB?       ¿nuevo runtime?   ¿métricas?
          │              │              │
          ▼              ▼              ▼
    verificación       Atlas        observación
          │                             │
          └──────────────┬──────────────┘
                         ▼
                RECOMMENDATION ENGINE
                         │
                         ▼
                    RECOMENDADOR
                         │
                         ▼
                       LEONES
```

Un cambio de licencia o disponibilidad de pesos puede afectar JGB. Un nuevo runtime puede hacer viable un modelo en hardware que antes no lo era. Una nueva medición puede cambiar la preferencia entre dos configuraciones. El Atlas debe conservar esos cambios como conocimiento, no perderlos al regenerar una tabla.

---

# 10. Principios que quedan fijados

### A. No confundir `Open weights` con JGB 3

La etiqueta no sustituye la verificación.

### B. No confundir apertura con calidad

JGB describe libertad/apertura, no inteligencia.

### C. No confundir apertura con ejecución local

Self-hostability es una dimensión técnica independiente.

### D. No convertir tokens/s en una propiedad universal

El rendimiento depende de la configuración.

### E. No usar un score universal como sustituto de la decisión

La recomendación depende de la necesidad.

### F. Conservar evidencia y confianza

Cada dato relevante debe ser auditable.

### G. Mantener JGB y Barahona independientes

Son marcos distintos que pueden coexistir.

### H. Preferir `unknown` a una afirmación no demostrada

La incertidumbre forma parte del dato.

### I. Explicar las recomendaciones

Una recomendación sin razones y evidencia no es suficiente para LEONES.

---

# 11. Estructura del subproyecto

```text
web/proyectos/atlas/
├── README.md
├── ATLAS-RECOMMENDER-ARCHITECTURE.md
├── SCHEMAS-EXPLICATIVOS.md
├── DECISION-RULES.md
├── hardware_profiles.csv
├── runtime_profiles.csv
├── workload_profiles.csv
│
└── openness/
    ├── JGB-INDEX.md
    ├── JGB-MATRIX.md
    ├── JGB-METHOD.md
    ├── jgb_schema.sql
    └── jgb_verification_queue.csv
```

---

# 12. Evolución prevista

### v0.1 — Fundamentos

- Atlas integrado en LEONES.
- JGB fijado como marco de apertura.
- Barahona preservado como taxonomía independiente.
- Hardware/runtime/workload definidos.
- Evidencia y confianza incorporadas.

### v0.2 — Clasificación

Clasificación JGB verificada de los modelos de mayor prioridad local.

### v0.3 — Observaciones

Ingesta automatizada de MSA, benchmarks y mediciones propias.

### v0.4 — Motor

Motor determinista de compatibilidad y recomendación explicable.

### v0.5 — Automatización

Integración completa con la prospección diaria de LEONES.

### v1.0 — Recomendador operativo

Recomendación contextual, evidencia trazable, incertidumbre explícita y actualización continua.

---

# 13. Regla de oro

```text
NO:
modelo → score universal → recomendación

SÍ:
modelo
  + evidencia
  + JGB / Barahona
  + hardware
  + runtime
  + cuantización
  + workload
  + observaciones
  + preferencias
       ↓
RECOMENDACIÓN EXPLICABLE
```

El objetivo final del Atlas es que LEONES pueda pasar de **«conozco los modelos»** a **«sé qué modelo/configuración tiene sentido para ti y puedo explicarte por qué»**.
