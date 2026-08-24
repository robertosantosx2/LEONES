# Contrato de fichas de conocimiento LEONES

## 1. Propósito

La sección **Conocimiento de IA en Local** de LEONES no es un directorio de enlaces. Es una capa documental trazable que transforma fuentes externas, proyectos, herramientas, runtimes, metodologías y experimentos en conocimiento reutilizable sin confundir descubrimiento con evidencia, estimación con medición ni medición con recomendación.

Una ficha ampliada debe permitir responder, como mínimo:

1. qué es;
2. qué problema resuelve;
3. cuál es su fuente primaria;
4. qué afirma o demuestra la fuente;
5. qué interpreta LEONES a partir de ello;
6. qué es evidencia externa y qué es estimación;
7. qué ha medido realmente LEONES;
8. qué puede aprender o reutilizar LEONES;
9. qué no está demostrado;
10. qué falta para llevarlo al pipeline ejecutable.

---

## 2. Las cuatro capas documentales son obligatorias y no se mezclan

Toda afirmación relevante de una ficha debe pertenecer a una de estas capas:

### A. FUENTE / DESCUBRIMIENTO

Es el artefacto externo que origina el conocimiento: repositorio, documentación, paper, benchmark publicado, artículo, informe, release, demo o proyecto.

**Pregunta:** «¿De dónde sale?»

La fuente conserva su identidad, autoría, versión, fecha y enlace. Descubrir algo no implica que LEONES lo valide.

### B. EVIDENCIA

Es información verificable sobre el comportamiento o las propiedades del objeto, procedente de una fuente primaria o de una medición externa identificable.

Debe distinguirse entre:

- `evidence-primary`: documentación, código, paper, release o resultado publicado por el autor;
- `evidence-external`: medición o benchmark de terceros con metodología identificable;
- `verification-leones`: comprobación documental o reproducibilidad realizada por LEONES, sin implicar todavía benchmark propio.

**Pregunta:** «¿Qué está realmente respaldado?»

### C. ESTIMACIÓN

Es una predicción, cálculo, heurística, recomendación o clasificación producida por una herramienta o por un modelo externo.

Ejemplos: estimación de memoria, compatibilidad, throughput esperado, modelo recomendado por LLMFit, cálculo de ajuste de hardware o predicción de rendimiento.

**Pregunta:** «¿Qué se espera que ocurra?»

Una estimación puede ser muy útil para reducir el espacio de búsqueda, pero nunca se registra como medición LEONES.

### D. MEDICIÓN LEONES

Es un resultado producido por una ejecución reproducible de LEONES, con identidad de modelo/runtime, hardware, versiones, configuración, workload y artefactos suficientes para repetir o auditar el resultado.

**Pregunta:** «¿Qué ha observado LEONES ejecutándolo?»

Una medición no convierte automáticamente el objeto medido en recomendado: todavía debe superar los criterios de selección, calidad, seguridad, compatibilidad y tarea definidos por LEONES.

---

## 3. Regla de oro

> **Descubrir no es verificar. Verificar no es estimar. Estimar no es medir. Medir no es aprobar. Aprobar no es recomendar automáticamente.**

Por tanto, nunca se debe escribir una frase que transforme implícitamente:

```text
fuente → evidencia
estimación → medición
medición → recomendación
```

sin registrar el paso intermedio y su condición de validación.

---

## 4. Pipeline canónico

```text
FUENTE / DESCUBRIMIENTO
        │
        ▼
ANÁLISIS DOCUMENTAL LEONES
        │
        ├──────────────► EVIDENCIA PRIMARIA / EXTERNA
        │
        └──────────────► ESTIMACIÓN / HIPÓTESIS
                              │
                              ▼
                    CANDIDATO EJECUTABLE
                              │
                              ▼
                     runtime-selection.v1
                              │
                              ▼
                          EXECUTOR
                              │
                              ▼
                           GRADER
                              │
                              ▼
                     BENCHMARK LEONES
                              │
                              ▼
                     MEDICIÓN LEONES
                              │
                              ▼
                    EVIDENCE / REGISTRY
                              │
                              ▼
                         ROUTER / ATLAS
```

El bloque de conocimiento alimenta **prospección y contexto**. La decisión ejecutable se produce en las capas canónicas de selección y benchmark.

---

## 5. Estructura obligatoria de una ficha ampliada

### 5.1 Identidad y procedencia

- nombre oficial;
- nombre de referencia LEONES, si existe;
- organización/autores;
- repositorio oficial;
- documentación, paper o proyecto oficial;
- licencia, únicamente si está verificada;
- versión/release revisada;
- fecha de revisión;
- estado de procedencia;
- fuentes secundarias relevantes, claramente marcadas como secundarias.

### 5.2 Qué es

Explicación técnica, pero comprensible. Debe indicar la **capa arquitectónica**: modelo, cuantización, runtime, serving, despliegue, selector, benchmark, harness, workspace, agente, herramienta, metodología o fuente de prospección.

### 5.3 Qué no es

Debe aclarar las confusiones previsibles. Por ejemplo:

- FreeToken no es el benchmark canónico de LEONES;
- Odysseus no debe describirse como runtime de inferencia si la fuente no lo define así;
- LLMFit es un preselector/estimador hardware-aware, no una medición LEONES;
- AirLLM es una tecnología/runtime candidato para inferencia con restricciones de memoria, no una prueba de rendimiento propia;
- Magnitude y ODS pueden aportar estimaciones o automatización, pero no sustituyen el selector ni el benchmark de LEONES.

### 5.4 Arquitectura y mecanismo

Explicar por qué funciona o por qué resulta interesante: memoria, offload, scheduling, caché, cuantización, paginación, agentes, herramientas, MCP, serving, hardware-awareness, selección de modelos, instalación o evaluación.

No se debe copiar lenguaje promocional sin separar el claim de la interpretación técnica.

### 5.5 Fuente

Registrar qué afirma literalmente la fuente, en forma de paráfrasis verificable, y conservar el enlace al artefacto primario.

### 5.6 Evidencia

Para cada afirmación importante indicar:

| Campo | Significado |
|---|---|
| `evidence_type` | `primary`, `external`, `verification-leones` |
| `claim` | afirmación que se quiere respaldar |
| `source` | artefacto que la respalda |
| `version/date` | versión o fecha relevante |
| `conditions` | hardware, modelo, contexto, configuración, etc. |
| `confidence` | nivel documental: alto/medio/bajo |

Nunca eliminar las condiciones experimentales cuando estén disponibles.

### 5.7 Estimación

Toda predicción externa se registra como tal. Debe conservar:

- herramienta que estima;
- versión;
- entrada utilizada;
- resultado estimado;
- supuestos;
- margen o incertidumbre cuando exista;
- estado: `unverified`, `verification-pending` o `corroborated`.

### 5.8 Medición LEONES

Una ficha puede incluir una sección de medición, pero solo se rellena con resultados producidos por el pipeline de LEONES.

Mínimos recomendados:

- `model_id` / identidad exacta;
- runtime y versión;
- hardware y sistema;
- modelo/cuanti exactos;
- configuración;
- contexto;
- workload;
- warm-up;
- TTFT;
- TPOT / tokens por segundo;
- throughput bajo concurrencia cuando proceda;
- memoria utilizada;
- resultado funcional del workload;
- grader y score;
- artefactos/evidence ID;
- fecha de medición;
- reproducibilidad.

Si alguno de estos datos falta, el resultado debe quedar marcado como parcial y no presentarse como medición canónica completa.

### 5.9 Valor para LEONES

Explicar qué hipótesis confirma, cuestiona o amplía. Debe conectarse con componentes reales del sistema: selector, runtime-selection.v1, executor, grader, benchmark, evidence, Router o Atlas.

### 5.10 Integración propuesta

Cuando corresponda:

```text
selector
   ↓
runtime-selection.v1
   ↓
executor
   ↓
grader
   ↓
runtime benchmark
   ↓
evidence
   ↓
Router
```

Para workspace/harness:

```text
modelo → runtime → endpoint → workspace/harness → workload → grader
```

### 5.11 Variables de selección y medición

Según la capa, considerar:

- VRAM;
- RAM;
- ancho de banda de memoria;
- CPU/GPU;
- transferencia host↔GPU/PCIe;
- tamaño total y activo de expertos;
- localidad/reutilización;
- KV cache;
- contexto;
- workload;
- latencia objetivo;
- throughput;
- concurrencia;
- compatibilidad modelo/cuanti/runtime;
- sistema operativo;
- versión del runtime;
- coste operativo.

### 5.12 Limitaciones

Registrar explícitamente hardware, sistemas operativos, dependencias, compatibilidad, estado de desarrollo, issues relevantes, ausencia de evidencia y condiciones que impidan generalizar resultados.

### 5.13 Clasificación LEONES

La clasificación describe el **estado dentro de LEONES**, no la calidad universal del proyecto.

Estados admitidos:

- `source-inspiration`
- `research-candidate`
- `runtime-candidate`
- `workspace-reference`
- `harness-reference`
- `preselector`
- `verified-primary`
- `measured`
- `rejected`
- `unresolved`

Puede haber más de una etiqueta funcional cuando sea necesario, pero solo una debe representar el estado de promoción principal.

### 5.14 Próximo paso

Toda ficha activa debe terminar indicando qué falta: verificación, integración, benchmark, regresión, documentación o decisión.

---

## 6. Modelo de estados

```text
source-inspiration
       │
       ▼
research-candidate
       │
       ├──► unresolved
       │
       ▼
verified-primary
       │
       ├──► rejected
       │
       ▼
 runtime/preselector/workspace/harness candidate
       │
       ▼
  runtime-selection.v1
       │
       ▼
      measured
       │
       ▼
 recommendation candidate
```

`measured` nunca significa «recomendado». Significa únicamente que LEONES ha obtenido una medición reproducible.

---

## 7. Regla específica FreeToken / «El otro FreeToken» / Odysseus

Los proyectos deben conservar fichas independientes porque el conocimiento que aportan no debe colapsarse en una única categoría.

```text
                         LEONES
                           │
             ┌─────────────┴─────────────┐
             │                           │
      selección/runtime          workload/workspace
             │                           │
         FreeToken                   Odysseus
             │                           │
             └────────── endpoint ───────┘
                           │
                        workload
                           │
                         grader
                           │
                    evidencia/medición
```

La posible combinación **FreeToken + Odysseus** es una hipótesis de integración que debe medirse; ninguno de los dos se convierte por ello en autoridad sobre el otro.

---

## 8. Regla específica para herramientas de estimación

LLMFit, ODS, Magnitude y herramientas equivalentes pueden reducir el espacio de búsqueda y aportar señales útiles. Sus resultados deben almacenarse como **estimaciones externas** hasta que una ejecución LEONES los corrobore.

La cadena correcta es:

```text
estimación externa
      ↓
recommendation candidate
      ↓
selector LEONES
      ↓
executor
      ↓
benchmark
      ↓
medición LEONES
```

Nunca:

```text
estimación externa → measured
```

---

## 9. Regla editorial de la web

La web de conocimiento es una vista navegable del conocimiento documental. No debe reducir las fichas a listas de proyectos.

Cada tarjeta debe mostrar, como mínimo:

- identidad;
- qué es;
- función/capa;
- estado LEONES;
- procedencia;
- tipo de evidencia disponible;
- si existen estimaciones;
- si existen mediciones LEONES;
- qué falta para promocionarlo;
- enlace a la ficha ampliada;
- enlace a la fuente primaria.

Las fichas estratégicas —FreeToken, «El otro FreeToken»/Odysseus, LLMFit, AirLLM, Magnitude, ODS, runtimes, harnesses y metodologías de evaluación— deben ser suficientemente amplias para entender su papel sin abrir el repositorio.

---

## 10. Regla de actualización

Cada revisión debe:

1. conservar el contenido histórico relevante;
2. identificar la versión/release revisada;
3. distinguir cambios de la fuente de cambios de LEONES;
4. actualizar evidencia sin reescribirla como medición;
5. invalidar estimaciones obsoletas cuando cambien sus supuestos;
6. mantener las mediciones LEONES como registros históricos reproducibles;
7. actualizar la web sin alterar la semántica del registro documental;
8. ejecutar los contract-tests/regresiones correspondientes cuando la ficha afecte al selector o runtime.

---

## 11. Criterio de calidad editorial

Una ficha está **homogeneizada** cuando un lector puede localizar siempre las mismas cuatro respuestas:

> **Fuente:** ¿de dónde procede?
>
> **Evidencia:** ¿qué está respaldado?
>
> **Estimación:** ¿qué se predice o recomienda externamente?
>
> **Medición LEONES:** ¿qué ha ejecutado y observado LEONES?

Si una cifra no puede responder a una de esas preguntas, debe marcarse como pendiente de clasificación y no utilizarse para decisiones automáticas.
