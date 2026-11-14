# Roadmap NEPENTHES

**Tipo:** hoja de ruta viva de investigación, instrumentación e implementación.  
**Última actualización:** 14-11-2026.  
**Estado global:** el sink JSONL y el aplicador determinista de sondas ya superan sus pruebas y la aplicación sobre el commit fijado de llama.cpp en CI. La compilación CPU de `llama-server` está en curso; la unidad CUDA `.cu` aún no se ha compilado con nvcc y no existe todavía una captura integral. La fase de observabilidad no se da por aceptada hasta superar esos gates y validar una ejecución real.  
**Issue:** [LEONES #148](https://github.com/robertosantosx2/LEONES/issues/148).  
**Ramas:** [LEONES — performance/capacity](https://github.com/robertosantosx2/LEONES/tree/nepenthes/performance-capacity-roadmap-20261114) · [Tandem.cpp — integración activa, PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1) · [rama de integración](https://github.com/robertosantosx2/tandem.cpp/tree/nepenthes/universal-observability-20261114).

> Documento operativo vivo. Se actualizará al superar cada fase, enlazando commits, PR, CI, pruebas y evidencias. Escribir código no basta para marcar una fase como completada: debe superar criterios verificables.

## 1. Misión

NEPENTHES desarrolla y evalúa dos vías independientes:

- **FAST PATH:** reducir latencia y aumentar tokens/s cuando el conjunto de trabajo cabe en los recursos rápidos.
- **CAPACITY PATH:** completar inferencias cuyo conjunto de pesos/KV excede VRAM o RAM mediante residencia jerárquica, streaming, prefetch y backpressure cuando el backend lo permita. Se acepta una velocidad extremadamente baja si hay progreso verificable, integridad y límites controlados.

No se promete compatibilidad universal. Arquitectura, operadores, formato, contexto, direccionamiento, almacenamiento y backend siguen imponiendo límites.

## 2. Historia del trabajo, desde el inicio

| N.º | Hito | Resultado y estado |
|---:|---|---|
| 1 | Definir el objetivo NEPENTHES | **Completado.** Separación FAST PATH / CAPACITY PATH; rendimiento y capacidad no se confunden. |
| 2 | Fijar la plataforma de referencia | **Completado.** MSI Thin 15 B12UC, Intel Core i7-12650H, RTX 3050 Laptop 4 GiB, 14 GiB RAM, Ubuntu y CUDA 13.4. |
| 3 | Preparar Tandem.cpp como motor de investigación | **Completado.** Repositorio separado robertosantosx2/tandem.cpp, basado en un conjunto de parches sobre llama.cpp. |
| 4 | Ejecutar la batería Qwen3.5-35B-A3B | **Completado como campaña histórica.** Se conservaron ejecuciones, respuestas, logs y datos de rendimiento de noviembre. |
| 5 | Investigar el comportamiento MoE | **Completado como análisis inicial.** Se estudiaron caché, routing disponible, expertos y límites de los contadores agregados. La telemetría por capa/experto sigue pendiente. |
| 6 | Preparar perfilado CUDA/Nsight | **Completado.** Herramientas, preflight y capturas Nsight Systems registradas. |
| 7 | Analizar esperas GPU/CPU | **Completado como diagnóstico preliminar.** Se identificaron secuencias k_host_add_wait; no se atribuyó causalidad al trabajo CPU porque faltan muestras correlacionadas de planificación/workers. |
| 8 | Archivar evidencia del 12–14 de noviembre | **Completado.** Expedientes originales, .nsys-rep, SQLite, logs, manifiestos y hashes archivados en LEONES. |
| 9 | Construir el recolector universal | **Completado en LEONES.** Recolector de host/GPU y recursos, formatos normalizados, metadatos y checksums. |
| 10 | Importar Nsight SQLite | **Completado en LEONES.** Importador de Runtime, kernels, memcpy y sincronización; conserva dominios de reloj y correlación. |
| 11 | Validar infraestructura de sondas LEONES | **Completado para la infraestructura.** Hook C++17, contrato de eventos y pruebas/CI. No significa que Tandem.cpp ya emita todos los eventos reales. |
| 12 | Preparar rama de integración Tandem.cpp | **Completado.** Rama [nepenthes/universal-observability-20261114](https://github.com/robertosantosx2/tandem.cpp/tree/nepenthes/universal-observability-20261114) y [PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1) para el puente de telemetría. |
| 13 | Crear sink JSONL asíncrono | **Implementado; validación en curso.** Cola acotada, escritor JSONL, escaping, contadores de descarte/error y activación optativa. Smoke test C++17 y prueba JSONL pasan; el aplicador de runtime ya supera CI. Compilación del servidor CPU pendiente. |
| 14 | Conectar ciclo de vida del sink | **Implementado en el applier.** Inicialización lazy en el primer graph-compute, callback de emisión y cierre al terminar el proceso; captura desactivada por defecto. Pendiente validar build y cierre con inferencia real. |
| 15 | Sondar KV cache | **Sondas implementadas; compilación/captura pendientes.** Allocation, teardown, clear, aplicación de ubatch y reutilización de celda/eviction con tamaño y contadores disponibles. |
| 16 | Sondar asignaciones y liberaciones | **Sondas implementadas; compilación/captura pendientes.** Allocation/free genérico de buffers backend CPU/GPU, OOM de buffer, CUDA device alloc, pool return/release y pinned-host alloc/free; duración host y bytes donde la API los expone. |
| 17 | Sondar transferencias | **Sondas implementadas; compilación/captura pendientes.** H2D, D2H, 2D H2D/D2H y D2D/peer en callsites; las actividades completas de memcpy y su timeline se obtienen además vía Nsight/CUPTI. |
| 18 | Sondar prefetch | **Sondas implementadas; compilación/captura pendientes.** Inicio/fin de enqueue, estimación de bytes y espera del backend event, distinguiendo enqueue host de finalización. |
| 19 | Sondar OOM y fallback | **Sondas iniciales implementadas; validación pendiente.** OOM en alloc CUDA/device buffer y fallback de pinned-host a CPU. Falta validar recuperación/fallback de extremo a extremo. |
| 20 | Sondar kernels CUDA individuales | **Cobertura dividida.** Callsite de despacho por `ggml_op` implementado; los nombres y tiempos de kernels CUDA individuales provienen de CUPTI/Nsight importado por LEONES. La unidad `.cu` aún requiere compilación nvcc; el span de dispatch no se presenta como tiempo GPU. |
| 21 | Sondar publicación y espera de workers CPU | **Sondas implementadas; compilación/captura pendientes.** Espera idle, inicio/cómputo/fin y publicación CPU/prefill. Los eventos internos conservan `request_id=0` hasta diseñar propagación segura entre hilos. |
| 22 | Unificar eventos con LEONES | **Parcialmente implementado.** El sink emite el sobre JSONL NEPENTHES y el importador Nsight conserva su dominio de reloj; falta validar la mezcla de eventos online/offline en una captura real. |
| 23 | Correlacionar timeline completo | **Pendiente.** Request → routing/cache → worker CPU → publicación → transferencias → kernels → sincronización → respuesta. Sin inferir causalidad por proximidad temporal. |
| 24 | Generar perfiles por petición | **Pendiente.** Informe por request con fases, recursos, KV, expertos, transferencias, esperas y errores, enlazado a datos primarios. |
| 25 | Ejecutar integración completa | **Pendiente.** CI aplica el applier; falta build CUDA, inferencia real y una captura que contenga todas las categorías, con comprobación de no bloqueo y checksums. |
| 26 | Repetir batería Qwen3.5-35B | **Pendiente de integración y autorización de ejecución.** Comparación con baseline bajo condiciones documentadas. |
| 27 | Optimizar FAST PATH y CAPACITY PATH | **Pendiente.** Priorizar con evidencia sincronización, transferencias, solapamiento, planificación, kernels, cache MoE, memoria jerárquica y backpressure. |
| 28 | Regresión, publicación y validación Ubuntu | **Pendiente.** CI, PRs separados, documentación reproducible y validación física del usuario en Ubuntu. No se modifica ni ejecuta nada local sin autorización. |

## 3. Próximo bloque: integración activa de sondas

La prioridad inmediata es terminar la instrumentación real en Tandem.cpp. El sink por sí solo no satisface el objetivo: cada familia de eventos debe originarse en puntos reales del runtime.

### Categorías obligatorias

- **KV cache:** asignación, crecimiento, reutilización, eviction, desplazamiento y liberación.
- **Memoria:** alloc/free CPU y CUDA, tamaño, tipo, propietario y duración.
- **Transferencias:** dirección, bytes, stream, objeto, inicio/fin y correlación.
- **Prefetch:** solicitud, cola, ejecución, finalización, cancelación, hit/miss y tardanza.
- **OOM/fallback:** presupuesto, nivel, causa, recuperación y degradación.
- **CUDA kernels:** cada kernel individual y su relación con la operación lógica.
- **Workers CPU:** cola del trabajo, espera, ejecución, publicación, señalización y consumo del resultado.
- **Ciclo de vida:** inicio/fin de request, carga/descarga, routing, errores y cierre/flush del sink.

### Criterios de aceptación

1. Cada evento tiene esquema versionado, fuente, timestamp, unidad y dominio de reloj explícitos.
2. Los IDs de request, objeto, worker, stream y correlación se registran cuando existen; los campos no disponibles quedan nulos, no inventados.
3. El camino de emisión no realiza I/O ni bloqueos prolongados en los hilos del motor.
4. La cola tiene límites, política de overflow observable y contador de eventos descartados.
5. El cierre vacía los eventos pendientes o informa explícitamente de los descartes.
6. Las pruebas cubren concurrencia, orden parcial, overflow, escaping JSON, cierre, errores de escritura y ausencia de callback.
7. La CI compila y ejecuta las pruebas en el commit exacto de la rama.
8. La integración demuestra que las categorías anteriores aparecen en una captura real y reproducible.

## 4. Fases de entrega y gates

### Gate A — infraestructura de captura
- [x] Recolector universal y documentación en LEONES.
- [x] Importador Nsight SQLite y pruebas.
- [x] Hook C++17 de eventos y pruebas en LEONES.
- [ ] Sink JSONL de Tandem.cpp revisado y validado por CI.
- [ ] Ciclo de vida del sink integrado.

### Gate B — sondas reales en Tandem.cpp
- [ ] KV cache.
- [ ] Asignaciones/liberaciones.
- [ ] Transferencias.
- [ ] Prefetch.
- [ ] OOM/fallback.
- [ ] Kernels CUDA individuales.
- [ ] Workers CPU: espera/publicación.

### Gate C — correlación y perfil por request
- [ ] Esquema LEONES/Tandem unificado.
- [ ] Relojes y correlaciones documentados.
- [ ] Timeline end-to-end.
- [ ] Perfil reproducible por petición.
- [ ] Prueba de no interferencia y overflow controlado.

### Gate D — campaña de rendimiento y capacidad
- [ ] Repetición de baseline con configuración fija.
- [ ] FAST PATH: una hipótesis/optimización por experimento.
- [ ] CAPACITY PATH: pruebas graduadas de residencia y streaming.
- [ ] Validación funcional, límites y regresiones.
- [ ] Archivo inmutable de evidencias y hashes.

### Gate E — publicación y validación
- [ ] PR de integración Tandem.cpp.
- [ ] Actualización LEONES con documentación y resultados.
- [ ] Guía de reproducción Ubuntu.
- [ ] Validación del usuario en su MSI, tras autorización explícita.

## 5. Orden de optimización posterior

Cuando los perfiles permitan distinguir causas:

1. Reducir sincronizaciones y esperas evitables.
2. Agrupar transferencias pequeñas y eliminar tráfico redundante.
3. Solapar prefetch/transferencias con trabajo independiente, verificándolo en timeline.
4. Mejorar planificación CPU/GPU y publicación de resultados.
5. Optimizar kernels dominantes según mediciones.
6. Mejorar localidad, retención y prefetch de expertos MoE.
7. Implementar memoria jerárquica L0 GPU → L1 RAM → L2 almacenamiento; swap del sistema como último recurso, no como caché controlada.
8. Añadir backpressure, degradación y fallback con límites verificables.

Cada cambio registrará hipótesis, baseline, control, métrica objetivo, prueba funcional, resultado y decisión de conservar o revertir. No agrupar varias optimizaciones en una comparación.

## 6. Reglas de rigor y seguridad

- No marcar como completado algo que solo esté diseñado, escrito o compilado parcialmente.
- No presentar contadores agregados como routing por capa/experto.
- No confundir tiempo de API CUDA host con duración del kernel en GPU.
- No interpretar bytes acumulados como memoria residente.
- No afirmar causalidad entre wait, transferencia y kernel sin correlación temporal y semántica.
- No borrar, reemplazar ni alterar expedientes primarios.
- No iniciar/detener servicios, benchmarks ni procesos en Ubuntu sin autorización.
- No modificar el working tree local; el desarrollo se realiza primero en GitHub.
- Informar de tests no ejecutados, fallidos o pendientes.

## 7. Registro de actualizaciones

| Fecha | Fase / cambio | Evidencia |
|---|---|---|
| 14-11-2026 | Primera versión del roadmap vivo; estado inicial de instrumentación Tandem.cpp y gates | [Rama LEONES](https://github.com/robertosantosx2/LEONES/tree/nepenthes/performance-capacity-roadmap-20261114) · [PR #1 Tandem.cpp](https://github.com/robertosantosx2/tandem.cpp/pull/1) |
| 14-11-2026 | Se reemplaza el parche manual frágil por `apply_runtime_probes.py`. Smoke test C++17, prueba JSONL y aplicación determinista de sondas pasan en CI; compilación CPU del servidor en curso. CUDA nvcc y captura end-to-end pendientes. | [PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1) · [applier](https://github.com/robertosantosx2/tandem.cpp/blob/nepenthes/universal-observability-20261114/nepenthes/apply_runtime_probes.py) · [CI](https://github.com/robertosantosx2/tandem.cpp/actions/runs/43643274410) |

**Regla de mantenimiento:** al superar una fase, actualizar su estado, añadir una fila fechada en este registro, enlazar commit/PR/CI y actualizar el índice NEPENTHES en el mismo cambio documental cuando sea posible.
