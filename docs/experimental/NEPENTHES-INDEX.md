# NEPENTHES — índice del proyecto

**Nepenthes es una metodología de experimentación, medición y documentación de motores de inferencia local. No es un motor de inferencia.** Los motores se identifican por separado —por ejemplo, `Tandem.cpp` y `cafe-llama.cpp`— y cada informe documenta una combinación concreta de motor, modelo, configuración, plataforma y campaña.

El objetivo es que cada ejecución sea trazable y reproducible: conservar la petición y la respuesta originales, registrar la configuración efectiva, medir rendimiento y recursos, evaluar el resultado funcional y publicar las limitaciones junto con los datos primarios.

## Qué documenta Nepenthes

Cada campaña debe distinguir claramente:

- **Motor:** repositorio, commit, versión, build, backend y parámetros de ejecución.
- **Modelo:** nombre, arquitectura, cuantización, tamaño, metadatos y, cuando esté disponible, SHA-256.
- **Plataforma:** CPU, RAM, swap, GPU/VRAM, driver, CUDA y sistema operativo.
- **Protocolo:** prompt, parámetros de generación, repeticiones, caché y condiciones de ejecución.
- **Resultados:** tokens/s, latencias cuando se midan, uso de CPU/GPU/memoria, temperatura, potencia y errores.
- **Calidad funcional:** criterios esperados, resultado observado, pruebas y defectos.
- **Evidencia primaria:** manifest, respuestas completas, muestras de recursos, logs, inventario de hashes y paquete reproducible.

Las métricas no medidas se identifican como tales. Se separan las mediciones de caché fría y caliente y los contadores globales del sistema de las métricas atribuibles al proceso. Enviar un parámetro a una API no demuestra que el motor lo haya aplicado.

## Metodología y documentación

| Recurso | Descripción |
|---|---|
| [Metodología Nepenthes](tandem-qwen35-reasoning-budget-methodology-2026-11-12.md) | Protocolo, estructura de evidencias, ejecución de scripts y reglas de interpretación. |
| [Plantilla de informe motor + modelo](NEPENTHES-engine-model-report-template.md) | Esquema reutilizable para registrar cada combinación de motor y modelo. |
| [Hoja de ruta de rendimiento y capacidad](NEPENTHES-performance-capacity-roadmap.md) | Plan de trabajo FAST PATH y CAPACITY PATH, fases, métricas y gates de validación. |
| [Diseño de memoria jerárquica](NEPENTHES-memory-tiering-design.md) | Propuesta técnica para VRAM, RAM, almacenamiento, caché, prefetch, backpressure y fallback. |
| [Informe de campaña NEPENTHES (14-11-2026)](NEPENTHES-campaign-report-2026-11-14.md) | Hallazgos de la batería y Nsight, hipótesis no demostradas y campaña priorizada de sondas, velocidad y capacidad. |
| [Issue de desarrollo #148](https://github.com/robertosantosx2/LEONES/issues/148) | Seguimiento del desarrollo completo. |

## Informes y campañas actuales

### Qwen3.5-35B-A3B — noviembre de 2026

| Motor / campaña | Documento | Evidencia |
|---|---|---|
| **Tandem.cpp** — comparación caché MoE 512 vs 768 MiB, 05-11-2026 | [Informe de baseline y comparación](https://github.com/robertosantosx2/LEONES/blob/Experimental/docs/experimental/tandem-qwen35-35b-a3b-rtx3050-2026-11-05.md) | [Logs, manifiesto y cinco resultados JSON](https://github.com/robertosantosx2/LEONES/tree/Experimental/artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-05/) |
| **Tandem.cpp** — batería de razonamiento y presupuesto, 12-11-2026 | [Informe de la batería](tandem-qwen35-reasoning-budget-battery-2026-11-12.md) | [Scripts, monitorización y artefactos](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/) |
| **cafe-llama.cpp** — ejecución independiente, 13-11-2026 | [Informe de ejecución](nepenthes-cafe-llama.cpp-qwen3.5-35b-a3b-2026-11-13.md) | [Datos primarios completos](../../artifacts/benchmarks/qwen35-35b-a3b-engine-comparison-2026-11-13/cafe-llama.cpp/) |
| **Tandem.cpp** — batería independiente instrumentada, 13-11-2026 (10 casos) | [Informe completo de ejecución](nepenthes-tandem.cpp-qwen3.5-35b-a3b-2026-11-13.md) | [Manifiesto, 10 respuestas, resumen, 255 muestras y SHA-256](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/full-run/) |
| **Tandem.cpp / Nsight Systems** — captura correlacionada y tooling CUDA, 14-11-2026 | [Informe de campaña y hallazgos](NEPENTHES-campaign-report-2026-11-14.md) | [Expediente bruto, `.nsys-rep`, SQLite, logs y SHA256SUMS](../../artifacts/benchmarks/nepenthes-raw-archive-2026-11-14/20261114-200707/) |

**Resultado Tandem.cpp (13-11-2026):** el runner completó 10/10 peticiones. Seis terminaron con `stop` y cuatro con `length` (truncadas). La inspección estática considera cinco respuestas completas correctas y señala un comentario de prueba contradictorio en otra; no se ejecutaron las pruebas Python. El informe separa explícitamente ejecución, finalización y corrección funcional. No es una comparación A/B controlada con cafe-llama.cpp.

**Importante sobre la interpretación:** la ejecución de cafe-llama.cpp del 13-11-2026 es una prueba independiente, no una comparación A/B controlada con Tandem.cpp. Sus condiciones y métricas —incluida la caché de prompt— deben leerse en su propio informe; no deben presentarse como una comparación directa de rendimiento.

## Scripts de reproducción e inspección

Los scripts publicados para la campaña actual se encuentran en:

- [Runner Nepenthes](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_NEPENTHES_independent_two_sum.py) — ejecuta una petición contra un servidor ya iniciado y registra la evidencia de la prueba.
- [Inspector Nepenthes](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_NEPENTHES_independent_run.py) — inspecciona el directorio de evidencia guardado, sin necesitar consultar el servidor.
- [Monitor de recursos](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/resource_monitor.py) — dependencia compartida de monitorización.\n- [Entrada de archivo histórico](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/archive_NEPENTHES_evidence.py) — copia no destructiva de expedientes locales, deduplicación SHA-256 y manifiesto.
- [Inspector Nsight SQLite](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_NEPENTHES_nsys_sqlite.py) — análisis offline de API CUDA, kernels, transferencias y secuencias de espera.

Consulta la [metodología](tandem-qwen35-reasoning-budget-methodology-2026-11-12.md) para los requisitos, comandos y precauciones de uso. El runner no inicia, detiene ni reconfigura el servidor; cada ejecución debe usar un directorio de salida nuevo.

## Convenciones de publicación

1. Un informe corresponde a una combinación concreta de **motor + modelo + campaña**.
2. Los nombres de motores y metodologías no se intercambian: Nepenthes es la metodología; Tandem.cpp y cafe-llama.cpp son motores.
3. Los datos originales no se sustituyen por resúmenes. El informe enlaza a la evidencia primaria.
4. Las condiciones que impiden comparar dos ejecuciones se declaran explícitamente.
5. Los resultados deben poder auditarse mediante logs, manifiestos y hashes cuando estén disponibles.

---

**Ubicación:** `docs/experimental/NEPENTHES-INDEX.md`  
**Rama de referencia:** `nepenthes/performance-capacity-roadmap-20261114`

## Referencias técnicas MoE

- [TensorFold-MoE — arquitectura y técnicas de inferencia sparse-MoE](../../research/moe/TensorFold-MoE.md).
- [Investigación MoE de LEONES — routing, cachés y evidencia empírica](../../atlas/MoE-investigacion.md).
- [Ostinato (arXiv:2611.11533) — ejecución CPU/GPU con expertos residentes en prefill y decode](https://arxiv.org/abs/2611.11533).

Estas fuentes aportan contexto para formular experimentos MoE; sus resultados externos no son benchmarks NEPENTHES ni deben atribuirse al hardware local.

## Sondas MoE y telemetría

- [Sonda de runtime MoE](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/moe_runtime_probe.py) — PSI, E/S y planificación del proceso, hilos/RSS y frecuencia CPU por petición.
- [Inspector de routing/cache MoE](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_NEPENTHES_moe_trace.py) — resumen de estadísticas de caché en logs y parser MCT1 para builds compatibles.
- [Monitorización y uso](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/RESOURCE_MONITORING.md) — formato de evidencias, límites y validación previa.

La integración se explica en la [metodología NEPENTHES](tandem-qwen35-reasoning-budget-methodology-2026-11-12.md). La build Tandem de referencia ofrece contadores agregados de caché, pero no routing por capa MCT1.
