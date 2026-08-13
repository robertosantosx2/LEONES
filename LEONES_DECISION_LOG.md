# LEONES — Historia, decisiones y fundamentos del proyecto

**Local Ecosystem of Open Neural Expert Systems (LEONES)**

Este documento recoge el conocimiento acumulado durante el diseño inicial del proyecto: qué problema queremos resolver, qué decisiones se han fijado, qué se ha descartado y por qué. Es el documento de referencia para que una persona nueva pueda entender el proyecto sin depender del historial de conversaciones.

> **Estado:** documento fundacional. Las decisiones marcadas como «congelada» solo deben cambiarse mediante una decisión explícita y documentada.

## 1. Punto de partida

LEONES nace de una investigación sobre la **capa agéntica de IA**: el conjunto de componentes que permite que un modelo deje de ser solamente un generador de texto y pueda planificar, usar herramientas, trabajar con archivos, ejecutar tareas de varios pasos, recuperar errores y completar objetivos.

El objetivo no es estudiar agentes de forma puramente teórica ni seleccionar la plataforma más potente en abstracto. El proyecto busca identificar y construir un **ecosistema agentic libre y abierto que pueda ejecutarse realmente en hardware de consumo**.

## 2. Principio rector: Libre, no «gratis»

Se adoptó deliberadamente la palabra **Libre** en lugar de «Free».

La razón es conceptual: el proyecto está interesado en la **libertad del software y la capacidad de estudiarlo, modificarlo, ejecutarlo y redistribuirlo**, no en que un servicio tenga precio cero.

El criterio de evaluación se integra ahora en el marco LEONES como denominación principal.

## 3. Prioridad a Open y, dentro de Open, a Copyleft

La investigación empezó considerando plataformas y herramientas de la capa agéntica, incluyendo proyectos como Buddy, LangGraph, Hermes, OpenHands y otros componentes del ecosistema.

Se estableció una regla de filtrado progresiva:

1. descartar lo que no sea Open;
2. priorizar especialmente licencias Copyleft;
3. entre alternativas comparables, favorecer las que maximicen libertad, auditabilidad y posibilidad de construir sobre ellas.

La licencia no es el único criterio de utilidad, pero sí un criterio estructural del proyecto.

## 4. Buddy como pieza imprescindible

Se incorporó **Buddy**, de Juanje Ojeda, como pieza imprescindible de la pila candidata.

Repositorio: https://github.com/juanje/buddy

La razón es que Buddy encaja con la orientación de LEONES hacia un agente local que consigue mantener el conocimiento aunque cambien el resto de capas de la pila y, según el repositorio estudiado durante el proyecto, está bajo **GPL-3.0**. La licencia Copyleft tiene un peso especial dentro de la investigación.

Buddy no se considera simplemente «otro agente» dentro de una lista: pasa a formar parte de la arquitectura candidata que debe probarse.

## 5. Ecosistema candidato congelado: LEONES

Se decidió congelar una primera pila candidata para pasar de la investigación conceptual a la implementación.

La pila incluye especialmente:

- **Buddy** como capa agéntica/local;
- **Hermes**;
- **LangGraph**;
- **llama.cpp** como backend local de inferencia;
- modelos en formato **GGUF**;
- herramientas complementarias que puedan permitir ejecutar modelos grandes en hardware de consumo.

La pila no se considera óptima para siempre. Se congela para poder medirla y disponer de una referencia experimental. Posteriormente se comparará con alternativas y se optimizará.

## 6. La restricción que cambia todo: hardware de consumo

Esta es una de las decisiones fundamentales del proyecto.

LEONES **no es un proyecto teórico para ricos ni una plataforma pensada exclusivamente para estaciones de trabajo o centros de datos**.

Debe poder ejecutarse en hardware que pueda tener una persona normal:

- **8 GB RAM**
- **16 GB RAM**
- **32 GB RAM**
- **64 GB RAM**

Con:

- Intel i5/i7 o equivalentes;
- con GPU o sin GPU.

Los perfiles de memoria son una variable de diseño central porque determinan qué modelos y qué técnicas de inferencia/offloading son realmente accesibles.

## 7. El criterio de utilidad: tareas, no solo tok/s

Inicialmente se utilizó tok/s como referencia de rendimiento. Después se decidió que LEONES debía pasar de medir únicamente velocidad de generación a medir **tareas agénticas reales**.

La razón es sencilla: un agente no existe para producir tokens; existe para completar objetivos.

Por ello se definió **LB** como una batería de tareas reproducibles:

- **B01 — memoria/localidad**
- **B02 — operación sobre archivos**
- **B03 — tarea multietapa**
- **B04 — recuperación ante fallo**
- **B05 — coding local**

La velocidad sigue siendo necesaria, pero deja de ser el único criterio.

## 8. Umbral de usabilidad

Se fijó una restricción especialmente importante:

**10 tok/s es el mínimo de usabilidad LEONES.**

Por debajo de 10 tok/s un resultado puede ser técnicamente interesante y debe conservarse como dato experimental, pero no se considera que la configuración sea suficientemente usable bajo el criterio actual.

Se fijó además:

**100 tok/s como máximo de comparación.**

No es un requisito de que todas las configuraciones lleguen a 100 tok/s. Es un techo práctico para las comparativas y visualizaciones.

## 9. «CABE» y «RULA»

Durante el diseño se decidió abandonar terminología anglosajona en dos conceptos operativos y utilizar deliberadamente:

- **CABE** en lugar de «fit»;
- **RULA** en lugar de «run».

La terminología forma parte del vocabulario del proyecto y debe conservarse en la documentación.

## 10. Del diseño a la implementación

Se pasó de una fase de investigación a una fase de implementación real.

La arquitectura experimental quedó conceptualmente:

```text
                    BUDDY
                  GPL-3.0
                     │
                 Pi / agente
                     │
                     ▼
          OpenAI-compatible API
                     │
                     ▼
                llama-server
                     │
                     ▼
                    GGUF
                     │
                     ▼
          Hardware de consumo
                     │
                     ▼
                  LB B01-B05
```

La primera infraestructura de referencia utiliza **llama.cpp server** porque permite exponer una API compatible con OpenAI y conectar la capa agéntica con un motor de inferencia local.

## 11. Baseline LB-0

Para que las comparaciones sean reproducibles se seleccionó un primer modelo de referencia:

**Qwen3-8B — Q4_K_M — GGUF**

Se escogió porque representa un compromiso razonable para comenzar las pruebas en máquinas de 16 GB y porque permite estudiar posteriormente el efecto de otras cuantizaciones.

Se conservaron como comparaciones:

- Qwen3-8B Q5_K_M;
- Qwen3-8B Q8_0;
- Qwen3-14B Q4_K_M para perfiles de 32/64 GB.

Importante: seleccionar LB-0 **no implica afirmar que alcance 10 tok/s en cualquier hardware**. Esa cifra debe medirse en la máquina real.

## 12. Separación entre benchmark de inferencia y evaluación agentiva

Se decidió no mezclar ambas cosas.

### Nivel 1 — Inferencia

Mide:

- carga del modelo;
- prompt evaluation tok/s;
- generation tok/s;
- memoria;
- estabilidad;
- tiempo total.

### Nivel 2 — Agentic

Mide:

- éxito de B01-B05;
- tiempo de tarea;
- tool calls;
- errores;
- capacidad de completar el objetivo;
- rendimiento del modelo dentro del agente.

Esto evita declarar que un agente es bueno simplemente porque su modelo genera tokens rápidamente.

## 13. Regla de evidencia

Los benchmarks encontrados en Internet pueden servir para **investigación, selección de candidatos e hipótesis**, pero no sustituyen un resultado oficial LEONES.

Un resultado oficial debe proceder de:

- hardware real;
- modelo exacto;
- cuantización exacta;
- backend exacto;
- versión/commit identificable;
- parámetros reproducibles;
- medición nativa;
- resultado de tarea cuando corresponda.

No se deben importar cifras de tok/s de terceros como si fueran medidas LB.

## 14. Primer experimento: H1

Se decidió comenzar por el perfil:

**H1 = 16 GB RAM**

con CPU i5/i7 o equivalente, con o sin GPU.

La secuencia es:

1. medir hardware;
2. identificar el GGUF por SHA-256;
3. fijar commit de llama.cpp;
4. fijar commit de Buddy;
5. ejecutar inferencia nativa;
6. repetir mediciones después de un warm-up;
7. comprobar llama-server;
8. conectar Buddy;
9. ejecutar B01-B05;
10. emitir el resultado según el protocolo.

El perfil H0 de 8 GB se conserva como prueba de estrés. H2 y H3 permiten estudiar escalado y margen de maniobra.

## 15. Por qué no basta con llama.cpp

La investigación incorpora como líneas de comparación técnicas/proyectos que buscan hacer viables modelos grandes en hardware limitado, incluyendo:

- **AirLLM**;
- **WASTE**;
- **KTransformers**;
- otras aproximaciones de offloading, memoria y ejecución local que se incorporen posteriormente.

La idea es comparar no solamente agentes, sino también la infraestructura que hace posible que esos agentes funcionen en máquinas de consumo.

Por eso la arquitectura se entiende como un ecosistema y no como un único programa.

## 16. metaLEONES: convertir LEONES en una red distribuida

Se decidió incorporar **metaLEONES** para que cualquier persona pueda aportar resultados de su propio hardware al repositorio de GitHub.

La aportación será un fichero **Markdown**, no una telemetría automática obligatoria.

Debe describir:

- CPU;
- arquitectura;
- núcleos/hilos;
- RAM;
- GPU/VRAM;
- almacenamiento relevante;
- sistema operativo/kernel;
- Buddy y commit;
- llama.cpp y commit;
- modelo;
- cuantización;
- SHA-256;
- parámetros;
- tok/s;
- memoria;
- B01-B05;
- errores y observaciones técnicas.

## 17. Privacidad de metaLEONES

Una decisión explícita es que **metaLEONES no debe convertirse en un sistema de recopilación de datos personales**.

No se deben publicar:

- nombres;
- emails;
- usuarios del sistema;
- hostnames identificables;
- números de serie;
- UUID;
- MAC/IP;
- ubicación exacta;
- rutas personales;
- credenciales;
- tokens;
- identificadores equivalentes.

El resultado identifica al **experimento**, no a la persona.

Ejemplo:

`ML-H1-QWEN3-8B-Q4KM-001`

## 18. Calidad y confianza de los resultados metaLEONES

Se estableció una clasificación de procedencia:

```text
reported → reproducible → verified
```

Y una categoría separada:

```text
rejected
```

Esto permite distinguir un dato aportado por un usuario de uno que contiene toda la información necesaria para reproducirlo y de uno que ha sido realmente verificado.

Nunca debe presentarse `reported` como `verified`.

## 19. GitHub como fuente canónica

Se decidió que el proyecto completo debe vivir en el repositorio público **LEONES**.

Los ZIP generados durante el desarrollo sirven como entregas auxiliares, pero **GitHub es la fuente canónica del proyecto**.

El repositorio debe contener el código, protocolos, documentación, configuración, tests, plantillas y resultados públicos, evitando modelos GGUF pesados, logs personales, credenciales y artefactos innecesarios.

## 20. Qué debe encontrar una persona nueva en LEONES

Una persona que llegue al proyecto debe poder entender, sin leer esta conversación:

1. qué es LEONES;
2. por qué es Libre/Open;
3. por qué se prioriza Copyleft;
4. por qué Buddy es una pieza central;
5. qué significa hardware de consumo;
6. qué son H0-H3;
7. qué es LB;
8. por qué 10 tok/s es el umbral;
9. qué significa CABE y RULA;
10. cómo se mide la inferencia;
11. cómo se miden las tareas agentic;
12. qué es metaLEONES;
13. cómo aportar un resultado sin datos personales;
14. cómo distinguir un resultado reportado de uno verificado.

## 21. Lo que NO está congelado

La arquitectura inicial sí está congelada como referencia, pero no se considera definitiva.

Especialmente quedan abiertos:

- optimización de las métricas LEONES;
- nuevos agentes y runtimes;
- nuevos backends de inferencia;
- nuevas técnicas para ejecutar modelos grandes en hardware de consumo;
- nuevas tareas de evaluación;
- ponderación de calidad frente a velocidad;
- métricas de memoria/energía;
- comparación sistemática entre CPU y GPU;
- resultados masivos procedentes de metaLEONES.

La intención es que los datos permitan mejorar el ecosistema, no que el ecosistema se diseñe para confirmar una conclusión previa.

## 22. Filosofía final

LEONES no pretende demostrar que la IA local es posible en abstracto.

Pretende responder experimentalmente a una pregunta mucho más concreta:

> **¿Qué ecosistema de software Libre/Open, especialmente Copyleft, permite convertir hardware de consumo en una máquina agentic realmente útil?**

Y la respuesta debe salir de mediciones reproducibles realizadas sobre máquinas reales, no de especificaciones comerciales ni de benchmarks aislados.

Ese es el principio que debe guiar las siguientes decisiones del proyecto.
