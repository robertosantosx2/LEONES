# Contribuir a LEONES

> **Constrúyelo. Mídelo. Explícalo. Conserva la evidencia.**

Gracias por contribuir a **LEONES — Local Ecosystem of Open Neural Expert Systems**.

LEONES es un ecosistema abierto para construir conocimiento reproducible sobre modelos, hardware, runtimes, benchmarks, agentes, mediciones y recomendaciones. Esta guía toma como referencia las buenas prácticas de contributing.md, adaptándolas a la arquitectura, los contratos y el sistema de evidencia de LEONES.

---

## 🚀 Primeras contribuciones: Easy First Issues

Si es tu primera contribución, empieza por **[las 10 Easy First Issues](docs/EASY-FIRST-ISSUES.md)**. Están clasificadas por dificultad e impacto y cada una explica exactamente qué hay que cambiar, qué se aprende y cuáles son los criterios de aceptación.

**No necesitas conocer todo LEONES para empezar.** Puedes comenzar con documentación, conocimiento, tests o pequeñas mejoras de CI y avanzar hacia selector, runtime y benchmarks.

---

## 1. Qué valoramos

> **Descubrir, documentar, verificar, medir y conservar la procedencia. No convertir una afirmación en un hecho simplemente por repetición.**

Preferimos:

- reproducibilidad frente a anécdota;
- fuentes primarias frente a afirmaciones copiadas;
- evidencia frente a suposiciones;
- procedencia explícita frente a enriquecimiento no documentado;
- mediciones frente a estimaciones cuando existen mediciones;
- cambios pequeños y revisables frente a reescrituras opacas;
- automatización cuando mejora la consistencia;
- separación estricta entre fuente, evidencia, estimación y medición de LEONES.

**La evidencia es parte del producto, no un comentario añadido después.**

---

## 2. Antes de contribuir

1. Busca primero en la documentación, issues, pruebas e implementaciones existentes.
2. Comprueba si el trabajo ya está siendo discutido o desarrollado.
3. Para cambios importantes, abre un issue explicando el problema y la solución propuesta.
4. Lee la arquitectura, el esquema y los contratos relacionados antes de modificar un flujo de datos.
5. Mantén separados los cambios no relacionados salvo que sean necesarios para la corrección.

Empieza por:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/PILLARS.md`
- `docs/RESULT_SCHEMA.md`
- `docs/SOURCE-DISCOVERY.md`
- `docs/PIPELINE_E2E.md`
- `docs/EVALUACION_AGENTIC_TESTS.md`
- `docs/`
- `tests/`
- `.github/workflows/`

**Primero entiende la cadena de conocimiento; después modifica el código.**

---

## 3. Formas de contribuir

### Código

Nuevas funcionalidades, correcciones, adaptadores, runtimes, benchmarks, ingesta, validación, web, CI y automatización.

### Conocimiento e investigación

Proyectos, modelos, runtimes, benchmarks, datasets y fuentes; hallazgos técnicos; evidencia primaria; información contradictoria u obsoleta.

### Mediciones

Ejecuciones reproducibles de benchmarks, escenarios, harnesses, graders y configuraciones precisas de hardware, modelo, cuantización y runtime.

### Documentación

Arquitectura, flujos, incorporación de colaboradores, limitaciones, web de conocimiento, navegación y terminología.

### Issues y revisiones

Errores reproducibles, propuestas, revisiones de pull requests y cuestionamiento de afirmaciones sin respaldo.

**Una contribución pequeña pero verificable puede ser más valiosa que una gran contribución imposible de reproducir.**

---

## 4. Fuente, evidencia, estimación y medición

LEONES mantiene deliberadamente separados estos estados:

- `estimated`: cálculo o estimación;
- `reported`: valor declarado por una fuente externa;
- `observed`: configuración o comportamiento observado en un entorno;
- `measured`: medición ejecutada por LEONES;
- `verified`: información que ha superado el quality gate del proyecto;
- `unknown`: información que todavía no está suficientemente demostrada.

**Nunca promociones silenciosamente un estado a otro.** Si un valor se infiere, indícalo como inferencia o estimación. Un benchmark de terceros sigue siendo evidencia de terceros y no se convierte en medición física de LEONES salvo que LEONES lo haya ejecutado realmente.

---

## 5. Contribuciones a la base de conocimiento

Una ficha de conocimiento debe incluir, cuando corresponda:

1. nombre del proyecto o fuente;
2. URL canónica;
3. categoría;
4. qué es;
5. qué problema resuelve;
6. descripción técnica útil;
7. relación con modelos, hardware y runtimes;
8. licencia y grado de apertura;
9. evidencia y fuentes primarias;
10. limitaciones;
11. relación con LEONES;
12. papel que desempeña: inspiración, evidencia, referencia de implementación, fuente de descubrimiento, etc.;
13. versión o fecha cuando la actualidad del dato sea relevante.

El descubrimiento no convierte automáticamente una fuente en conocimiento canónico. Primero deben aplicarse las reglas de evidencia y quality gate del repositorio.

**No atribuyas a una fuente una conclusión que realmente pertenece a LEONES.**

---

## 6. Benchmarks y mediciones

Registra, cuando corresponda:

- modelo y revisión exactos;
- formato y cuantización;
- modelo de hardware, RAM/VRAM y capacidades relevantes;
- sistema operativo y versiones de drivers/runtime;
- runtime de inferencia y versión;
- flags y configuración del runtime;
- contexto, entrada y longitud de salida;
- concurrencia/batching;
- carga de trabajo y prompts;
- calentamiento y repeticiones;
- métricas recogidas;
- evidencia estructurada o bruta;
- limitaciones.

**No compares tokens/s sin documentar las condiciones de ejecución.**

Una clasificación derivada —por ejemplo CABE/RULA— no debe sustituir al dato primario (`tokens_per_second` u otra métrica medida).

---

## 7. Integraciones de modelo, runtime, selector y router

Mantén explícito el conjunto de ejecución:

`modelo + cuantización + runtime + hardware + configuración`

No escondas los supuestos del runtime dentro de los registros de modelos. Que un runtime sea compatible con un modelo no demuestra un rendimiento equivalente en todos los modelos o configuraciones.

Para trabajos sobre selector/router conserva la cadena:

`selección de candidatos → selección de runtime → ejecución → evaluación → benchmark → evidencia`

**La selección es una hipótesis hasta que la ejecución y la evidencia permitan validarla.**

---

## 8. Cambios de código

Prioriza cambios mínimos, legibles, deterministas y cubiertos por pruebas cuando sea razonable, manteniendo los contratos existentes. Documenta los cambios de comportamiento público.

Evita:

- ruido de formato no relacionado;
- borrar evidencia histórica;
- introducir valores medidos codificados a mano en selectores;
- cambios silenciosos de esquema o semántica;
- dependencias innecesarias;
- saltarse quality gates.

**El código debe hacer explícitos los supuestos que puedan afectar al resultado.**

---

## 9. Pruebas y CI

**GitHub Actions forma parte del contrato de contribución.** El conjunto de workflows puede evolucionar; consulta `.github/workflows/` y ejecuta las comprobaciones correspondientes al área afectada.

El workflow `contract-tests.yml` realiza, entre otras, estas comprobaciones principales:

```bash
python -m unittest discover -s tests/contracts -p 'test_*.py' -v
python -m pytest tests/contracts/test_freetoken_selector_contract.py -q
python -m pytest tests/contracts/test_knowledge_four_layers.py -q
python -m pytest tests -q
```

También comprueba aspectos como:

- todos los JSON Schema de `schemas/`;
- invariantes de versiones de contratos;
- estados de verificación de evidencia;
- modos OSI del router;
- invariantes de promoción y almacenamiento de Atlas;
- procedencia obligatoria en almacenamiento de evidencia;
- existencia y contenido de `tests/contracts/contract-tests.md`.

Otros workflows cubren áreas como ingesta/prospección/recomendaciones de Atlas, contratos de agentes A01, benchmarks medidos y descubrimiento diario. Los cambios que afecten a esas áreas deben validarse con sus workflows o pruebas correspondientes.

Para cambios de la web, valida las páginas afectadas, la navegación y los artefactos públicos generados.

Si una comprobación no puede ejecutarse localmente, indica exactamente qué se validó y qué no. **Nunca afirmes que una prueba ha pasado si no se ha ejecutado.**

---

## 10. Issues: errores y propuestas

### Informar de un error

Un buen informe debe incluir:

- comportamiento esperado;
- comportamiento observado;
- pasos para reproducirlo;
- entorno relevante;
- versiones relevantes;
- mensajes de error o trazas;
- resultado de las pruebas pertinentes;
- si el problema es reproducible y bajo qué condiciones.

**Un error reproducible es mucho más fácil de corregir que una descripción genérica del fallo.**

No publiques contraseñas, tokens, secretos, datos personales innecesarios ni detalles de vulnerabilidades privadas en un issue público.

### Proponer una mejora

Explica:

- qué problema resuelve;
- qué comportamiento existe actualmente;
- qué comportamiento propones;
- por qué es útil para LEONES;
- qué alternativas has considerado;
- cómo podría probarse.

**Describe primero el problema; después propone la solución.**

---

## 11. Pull requests

Un pull request debe ser revisable y trazable.

Incluye:

### Problema
Qué problema se resuelve.

### Solución
Qué ha cambiado y por qué esta es la capa adecuada.

### Evidencia
Qué fuentes, pruebas, mediciones u observaciones lo respaldan.

### Validación
Qué comprobaciones se ejecutaron realmente y con qué resultado.

### Riesgos y limitaciones
Qué sigue siendo desconocido o podría producir una regresión.

Indica expresamente si el cambio afecta a contratos, esquemas, datos públicos o al pipeline de recomendaciones.

### Checklist

- [ ] El cambio tiene un propósito claramente explicado.
- [ ] He comprobado que no existe ya una solución equivalente.
- [ ] He mantenido separadas fuente, evidencia, estimación y medición.
- [ ] He añadido o actualizado pruebas cuando corresponde.
- [ ] He actualizado la documentación afectada.
- [ ] He conservado la procedencia de los datos externos.
- [ ] He documentado las condiciones de las mediciones.
- [ ] No he introducido credenciales, secretos ni información sensible.
- [ ] He comprobado los contratos y regresiones relevantes.

**El pull request debe permitir a otra persona entender qué cambió, por qué y con qué evidencia.**

---

## 12. Datos y procedencia

Al modificar conocimiento o evidencia estructurada:

- conserva URLs de origen y procedencia;
- conserva timestamps/versiones cuando sean relevantes;
- conserva mediciones históricas cuando la diferencia tenga significado;
- no conviertas observaciones contradictorias en un valor único sin explicarlo;
- mantén distinguibles informes, estimaciones, observaciones y mediciones;
- prefiere `unknown` antes que inventar una completitud que no existe.

El objetivo es **datos confiables y trazables**, no simplemente más datos.

---

## 13. Web y publicación del conocimiento

La web pública de conocimiento debe conservar las capas del proyecto. Una ficha debe explicar qué es la fuente, qué aporta, qué evidencia respalda las afirmaciones y qué permanece incierto.

No publiques un elemento descubierto como evidencia establecida de LEONES sin la validación correspondiente. Prioriza URLs canónicas.

**La web publica conocimiento; no debe borrar la incertidumbre que existe en la evidencia original.**

---

## 14. Seguridad e información sensible

Nunca hagas commit de:

- contraseñas;
- API keys;
- access tokens;
- credenciales privadas;
- datos personales innecesarios;
- datos privados de benchmarks sin permiso;
- material propietario que legalmente no pueda redistribuirse.

Para vulnerabilidades de seguridad, no publiques detalles explotables en un issue público; utiliza el canal privado disponible para seguridad.

---

## 15. Colaboración y revisión

Cuestiona afirmaciones, implementaciones y metodologías, no a las personas. Pide evidencia y prefiere demostraciones reproducibles frente a autoridad o popularidad.

La revisión puede considerar procedencia, metodología, reproducibilidad, contratos, seguridad, licencias, coste de mantenimiento, impacto sobre el modelo de conocimiento y corrección de las recomendaciones, no solamente si el código funciona.

**La revisión protege la evidencia tanto como protege el código.**

---

## 16. Licencias

Al contribuir, confirma que tienes derecho a entregar la contribución bajo la licencia aplicable al repositorio. Para código, datasets, documentación o material externo, registra licencia y procedencia antes de incorporarlo.

**No confundas disponibilidad pública con permiso para redistribuir.**

---

## 17. Flujo de contribución

```text
IDEA / PROBLEMA
      ↓
BUSCAR TRABAJO EXISTENTE
      ↓
ISSUE / DISCUSIÓN (cuando sea útil)
      ↓
CAMBIO CENTRADO
      ↓
FUENTE + PROCEDENCIA
      ↓
PRUEBA / MEDICIÓN / VALIDACIÓN
      ↓
PULL REQUEST
      ↓
REVISIÓN
      ↓
MERGE
      ↓
DOCUMENTAR / PUBLICAR / CONSERVAR LA EVIDENCIA
```

---

## 18. Principio final

La contribución más valiosa no tiene por qué ser la más grande. Una pequeña modificación que conserva la procedencia, añade una prueba que faltaba, reproduce una medición, documenta una limitación de runtime o evita una afirmación sin respaldo puede valer más que una gran funcionalidad.

> **Constrúyelo. Mídelo. Explícalo. Conserva la evidencia.**

Esta frase resume la cultura técnica que queremos preservar en LEONES.

Para la guía general de contribución de código abierto, consulta contributing.md.
