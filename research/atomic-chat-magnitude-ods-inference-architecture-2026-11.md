# Atomic Chat, Magnitude y ODS: análisis comparativo de arquitecturas de inferencia local

**Fecha:** 2026-11-05  
**Estado:** Investigación preliminar archivada; pendiente de validación técnica y benchmarks reproducibles.  
**Ámbito:** Arquitectura de runtimes, gestión de modelos, rendimiento, agentes e integración potencial en LEONES/ODS.

## 1. Resumen ejecutivo

Se comparan tres proyectos con objetivos parcialmente solapados:

- **Atomic Chat / atomic-chat-core:** referencia para separar la experiencia de usuario de un núcleo de gestión de runtimes, modelos, hardware y API.
- **Magnitude:** referencia para optimización de inferencia y ajuste de kernels según modelo y hardware, además de su infraestructura de agentes.
- **ODS (Osmantic Deployment System):** plataforma de despliegue y operación de un ecosistema local de IA: servicios, agentes, conocimiento, interfaces, seguridad y administración.

Conclusión: no conviene sustituir ODS por Atomic Chat ni por Magnitude. La oportunidad consiste en reforzar ODS con una capa de gestión de runtimes e inferencia desacoplada, estudiar Atomic como referencia de arquitectura de backends y evaluar Magnitude como motor o implementación candidata cuando exista compatibilidad verificable.

La propuesta de trabajo se denomina provisionalmente **ODS Inference Fabric**. Es una propuesta de arquitectura para LEONES, no una funcionalidad existente ni un compromiso de implementación aprobado.

## 2. Alcance y metodología

Esta nota sintetiza la investigación y comparación arquitectónica realizada el 2026-11-05. Distingue cuatro niveles de certeza:

1. **Publicado/documentado:** afirmación rastreable a documentación, código o releases del proyecto.
2. **Implementado:** existe código o release, pero su disponibilidad puede depender del sistema operativo, hardware, formato o configuración.
3. **Roadmap/dirección:** objetivo o línea de evolución; no debe presentarse como función disponible.
4. **Hipótesis LEONES:** propuesta propia que requiere diseño, prueba o decisión.

La documentación y los catálogos evolucionan. Antes de tomar decisiones de integración deben revisarse de nuevo los repositorios, releases, licencias, requisitos y compatibilidad efectiva. Las cifras de rendimiento publicadas por los propios proyectos no son benchmarks independientes.

## 3. Atomic Chat y atomic-chat-core

### 3.1. Enfoque

Atomic combina una aplicación orientada al usuario con un esfuerzo de extracción de un núcleo reutilizable. La separación entre la aplicación Atomic Chat y el proyecto atomic-chat-core es la observación arquitectónica más relevante para LEONES.

- Aplicación: experiencia de escritorio, interacción, proyectos y flujos de usuario.
- Core: gestión de motores/proveedores, modelos, hardware, ejecución y exposición de servicios.

Repositorios:
- https://github.com/AtomicBot-ai/Atomic-Chat
- https://github.com/AtomicBot-ai/atomic-chat-core

### 3.2. Capacidades y áreas observadas

La propuesta de Atomic es más amplia que un frontend de chat. Su ecosistema documenta distintos backends y proveedores, gestión de modelos y hardware y una API compatible con OpenAI. El catálogo incluye tecnologías de inferencia local y serving que pueden variar por plataforma y nivel de madurez.

Entre las tecnologías que aparecen en la investigación están llama.cpp, MLX/MLX-VLM, TensorRT-LLM, vLLM, SGLang, Foundry Local, LiteRT-LM, GenieX y componentes de difusión. Esta lista debe tratarse como catálogo/documentación del proyecto, no como garantía de que todas las combinaciones estén soportadas en cualquier equipo.

La API unificada documentada se ha identificado como http://localhost:1337/v1; comprobar puerto, configuración y versión antes de automatizar contra ella.

### 3.3. Roadmap y madurez

El repositorio atomic-chat-core incluye documentación de planificación y decisiones de ingeniería. La línea de evolución que interesa estudiar es:

1. Extraer un core independiente de la aplicación.
2. Definir contratos para runtimes y proveedores.
3. Gestionar instalación, actualización y ciclo de vida de motores.
4. Centralizar catálogo de modelos y capacidades de hardware.
5. Resolver modelos/proveedores mediante router y API.
6. Mejorar gestión de GPU, cargas y fallos.
7. Extender conectividad remota e integraciones.

No se debe interpretar un plan, una decisión de arquitectura o un test parcial como certificación de que toda la funcionalidad está disponible en todos los sistemas.

### 3.4. Fortalezas

- Separación clara entre interfaz y capa de ejecución.
- Orientación multimotor.
- Gestión centralizada de modelos y runtimes.
- API común que reduce el acoplamiento de clientes y agentes.
- Documentación de decisiones y pruebas de ingeniería.

### 3.5. Riesgos y cuestiones por verificar

- Diferencias de soporte entre sistemas operativos y aceleradores.
- Madurez desigual entre backends.
- Dependencia de builds, paquetes y requisitos específicos.
- Alcance real de la administración como servicio de servidor frente a la experiencia desktop.
- Compatibilidad efectiva con TensorFold y Strata.

**Corrección de cautela:** esta investigación no confirma una integración publicada y funcional de TensorFold ni de Strata en Atomic. No deben presentarse como backends disponibles sin evidencia nueva en el catálogo, código o releases oficiales.

## 4. Magnitude

Repositorio: https://github.com/magnitudedev/magnitude

### 4.1. Enfoque

Magnitude se diferencia por priorizar la ejecución eficiente y la optimización adaptada al modelo y al hardware. Su propuesta incluye ajuste de kernels y optimizaciones de inferencia. También contiene una arquitectura de agentes/clientes; por tanto, no es exclusivamente un motor de bajo nivel.

### 4.2. Líneas técnicas relevantes

- Ajuste/selección de kernels por hardware.
- Optimización de prefill y decode.
- Gestión de KV cache y memoria.
- Decodificación especulativa y otras técnicas de aceleración, según soporte.
- Sesiones y concurrencia.
- Integración con clientes, agentes y proveedores.

### 4.3. Rendimiento publicado

Magnitude publica comparativas frente a Ollama y cifras de aceleración. Son resultados del propio proyecto, dependientes de modelos, hardware, versiones y configuración. No se deben extrapolar directamente a una NVIDIA RTX 3050 Laptop de 4 GB.

No se ha establecido en esta investigación un benchmark independiente y reproducible en el equipo LEONES de referencia.

### 4.4. Roadmap

No se ha identificado un roadmap público único, fechado y verificable que permita asignar hitos futuros con la misma precisión que un plan de releases. La dirección tecnológica observable se puede resumir en:

- Ampliar modelos y arquitecturas compatibles.
- Afinar kernels para más dispositivos.
- Mejorar gestión de caché, memoria y concurrencia.
- Mejorar la experiencia de agentes y clientes.
- Facilitar el serving local/remoto.

Esta sección describe una dirección inferida de capacidades y arquitectura, no una promesa oficial de roadmap.

### 4.5. Fortalezas y riesgos

**Fortalezas**
- Foco explícito en rendimiento real por modelo/hardware.
- Técnicas de optimización que ODS podría aprovechar.
- Posible backend adicional para una estrategia multimotor.
- Arquitectura de clientes/agentes que merece inspección.

**Riesgos**
- Compatibilidad concreta por modelo, formato y GPU pendiente de pruebas.
- Las cifras comerciales no son comparables sin metodología equivalente.
- No sustituye las funciones de despliegue y operación de ODS.
- Debe verificarse la API y el contrato de servidor antes de crear un adaptador.

## 5. ODS

Repositorio: https://github.com/Osmantic/ODS

### 5.1. Enfoque

ODS es una plataforma de despliegue y operación de servicios de IA local. Su alcance incluye instalación, inventario de hardware, modelos, inferencia, interfaces, agentes, automatización, recuperación de conocimiento, voz, observabilidad y seguridad.

Entre los componentes del ecosistema observados en la documentación y configuración del proyecto están CLI/dashboard, LiteLLM, llama.cpp, Open WebUI, Hermes, n8n, Qdrant, SearXNG y servicios de voz y multimedia. La composición exacta depende de la versión, perfil y extensiones.

### 5.2. Fortalezas

- Visión de plataforma completa, no solo de ejecución de modelos.
- Gestión e instalación de servicios.
- Integración con agentes y automatización.
- Componentes de RAG, búsqueda y voz.
- Extensibilidad y posibilidad de operar en hardware ordinario.
- Integración de varios proyectos de terceros en un sistema coherente.

### 5.3. Riesgos y oportunidad

El riesgo arquitectónico es que la gestión de modelos y motores quede demasiado ligada a un backend concreto o a decisiones dispersas entre instalador, dashboard, configuración y gateway.

La oportunidad es formalizar una capa de runtime independiente y contratos comunes sin reescribir el resto de ODS.

La versión y estado de cada release deben verificarse en el repositorio oficial. No debe confundirse una rama en desarrollo o pre-release con una versión final validada.

## 6. Comparación arquitectónica

| Dimensión | Atomic Chat | Magnitude | ODS |
|---|---|---|---|
| Propósito principal | Gestión multimotor y experiencia local | Optimización de inferencia y agentes | Plataforma de despliegue/operación |
| Abstracción de runtimes | Alta prioridad | No es el foco principal | Área a formalizar |
| Optimización de kernels | Depende del backend | Diferenciador | Delegada al backend |
| Catálogo y gestión de modelos | Sí | Sí | Sí |
| Hardware awareness | Sí | Ajuste por hardware | Inventario y selección |
| API/serving | API unificada | Serving/cliente según versión | Gateway y servicios |
| Agentes | Integraciones | Parte importante del producto | Integración de agentes |
| RAG/servicios de conocimiento | No es el foco | No es el foco | Sí |
| Automatización de servicios | Parcial | Parcial | Sí |
| Extensibilidad de plataforma | Backends/integraciones | Clientes y herramientas | Extensiones/servicios |

Esta tabla es cualitativa. No constituye una puntuación de calidad ni una prueba de rendimiento.

## 7. Recomendación para LEONES/ODS

### 7.1. Principio

ODS debe seguir siendo el plano de control y la plataforma de servicios. La inferencia debe convertirse progresivamente en una capacidad desacoplada, con motores intercambiables y medibles.

### 7.2. Propuesta: ODS Inference Fabric

Arquitectura conceptual:

1. **Experiencia:** ODS Portal, Open WebUI, Hermes, OpenCode y otros clientes.
2. **Control plane:** inventario de hardware, catálogo, instalación, configuración, ciclo de vida y supervisión.
3. **Inference gateway:** API común, routing, health, métricas, sesiones y fallback.
4. **Runtime adapters:** llama.cpp, TensorFold, Magnitude, vLLM, SGLang, TensorRT-LLM, LocalAI y otros candidatos, solo cuando la compatibilidad esté validada.

La propuesta no implica que todos esos motores deban integrarse ni que todos sean adecuados para el mismo hardware.

### 7.3. Contrato conceptual de backend

    InferenceBackend
        detect()
        capabilities()
        install()
        update()
        list_models()
        inspect_model()
        load_model()
        unload_model()
        health()
        metrics()
        serve()

El contrato debe ser versionado, explícito y capaz de expresar capacidades no soportadas. No todos los backends implementarán todas las operaciones de la misma manera.

### 7.4. Metadatos de modelo

Cada modelo debería declarar, como mínimo:

- Arquitectura y familia.
- Formato y cuantización.
- Tamaño de pesos y memoria estimada.
- Contexto máximo declarado y contexto validado.
- Compatibilidad de backend y acelerador.
- Capacidades: texto, visión, audio, herramientas.
- Procedencia, licencia y revisión del artefacto.
- Configuración probada y evidencia de benchmark.

### 7.5. Gestión de recursos

La capa de control debería conocer:
- Memoria VRAM disponible y reservada.
- RAM disponible y presión de memoria.
- Modelos residentes y procesos consumidores.
- Política de carga/descarga.
- Límites de concurrencia.
- Coste y resultado de cada ejecución.

La residencia única por GPU puede ser una política útil en dispositivos pequeños, pero no debe imponerse universalmente: hay que soportar motores y hardware que permitan concurrencia real.

## 8. Plan de trabajo propuesto

| Fase | Trabajo | Resultado verificable |
|---|---|---|
| 0 | Auditoría de APIs, licencias, formatos y soporte real | Matriz de compatibilidad con fuentes |
| 1 | Diseño del contrato de backend | Especificación versionada y tests de contrato |
| 2 | Adaptador de llama.cpp | Integración de referencia sin romper el servicio actual |
| 3 | Adaptador experimental de TensorFold | Pruebas aisladas y evidencia de compatibilidad |
| 4 | Evaluación de Magnitude como backend | Informe API, formatos, rendimiento y limitaciones |
| 5 | Runtime manager y supervisión | Carga, descarga, health y métricas |
| 6 | Benchmark automatizado | Resultados reproducibles y procedencia |
| 7 | Routing, fallback y concurrencia | Tests de integración y recuperación |
| 8 | Catálogo de compatibilidad | Matriz hardware/modelo/backend basada en evidencia |

**Restricción operativa:** no alterar ni sustituir el llama-server por defecto de ODS durante los experimentos. Las pruebas con TensorFold, Magnitude u otros motores deben ejecutarse en perfiles, puertos y directorios aislados, con posibilidad de rollback.

## 9. Protocolo de benchmark para el laboratorio LEONES

Hardware de referencia conocido en las mediciones compartidas:
- MSI Thin 15 B12UC.
- Intel Core i7-12650H.
- NVIDIA RTX 3050 Laptop, 4 GB VRAM.
- Ubuntu.
- Última medición de RAM compartida: aproximadamente 14 GB físicos.

Estos datos deben actualizarse antes de iniciar una campaña de benchmark; no son una medición tomada durante esta investigación.

### Modelos candidatos

- Qwen3.5-2B.
- Qwen3.5-4B.
- LFM3-1.7B.

### Motores candidatos

- llama.cpp CUDA.
- TensorFold 1.2.
- Magnitude, únicamente si admite el modelo/formato y el hardware concretos.

No se debe asumir que los motores comparten formato, tokenizer, configuración, soporte de arquitectura o condiciones de ejecución.

### Métricas obligatorias

- Tiempo de descarga y carga por separado.
- Time to first token.
- Prefill tokens/s.
- Decode tokens/s.
- VRAM pico y estable.
- RAM pico y estable.
- Consumo energético si puede medirse de forma fiable.
- Temperatura y throttling.
- Calidad/validez de salida.
- Errores, reinicios y estabilidad de al menos 30 minutos.
- Resultado con contextos comparables de 2K, 4K y 8K cuando el modelo y motor lo permitan.

Cada resultado debe guardar versiones, commit/build, hash de modelo, cuantización, parámetros, contexto, sistema operativo, driver, CUDA y logs. Solo una ejecución física en el equipo puede producir un resultado **MEASURED** de LEONES. Las cifras externas o estimaciones deben etiquetarse **EXTERNAL** o **ESTIMATED**.

## 10. Relación con REDIL

La separación entre control plane, gateway y runtime local facilita una futura extensión distribuida. REDIL podría coordinar nodos y capacidades sin quedar acoplado a un motor único.

No obstante, la distribución debe abordarse después de estabilizar:
- Identidad y capacidades de cada nodo.
- Contrato de backend.
- Telemetría y estado.
- Políticas de carga y descarga.
- Seguridad y autenticación.
- Manejo de fallos y particiones de red.

No se propone introducir distribución en la primera fase del Inference Fabric.

## 11. Decisión recomendada

- Usar **Atomic Chat Core** como referencia de diseño para la capa de runtimes y sus contratos.
- Usar **Magnitude** como candidato de rendimiento y objeto de evaluación experimental, no como sustituto de ODS.
- Mantener **ODS** como plataforma de despliegue, operación y servicios.
- Desarrollar en LEONES una especificación de **ODS Inference Fabric** y validar primero con el backend actual.
- Integrar TensorFold y Magnitude de forma aislada y experimental hasta superar pruebas de compatibilidad y estabilidad.

La decisión de integrar un motor debe basarse en evidencia reproducible, licencia compatible, soporte real y coste de mantenimiento; no solo en velocidad anunciada o amplitud del catálogo.

## 12. Fuentes primarias

### Atomic
- https://github.com/AtomicBot-ai/Atomic-Chat
- https://github.com/AtomicBot-ai/atomic-chat-core

### Magnitude
- https://github.com/magnitudedev/magnitude
- https://magnitude.dev/benchmarks

### ODS
- https://github.com/Osmantic/ODS

### LEONES
- https://github.com/robertosantosx2/LEONES

## 13. Próximas preguntas de investigación

1. ¿Cuál es el contrato/API estable y documentado de atomic-chat-core en la versión actual?
2. ¿Qué backends del catálogo Atomic están realmente disponibles en Ubuntu x86_64 con NVIDIA sm_86?
3. ¿Qué interfaz de serving ofrece Magnitude y qué modelos/formatos soporta en Linux CUDA?
4. ¿Qué componentes de gestión de modelos y runtimes de ODS están acoplados actualmente a llama.cpp?
5. ¿Qué estrategia de procesos, puertos, logs, healthchecks y rollback es común a todos los adaptadores?
6. ¿Qué benchmark comparable puede ejecutarse sin alterar el llama-server por defecto?
7. ¿Qué requisitos de licencia y redistribución aplican a cada runtime y build?

---

**Clasificación LEONES:** investigación de arquitectura e inferencia local.  
**Estado de implementación:** ninguna modificación de ODS se deriva automáticamente de esta investigación.  
**Regla de evidencia:** no confundir capacidades anunciadas, documentación, pruebas sintéticas y resultados físicos MEASURED.
