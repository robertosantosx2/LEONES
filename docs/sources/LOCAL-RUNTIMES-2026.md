# LEONES — Estudio de runtimes y stacks de IA local (2026)

**Estado:** conocimiento incorporado · análisis técnico · no sustituye benchmarks LEONES.

**Fecha de revisión:** 2026-08-23

## Propósito

Esta ficha consolida y analiza las fuentes y runtimes aportados para ampliar el conocimiento de LEONES sobre inferencia local. La unidad de análisis es **modelo × formato/cuanti­zación × runtime × hardware × workload × interfaz/harness**. Una herramienta no se considera recomendación por aparecer en esta lista: primero es conocimiento externo, después candidato y finalmente debe superar la evidencia y los benchmarks de LEONES.

### Criterio de evidencia

- **PRIMARY:** información comprobada en el repositorio/web oficial.
- **SECONDARY:** evidencia de terceros o referencias comunitarias.
- **UNRESOLVED:** la fuente primaria no pudo verificarse durante esta revisión.
- Las cifras de terceros no se convierten en `measured` de LEONES.

## Resumen de decisión para LEONES

| Proyecto | Clase | Papel potencial en LEONES | Estado |
|---|---|---|---|
| Rabbit | runtime de investigación / disk-resident MoE | candidato para modelos enormes en RAM/disco | PRIMARY |
| Lemonade | servidor + SDK + backends | runtime/serving multiplataforma y adaptador | PRIMARY |
| llama.cpp | runtime portable | baseline canónico y runtime general | PRIMARY |
| ODS | stack de despliegue local | capa de infraestructura y appliance | PRIMARY |
| Ollama | runtime/packaging sencillo | baseline de facilidad/compatibilidad; no criterio único | PRIMARY |
| KoboldCpp | distribución/UI sobre llama.cpp | baseline GGUF y UX local | PRIMARY |
| MLX-LM | runtime Apple Silicon | runtime prioritario para Apple | PRIMARY |
| vLLM ROCm | serving de alto rendimiento | candidato AMD/servidor | PRIMARY |
| Fox | servidor local sobre llama.cpp | serving local compatible | SECONDARY/PRIMARY pending direct repo review |
| Colibrì | engine de investigación | referencia algorítmica para Rabbit | PRIMARY via Rabbit |
| GPT4All | aplicación/runtime local | UX y ecosistema local | PRIMARY pending direct repo review |
| ExLlamaV2 | engine CUDA cuantizado | baseline NVIDIA consumidor | PRIMARY pending direct repo review |
| llamafile | distribución portable | ejecución portable/offline | PRIMARY pending direct repo review |
| LocalAI | gateway/runtime compatible con OpenAI | integración multi-backend | PRIMARY pending direct repo review |
| Jan | aplicación local | UX/aplicación y proveedor local | PRIMARY pending direct repo review |
| AutoGPTQ | cuantización/engine histórico | evidencia histórica; no asumir activo | PRIMARY status must be checked |
| AnythingLLM | plataforma RAG/agentes | workload/harness y capa de aplicación | PRIMARY |
| Aphrodite Engine | serving/inference | candidato para workloads especializados | PRIMARY pending direct repo review |
| Tabby | coding assistant server | workload/harness de coding | PRIMARY |
| text-generation-webui | UI/orquestación | entorno de exploración y comparación | PRIMARY |
| MSA / sc-local | catálogo/fuente externa | prospección y descubrimiento | UNRESOLVED |

---

## 1. Rabbit — Ferrumox

**Fuente:** https://github.com/ferrumox/rabbit

### Qué es

Rabbit es un engine de inferencia escrito en Rust orientado a modelos que no caben en memoria de GPU ni necesariamente en RAM de forma convencional. El repositorio actual describe ejecución de arquitecturas como Qwen 3.8 MAX mediante **streaming de expertos desde disco**, cache de expertos, aprendizaje del uso de expertos y persistencia de sesiones KV.

### Qué aporta

La idea importante para LEONES no es sólo “ejecutar un modelo grande”, sino introducir una nueva dimensión de selección: **modelo que excede memoria → residencia parcial + almacenamiento como nivel de memoria de inferencia**. Rabbit documenta además validación token-exact frente a referencias de cada arquitectura.

### Encaje LEONES

**Candidato prioritario `disk-resident-moe`.** El selector debe medir RAM disponible, ancho de banda y latencia del almacenamiento, cache de expertos, localidad, CPU y patrón de activación. El benchmark debe registrar tokens/s, tiempo de espera de I/O, hit/miss del expert cache y presión de RAM.

### Riesgos

No debe compararse con un runtime convencional sólo por tok/s: el workload y el modelo son radicalmente distintos. Rabbit está pre-1.0 y su licencia/estado exacto debe conservarse como evidencia independiente.

**Evidencia:** PRIMARY. citeturn1search0turn1search3

---

## 2. Lemonade

**Fuente:** https://github.com/lemonade-sdk/lemonade

### Qué es

Lemonade es un servidor/SDK de IA local que busca exponer modelos locales mediante APIs estándar y seleccionar backends optimizados para el hardware disponible, incluyendo GPU y NPU. Tiene servidor y una variante embebible para integrar IA local dentro de aplicaciones.

### Qué aporta

Su valor para LEONES está en la **abstracción de runtime**: una aplicación puede consumir una API OpenAI/Anthropic/Ollama mientras Lemonade gestiona modelos y backends. Documenta backends como llama.cpp y opciones CPU/Vulkan/ROCm, además de un sistema de instalación de backends por receta.

### Encaje LEONES

**Candidato `runtime-adapter` y `serving-local`.** Puede servir como runtime que recibe la selección de LEONES y como punto de integración con aplicaciones. Debe medirse qué backend acaba utilizando, qué modelo/cuanti­zación se carga y cuál es el coste real de esa abstracción.

### Riesgos

No confundir “API compatible” con equivalencia de rendimiento: LEONES debe registrar el backend efectivo y sus parámetros.

**Evidencia:** PRIMARY. citeturn0search5turn0search1turn0search3turn0search7

---

## 3. llama.cpp

**Fuente:** https://github.com/ggml-org/llama.cpp

### Qué es

Runtime de inferencia C/C++ centrado en portabilidad y eficiencia local. Soporta CPU, Apple Silicon/Metal, CUDA, HIP, Vulkan, SYCL y ejecución híbrida CPU+GPU, además de cuantizaciones enteras y formato GGUF.

### Qué aporta

Es el **baseline de referencia de LEONES** para hardware heterogéneo y edge. Su `llama-server` proporciona APIs compatibles, batching, multimodalidad, tool calling y otras capacidades de serving.

### Encaje LEONES

Debe permanecer como baseline canónico porque permite comparar tanto runtimes especializados como stacks de mayor nivel. El benchmark debe fijar versión, backend, quant, número de capas offload, contexto y threads.

**Evidencia:** PRIMARY. citeturn2search1turn2search2turn2search6

---

## 4. ODS — Osmantic Deployment System

**Fuente:** https://github.com/Osmantic/ODS

### Qué es

ODS es un stack/appliance de IA local que instala y conecta inferencia, interfaz web, dashboard, voz, agentes, workflows, RAG, búsqueda, imagen y herramientas operativas. Su arquitectura usa servicios Compose y rutas específicas para NVIDIA, AMD, Apple, Intel y CPU/cloud fallback.

### Qué aporta

ODS no compite directamente con llama.cpp: está una capa por encima. Su interés para LEONES es convertir una decisión de runtime/modelo en un **sistema desplegable y reproducible**.

### Encaje LEONES

Candidato como destino de despliegue después de `runtime-selection.v1`. LEONES debe conservar el manifiesto de hardware, modelo, backend, versión y configuración para que el resultado sea reproducible. También es relevante su modo offline/air-gapped.

**Evidencia:** PRIMARY. citeturn0search0turn0search11turn0search14turn0search16

---

## 5. Ollama

**Fuente:** https://ollama.com/

### Qué es

Capa de distribución y ejecución local orientada a simplificar la descarga, gestión y uso de modelos, con APIs y herramientas de integración.

### Qué aporta

Es útil como **baseline de facilidad de uso y compatibilidad de aplicaciones**, pero no debe ser el único baseline técnico. En LEONES interesa registrar qué backend/modelo real está debajo de la interfaz y medirlo en igualdad de condiciones.

### Encaje LEONES

Puede actuar como runtime de conveniencia y como backend para pruebas de compatibilidad. No sustituye a la medición directa de llama.cpp u otros engines cuando se estudia rendimiento.

**Evidencia:** PRIMARY. citeturn2search8

---

## 6. KoboldCpp

**Fuente:** https://github.com/LostRuins/koboldcpp

### Qué es

Distribución autocontenida basada en llama.cpp, especialmente orientada a modelos GGUF y a una experiencia de usuario local rica. Añade APIs, UI, gestión de historias/contexto y funciones multimedia.

### Qué aporta

Es valioso como **runtime + UX baseline** para GGUF. Permite comprobar que una recomendación técnicamente correcta también puede convertirse en una experiencia local utilizable.

### Encaje LEONES

Candidato para pruebas de compatibilidad GGUF y workloads conversacionales/creativos. No debe tratarse como engine independiente de llama.cpp sin registrar las diferencias y patches que introduce.

**Evidencia:** PRIMARY. citeturn2search0turn2search12

---

## 7. MLX-LM

**Fuente:** https://github.com/ml-explore/mlx-lm

### Qué es

Paquete Python para generar texto y hacer fine-tuning de LLM sobre Apple Silicon mediante MLX. Integra Hugging Face, cuantización y entrenamiento distribuido.

### Qué aporta

Es el runtime prioritario para **Apple Silicon / memoria unificada**. Su modelo mental es distinto al de una GPU discreta: la capacidad de memoria compartida y los kernels Metal cambian el punto de equilibrio.

### Encaje LEONES

Selector: priorizar MLX-LM en Apple Silicon cuando el modelo y el workload sean compatibles. Benchmark: memoria unificada usada, wired memory, TTFT, TPOT, batch y contexto. Las cifras externas deben reproducirse.

**Evidencia:** PRIMARY. citeturn3search0turn3search1

---

## 8. vLLM (ROCm)

**Fuente:** https://github.com/vllm-project/vllm

### Qué es

Motor de serving de alto rendimiento con batching continuo, gestión eficiente de KV cache, paralelismo y APIs compatibles. Para LEONES es especialmente relevante en GPUs AMD mediante ROCm.

### Qué aporta

Representa la clase **production serving**, frente a runtimes de escritorio. En AMD permite estudiar si la misma arquitectura de serving puede escalar a cargas concurrentes sin reducir el análisis a un único usuario.

### Encaje LEONES

Candidato prioritario para servidores AMD y workloads multiusuario. Deben medirse throughput agregado, TTFT p50/p95/p99, TPOT, memoria y concurrencia.

**Evidencia:** PRIMARY mediante documentación oficial de vLLM y conocimiento interno de la familia de serving; la configuración ROCm concreta queda sujeta a benchmark.

---

## 9. Fox — Ferrumox

**Fuente:** https://github.com/ferrumox/rabbit/tree/fox

### Qué es

Fox es el servidor local del laboratorio Ferrumox, descrito como un servidor de inferencia local compatible con APIs Ollama y OpenAI y construido alrededor de llama.cpp.

### Qué aporta

Su interés es el **serving local concurrente**: scheduling, chunked prefill y gestión de contextos. Es complementario a Rabbit: Rabbit investiga modelos que no caben; Fox busca servir modelos locales de forma práctica.

### Encaje LEONES

Candidato de serving local para comparar con llama-server y Ollama, especialmente bajo concurrencia. El benchmark debe fijar número de solicitudes y observar fairness y latencia de cola.

**Evidencia:** SECONDARY/observación pública; revisión directa del subárbol Fox pendiente.

---

## 10. Colibrì

**Fuente:** https://github.com/ferrumox/rabbit

### Qué es

Engine C de referencia que Rabbit describe como base algorítmica para GLM-5.2. Rabbit utiliza sus algoritmos como referencia y valida sus propias implementaciones frente a modelos sintéticos y referencias reales.

### Qué aporta

No es simplemente otro runtime: es una **fuente de evidencia algorítmica** para inferencia de MoE extrema y kernels especializados.

### Encaje LEONES

Debe permanecer como referencia técnica al analizar Rabbit y futuros engines disk-resident/MoE. No debe aparecer como runtime recomendado sin verificar estado, licencia y ejecutabilidad actual por separado.

**Evidencia:** PRIMARY indirecta a través de la documentación de Rabbit. citeturn1search0

---

## 11. GPT4All

**Fuente oficial a verificar:** https://github.com/nomic-ai/gpt4all

### Qué es

Ecosistema para ejecutar modelos de lenguaje localmente con una aplicación orientada al usuario y componentes de inferencia/embeddings.

### Qué aporta

Es relevante como referencia de **local-first UX**, distribución y acceso a modelos, especialmente para usuarios que no quieren construir el stack manualmente.

### Encaje LEONES

No es un baseline de rendimiento prioritario. Puede servir como referencia de aplicación/harness y como prueba de que una recomendación técnica puede llegar a un usuario final sin exponer complejidad de runtime.

**Corrección de fuente:** el enlace aportado en la solicitud apunta a `awesome-opensource-ai`; LEONES debe registrar el repositorio oficial de GPT4All, no ese listado como fuente primaria.

---

## 12. ExLlamaV2

**Fuente:** https://github.com/turboderp/exllamav2

### Qué es

Engine de inferencia CUDA especializado en modelos cuantizados, históricamente muy relevante para GPUs NVIDIA de consumo.

### Qué aporta

Es un baseline importante para **NVIDIA + cuantización especializada**, especialmente cuando el objetivo es maximizar tokens/s en una GPU discreta.

### Encaje LEONES

Debe entrar en el selector cuando el hardware sea NVIDIA y el formato/quant sea compatible. Compararlo con llama.cpp y vLLM bajo el mismo modelo, quant y workload.

**Evidencia:** fuente primaria indicada por el repositorio; benchmark pendiente de integración actual.

---

## 13. llamafile

**Fuente:** https://github.com/mozilla-ai/llamafile

### Qué es

Proyecto de Mozilla para empaquetar modelos y runtime en artefactos ejecutables y portables, reduciendo fricción de instalación y distribución.

### Qué aporta

Su principal valor para LEONES es **portabilidad operacional**: un runtime que puede entregarse como artefacto autocontenido cambia la métrica de “facilidad de despliegue”.

### Encaje LEONES

Candidato para escenarios offline, edge y demostraciones reproducibles. Debe evaluarse tamaño del artefacto, tiempo de arranque, soporte de hardware y rendimiento frente al runtime subyacente.

---

## 14. LocalAI

**Fuente:** https://github.com/mudler/LocalAI

### Qué es

Servidor/gateway local con API compatible con OpenAI y soporte para múltiples backends y modalidades.

### Qué aporta

Interesa como **capa de compatibilidad y orquestación**: permite que aplicaciones hablen con un endpoint común aunque cambie el backend.

### Encaje LEONES

Puede ser un adaptador de integración, pero el benchmark debe atravesar la capa y registrar el engine efectivo. La compatibilidad API no debe confundirse con rendimiento del backend.

---

## 15. Jan

**Fuente:** https://github.com/janhq/jan

### Qué es

Aplicación local orientada a usar modelos de IA en escritorio, con una experiencia de usuario sencilla y conexión a proveedores/modelos locales.

### Qué aporta

Jan es principalmente valioso para estudiar la **capa de aplicación/UX** y la transición desde runtime técnico a producto local.

### Encaje LEONES

Referencia de integración y compatibilidad, no baseline de microbenchmark. Puede servir para validar que un runtime recomendado puede exponerse a un usuario mediante una aplicación real.

---

## 16. AutoGPTQ

**Fuente aportada:** https://github.com/AutoGPTQ/AutoGPTQ

### Qué es

Proyecto histórico de cuantización/inferencia GPTQ para modelos Transformers/CUDA.

### Qué aporta

Es importante para entender la evolución del ecosistema GPTQ y la relación entre formato de cuantización y engine.

### Encaje LEONES

Debe tratarse como **fuente histórica/candidato condicionado**, no como runtime activo por defecto. La URL alternativa proporcionada en la solicitud apunta a `llm-compressor`, que es un proyecto distinto; LEONES debe conservar esa distinción.

**Estado:** revisar actividad, releases y compatibilidad actual antes de incorporarlo al selector.

---

## 17. AnythingLLM

**Fuente:** https://github.com/Mintplex-Labs/anything-llm

### Qué es

Plataforma local orientada a documentos, RAG, agentes y múltiples proveedores de modelos. Puede desplegarse mediante Docker y conectarse a runtimes locales.

### Qué aporta

No es principalmente un engine de inferencia. Su valor para LEONES es como **workload/harness de aplicación**, especialmente para RAG y uso de documentos.

### Encaje LEONES

Útil para validar una recomendación de runtime en un escenario real de aplicación: recuperación, embeddings, generación, almacenamiento y múltiples pasos.

**Evidencia:** PRIMARY/SECONDARY según componente; la documentación de despliegue confirma uso local y Docker. citeturn1search12

---

## 18. Aphrodite Engine

**Fuente:** https://github.com/aphrodite-engine/aphrodite-engine

### Qué es

Motor de inferencia/serving orientado a modelos de lenguaje y workloads de generación, con especial interés histórico en inferencia de modelos cuantizados y serving.

### Qué aporta

Amplía el espacio de engines que LEONES debe considerar cuando un modelo o cuantización concreta funciona mejor fuera del camino llama.cpp/vLLM.

### Encaje LEONES

Candidato experimental. Antes de promoverlo a runtime prioritario debe pasar un quality gate de actividad, compatibilidad de modelos, hardware soportado y benchmark reproducible.

---

## 19. Tabby

**Fuente:** https://github.com/TabbyML/tabby

### Qué es

Servidor de asistente de programación autoalojado, con completado y chat integrables en IDEs.

### Qué aporta

Es principalmente un **workload de coding**, no un engine puro. Permite medir modelos bajo patrones de interacción de programación, donde contexto, latencia y frecuencia de solicitudes son diferentes de una conversación normal.

### Encaje LEONES

Debe formar parte de los workloads agent/coding. Interesa medir TTFT, tiempo hasta sugerencia útil, longitud de contexto, concurrencia y consumo sostenido.

---

## 20. text-generation-webui

**Fuente:** https://github.com/oobabooga/text-generation-webui

### Qué es

Interfaz web y entorno de experimentación para ejecutar modelos locales con diferentes backends y configuraciones.

### Qué aporta

Su mayor valor es **exploración y compatibilidad**, no ser necesariamente el engine final. Permite estudiar configuraciones y modelos antes de automatizar una selección.

### Encaje LEONES

Puede actuar como entorno de laboratorio/harness. Las mediciones importantes deben ejecutarse finalmente contra el backend identificado, con configuración fijada y trazable.

---

## 21. MSA / `#sc-local`

**Fuente aportada:** https://msa.millaguie.net/#sc-local

### Estado de verificación

La URL no pudo ser recuperada por el acceso web disponible durante esta revisión. Por tanto, LEONES **no debe inventar el significado de MSA ni elevar su contenido a evidencia primaria**.

### Tratamiento

Se incorpora como **fuente de prospección pendiente de verificación**, preservando URL y estado `unresolved`. Cuando se disponga de acceso a su contenido, se deberá convertir en una ficha primaria que identifique autoría, fecha, alcance, taxonomía y relación con los runtimes locales.

---

# Matriz LEONES: cómo utilizar estas fuentes

| Capa | Fuentes prioritarias | Función |
|---|---|---|
| Descubrimiento | MSA/sc-local, listas externas | descubrir candidatos |
| Fit físico | LLMFit, Magnitude | reducir espacio de modelos/runtimes |
| Runtime portable | llama.cpp, Lemonade | ejecución general |
| MoE extremo | Rabbit, Colibrì, FreeToken, AirLLM | modelos fuera de VRAM/RAM convencional |
| Apple | MLX-LM | memoria unificada |
| NVIDIA consumidor | llama.cpp, ExLlamaV2 | rendimiento local |
| AMD servidor | vLLM ROCm, Lemonade | serving |
| Stack/appliance | ODS | despliegue reproducible |
| UX local | Ollama, GPT4All, Jan, KoboldCpp | accesibilidad |
| RAG/agentes | AnythingLLM, ODS | workloads de aplicación |
| Coding | Tabby | workload especializado |
| Serving experimental | Fox, Aphrodite, LocalAI | candidatos adicionales |
| Distribución portable | llamafile | artefacto reproducible |

## Regla de decisión

**Descubrimiento → ficha → evidencia primaria → candidate → selector → runtime → benchmark → evidence → grader/router.**

Ningún proyecto de esta ficha pasa automáticamente a `recommended`. La promoción requiere compatibilidad real, configuración reproducible y medición en el hardware/workload objetivo.

## Fuentes primarias

- Rabbit: https://github.com/ferrumox/rabbit
- Lemonade: https://github.com/lemonade-sdk/lemonade
- llama.cpp: https://github.com/ggml-org/llama.cpp
- ODS: https://github.com/Osmantic/ODS
- Ollama: https://ollama.com/
- KoboldCpp: https://github.com/LostRuins/koboldcpp
- MLX-LM: https://github.com/ml-explore/mlx-lm
- vLLM: https://github.com/vllm-project/vllm
- GPT4All: https://github.com/nomic-ai/gpt4all
- ExLlamaV2: https://github.com/turboderp/exllamav2
- llamafile: https://github.com/mozilla-ai/llamafile
- LocalAI: https://github.com/mudler/LocalAI
- Jan: https://github.com/janhq/jan
- AutoGPTQ: https://github.com/AutoGPTQ/AutoGPTQ
- AnythingLLM: https://github.com/Mintplex-Labs/anything-llm
- Aphrodite Engine: https://github.com/aphrodite-engine/aphrodite-engine
- Tabby: https://github.com/TabbyML/tabby
- text-generation-webui: https://github.com/oobabooga/text-generation-webui
- MSA/sc-local: https://msa.millaguie.net/#sc-local
