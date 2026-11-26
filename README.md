# LEONES

**Local Ecosystem of Open Neural Expert Systems**

IA local con criterio: descubrir, estimar, elegir, preparar, verificar, medir y evidenciar — sin confundir ESTIMATED con MEASURED.

## Metodología rectora: Human-Directed Agentic Engineering (HDAE)

**HDAE es el método de ingeniería rector de LEONES y de todos sus subproyectos.** No es una herramienta auxiliar, una preferencia de estilo ni una automatización opcional: establece cómo se decide, ejecuta, verifica y acepta el trabajo. La referencia metodológica original es el proyecto de [Gregory M. Kurtzer: gmkurtzer/hdae](https://github.com/gmkurtzer/hdae); LEONES conserva un [fork propio](https://github.com/robertosantosx2/hdae) con un snapshot fijado para que la norma aplicada sea reproducible y no cambie silenciosamente cuando avance upstream.

### Origen: experiencia real convertida en método

HDAE nace de la experiencia de Gregory M. Kurtzer dirigiendo el desarrollo de **Ginux**, un kernel independiente capaz de ejecutar userspace de Linux. El propio proyecto HDAE identifica Ginux como su origen: el trabajo exigía mantener una dirección arquitectónica coherente, restricciones e invariantes persistentes, criterios de aceptación verificables y ciclos de implementación y diagnóstico ejecutados por agentes bajo dirección humana.

Esa experiencia se documenta en el estudio de caso [*Ginux: Building an Independent Kernel That Runs Linux Userspace through Human-Directed Agentic Engineering*](https://zenodo.org/records/23682548), y se acompaña del [relato de Gregory M. Kurtzer en X](https://x.com/gmkurtzer/status/2118146379168297443). HDAE formaliza y empaqueta esas prácticas como una metodología reutilizable y como Agent Skills; no debe confundirse el método con la instalación automática de esas skills, que requiere una decisión y configuración explícitas por entorno.

### Qué significa HDAE en la práctica

La autoridad y la responsabilidad se separan deliberadamente:

- **La persona dirige:** propósito, intención, arquitectura, restricciones, prioridades, recursos, alcance, riesgos y criterios de aceptación. Las decisiones sustanciales y la aceptación final permanecen bajo autoridad humana.
- **Los agentes ejecutan:** investigación, diseño detallado, implementación, pruebas, diagnóstico, correcciones iterativas, documentación y preparación de cambios, siempre dentro de un alcance y unas gates autorizadas.
- **El trabajo se gobierna mediante evidencia:** cada tarea sustancial parte de un resultado verificable, límites explícitos, invariantes, riesgos, pruebas/gates, artefactos que conservar y un checkpoint con condición de parada.
- **La iteración es autónoma, pero acotada:** implementar → probar → diagnosticar → corregir → repetir. El agente puede completar secuencialmente gates objetivas ya autorizadas; no puede ampliar el alcance, alterar prioridades ni declarar éxito sin evidencia.
- **El contexto sobrevive a las sesiones:** directivas, decisiones, estado, commits, pruebas, bloqueos y siguientes pasos se mantienen en documentación y checkpoints versionados, no únicamente en el historial de conversación.
- **La aceptación no se presume:** implementación, tests, CI, medición física y aceptación son estados distintos. Cada gate se cierra solo con sus criterios y evidencia correspondientes; los límites y resultados inconclusos se registran sin ocultarlos.

En LEONES, el trabajo se realiza primero en GitHub mediante ramas, commits, PRs y CI. El MSI se reserva para builds, benchmarks, capturas y validaciones físicas que requieran el hardware real. Los agentes no sustituyen la decisión humana ni convierten una prueba sintética o una ejecución remota en evidencia física.

### Precedencia y aplicación en LEONES

HDAE define **el método de trabajo**, pero no inventa prioridades de producto: el INDEX maestro expresamente designado para cada proyecto sigue siendo la única fuente de prioridades, estado y aceptación. En NEPENTHES, esa autoridad corresponde a [NEPENTHES-INDEX.md](research/moe/tandem.cpp/NEPENTHES-INDEX.md). Los roadmaps, informes, Issues, PRs y checkpoints aportan detalle y evidencia, y deben mantenerse sincronizados con el INDEX; no crean una jerarquía paralela.

La directiva es transversal a la raíz de LEONES y sus subproyectos. Su adopción efectiva en repositorios externos, forks o entornos separados solo se declara cuando exista evidencia de esa adopción; la existencia de esta directiva no demuestra por sí sola que las skills estén instaladas ni que cada subproyecto haya completado su auditoría.

- **[Directiva HDAE](docs/engineering/HDAE-DIRECTIVE.md)**: reglas normativas, autoridad, gates, evidencia, checkpoints y precedencia.
- **[Referencia HDAE fijada](docs/engineering/HDAE-REFERENCE.md)**: procedencia, snapshot y política de actualización del fork LEONES.
- **[Fork LEONES de HDAE](https://github.com/robertosantosx2/hdae/tree/12d1a3389e74642dddee47a6cc4cb217f55f1144)**: snapshot normativo fijado al commit `12d1a3389e74642dddee47a6cc4cb217f55f1144`; upstream [gmkurtzer/hdae](https://github.com/gmkurtzer/hdae) se consulta para evaluar cambios, no como referencia móvil.
- [AGENTS.md](AGENTS.md) · [Checkpoint de adopción HDAE](docs/engineering/HDAE-CHECKPOINT.md) · [Auditoría de adopción por subproyecto](docs/engineering/HDAE-SUBPROJECT-AUDIT.md).

## LEONES — Discovery Atlas

> **[EXPLORAR EL DISCOVERY ATLAS →](web/discovery-atlas.html)**  
> Catálogo general de los descubrimientos de la prospección federada de LEONES: software, repositorios, modelos y papers de GitHub, GitLab, Hugging Face, Framagit y otras forjas.

- **HTML autocontenido y offline:** incorpora el catálogo en el propio archivo; no necesita CDN, JSON remoto ni llamadas a APIs para consultarlo.
- **Actualización diaria:** [Daily Atlas Prospection](.github/workflows/daily-prospection.yml) regenera la página después de publicar el feed de descubrimientos.
- **Datos y trazabilidad:** [feed JSON de prospección](web/data/prospeccion.json) · [generador reproducible](scripts/prospection/build_discovery_atlas.py).
- Los elementos se presentan como hallazgos pendientes de revisión; descubrir un proyecto no significa aprobarlo, recomendarlo ni haberlo ejecutado.

---

## <img src="web/assets/graphics/logos/leones-agents.svg" alt="LEONES Agents" width="34" align="absmiddle"> LEONES — Agent Use Case Observatory

> **[EXPLORAR EL OBSERVATORIO DE AGENTES →](web/agent-use-cases.html)**  
> Catálogo vivo de casos concretos, repositorios de código, Agent Skills, prompts, servidores MCP, ejemplos y workflows reutilizables. Priorizamos proyectos inspeccionables y reproducibles, con procedencia y señales de evidencia visibles.

- **[Interfaz del catálogo](web/agent-use-cases.html)** · [Feed JSON](web/data/agent-use-cases.json) · [Documentación y gates](docs/subprojects/AGENT-USE-CASE-OBSERVATORY/README.md).
- Se alimenta del catálogo de prospección existente y de búsquedas diarias en GitHub mediante [Daily Atlas Prospection](.github/workflows/daily-prospection.yml).
- Registra README, licencia declarada, actividad, instrucciones de instalación y ejemplos detectados para ayudar a priorizar la revisión.
- **Descubierto ≠ aprobado.** Ningún resultado se recomienda, ejecuta o integra automáticamente; la reproducibilidad real requiere una validación explícita.

---



## Mobile-LLMs-ARM — IA local en móviles y sistemas ARM

> **[EXPLORAR MOBILE-LLMS-ARM →](web/mobile-llms-arm.html)**  
> Observatorio de LLMs e IA en Android, Linux móvil, ARM64 y sistemas embebidos: runtimes, CPU/GPU/NPU, modelos, benchmarks, eficiencia y clústeres móviles.

- [Documentación](docs/subprojects/Mobile-LLMs-ARM/README.md) · [Roadmap](docs/subprojects/Mobile-LLMs-ARM/ROADMAP.md) · [Feed JSON](web/data/mobile-llms-arm.json) · [Fuentes](research/mobile-llms-arm/sources.json).
- **Plataforma móvil de referencia:** [Xiaomi Mi 9T Pro — 6 GB RAM, octa-core hasta 2,84 GHz (datos comunicados; pendiente caracterización)](hardware/XIAOMI-MI-9T-PRO-6GB.md).
- Prospección diaria de GitHub y Reddit integrada en [Daily Atlas Prospection](.github/workflows/daily-prospection.yml); X mantiene búsquedas directas hasta disponer de API autorizada.
- Descubierto no significa aprobado ni medido. Las pruebas físicas requieren protocolo y evidencia.

## Proyectos de investigación y arquitectura

- **[NEPENTHES — subproyecto de observabilidad](docs/subprojects/NEPENTHES/README.md)**: arquitectura y plan maestro para llama.cpp/GGML, AIPerf (runner primario), NVML/energía, latencia por token, OpenTelemetry/OTLP, adaptadores de métricas y análisis reproducible.
  - [Roadmap maestro](docs/subprojects/NEPENTHES/ROADMAP.md) · [Integración AIPerf](docs/subprojects/NEPENTHES/AIPERF-INTEGRATION.md) · [Índice histórico y validación](research/moe/tandem.cpp/NEPENTHES-INDEX.md) · [Campañas](research/moe/tandem.cpp/NEPENTHES-CAMPAIGNS.md) · [CLI e instalador](research/moe/tandem.cpp/NEPENTHES-CLI.md) · [Importador Nsight/CUPTI](research/moe/tandem.cpp/NEPENTHES-IMPORTER.md).
  - [Tandem.cpp — instrumentación universal, PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1) · [LEONES PR #153 — Nsight-only](https://github.com/robertosantosx2/LEONES/pull/153).
- **[Unkernel + Box Inference Bridge](research/unkernel-box/README.md)**: auditoría fijada de `KernelHandle`, host commands y vsock; diseño de un broker host-side compatible con OpenAI Chat Completions. La integración guest real y la conexión a llama.cpp siguen pendientes.
- **[llm.asm — campaña Qwen3-0.6B](docs/benchmarks/llm-asm-qwen3-0.6b-context-2026-11-25.md) · [investigación llm.asm móvil](research/mobile-llms-arm/llm-asm-mobile-intelligence-platform-2026-11.md)**: desarrollo experimental del motor y validaciones Qwen; consultar el inventario y los informes para distinguir builds, inferencias medidas y gates pendientes.
- **[REDIL — IA distribuida](docs/subprojects/REDIL-IA-distribuida/README.md)**: arquitectura de nodos, malla de inferencia y planificación de despliegue.
  - [Arquitectura visual](docs/subprojects/REDIL-IA-distribuida/ARQUITECTURA-VISUAL.md) · [Evaluación Distributed Llama](docs/subprojects/REDIL-IA-distribuida/DISTRIBUTED-LLAMA-EXPERIMENTAL.md) · [Comparativa de modelos locales](docs/subprojects/REDIL-IA-distribuida/COMPARATIVA-MODELOS-LOCALES-2026-11.md).
- **[Índice de informes de benchmarks e inferencia](docs/reports/indice-informes-inferencia-LEONES-2026-11-11.md)**: inventario navegable de campañas, comparativas, ejecuciones y evidencias.
- **[Inventario maestro de modelos y motores](docs/benchmarks/INVENTARIO_MODELOS_Y_MOTORES.md)**: estado MEASURED/ESTIMATED, compatibilidad y referencias a resultados.

## Informes y campañas de benchmark

### Consolidaciones y comparativas
- [Informe de inferencia densa — octubre 2026](docs/benchmarks/report-inferencia-dense_Octubre26.md) · [versión inglesa](docs/reports/report-inference-dense-october-2026.md).
- [Comparativa de ejecuciones en Ubuntu/MSI — 30-10-2026](docs/benchmarks/inventario-comparativo-ejecuciones-modelos-ubuntu-2026-10-30.md).
- [Qwen3.5-4B: comparativa de tres runtimes](docs/benchmarks/qwen35-4b-three-runtimes-2026-10-20.md).
- [Qwen3-30B-A3B IQ3_XXS: head-to-head llama.cpp vs RustingStrata y artefactos](docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/README.md).
- [Picchio: RAM dual-channel y escalado CPU](docs/reports/picchio-ram-dual-channel-msi-2026-11-08.md).

### Modelos y motores
- [TwIL-8B Q4_K_M — RTX 3050](docs/TWIL-8B-Q4_K_M-RTX3050-2026-11-05.md).
- [Pithos 0.5.0 + LFM3-1.7B](docs/PITHOS-LFM3-1.7B-RTX3050-2026-11-06.md).
- [Pithos 0.5.1 — CPU/Intel Vulkan/NVIDIA Vulkan, PP/TG y artefactos](docs/PITHOS-LFM3-1.7B-RTX3050-2026-11-07.md).
- [MiniCPM5-2B Q4_K_M — llama.cpp CUDA y evaluación DSpark](docs/MINICPM5-2B-RTX3050-2026-11-11.md).
- [Qwen3.5-9B — evaluación de viabilidad (ESTIMATED, no benchmark físico)](docs/QWEN3.5-9B-RTX3050-2026-11-11.md).
- [Spark-X2.6-4B-abliterated](docs/benchmarks/spark-x26-4b-abliterated-rtx3050-2026-10-30.md).
- [Ling 3.0 Tiny — MSI Ubuntu](docs/reports/ling-3.0-tiny-ubuntu-msi-rtx3050-2026-10-29.md).
- [Cosmic Lightning — informe](docs/benchmarks/cosmic-lightning/INFORME-COSMIC-LIGHTNING-2026-10-31.md).
- [TensorFold MoE — análisis forense](docs/reports/analisis-forense-tensorfold-moe-2026-10-24.md).
- [Otras campañas y estado por motor](docs/benchmarks/INVENTARIO_MODELOS_Y_MOTORES.md).

> Los enlaces agrupan resultados físicos, intentos, análisis forenses y evaluaciones documentales. Consultar cada informe para distinguir MEASURED, ESTIMATED, prueba funcional y campaña inconclusa; no comparar directamente cifras obtenidas con protocolos distintos.

## Perfiles y benchmarks de hardware

- Equipo de pruebas Ubuntu MSI Thin 15 B12UC: [perfil de hardware y software](hardware/UBUNTU-MSI-THIN-15-B12UC.md).
- TwIL-8B Q4_K_M en RTX 3050 Laptop con llama.cpp CUDA: [informe de benchmark y metodología](docs/TWIL-8B-Q4_K_M-RTX3050-2026-11-05.md).
- Pithos 0.5.0 + LFM3-1.7B Q4_K_M en RTX 3050 Laptop con Vulkan: [informe de ejecución y benchmark](docs/PITHOS-LFM3-1.7B-RTX3050-2026-11-06.md).
- Pithos 0.5.1 + LFM3-1.7B Q4_K_M: [comparativa CPU/Intel Vulkan/NVIDIA Vulkan y barrido PP/TG](docs/PITHOS-LFM3-1.7B-RTX3050-2026-11-07.md), con [CSV](artifacts/pithos-0.5.1-2026-11-07/benchmark-results.csv), [registro consolidado](artifacts/pithos-0.5.1-2026-11-07/benchmark-session.log) y [script reproducible](artifacts/pithos-0.5.1-2026-11-07/reproduce.sh).
- Qwen3.5-9B en RTX 3050 Laptop 4 GiB: [evaluación de viabilidad ES](docs/QWEN3.5-9B-RTX3050-2026-11-11.md) · [English report](docs/QWEN3.5-9B-RTX3050-2026-11-11-EN.md) (ESTIMATED; no benchmark físico 9B).
- MiniCPM5-2B Q4_K_M en RTX 3050 Laptop con llama.cpp CUDA: [informe de benchmark MEASURED y evaluación de viabilidad DSpark](docs/MINICPM5-2B-RTX3050-2026-11-11.md).

- NEPENTHES: [subproyecto y roadmap maestro](docs/subprojects/NEPENTHES/README.md) · [índice histórico de campañas](research/moe/tandem.cpp/NEPENTHES-INDEX.md).

## Catálogo completo de investigación

El inventario recursivo de proyectos, subproyectos y líneas de investigación de LEONES —con descripción, ubicación canónica, potencial, estado documental y reglas para evitar duplicidades— está disponible en el **[Observatorio visual de investigación](web/investigacion.html)** y en su [índice canónico Markdown](docs/research/RESEARCH-PROJECTS-INDEX.md). El observatorio se reconstruye diariamente mediante GitHub Actions y propone actualizaciones mediante PR. Para navegar por el trabajo experimental y sus resultados, consultar también el [inventario maestro de modelos y motores](docs/benchmarks/INVENTARIO_MODELOS_Y_MOTORES.md) y el [índice de informes de inferencia](docs/reports/indice-informes-inferencia-LEONES-2026-11-11.md).

### Cobertura temática de la investigación

- **Arquitectura, sistemas y despliegue:** [Unkernel + Box](research/unkernel-box/README.md), [ODS](docs/subprojects/ODS/README.md), [ODS + Magnitude](docs/subprojects/ODS-Magnitude-INTEGRATION.md), [Atomic Chat / Magnitude / ODS](research/atomic-chat-magnitude-ods-inference-architecture-2026-11.md), [LocalAI 5.0](research/localai-v5-integration-2026-11.md) y [REDIL](docs/subprojects/REDIL-IA-distribuida/README.md).
- **Motores, inferencia y optimización:** [inventario maestro](docs/benchmarks/INVENTARIO_MODELOS_Y_MOTORES.md), [NEPENTHES](research/moe/tandem.cpp/NEPENTHES-INDEX.md), [TensorFold](docs/subprojects/TensorFold/README.md), [llm.asm](https://github.com/robertosantosx2/LEONES/tree/main/projects/llm-asm), [Edge0](research/edge0-comparativa-open-source-2026-10.md), [Project Maya](research/project-maya-2026-10.md), [Clover](research/clover-35b-a3b-preview-experimental-2026-10.md) y [DSpine](https://github.com/robertosantosx2/LEONES/pull/143).
- **Modelos, runtimes y benchmarks:** [índice de informes de inferencia](docs/reports/indice-informes-inferencia-LEONES-2026-11-11.md), [comparativas Qwen3.5-4B](docs/benchmarks/qwen35-4b-three-runtimes-2026-10-20.md), [Qwen3-30B-A3B](docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/README.md), [TwIL-8B](docs/TWIL-8B-Q4_K_M-RTX3050-2026-11-05.md), [MiniCPM5](docs/MINICPM5-2B-RTX3050-2026-11-11.md), [Pithos/LFM3](docs/PITHOS-LFM3-1.7B-RTX3050-2026-11-07.md), Strata/Inkling (ver inventario maestro) y campañas móviles ARM.
- **Agentes, harnesses y evaluación:** [Agent Use Case Observatory](docs/subprojects/AGENT-USE-CASE-OBSERVATORY/README.md), [LEONES Agentic Benchmark](benchmarks/agentic/README.md), [LEONES Lab Agent](projects/leones-lab-agent/README.md), [Buddy](docs/subprojects/buddy/README.md) y [contrato de harnesses](docs/AGENT_HARNESSES.md).
- **Adaptación, datos y técnicas:** [fine-tuning](finetuning/README.md), [cuantización](quant/README.md), [Open-dCoder](docs/subprojects/Open-dCoder/README.md), [ASR LocalAI/Parakeet](research/localai-parakeet-integration.md) e [iWSP](docs/investigacion-prospectiva/iWSP-Interpretable-Weight-Space-Programming-2026-11.md).
- **Móvil y edge:** [Mobile-LLMs-ARM](docs/subprojects/Mobile-LLMs-ARM/README.md), [LG-H930](research/mobile-llms-arm/sources.json) y [Xiaomi Mi 9T Pro](hardware/XIAOMI-MI-9T-PRO-6GB.md).

Este README es una puerta de entrada, no duplica los informes. El índice recursivo enumera las líneas con identidad propia; los índices de campañas enlazan evidencia, artefactos y resultados. Cada documento conserva su clasificación real (REVIEWED, TESTED, CI-VALIDATED, MEASURED, ESTIMATED o PENDING). La presencia en el catálogo no implica aprobación, integración, benchmark físico ni aceptación.
