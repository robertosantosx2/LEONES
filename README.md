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

## Proyectos de investigación y arquitectura

- **[NEPENTHES — índice, roadmap y campañas](research/moe/tandem.cpp/NEPENTHES-INDEX.md)**: instrumentación universal de motores, captura JSONL, CLI, Nsight/CUPTI, importación LEONES, campañas físicas, informes y gates de aceptación.
  - [Roadmap](research/moe/tandem.cpp/NEPENTHES-ROADMAP.md) · [Registro de campañas y resultados](research/moe/tandem.cpp/NEPENTHES-CAMPAIGNS.md) · [CLI e instalador](research/moe/tandem.cpp/NEPENTHES-CLI.md) · [Importador Nsight/CUPTI](research/moe/tandem.cpp/NEPENTHES-IMPORTER.md) · [Informe histórico Qwen3.5-35B](research/moe/tandem.cpp/NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md).
  - [Tandem.cpp — instrumentación universal, PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1).
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

- NEPENTHES / Tandem.cpp: [índice de observabilidad, roadmap y criterio de aceptación](research/moe/tandem.cpp/NEPENTHES-INDEX.md).

## RC4 — estado actual (2026-09-07)

**Regla de autoridad:** LEONES descubre el hardware y conserva procedencia. FitLLM/LLMFit es preselector (ESTIMATED). El usuario elige modelo y stack. Solo una ejecución física autorizada produce MEASURED.

### Flujo TUI fijado

```text
IDIOMA
  ↓
ESTADO DE LA MÁQUINA
  ├─ Hardware
  ├─ RAM / CPU / DISCO
  └─ IA instalada
       ├─ FitLLM
       ├─ ODS
       ├─ Magnitude
       ├─ LLMs
       └─ Agentes / harnesses
  ↓
si FitLLM falta → INSTALAR FitLLM
  ↓
PROPÓSITO(S) · selección múltiple
  ↓
HF + Artificial Analysis
  ↓
RECOMENDACIÓN FitLLM
  ↓
SELECCIÓN HUMANA
  ↓
STACK
  ├─ gestionar / instalar
  │    ├─ LLMs seleccionados
  │    ├─ instalar LLM concreto (ruta completa del fichero)
  │    ├─ ODS
  │    ├─ Magnitude
  │    └─ otros
  └─ desinstalar
       ├─ modelo
       ├─ FitLLM
       ├─ Magnitude
       └─ ODS
  ↓
RUNTIME
  ↓
BENCHMARK A01 → MEASURED
```

**No existe bootstrap obligatorio de todos los componentes.** `install.sh` solo instala el componente solicitado mediante `--fitllm`, `--ods`, `--magnitude`, etc. `--all` queda como operación explícita, no como comportamiento por defecto.

### Implementado

- `USER_INTENT[]` obligatorio · feed HF + Artificial Analysis ≤100 · intersección con CLI LLMFit.
- Hasta 3 candidatos ESTIMATED o `insufficient` (sin padding).
- Estado de máquina e inventario de componentes dentro de la TUI.
- Instalación bajo demanda desde la TUI para FitLLM, ODS y Magnitude.
- Gestión independiente de LLMs, ODS, Magnitude y otros componentes.
- Desinstalación independiente; LEONES se conserva como último nivel.
- Cadena post-recomendación: selección humana → stack → runtime → A01 → MEASURED.

## RC4 Beta

La rama `rc4-fitllm-recommender` dispone de una guía específica para los beta testers:

- `docs/RC4-BETA-TESTERS.md`

La beta debe tratar toda recomendación como `ESTIMATED` y toda medición como evidencia producida por una ejecución física real. No se deben reutilizar resultados de otras máquinas como mediciones propias.

## Arranque

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
git checkout rc4-fitllm-recommender
./leones
```

Instalación explícita, si se desea hacerla fuera de la TUI:

```bash
./install.sh --fitllm
./install.sh --ods
./install.sh --magnitude
```

`./install.sh` sin argumentos **no instala nada** y muestra su ayuda.

## Evidencia y gate

- RC4: `scripts/rc4_release_gate.py`.
- Contrato: `docs/RC4-ARCHITECTURE.md`.
- Cadena estricta: `docs/completed/RC4-STRICT-MEASURED-CHAIN-2026-09-07.md`.
- E2E físico MEASURED sigue pendiente.

## Principio LEONES

> **Los proveedores pueden proponer. FitLLM puede recomendar. El usuario elige. Solo una ejecución controlada sobre el equipo real puede producir una medición LEONES.**

Web: `web/estado.html` · `web/rc4.html` · `web/inicio-rapido.html` · `web/operacion.html`
