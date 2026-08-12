# LEONES 0.2 — Arquitectura congelada

**Estado:** CONGELADA — 12 agosto 2026  
**Proyecto:** Local Ecosystem of Open Neural Expert Systems (LEONES)

## 1. Definición

LEONES es una plataforma autónoma de IA local capaz de **descubrir, preparar, ejecutar, evaluar y optimizar modelos** para el hardware disponible.

LEONES no depende de un producto concreto de inferencia o de una aplicación de escritorio. Los runtimes externos son adaptadores intercambiables.

## 2. Principios congelados

1. **Autonomía:** LEONES debe poder ejecutar modelos localmente sin depender de Unsloth Desktop, Ollama u otro producto concreto.
2. **Hardware de consumo:** la arquitectura prioriza CPU, GPU y NPU de equipos de usuario, incluidos perfiles de 8/16/32/64 GB RAM.
3. **Libre/Open:** se mantiene la prioridad por software libre/open y, cuando sea comparable, Copyleft.
4. **Evidencia reproducible:** las decisiones del sistema deben poder apoyarse en datos de hardware, modelo, backend, cuantización y benchmarks identificables.
5. **Tareas antes que tok/s:** la velocidad es una métrica, no el objetivo único; LOTB mide utilidad agentic real.
6. **Independencia de backend:** llama.cpp, KTransformers, Unsloth, Ollama, vLLM, MLX, TensorRT-LLM y otros son adaptadores, no el núcleo de LEONES.

## 3. Componentes

### 3.1 Leones Atlas

Fuente de conocimiento estructurado de LEONES. Mantiene modelos, familias, versiones, organizaciones, licencias, grado de apertura, capacidades, hardware, formatos, cuantizaciones, runtimes, benchmarks, experimentos y procedencia.

Atlas no decide por sí mismo: proporciona evidencia al Router y conserva los resultados obtenidos por LEONES.

### 3.2 Leones Router

Motor de decisión. Selecciona, según tarea y hardware:

- modelo;
- versión;
- cuantización;
- backend/runtime;
- dispositivo;
- parámetros de ejecución;
- estrategia de fallback.

El Router debe optimizar para el objetivo real de la tarea, teniendo en cuenta calidad, latencia, memoria, capacidad de herramientas y restricciones del equipo.

### 3.3 Leones Agents

Capa agéntica. Gestiona planificación, agentes especializados, herramientas, memoria, RAG, workflows, tool-calling, recuperación ante errores y colaboración entre agentes.

Los Agents solicitan inferencia al Router; no deben quedar acoplados a un motor concreto.

### 3.4 Leones Runtime

Capa de ejecución autónoma. Debe poder descubrir, instalar/preparar, cargar, ejecutar, descargar y gestionar modelos localmente.

Su interfaz separa el núcleo de LEONES de los backends concretos. Los adaptadores pueden incluir llama.cpp, KTransformers, Unsloth, Ollama, vLLM, MLX, TensorRT-LLM y otros cuando aporten valor.

Unsloth **no es un componente principal de la arquitectura**; es un backend/adaptador posible.

### 3.5 Leones Quant

Subsistema de cuantización y asistencia a cuantización. Debe poder evaluar alternativas y ayudar a seleccionar o producir configuraciones que equilibren:

`calidad ↔ memoria ↔ velocidad`

Debe conservar la trazabilidad de modelo base, método, parámetros, resultado y hash cuando sea aplicable.

### 3.6 Leones Fine-Tuning

Subsistema de adaptación de modelos. Debe asistir y, cuando el hardware y las herramientas disponibles lo permitan, ejecutar fine-tuning/PEFT, incluyendo LoRA y QLoRA.

El objetivo no es reinventar cada framework de entrenamiento, sino orquestarlo de forma autónoma y reproducible.

### 3.7 Benchmark & Evaluation

Motor permanente de medición. Separa:

**Inferencia:** carga, prompt evaluation, generation tok/s, memoria, estabilidad y tiempo.

**Agentic:** LOTB B01-B05, éxito, tiempo de tarea, tool calls, errores y capacidad de completar objetivos.

Los resultados alimentan Leones Atlas y posteriormente mejoran Leones Router.

## 4. Flujo autónomo

```text
TAREA
  ↓
TASK INTELLIGENCE
  ↓
HARDWARE INTELLIGENCE
  ↓
LEONES ATLAS
  ↓
LEONES ROUTER
  ↓
modelo + cuantización + backend + configuración
  ↓
LEONES RUNTIME
  ↓
EJECUCIÓN
  ↓
BENCHMARK / EVALUATION
  ↓
LEONES ATLAS
  ↓
mejor decisión futura
```

## 5. Hardware Intelligence

Debe existir un perfil de hardware medible, no solo descriptivo:

- CPU, arquitectura, núcleos/hilos e instrucciones relevantes;
- RAM y disponibilidad;
- GPU, VRAM y capacidades relevantes;
- NPU cuando exista;
- almacenamiento disponible/relevante;
- sistema operativo y kernel cuando afecten a la ejecución;
- resultados de microbenchmarks y benchmarks LEONES.

## 6. Task Intelligence

Convierte una petición en requisitos operativos. Ejemplos:

- coding → contexto, herramientas, filesystem, shell, ejecución/verificación;
- investigación → web, recuperación, síntesis y fuentes;
- documentos → extracción, contexto, RAG y generación;
- automatización → planificación, herramientas, memoria y verificación.

## 7. Independencia y autonomía

LEONES debe poder funcionar aunque un backend concreto no esté instalado. El Runtime detectará capacidades disponibles y el Router escogerá una alternativa compatible.

La arquitectura no debe asumir que existe una aplicación gráfica externa.

## 8. Relación con Leones Atlas

**Leones Atlas = conocimiento.**

**Leones Router = decisión.**

**Leones Agents = acción/planning.**

**Leones Runtime = ejecución.**

**Leones Quant = adaptación de representación.**

**Leones Fine-Tuning = adaptación del modelo.**

**Benchmark & Evaluation = evidencia y aprendizaje operativo.**

## 9. Qué queda fuera del núcleo

No forman parte del núcleo de LEONES:

- una UI concreta de escritorio;
- un proveedor único de modelos;
- un backend único;
- un formato único de modelo;
- Unsloth Desktop como dependencia obligatoria;
- Ollama como dependencia obligatoria;
- llama.cpp como dependencia conceptual, aunque siga siendo backend de referencia.

## 10. Decisión de congelación

Esta arquitectura queda congelada como **LEONES 0.2**. Cambiar sus componentes principales requiere una nueva decisión explícita y documentada.

Los detalles internos, implementaciones, backends compatibles, algoritmos de routing, métricas y resultados experimentales permanecen abiertos a evolución.
