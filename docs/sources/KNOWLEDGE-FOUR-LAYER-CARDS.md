# Fichas aplicadas al contrato de cuatro capas

**Contrato:** `KNOWLEDGE-FICHA-CONTRACT.v1`  
**Fecha:** 2026-08-24

Este documento es la normalización semántica ficha por ficha. No sustituye las fichas extensas: fija cómo debe leerse cada fuente en LEONES y qué puede llegar al pipeline.

## 1. FreeToken

**Capa:** runtime/serving MoE · **Estado:** `runtime-candidate`

### Fuente / Descubrimiento
Runtime edge-native de FlashML para MoE, con paper y repositorio oficiales. Su propuesta gira alrededor de GPU + CPU + RAM + PCIe como plataforma elástica.

### Evidencia
El paper aporta resultados condicionados por modelo, hardware, cuantización y workload; por ejemplo, los resultados publicados para RTX 4060 Laptop y RTX PRO 6000. Son evidencia primaria externa, no mediciones LEONES.

### Estimación
La señal LEONES es que FreeToken resulta especialmente prometedor cuando el MoE excede la VRAM y existe suficiente ancho de banda de RAM/PCIe. Debe conservarse como hipótesis de selección, no como garantía.

### Medición LEONES
Pendiente. El gate exige executor + grader + benchmark, registrando TTFT, TPOT, prefill, VRAM/RAM, bandwidth, expert cache y éxito del workload.

## 2. El otro FreeToken

**Capa:** runtime/serving MoE · **Estado:** `runtime-candidate`

### Fuente / Descubrimiento
Es la ficha nominal separada solicitada para distinguirlo de otras referencias históricas a FreeToken.

### Evidencia
Código/documentación y claims del proyecto se mantienen separados de resultados LEONES.

### Estimación
La ficha lo clasifica como `edge-moe-bandwidth-adaptive`; las variables decisivas son VRAM, RAM, PCIe, KV, localidad de expertos y workload.

### Medición LEONES
Pendiente de reproducción; no se heredan las cifras de la ficha FreeToken.

## 3. Odysseus

**Capa:** workspace/harness agentivo · **Estado:** `workspace-reference`

### Fuente / Descubrimiento
Workspace self-hosted con chat, agentes, tools, MCP, memoria, investigación, documentos y workflows.

### Evidencia
La fuente primaria demuestra que consume endpoints y proporciona una capa superior al runtime.

### Estimación
El Cookbook hardware-aware es una señal externa de recomendación. No sustituye LLMFit ni el selector LEONES.

### Medición LEONES
Pendiente de workload reproducible. Debe medirse modelo + runtime + endpoint + workspace + workload.

## 4. LLMFit

**Capa:** preselector hardware-aware · **Estado:** `preselector`

### Fuente / Descubrimiento
Herramienta que detecta hardware y produce candidatos según quality, speed, fit, context, cuantización y modo de ejecución.

### Evidencia
Código y documentación primaria verifican el mecanismo de detección y selección. Sus benchmarks comunitarios son evidencia externa.

### Estimación
`estimated_tps`, memoria requerida, cuantización, run mode y score son estimaciones de LLMFit. Nunca deben escribirse como `measured_tps` LEONES.

### Medición LEONES
Existe observación real de LLMFit sobre hardware Debian, pero se clasifica como verificación/observación de la herramienta, no como benchmark canónico hasta ejecutar runtime + protocolo + grader.

## 5. LLMFit — hardware real

**Capa:** evidencia de verificación · **Estado:** `verification-leones`

### Fuente / Descubrimiento
Captura de una ejecución real de LLMFit en Intel i5-1035G1, 8 GB y gráfica integrada.

### Evidencia
La observación registra hardware, memoria disponible, backend y candidatos/estimaciones mostrados por LLMFit.

### Estimación
Las cifras tok/s y etiquetas `Perfect` pertenecen a LLMFit. La observación documenta explícitamente que con solo 0,7 GB libres no deben interpretarse como garantía de estabilidad.

### Medición LEONES
No es todavía medición de inferencia. El siguiente gate es instalar un runtime compatible, ejecutar y comparar `estimated_tps` contra `measured_tps`.

## 6. AirLLM

**Capa:** runtime memory-constrained · **Estado:** `runtime-candidate`

### Fuente / Descubrimiento
Runtime/biblioteca que reduce el requisito de memoria aceleradora mediante ejecución por capas, prefetch y uso combinado de recursos.

### Evidencia
Código y documentación proporcionan mecanismos y compatibilidades; siempre condicionados por versión, modelo, precisión y hardware.

### Estimación
Su valor esperado es ampliar el conjunto de modelos ejecutables cuando la memoria es el cuello de botella. Esto no predice rendimiento útil.

### Medición LEONES
Pendiente en Debian. Deben registrarse carga, TTFT, prefill/decode, RAM, VRAM, I/O, contexto, estabilidad y calidad.

## 7. ODS

**Capa:** despliegue/appliance · **Estado:** `research-candidate`

### Fuente / Descubrimiento
Osmantic Deployment System instala y conecta inferencia, UI, voz, agentes, workflows, RAG y otros servicios mediante un stack gestionado.

### Evidencia
La arquitectura e instalador documentan autodetección de hardware, selección de modelo y operación mediante Compose/CLI.

### Estimación
La selección de modelo/backend realizada por ODS es una señal externa de despliegue. LEONES conserva la autoridad del selector.

### Medición LEONES
Pendiente. Debe medirse instalación, backend efectivo, modelo, configuración, estabilidad y rendimiento.

## 8. Magnitude

**Capa:** agente + inference engine · **Estado:** `research-candidate`

### Fuente / Descubrimiento
Combina agente de coding, motor local, perfilado hardware y recomendación/configuración de modelos.

### Evidencia
El upstream documenta perfilado, configuración y workloads agentivos.

### Estimación
Recomendaciones de hardware/modelo y throughput estimado son señales externas.

### Medición LEONES
Pendiente. El pin técnico no se considera verificado hasta instalación reproducible y el benchmark agentivo debe conservar trayectoria y outcome.

## 9. Runtimes locales 2026

**Capa:** radar/runtime · **Estado:** `source-inspiration`

### Fuente / Descubrimiento
Mapa consolidado de llama.cpp, Lemonade, Rabbit, ODS, Ollama, KoboldCpp, MLX-LM, vLLM, SGLang, TensorRT-LLM, LocalAI y otros.

### Evidencia
Cada entrada remite a su fuente primaria y a la verificación individual. El radar no sustituye las fichas primarias.

### Estimación
El radar reduce el espacio de búsqueda y formula hipótesis de encaje. No es un ranking homogéneo.

### Medición LEONES
Por runtime + modelo + cuantización + hardware + workload. No se promociona ningún runtime por aparecer en el radar.

## 10. Infraestructura IA local 2026

**Capa:** prospección · **Estado:** `source-inspiration`

### Fuente / Descubrimiento
Informe de prospección que descubre runtimes, servidores, técnicas de memoria, formatos y modelos.

### Evidencia
Los claims se verifican después contra repositorios/fichas primarias mediante el documento de verificación uno a uno.

### Estimación
Las recomendaciones orientativas de hardware/modelo del informe permanecen como hipótesis hasta pasar por LLMFit y medición.

### Medición LEONES
No aplica al informe como tal. Las mediciones se producen sobre candidatos ejecutables.

## 11. Candidatos de infraestructura 2026

**Capa:** promoción documental · **Estado:** `research-candidate`

### Fuente / Descubrimiento
Lista derivada de 23 proyectos y 10 familias/modelos revisados.

### Evidencia
`verified-primary` demuestra identidad/estado/licencia/capacidad básica; `archived` y `unresolved` se conservan explícitamente.

### Estimación
La transición a LLMFit y runtime+cuantización es una fase de estimación/selección, no de medición.

### Medición LEONES
Pendiente por candidato. `unresolved` no puede generar recomendación canónica.

## 12. Verificación de infraestructura 2026

**Capa:** evidencia · **Estado:** `verified-primary`

### Fuente / Descubrimiento
Verificación uno a uno frente a fuentes primarias.

### Evidencia
23 proyectos: 18 `verified-primary`, 3 `archived`, 2 `unresolved`; además 10 familias/modelos con estados diferenciados.

### Estimación
La verificación no estima rendimiento. Los candidatos pasan posteriormente por LLMFit y selección de runtime.

### Medición LEONES
Ningún `verified-primary` equivale a `measured`. El benchmark propio es un gate posterior.

## 13. Artificial Analysis / Optima

**Capa:** metodología de benchmark · **Estado:** `research-candidate`

### Fuente / Descubrimiento
Fuente metodológica incorporada para diseñar evaluación de tareas agentivas completas.

### Evidencia
Aporta principios sobre outcome, trajectory, herramientas, graders y métricas multidimensionales. Los resultados externos siguen siendo externos.

### Estimación
No es estimador principal. Sirve para formular hipótesis de diseño de benchmark.

### Medición LEONES
Pendiente de Agentic Benchmark V1 con tareas versionadas, entorno reproducible, herramientas instrumentadas y graders versionados.

## 14. Buddy

**Capa:** harness · **Estado:** `harness-reference`

### Fuente / Descubrimiento
Asistente personal local con memoria persistente Markdown/Git y herramientas file-first.

### Evidencia
La arquitectura upstream documenta Tauri/Svelte/worker, memoria y permisos.

### Estimación
Su valor es metodológico: representa un workload/harness alternativo, no un score del selector.

### Medición LEONES
Pendiente. Debe compararse con DSH/Hermes/Magnitude sobre el mismo endpoint y tareas.

## 15. Mozilla Open Source AI Ecosystem

**Capa:** ecosistema/metodología · **Estado:** `source-inspiration`

### Fuente / Descubrimiento
Informe publicado que aporta contexto sobre el ecosistema de IA abierta.

### Evidencia
Sus afirmaciones se conservan como claims de la publicación.

### Estimación
Puede inspirar taxonomía y relaciones, pero no genera scores LEONES.

### Medición LEONES
No aplica directamente; cualquier hipótesis debe transformarse en una prueba ejecutable independiente.

## 16. LLMs de Cero a Héroe 2026

**Capa:** fundamentos/metodología · **Estado:** `source-inspiration`

### Fuente / Descubrimiento
Serie técnica incorporada al conocimiento sobre memoria, bandwidth, runtimes y evaluación.

### Evidencia
Aporta principios documentales y marco conceptual, no mediciones propias de LEONES.

### Estimación
Sus reglas sirven para construir hipótesis de encaje, memoria y rendimiento, siempre marcadas como derivadas.

### Medición LEONES
No aplica directamente. Las mediciones físicas deben salir del pipeline canónico.

## 17. Regla transversal para runtimes y benchmarks

**Unidad real de medición:** `modelo × formato/cuanti × runtime × hardware × workload × harness`.

Una cifra de un runtime, leaderboard o benchmark externo permanece en **EVIDENCIA**, no en **MEDICIÓN LEONES**. Una cifra calculada por LLMFit/Magnitude/ODS permanece en **ESTIMACIÓN**. Solo el executor + grader + benchmark de LEONES puede producir la cuarta capa.
