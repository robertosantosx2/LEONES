# 🦁 Easy First Issues — LEONES

Esta página reúne diez tareas pequeñas y acotadas para que una persona que todavía no conozca profundamente LEONES pueda hacer su primera contribución útil.

La selección sigue una regla: **la primera contribución debe ser pequeña, verificable y pedagógica, pero debe reforzar una parte real del proyecto**.

## Cómo elegir

- **Dificultad 1/5:** principalmente documentación y cambios muy acotados.
- **Dificultad 2/5:** documentación estructurada o tests sencillos.
- **Dificultad 3/5:** requiere entender una parte del pipeline y añadir una validación o integración controlada.
- **Impacto 2/5:** mejora local.
- **Impacto 3/5:** mejora reutilizable.
- **Impacto 4/5:** fortalece una capa importante de conocimiento o documentación.
- **Impacto 5/5:** protege contratos, evidencia o CI y puede evitar regresiones relevantes.

> **No hace falta ser experto en IA para empezar. Hace falta respetar la evidencia, la procedencia y los contratos del proyecto.**

## Las 10 primeras contribuciones

| # | Issue | Dificultad | Impacto | Área |
|---|---|---:|---:|---|
| 1 | [#43 — Mejorar la guía de contribución con un ejemplo completo](https://github.com/robertosantosx2/LEONES/issues/43) | 1/5 | 2/5 | Documentación |
| 2 | [#44 — Añadir glosario de términos de LEONES](https://github.com/robertosantosx2/LEONES/issues/44) | 1/5 | 3/5 | Documentación |
| 3 | [#45 — Documentar cómo validar enlaces internos](https://github.com/robertosantosx2/LEONES/issues/45) | 1/5 | 3/5 | Calidad documental |
| 4 | [#46 — Añadir plantilla de ficha para una nueva fuente de conocimiento](https://github.com/robertosantosx2/LEONES/issues/46) | 2/5 | 4/5 | Conocimiento |
| 5 | [#47 — Añadir un test de contrato para una distinción de evidencia](https://github.com/robertosantosx2/LEONES/issues/47) | 2/5 | 5/5 | CI / contratos |
| 6 | [#48 — Documentar una fuente externa de benchmark con procedencia completa](https://github.com/robertosantosx2/LEONES/issues/48) | 2/5 | 4/5 | Evidencia |
| 7 | [#49 — Añadir un caso de prueba para hardware sin GPU](https://github.com/robertosantosx2/LEONES/issues/49) | 3/5 | 5/5 | Hardware / selector |
| 8 | [#50 — Añadir documentación de un runtime al conocimiento](https://github.com/robertosantosx2/LEONES/issues/50) | 3/5 | 4/5 | Runtime |
| 9 | [#51 — Crear un benchmark sintético mínimo para CI](https://github.com/robertosantosx2/LEONES/issues/51) | 3/5 | 5/5 | Benchmarks / CI |
| 10 | [#52 — Añadir validación de procedencia a una entrada de conocimiento](https://github.com/robertosantosx2/LEONES/issues/52) | 3/5 | 5/5 | Evidencia / datos |

---

## 1. Mejorar la guía de contribución con un ejemplo completo

**Issue:** #43 · **Dificultad:** 1/5 · **Impacto:** 2/5

### Qué se aprende
Cómo se transforma una idea sencilla en una contribución revisable: localizar el lugar correcto, hacer un cambio pequeño, conservar procedencia y ejecutar la validación correspondiente.

### Qué hay que hacer
Añadir a `CONTRIBUTING.md` un ejemplo realista de principio a fin, preferiblemente documental o de conocimiento. El ejemplo debe enseñar qué archivos se tocan, cómo se justifica el cambio y qué comprobaciones se ejecutan.

### Por qué importa
La documentación de contribución es la puerta de entrada al proyecto. Un ejemplo concreto reduce la barrera de entrada mucho más que una lista abstracta de reglas.

### Aceptación
- El ejemplo puede seguirlo una persona nueva.
- No contiene evidencia inventada.
- Distingue fuente, evidencia, estimación y medición.
- Incluye validaciones reales del repositorio.

---

## 2. Añadir glosario de términos de LEONES

**Issue:** #44 · **Dificultad:** 1/5 · **Impacto:** 3/5

### Qué se aprende
La terminología es parte de la arquitectura. Cambiar el significado de `measured`, `reported` o `verified` puede producir errores aunque el código siga funcionando.

### Qué hay que hacer
Crear o ampliar un glosario con `source`, `evidence`, `reported`, `observed`, `estimated`, `measured`, `verified`, `unknown`, `runtime`, `quantization`, `selector`, `router`, `benchmark` y `provenance`.

### Por qué importa
Permite que documentación, código, issues y PR usen el mismo vocabulario.

### Aceptación
Cada término debe tener definición en español, significado específico dentro de LEONES y enlace a documentación relevante cuando exista. No deben alterarse contratos existentes.

---

## 3. Documentar cómo validar enlaces internos

**Issue:** #45 · **Dificultad:** 1/5 · **Impacto:** 3/5

### Qué se aprende
Cómo mantener documentación navegable sin convertir una tarea de mantenimiento en una reescritura.

### Qué hay que hacer
Documentar un procedimiento sencillo para comprobar enlaces relativos de `README.md`, `CONTRIBUTING.md` y documentación relacionada. Explicar cómo detectar rutas movidas y cómo corregirlas sin cambios no relacionados.

### Por qué importa
El conocimiento de LEONES se distribuye entre muchas páginas. Los enlaces rotos dificultan el descubrimiento y hacen que una ruta documental parezca inexistente.

### Aceptación
Procedimiento claro, reproducible y sin dependencias innecesarias.

---

## 4. Añadir plantilla de ficha para una nueva fuente de conocimiento

**Issue:** #46 · **Dificultad:** 2/5 · **Impacto:** 4/5

### Qué se aprende
Cómo LEONES convierte una fuente externa en conocimiento documentado sin confundir descubrimiento con evidencia canónica.

### Qué hay que hacer
Crear una plantilla que cubra identidad, URL canónica, categoría, qué es, utilidad, evidencia primaria, licencia/apertura, limitaciones, relación con LEONES, estado de evidencia y fecha/versionado cuando sea relevante.

### Por qué importa
Las fichas son una interfaz humana de la base de conocimiento. Una plantilla homogénea permite comparar fuentes sin borrar sus diferencias.

### Aceptación
La plantilla debe reflejar la procedencia y mantener separadas fuente, evidencia, estimación y medición.

---

## 5. Añadir un test de contrato para una distinción de evidencia

**Issue:** #47 · **Dificultad:** 2/5 · **Impacto:** 5/5

### Qué se aprende
Cómo una regla metodológica se convierte en una garantía automática de CI.

### Qué hay que hacer
Añadir un test en `tests/contracts/` que demuestre que un dato `estimated` o `reported` no se presenta como `measured`.

### Por qué importa
Es una de las defensas fundamentales de LEONES: **una cifra no se vuelve una medición por repetirse en varias fuentes**.

### Aceptación
Test determinista, mensaje de fallo claro, reutilización de estructuras existentes y compatibilidad con `contract-tests`.

---

## 6. Documentar una fuente externa de benchmark con procedencia completa

**Issue:** #48 · **Dificultad:** 2/5 · **Impacto:** 4/5

### Qué se aprende
Cómo registrar conocimiento externo sin atribuir a LEONES una medición que nunca ejecutó.

### Qué hay que hacer
Elegir un benchmark relevante y crear/ampliar su ficha con fuente primaria, URL canónica, qué mide, condiciones conocidas, limitaciones y utilidad para LEONES.

### Por qué importa
Los benchmarks externos son evidencia útil, pero sus condiciones pueden ser diferentes de las del hardware del usuario.

### Aceptación
Procedencia completa, ausencia de datos inventados y distinción explícita entre evidencia de terceros y medición LEONES.

---

## 7. Añadir un caso de prueba para hardware sin GPU

**Issue:** #49 · **Dificultad:** 3/5 · **Impacto:** 5/5

### Qué se aprende
Cómo el selector debe razonar sobre capacidades reales y no asumir que toda máquina dispone de aceleración GPU.

### Qué hay que hacer
Crear un caso de prueba CPU-only y verificar que el flujo de selección no atribuye una GPU inexistente. Cuando haga falta ejecución, usar un runtime falso/controlado.

### Por qué importa
LEONES debe servir también para hardware de consumo sin GPU dedicada. Este caso evita que las recomendaciones se construyan sobre capacidades implícitas.

### Aceptación
Ejecución determinista en CI, perfil de hardware explícito y comprobación de que la recomendación no afirma capacidades inexistentes.

---

## 8. Añadir documentación de un runtime al conocimiento

**Issue:** #50 · **Dificultad:** 3/5 · **Impacto:** 4/5

### Qué se aprende
Cómo describir un runtime como componente independiente del modelo.

### Qué hay que hacer
Documentar un runtime de inferencia relevante: qué es, modelos soportados, plataformas, cuantización/configuración conocida, licencia, fuente primaria, limitaciones y posible papel en selector/router.

### Por qué importa
El rendimiento depende de la combinación **modelo + cuantización + runtime + hardware + configuración**. Una ficha de modelo no puede esconder las características del motor.

### Aceptación
Fuente canónica, procedencia completa y separación entre capacidades declaradas y rendimiento medido.

---

## 9. Crear un benchmark sintético mínimo para CI

**Issue:** #51 · **Dificultad:** 3/5 · **Impacto:** 5/5

### Qué se aprende
Cómo probar el pipeline de benchmark sin depender de GPU, pesos externos, Internet o un modelo concreto.

### Qué hay que hacer
Crear un escenario sintético/controlado que produzca métricas deterministas o acotadas y permita comprobar el almacenamiento de resultados y evidencia.

### Por qué importa
La infraestructura de benchmark necesita una prueba barata y estable para detectar regresiones antes de ejecutar mediciones costosas.

### Aceptación
Rápido, reproducible en GitHub Actions, etiquetado inequívocamente como `synthetic`/`controlled` y sin presentarlo como rendimiento físico real.

---

## 10. Añadir validación de procedencia a una entrada de conocimiento

**Issue:** #52 · **Dificultad:** 3/5 · **Impacto:** 5/5

### Qué se aprende
Cómo convertir la procedencia en una condición técnica de calidad, no solo en una recomendación editorial.

### Qué hay que hacer
Elegir un punto de ingesta o publicación y añadir una comprobación que rechace una entrada sin la procedencia mínima definida por el esquema/contrato.

### Por qué importa
Una base de conocimiento con más datos pero sin procedencia puede ser menos fiable que una base más pequeña y trazable.

### Aceptación
Debe existir un caso válido y otro inválido, el error debe ser claro y no deben rellenarse automáticamente campos ausentes con información inventada.

---

## Principio para todas estas tareas

**Construir pequeño. Medir lo que se pueda. Explicar lo que se haga. Conservar la evidencia.**

Una primera contribución no tiene que ser espectacular. Si mejora la reproducibilidad, la trazabilidad, la documentación, los contratos o la capacidad de medir, ya está fortaleciendo LEONES.