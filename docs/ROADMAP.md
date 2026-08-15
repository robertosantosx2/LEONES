# LEONES — Roadmap y trabajo pendiente

Este documento consolida el estado de las líneas de trabajo de LEONES y evita que las tareas pendientes queden repartidas entre conversaciones, workflows y documentos aislados.

> **Criterio:** una capacidad se considera terminada cuando está implementada, documentada y validada cuando la naturaleza de la tarea lo permite. «Existe código» no equivale a «está terminado».

## 1. Estado general

LEONES ya dispone de una base funcional importante: prospección automatizada, Atlas, workflows de ingestión, bot mensual de precios de hardware, control de calidad de precios, integración de precios con el recomendador y un ranking económico V1 validado mediante GitHub Actions.

El siguiente salto consiste en pasar de componentes funcionales a un **sistema integrado, medible y mantenible** que cierre el bucle:

```text
PROSPECCIÓN
    ↓
ATLAS
    ↓
JGB + evidencia
    ↓
RECOMENDADOR
    ↓
HARDWARE + PRECIO
    ↓
EJECUCIÓN LOCAL
    ↓
BENCHMARK / AGENTIC
    ↓
MANADA
    ↓
NUEVA EVIDENCIA
    ↺
```

---

## 2. Prioridad P0 — cerrar el núcleo de conocimiento

### 2.1 Atlas como fuente única de verdad

- Consolidar definitivamente modelos, familias, organizaciones, benchmarks, hardware y procedencia.
- Definir identificadores estables y reglas de deduplicación.
- Evitar que CSV, JSON, SQLite y páginas web diverjan.
- Definir claramente qué campos son observados, derivados, inferidos o verificados.
- Añadir validaciones de esquema al pipeline.
- Garantizar trazabilidad desde cada dato hasta su fuente.

### 2.2 Índice JGB

- Mantener el JGB como dimensión independiente de rendimiento y precio.
- Documentar de forma exhaustiva la aplicación del criterio a cada modelo.
- Completar la clasificación de los modelos pendientes.
- Añadir procedencia/evidencia para cada valoración.
- Separar claramente clasificación conceptual, puntuación y ranking económico.
- Incorporar pruebas para evitar que el motor sustituya accidentalmente JGB por una puntuación de rendimiento.

### 2.3 Taxonomía y benchmarks

- Completar la taxonomía de familias/modelos.
- Normalizar nombres y variantes.
- Ampliar benchmarks científicos, de código, razonamiento y agentic.
- Registrar versión, fecha y condiciones de cada benchmark.
- Separar resultados publicados por terceros de mediciones locales de LEONES.

---

## 3. Prioridad P0 — recomendador completo

### 3.1 Matriz de hardware

Completar la matriz objetivo con:

- RAM: **2 / 4 / 8 / 16 / 32 / 64 / 128 GB**.
- Intel: **i3 / i5 / i7 / i9**.
- AMD: equivalentes **Ryzen 3 / 5 / 7 / 9**.
- GPU NVIDIA relevantes para IA.
- configuraciones CPU-only y CPU+GPU.
- VRAM como dimensión independiente de la RAM del sistema.

### 3.2 CABE y RULA

- Formalizar la función **CABE**: determinar si una combinación modelo/hardware es técnicamente viable.
- Formalizar **RULA**: determinar si una configuración viable es realmente utilizable bajo los criterios LEONES.
- Incorporar contexto: cuantización, backend, offloading, contexto, batch y VRAM.
- Evitar que «cabe» se interprete como «rinde bien».

### 3.3 Ranking económico V1 → V2

La V1 ya está implementada y validada. Queda:

- ampliar la cobertura de precios a toda la matriz;
- incorporar GPU y VRAM de forma sistemática;
- mejorar el cálculo de coste cuando exista cobertura parcial;
- distinguir coste de componentes de coste de equipo completo;
- validar sensibilidad de los pesos del ranking;
- comparar rankings con diferentes perfiles de usuario;
- documentar casos límite y ausencia de precio.

Evolución prevista:

```text
V1  componentes observados
 ↓
V1.1 cobertura completa CPU/RAM/GPU
 ↓
V2  PC completo
 ↓
V3  consumo eléctrico / TCO
 ↓
V4  optimización multiobjetivo
```

---

## 4. Prioridad P0 — rendimiento real

### 4.1 Benchmark reproducible

- Ejecutar la batería de inferencia en hardware real.
- Registrar tok/s, latencia, memoria, contexto y backend.
- Normalizar condiciones de prueba.
- Registrar versión del modelo y cuantización.
- Registrar runtime y versión.
- Separar prompt processing de generation cuando sea posible.

### 4.2 Batería agentiva LB

Completar y validar:

- B01 — memoria/localidad.
- B02 — operación sobre archivos.
- B03 — tarea multietapa.
- B04 — recuperación ante fallo.
- B05 — coding local.

Añadir criterios objetivos de éxito, artefactos de salida y estados `pass`, `fail`, `manual_review`, `tool_unavailable` y `not_evaluable`.

### 4.3 Baselines

- Mantener el baseline inicial documentado.
- Añadir nuevos modelos representativos por segmento de hardware.
- Evitar que los benchmarks publicados por terceros se mezclen con mediciones propias.

---

## 5. Prioridad P1 — prospección diaria y calidad del Atlas

- Mantener prospección diaria automática.
- Reducir duplicados y falsos positivos.
- Añadir seguimiento de cambios en modelos existentes.
- Detectar releases, cambios de licencia, pesos, cuantizaciones y runtimes.
- Incorporar fuentes especializadas de eficiencia/local AI.
- Mejorar la clasificación automática antes de la revisión.
- Registrar cambios como eventos, no solo como nuevas filas.
- Crear un mecanismo claro de revisión de candidatos.

---

## 6. Prioridad P1 — bot de precios

El bot está operativo. Queda evolucionarlo:

- mantener las cuatro fuentes activas: Coolmod, PcComponentes, MediaMarkt España y LDLC España;
- mantener Amazon descartada salvo decisión explícita futura;
- recuperar cobertura de productos que las tiendas cambien de categoría;
- cubrir los huecos de RAM restantes cuando existan realmente en el mercado;
- mejorar detección de precios truncados;
- registrar stock/disponibilidad cuando sea posible;
- conservar histórico mensual limpio;
- detectar anomalías de precio;
- diferenciar precio observado, precio promocional y precio habitual cuando la fuente lo permita;
- monitorizar cambios en HTML y adaptadores.

Regla congelada:

> **No se inventa un precio que no haya sido observado.**

---

## 7. Prioridad P1 — integración de workflows

Hay varios workflows de Atlas, prospección, precios, recomendaciones, estadísticas y web. Queda:

- documentar el grafo completo de workflows;
- evitar dos workflows haciendo el mismo trabajo;
- definir qué workflow es fuente de cada artefacto;
- añadir dependencias explícitas donde corresponda;
- hacer que los fallos sean visibles y accionables;
- unificar convenciones de nombres;
- revisar versiones de Actions y runtimes Node/Python;
- añadir tests de integración end-to-end.

Objetivo:

```text
PROSPECCIÓN → INGESTA → ATLAS → PRECIOS → RECOMENDADOR → WEB
                         ↓
                     MANADA / STATS
```

---

## 8. Prioridad P1 — web y aplicación

### Web pública

- Unificar estilo visual de todas las páginas.
- Revisar logos, fondos y gráficos.
- Verificar navegación cruzada.
- Publicar todos los esquemas de arquitectura relevantes.
- Mostrar claramente estado, fecha y procedencia de los datos.
- Crear páginas específicas para Atlas, JGB, hardware, precios y ranking económico.

### Aplicación

- Convertir `app.html` en verdadero centro de operaciones.
- Guiar por necesidad → hardware → modelo → runtime → inferencia → evaluación → informe → privacidad → Manada.
- Mostrar CABE antes de recomendar una configuración.
- Mostrar por qué una recomendación ocupa una posición concreta.
- Mostrar precio y fecha de observación sin ocultar incertidumbre.
- Permitir comparar alternativas.
- Mantener ejecución local y control explícito del usuario.

---

## 9. Prioridad P1 — Manada y conocimiento colectivo

- Completar flujo de publicación voluntaria.
- Mejorar anonimización preventiva.
- Definir esquema estable de resultados compartidos.
- Deduplicar mediciones.
- Clasificar confianza (`reported`, `reproducible`, `verified`, `rejected`).
- Crear estadísticas por hardware/modelo/runtime.
- Alimentar recomendaciones únicamente con evidencia que cumpla las reglas.
- Crear mecanismos de revisión comunitaria.

---

## 10. Prioridad P2 — privacidad y seguridad

- Auditoría completa de todos los campos publicados.
- Tests automáticos contra PII, secretos, rutas y identificadores.
- Revisar workflow de publicación.
- Documentar amenazas y límites del análisis de privacidad.
- Verificar que ningún script publique por defecto.
- Revisar integraciones sociales y permisos.

---

## 11. Prioridad P2 — runtimes y pila local

Comparar de forma reproducible la pila candidata:

- llama.cpp
- GGUF
- Buddy
- Hermes
- LangGraph
- OpenHands y alternativas relevantes
- herramientas de offloading/eficiencia

Para cada combinación interesa medir:

```text
modelo + cuantización + runtime + backend + hardware
                       ↓
                  rendimiento
                       ↓
                    RULA
                       ↓
                 tarea agentiva
```

---

## 12. Prioridad P2 — economía real

Evolucionar el ranking desde precio de componentes hacia coste total de uso:

- precio de compra;
- consumo eléctrico;
- horas de utilización;
- mantenimiento;
- actualización de RAM/GPU;
- vida útil;
- coste por tarea útil;
- coste por millón de tokens cuando sea una métrica pertinente;
- TCO.

El objetivo final no es «hardware barato», sino **valor útil por euro** bajo unas condiciones explícitas.

---

## 13. Prioridad P2 — documentación

- Mantener README como índice de navegación.
- Mantener `LEONES_DECISION_LOG.md` como registro de decisiones congeladas.
- Mantener este roadmap sincronizado con el estado real.
- Documentar cada fórmula y cada cambio de criterio.
- Añadir esquemas de arquitectura a las partes principales.
- Separar claramente documentación normativa, experimental y de resultados.

---

## 14. Prioridad P3 — automatización avanzada

- Generar automáticamente matrices y tablas de compatibilidad.
- Detectar regresiones en recomendaciones.
- Comparar la recomendación de hoy con la anterior.
- Alertar cuando cambia sustancialmente el precio o rendimiento.
- Crear snapshots versionados del Atlas.
- Añadir changelog automático de modelos y hardware.
- Construir un sistema de evaluación continua del recomendador.

---

# 15. Orden recomendado de ejecución

Para no caer en trabajo paralelo sin cierre, el orden recomendado es:

```text
1.  Consolidar Atlas + JGB
          ↓
2.  Completar matriz hardware
          ↓
3.  Completar precios CPU/RAM/GPU
          ↓
4.  CABE + RULA
          ↓
5.  Benchmark reproducible
          ↓
6.  Ranking económico V1.1
          ↓
7.  Evaluación agentiva LB
          ↓
8.  Router basado en evidencia
          ↓
9.  Integración web/app
          ↓
10. Manada y conocimiento colectivo
          ↓
11. TCO / economía avanzada
```

# 16. Criterio de «terminado»

Una tarea de LEONES solo se marcará como terminada cuando corresponda:

- código implementado;
- documentación actualizada;
- pruebas automatizadas o validación manual definida;
- workflow validado si afecta a automatización;
- salida inspeccionada;
- decisiones de diseño registradas;
- enlaces desde la documentación principal.

Esto evita repetir el problema de considerar terminado un desarrollo que solo está escrito pero no ejecutado.

# 17. Estado resumido

| Área | Estado | Próximo objetivo |
|---|---|---|
| Atlas | 🟡 En evolución | Consolidar fuente única de verdad |
| JGB | 🟡 En evolución | Completar clasificación y evidencia |
| Prospección | 🟢 Automatizada | Mejorar calidad y revisión |
| Precios | 🟢 Operativo | Ampliar cobertura y anomalías |
| Integración precios | 🟢 Validada | Escalar matriz |
| Ranking económico V1 | 🟢 Validado | V1.1 con cobertura completa |
| Matriz hardware | 🟡 En construcción | 2–128 GB + Intel/AMD + NVIDIA |
| CABE/RULA | 🟡 En construcción | Formalización y pruebas |
| Benchmark inferencia | 🟡 En construcción | Medición reproducible |
| Benchmark agentic | 🟡 En construcción | Validar LB |
| Router | 🟡 En construcción | Evidencia real acumulada |
| Web | 🟡 En evolución | Unificación y explicación |
| App | 🟡 En evolución | Flujo completo de usuario |
| Manada | 🟡 En evolución | Más mediciones verificables |
| TCO | ⚪ Pendiente | Después de ranking V1.1 |
