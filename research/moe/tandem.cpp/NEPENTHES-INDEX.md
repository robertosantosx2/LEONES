# NEPENTHES — documento maestro único: plan, estado y motores

> **Fuente única de verdad del proyecto.** Este documento reúne el estado global, la arquitectura, las prioridades, los gates de aceptación y el plan/estado de cada motor de inferencia. Toda actualización de estado debe reflejarse aquí. Los documentos especializados enlazados son anexos técnicos, contratos o expedientes de evidencia; no mantienen un roadmap paralelo ni prevalecen sobre este documento.

**Última actualización:** 2026-11-19.
**Estado global:** infraestructura de observabilidad LEONES en evolución; integración llama.cpp en reconciliación/CI remota; integración TensorFold en fase de contrato y dependencia; sin aceptación física nueva en MSI para las integraciones en curso.

## 1. Resumen ejecutivo y decisión de arquitectura

NEPENTHES es una capa común de observabilidad y evidencia para motores de inferencia. LEONES conserva el núcleo compartido: runner, identidad de ejecución, captura host/GPU, esquema/eventos, importadores, manifiestos, validación, correlación explícita, informes y exportación. Cada motor aporta únicamente un conector/adaptador que traduce su telemetría nativa al contrato común.

Principios no negociables:
- Un solo contrato común y un solo pipeline de evidencia; no crear un sistema paralelo por motor.
- Conservar particularidades del motor en metadata namespaced, sin fragmentar el esquema común.
- Correlación únicamente mediante IDs/tokens y calibración explícitos; nunca atribuir por proximidad temporal.
- Instrumentación opt-in, disabled por defecto y overhead acotado.
- No modificar drivers, CUDA toolkit, kernels/modelos ni introducir sincronizaciones en el hot path.
- Separar aceptación de código/CI de validación física. No declarar un motor aceptado por tener una PR o tests sintéticos.

## 2. Panel general del proyecto

| Área | Estado | Próximo gate |
|---|---|---|
| Núcleo LEONES (runner, captura, manifiestos, informes, AIPerf/OTLP) | Implementación integrada en main para las capacidades documentadas; aceptación física parcial | Completar campañas reales y auditoría de paquetes |
| Contrato común multi-motor | Implementación en [LEONES PR #209](https://github.com/robertosantosx2/LEONES/pull/209) (abierta, lista para revisión; CI host-only verde; no aceptada hasta merge/revisión) para [issue #207](https://github.com/robertosantosx2/LEONES/issues/207) | Revisión final de compatibilidad y semántica; merge de #209 y cierre de #207 tras aceptación |
| llama.cpp | Integración activa; [PR #10](https://github.com/robertosantosx2/llama.cpp/pull/10) en draft/CI según último estado documentado | Cerrar CI/revisión, aceptar contrato y luego C07/C08 en MSI |
| TensorFold 1.2.10 | Contrato documentado en fork; [issue #1](https://github.com/robertosantosx2/TensorFold/issues/1) reclamada; depende de LEONES #207 | Aceptar validador común; después adaptador host-only y CI |
| tandem.cpp (distribución patch-based sobre llama.cpp) | Instrumentación NEPENTHES implementada en repo propio; PR #1 abierta, CI de smoke + compilación CUDA SM86 exitosa; captura real histórica CPU-only disponible | Cerrar revisión/merge, validar captura emparejada con Nsight y completar cobertura/correlación/overhead |
| Otros motores | No hay conector aceptado registrado | Incorporar solo mediante el contrato común y una fila de estado/evidencia |

### Orden de trabajo vigente

**Ejecución actual:** [PR LEONES #209](https://github.com/robertosantosx2/LEONES/pull/209), draft, rama `feat/nepenthes-shared-envelope-207`. La rama contiene el validador común, el registry cerrado (`llama.cpp`, `tensorfold`, `tandem.cpp`), la compatibilidad del entry point llama.cpp, fixtures host-only y un anexo técnico subordinado. En el HEAD de código/tests `68aa53c47cabcfc92531451e7dc1098eb69e7c17`, el workflow remoto **LEONES Contract Tests** terminó `success`: `python -m pytest tests -q` informó **602 passed, 15 subtests passed**. El workflow dedicado **NEPENTHES llama.cpp trace import** también terminó `success` en el HEAD previo `a80bd7fc938f8390364ebfbf9f250bdf30e017ef` (12 tests llama.cpp + 15 tests envelope); el full suite del HEAD de código posterior incluye las regresiones ampliadas de identidad TensorFold, summary duplicado/identificadores vacíos y writer errors. Esto acredita CI host-only, no runtime, GPU, C07 ni C08. La PR #209 sigue abierta y lista para revisión; **#207 no se cierra ni se considera aceptada hasta completar revisión y merge**. El HEAD posterior `cd470dd27089a7543aa8df1b91381725de211858` fue documental; el código probado no cambió antes del commit de documentación actual.
1. **LEONES #207 — contrato común multi-motor.** Extraer la validación del envelope del importador llama.cpp sin debilitarlo; registry explícito de sources; clocks y semántica específicos por motor; fixtures positivos y negativos para llama.cpp y TensorFold.
2. **CI y aceptación de #207.** Preservar compatibilidad llama.cpp; rechazar sources desconocidos, mismatch event/summary, IDs/valores inválidos, privacidad incorrecta y summaries malformados; no declarar aceptación hasta observar CI real.
3. **TensorFold — adaptador sin CUDA.** Solo tras #207: ciclo request/run, eventos compatibles, metadata namespaced, privacidad y pruebas host-only. No duplicar importador ni runner.
4. **llama.cpp — reconciliación de integración.** Resolver el candidato limpio [PR #10](https://github.com/robertosantosx2/llama.cpp/pull/10) sobre upstream actual, revisar diff/semántica y cerrar CI antes de merge o de actualizar el gitlink LEONES.
5. **Validación física MSI.** Solo cuando los gates remotos estén cerrados: build CUDA, C07 con NVTX+Nsight y C08 con baseline/tratamientos emparejados.
6. **Aceptación por motor y release.** Publicar evidencia, límites, overhead, cobertura y hashes; un motor no hereda la aceptación de otro.

## 3. Estado y plan por motor

### 3.1 llama.cpp

**Estado:** integración activa en el fork; PR [#10](https://github.com/robertosantosx2/llama.cpp/pull/10) preparada como integración limpia sobre upstream c406f4367e19bea7930e7f74e1984c9acc6d44bf, con un commit NEPENTHES y 23 archivos. En la última evidencia registrada, CI seguía en curso y los runners self-hosted/Models Backend Check estaban queued. No se declara CI global verde, merge ni aceptación.

**Ya conseguido:** contrato de eventos/sink, puente CPU, instrumentación NVTX opt-in y port de cambios NEPENTHES sobre upstream actual en PR #10. Los históricos RC1/#6 y #1–#3 son candidatos/antecedentes, no deben tratarse como línea aceptada ni fusionarse sin reconciliación.

**Siguientes pasos:**
- [ ] Consultar CI del HEAD actual de PR #10 y clasificar todos los checks, incluidos queued/skipped y fallos externos.
- [ ] Revisar diff y semántica de lifecycle, concurrencia, JSONL, NVTX y límites de eventos; comparar cobertura con los candidatos previos.
- [ ] Cerrar contrato común LEONES #207 y comprobar compatibilidad del productor con el importador.
- [ ] Merge solo tras CI/revisión; actualizar el gitlink LEONES después de la aceptación.
- [ ] MSI: build Linux/CUDA, C07 real NVTX+Nsight y C08 emparejado; conservar artefactos y métricas.

**Límite de aceptación:** la CI remota no demuestra overhead, cobertura real ni correlación con CUPTI; hacen falta C07/C08 físicos.

### 3.2 TensorFold 1.2.10

**Estado (corte remoto 2026-11-19):** contrato y auditoría de fuente publicados en el fork [robertosantosx2/TensorFold](https://github.com/robertosantosx2/TensorFold), rama [nepenthes/tensorfold](https://github.com/robertosantosx2/TensorFold/tree/nepenthes/tensorfold). [TensorFold #1](https://github.com/robertosantosx2/TensorFold/issues/1) permanece abierta. No existe PR de runtime. La auditoría de fuente está en [SOURCE-AUDIT-1.2.10.md](https://github.com/robertosantosx2/TensorFold/blob/nepenthes/tensorfold/docs/nepenthes/SOURCE-AUDIT-1.2.10.md); commits documentales: `817029091fc6ca87ad21a11852c2c544a2bd2e7e` (auditoría) y `21be08979396fd73c146dc33fdb744f9df722a45` (enlace desde README). Los status checks consultados para ambos commits no devolvieron checks; no se afirma CI verde.

**Dependencias duras:** [LEONES #207](https://github.com/robertosantosx2/LEONES/issues/207) sigue abierta y sin implementación/aceptación. El importador actual exige `source=llama.cpp` y `clock_domain=steady_clock`; cambiar solo el source no hace compatible TensorFold. La generalización debe preservar el comportamiento llama.cpp, introducir registry cerrado y validar clocks/semántica por conector. La segunda dependencia es el gate ATC de TensorFold: el último `atc overlap --repo robertosantosx2/TensorFold --json` registrado devolvió `complete=false`, limitación `workingTreeUnavailable`, `changedFiles=null` y sin resultado de solapamiento concluyente. Por tanto, no equivale a `clean` ni demuestra ausencia de conflictos.

**Auditoría de fuente 1.2.10:** se revisaron `server/http_conn.zig`, `server/routes.zig`, `server/server.zig`, `server/request_journal.zig`, `cuda/launch.zig`, `cuda/graph.zig`, `cuda/stream.zig`, `cuda/memory.zig`, `cuda/driver.zig` y `cuda/abi.zig`. La identidad lógica debe nacer por petición en `routes.dispatch`, no por conexión; keep-alive reutiliza conexiones y los IDs existentes son IDs de respuesta. El journal puede contener contenido privado y no es un sink. CUDA expone límites host para launch/graph/memoria/copias/errores, pero launch/graph return solo demuestran submission; los contadores de memoria son agregados. No añadir sincronizaciones para telemetría. No se encontró productor/sink NEPENTHES runtime en los archivos auditados.

**Secuencia obligatoria:**
1. [ ] Cerrar LEONES #207 con envelope común, registry cerrado y fixtures llama.cpp/TensorFold; CI del HEAD exacto debe pasar.
2. [ ] Completar ATC overlap desde el checkout TensorFold correcto; exigir `complete=true` y revisar todos los resultados `conflicts/clean/unknown`. El resultado previo `workingTreeUnavailable` no supera el gate.
3. [ ] Abrir PR pequeña del adaptador host-only: opt-in, no-op real cuando disabled, sink acotado, IDs/run identity, privacidad y metadata namespaced; sin sondas CUDA.
4. [ ] Añadir pruebas host para concurrencia, keep-alive/múltiples peticiones, lifecycle balanceado, sink_summary final, drops/errors y camino disabled; validar fixtures con el importador común.
5. [ ] Separar futuras sondas CUDA por áreas ATC (launch/graph; memoria/copias; sync/errores) y después NVTX/Nsight con tokens explícitos.
6. [ ] Solo después de aceptación host/CI planificar validación física y overhead; MSI no es necesario en esta fase.

**Límite actual:** TensorFold está en fase de contrato/auditoría, no de implementación runtime. No declarar CI, pruebas, captura, correlación u overhead aceptados. No abrir PR runtime hasta superar ambos gates 1 y 2.

### 3.3 tandem.cpp — distribución patch-based sobre llama.cpp

**Naturaleza:** `robertosantosx2/tandem.cpp` no es un runtime independiente desde cero; es una distribución de parches sobre una revisión fijada de llama.cpp. Su build aplica primero `tandem.patch` (optimizaciones/funcionalidad Tandem) y después la capa de instrumentación NEPENTHES. Debe tratarse como un perfil/runtime derivado de llama.cpp, conservando su identidad de source `tandem.cpp` y sin duplicar el núcleo de captura LEONES.

**Implementación localizada:**
- Repositorio de implementación: [robertosantosx2/tandem.cpp](https://github.com/robertosantosx2/tandem.cpp).
- PR canónica de instrumentación: [Tandem.cpp #1 — active JSONL sink and full runtime probe applier](https://github.com/robertosantosx2/tandem.cpp/pull/1), rama `nepenthes/universal-observability-20261114`, HEAD auditado `170d3af9918e2cdf3b5c72f6bb61ab0c3b7b6b52`. Está **abierta, sin fusionar**; GitHub la reporta `mergeable=true` / `mergeable_state=clean`.
- La carpeta `nepenthes/` incluye `nepenthes_trace.hpp` (hook C++17), `nepenthes_jsonl_sink.hpp` (sink asíncrono acotado), `runtime.patch`, `apply_runtime_probes.py`, pruebas C++ y README de aplicación.
- `build.sh` aplica, en orden, `tandem.patch`, `nepenthes/runtime.patch` y `apply_runtime_probes.py`; los anclajes exactos hacen fallar el proceso si la fuente pinned deriva.
- Activación opt-in mediante `NEPENTHES_TRACE_JSONL` y `NEPENTHES_RUN_ID`; el sink se crea de forma lazy en la primera entrada de graph-compute. Sin la variable JSONL no se activa la captura interna.
- El productor usa cola bounded de 8192 entradas y writer thread separado; el callback solo encola, cuenta drops y errores, y no hace I/O de fichero en el hilo productor. El apagado bloquea nuevas callbacks y espera a las que ya estaban en vuelo.
- El JSONL emite schema 1.0, `source=tandem.cpp`, reloj monotónico steady-clock y timestamp Unix; los IDs de evento son secuenciales. Los eventos internos sin identidad explícita mantienen `request_id=0`.

**Cobertura instrumentada declarada por el código y el README de la PR:**
- lifecycle de petición del servidor (task ID como request_id), graph-compute y sincronización;
- MoE cache hit/miss/eviction, lookahead prefetch enqueue/wait, jobs y workers CPU, publicación de resultados y espera del consumidor GPU;
- KV cache: allocation/teardown/clear/update, ubatch insertion, cell reuse/release y operaciones de secuencia;
- alloc/free/OOM/fallback de backend, CUDA device/pool y pinned-host;
- spans host de submission para H2D/D2H, 2D copies y D2D/peer; dispatch por `ggml_op`;
- los tiempos reales de kernels individuales y actividades memcpy CUDA proceden de Nsight/CUPTI importado por LEONES, no de los spans host.

**Evidencia de CI:** [Actions run #43654679693](https://github.com/robertosantosx2/tandem.cpp/actions/runs/43654679693), asociado exactamente al HEAD `170d3af...`, terminó `completed/success` el 2026-11-15. El workflow compila y ejecuta las pruebas C++17 del hook y del sink (incluida carrera de shutdown y 4.256 eventos concurrentes), aplica los parches sobre la base pinned `f5222f25c18da062ab2b8a2dbbfbf4feae398566`, ejecuta el aplicador determinista y compila llama-server CPU y CUDA para SM 86. Esto es aceptación de pruebas/build de CI, no una captura GPU ni una medición de overhead. La PR sigue abierta y sin merge.

**Evidencia física histórica ya registrada en este documento:** se construyó el runtime instrumentado y se ejecutó una inferencia real Qwen3.5-4B Q4_K_M en modo CPU-only mediante `nepenthes run`: 3.683 eventos del motor, de los que 3.117 quedaron dentro de la ventana request_start/request_end; 49 eventos KV, 2.540 transferencias, 290 eventos kernel y 226 sincronizaciones dentro de esa ventana. La petición duró 1,864918 s; 10 tokens de prompt y 16 generados, prefill 21,50 tok/s y decode 10,72 tok/s. En esa captura todos los eventos de la ventana tenían `request_id=0`; por tanto, la segmentación temporal no constituye correlación robusta por petición. Nsight estaba desactivado. Esta evidencia prueba que el productor emitió eventos en una inferencia real, pero no acredita cobertura CUDA efectiva ni correlación request→kernel.

**Pendiente / plan de aceptación:**
- [ ] Revisar y fusionar Tandem.cpp #1; conservar el HEAD exacto y el resultado de CI como evidencia.
- [ ] Reconciliar el contrato `schema_version=1.0`, `source=tandem.cpp` con el validador multi-engine LEONES #207; no relajar el importador llama.cpp ni aceptar sources arbitrarios.
- [ ] Ejecutar una captura nueva con `nepenthes run --profile full` para obtener JSONL + Nsight en el mismo RUN_ID; verificar el paquete y realizar importación emparejada.
- [ ] Medir pérdidas/errores del sink y cobertura de cada categoría; completar correlación solo con IDs explícitos y calibración de relojes. No convertir `request_id=0` ni cercanía temporal en atribución.
- [ ] Ejecutar C07 y C08 emparejados para medir overhead; separar spans host de actividad GPU real.
- [ ] Actualizar la evidencia de hardware solo después de conservar manifest, hashes, JSONL, Nsight SQLite y resultados de importación.

**Límite actual:** instrumentación implementada y CI de build/test verde en el HEAD auditado; existe una captura real CPU-only histórica. No hay evidencia en esta auditoría de una captura nueva emparejada JSONL+Nsight, de correlación robusta request-kernel ni de overhead aceptado. El runtime derivado Tandem no debe contabilizarse como un motor independiente de llama.cpp a efectos de duplicar colectores o importadores.

### 3.4 Otros motores

No se registra todavía ningún otro motor con conector y aceptación NEPENTHES demostrados. Cualquier candidato nuevo deberá añadirse aquí con versión/base, rama/PR, estado CI, estado host-only, estado hardware, límites y siguiente gate. No se inferirá compatibilidad por compartir CUDA o formato de modelo.

## 4. Gates de aceptación comunes

| Gate | Qué demuestra | Qué no demuestra |
|---|---|---|
| Diseño/documentación | Contrato y límites definidos | Implementación |
| Host tests | Validación lógica sin GPU | Compatibilidad real con runtime/CUDA |
| CI_PASS | Checks automatizados del commit exacto | Captura física ni overhead |
| CAPTURED | Ejecución real con artefactos y manifiesto | Correlación/atribución no validada |
| C07_ACCEPTED | Captura emparejada JSONL + NVTX/Nsight con calibración/IDs explícitos e integridad | Overhead estadístico |
| C08_ACCEPTED | Baseline/tratamientos repetidos y overhead dentro de umbral | Cobertura de sondas no ejercitadas |
| ENGINE_ACCEPTED | Gates de software, contrato y hardware aplicables superados | Aceptación automática de otros motores |

Umbral C08 standard vigente: decode overhead ≤5% aceptable; 5–8% requiere excepción/revisión; >8% bloquea aceptación standard. Reportar por separado TTFT, decode tok/s, latencia, RSS/RAM y VRAM device-wide. No atribuir memoria/uso GPU global al proceso sin evidencia.

## 5. Documentos auxiliares (no son fuentes de estado paralelas)

- [Roadmap histórico/detallado y checklist de gates](NEPENTHES-ROADMAP.md): detalle operativo subordinado a este documento; actualizar el estado maestro aquí.
- [Contrato Nsight/CUPTI](NEPENTHES-IMPORTER.md): referencia técnica del importador.
- [CLI e instalador](NEPENTHES-CLI.md): referencia de uso.
- [Campañas](NEPENTHES-CAMPAIGNS.md): registro de ejecuciones y resultados; las conclusiones aceptadas se resumen aquí.
- [Informe histórico Qwen3.5-35B](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md): evidencia histórica, no roadmap.

---

## Registro histórico y evidencia detallada

El contenido histórico que sigue se conserva como expediente de evidencias. Para el estado vigente, la prioridad y el plan por motor, prevalecen las secciones 1–5 de este documento maestro.


**Corte de estado:** 2026-11-15 (validación histórica Nsight-only real completada).  
**Estado global:** CLI funcional, motor CUDA instrumentado compilado sobre base pinned, primera inferencia real con JSONL del motor y validación E2E de importación Nsight-only sobre captura histórica real completadas. Aún falta la captura emparejada con Nsight, correlación robusta y auditoría de cobertura/overhead de una ejecución instrumentada.

## Resumen ejecutivo

NEPENTHES ya dispone de cuatro bloques de trabajo en LEONES y una integración de instrumentación en Tandem.cpp:

1. Instrumentación universal y sink JSONL en Tandem.cpp (PR #1).
2. Importador LEONES para JSONL + Nsight/CUPTI (PR #151).
3. Instalador user-space, CLI de una línea, captura de host/GPU y paquete de informes (PR #152).
4. Importación histórica Nsight-only con procedencia aislada (PR #153).

Estado remoto de las PR: LEONES #150 sigue abierto y actualmente no es mergeable; #151 está cerrado e integrado en la rama `research/nepenthes-universal-collector-20261115` (no en `main`); #152 y #153 están cerrados e integrados en `main`. Tandem.cpp #1 sigue abierto y sin fusionar. La cadena histórica de desarrollo no debe confundirse con el estado actual de integración.

**Validación física MSI completada hasta ahora:**
- Build CUDA local del motor instrumentado sobre llama.cpp pinned `f5222f25c18da062ab2b8a2dbbfbf4feae398566`, tras aplicar `tandem.patch`, `runtime.patch` y el aplicador determinista de probes.
- Primera inferencia real con Qwen3.5-4B Q4_K_M mediante servidor instrumentado, CPU-only, capturada por `nepenthes run`; 3.683 eventos del motor y 3.117 dentro de la ventana request_start/request_end.
- 49 eventos KV cache dentro de la petición; 2.540 transferencias, 290 kernels y 226 sincronizaciones dentro de la ventana.
- Tiempo de petición monotónico 1,864918 s, consistente con los 1.864,85 ms del servidor; 10 tokens prompt, 16 generados, prefill 21,50 tok/s y decode 10,72 tok/s.
- El `request_id` de todos los eventos de la ventana es 0; la segmentación es temporal y no una correlación robusta por petición.
- Instalación user-space correcta.
- `nepenthes doctor`: entorno detectado correctamente.
- `nepenthes self-test`: correcto; 3 eventos, 1 muestra, HTML, checksums e integridad de eventos válidos.
- Inspección del SQLite Nsight histórico y posterior importación standalone: 151.039 actividades.
- Revalidación E2E desde el `main` de LEONES en `d548a37cc4f05632eba946495ad9d98bdf862c63`: CLI `--nsys-only` con código de salida 0 y destino independiente `qwen35-nsys-only.sqlite` (~90 MiB).
- Auditoría independiente del destino: distribución exacta de las ocho familias CUPTI, 151.039 IDs únicos, pares tabla/actividad únicos, SHA-256 y procedencia coincidentes, cero filas no soportadas, `integrity_check=ok` y `foreign_key_check` vacío.
- Import ID de la revalidación: `qwen35-real-nsys-only-20261115`; `run_id=null`, `jsonl=null`, sin correlación NEPENTHES inventada.
- La fuente Nsight conserva SHA-256 `30df43c0a1b235cc25987e2af87e5cf19e5f900f324c26fa22f28cd83144e4fc`; no se modificó.

**Aún no demostrado:** cobertura de todas las sondas, captura Nsight en la misma ejecución, importación emparejada JSONL+Nsight, correlación request-kernel, medición del overhead y recomendaciones cuantitativas de optimización.

## Fuente de verdad y cambios

| Área | PR / rama | Estado actual |
|---|---|---|
| Instrumentación universal Tandem.cpp | [Tandem.cpp #1](https://github.com/robertosantosx2/tandem.cpp/pull/1), `nepenthes/universal-observability-20261114` | Abierto, sin fusionar |
| Índice y documentación | [LEONES #150](https://github.com/robertosantosx2/LEONES/pull/150), `research/nepenthes-universal-collector-20261115` | Abierto; GitHub informa `mergeable=false` |
| Importador JSONL + Nsight | [LEONES #151](https://github.com/robertosantosx2/LEONES/pull/151), `feat/nepenthes-nsys-importer-20261115` | Fusionado en rama de investigación, no en `main` |
| Instalador y CLI | [LEONES #152](https://github.com/robertosantosx2/LEONES/pull/152), `feat/nepenthes-cli-installer-20261115` | Fusionado en `main` |
| Importador Nsight-only | [LEONES #153](https://github.com/robertosantosx2/LEONES/pull/153), `feat/nepenthes-nsys-only-20261115` | Fusionado en `main` (merge `838de99`); CI 7/7 en HEAD funcional `9e0383e` |

Los siete workflows asociados al HEAD funcional `9e0383e7d84334bb2935c229722c9b7a80ac02af` de LEONES #153 terminaron en `success`. Los commits posteriores de esta rama solo corrigen documentación; GitHub no ha asociado nuevos workflows a esos commits. Los estados de #150, #151 y #152 se indican por separado arriba. CI valida los contratos automatizados, no sustituye las pruebas físicas del motor.

## Estado por capacidad

| Capacidad | Estado | Evidencia / límite |
|---|---|---|
| Contrato de evento universal y sink JSONL | Implementado | Tandem.cpp PR #1; CI success |
| Barrera de apagado y concurrencia del sink | Implementado y probado en CI | No implica captura real MSI |
| Aplicación determinista de sondas en Tandem.cpp | Implementada en el parche | Compilación CUDA CI; falta medir cobertura en ejecución |
| Instalador user-space | Implementado y ejecutado | MSI: instalación correcta en `~/.local` |
| CLI de una línea `nepenthes run` | Implementado y probado con motor instrumentado | Qwen3.5-4B real: JSONL del motor, exit code 0 y 3.683 eventos; Nsight desactivado en esta prueba |
| Doctor y self-test | Ejecutados correctamente | MSI: 3 eventos, 1 muestra, reporte HTML |
| Muestreo CPU/RSS del árbol de procesos | Implementado | Self-test; falta perfil real de motor |
| Muestreo NVIDIA global con nvidia-smi | Implementado | Doctor detecta nvidia-smi; falta captura integral de inferencia |
| Captura Nsight opcional/obligatoria/off | Implementada | Falta ejecutar wrapper real con Nsight en MSI |
| Paquete CSV/JSONL/SQLite/Markdown/HTML/SVG | Implementado; aceptación de inferencia parcial | Captura de motor JSONL real; falta `nepenthes verify` y auditoría completa del paquete de inferencia |
| Verificación de hashes y estructura | Implementada | Self-test correcto; falta `verify` sobre captura real |
| Importador emparejado JSONL + Nsight | Implementado y CI | Falta validar un par real de una misma ejecución |
| Inspección de esquema Nsight | Implementada y ejecutada | MSI: 8 tablas CUPTI reconocidas |
| Importación Nsight-only | Implementada, CI success y E2E histórico real superado | MSI: 151.039 filas; 8/8 tablas CUPTI detectadas importadas; 0 filas no soportadas; auditoría de procedencia, unicidad e integridad correcta |
| Procedencia, hashes y cobertura parcial | Implementado | Import standalone con `run_id=null`, sin JSONL |
| Correlación request-kernel entre relojes | No implementada deliberadamente | Requiere IDs comunes y calibración; no se debe inferir por proximidad |
| Informe histórico Qwen3.5-35B | Construido en documentación | Nsight-only histórico, sin JSONL emparejado |\n| Primera captura Qwen3.5-4B | Capturada; informe de campaña | Inferencia real CPU-only con motor instrumentado; Nsight off; request_id=0 |
| Matriz de cobertura de sondas por ejecución | Parcial | Qwen3.5-4B confirma request, routing, KV, transfer, kernel, sync y allocation; MoE/workers/prefetch/OOM aún no aceptados |
| Batería repetible y comparación entre ejecuciones | Pendiente | Requiere capturas emparejadas y manifiestos |

## Roadmap

El roadmap operativo detallado está en [NEPENTHES-ROADMAP.md](NEPENTHES-ROADMAP.md).

1. **Cerrar el árbol de PRs:** revisión, resolver comentarios y fusionar en orden de dependencias con autorización explícita.
2. **Prueba de extremo a extremo MSI:** `doctor`, `self-test`, `run --profile smoke` con un comando inocuo y después motor instrumentado; verificar logs, exit code y paquete.
3. **Captura real instrumentada:** Qwen3.5 u otro motor Tandem parcheado, JSONL del motor + host + Nsight en el mismo RUN_ID; validar pérdidas y overhead.
4. **Importación emparejada:** validar tablas, hashes, cobertura y límites de correlación en LEONES.
5. **Cobertura de sondas:** matriz para request/graph, KV, MoE cache, workers, prefetch, alloc/free, OOM/fallback y transferencias.
6. **Informes comparativos:** tablas y gráficas con series temporales, kernels, transferencias, memoria y rendimiento, distinguiendo observación, estimación y medición.
7. **Release reproducible:** instalación limpia, pruebas, documentación, manifiesto, checksums y procedimiento de desinstalación/actualización.

## Captura histórica Qwen3.5-35B

Informe completo: [NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md).

La importación Nsight-only del MSI contiene 151.039 actividades:
- kernel 8.982; memcpy 44.488; memset 9; runtime 84.116;
- graph trace 5.207; synchronization 7.864; CUDA event 262; overhead 111.

Cobertura declarada: `complete_for_detected_cupti_tables`, con 8 tablas detectadas, 151.039 filas importadas y cero filas/tablas no soportadas. No significa que todas las categorías que Nsight pudiera producir estén presentes en el archivo. La auditoría independiente confirmó 151.039 IDs únicos, 151.039 pares tabla/actividad únicos, `integrity_check=ok` y `foreign_key_check` vacío. Los 262 CUDA_EVENT tienen `timestamp=0` en el SQLite fuente y en el importado; se conservan como eventos puntuales sin intervalo temporal. No se usan para reconstruir duración.

## Reglas de evidencia

- `CI_PASS` significa que las pruebas automatizadas del commit pasaron.
- `INSTALLED` significa que el instalador terminó en el MSI.
- `SELF_TEST_PASS` significa que el autodiagnóstico produjo su paquete de prueba válido.
- `CAPTURED` exige una ejecución real del motor y artefactos conservados.
- `MEASURED` solo se usa para valores derivados de una captura real identificada.
- `ESTIMATED` nunca se presenta como medida.
- No unir `request_id` con `correlationId` CUPTI ni relojes monotónicos con timestamps Nsight sin un mecanismo demostrado de correlación.
- La utilización/memoria GPU de `nvidia-smi` es device-wide; no atribuirla al proceso sin evidencia.
- Los spans de submission host no son duración de ejecución GPU.


## Estado remoto verificado — 2026-11-19

Este bloque sustituye como estado operativo actual las referencias de integración del corte 2026-11-15; los resultados MSI históricos descritos arriba siguen siendo históricos y no se atribuyen al nuevo runtime llama.cpp.

- **AIPerf-first C08 software:** integrado en main mediante [LEONES PR #197](https://github.com/robertosantosx2/LEONES/pull/197), merge commit c2f0eb92fc50bbf8bb95d35f540927589f034544. CI completo: 519 pruebas pasadas, junto con los gates V1, runtime v1.1, RC3, RC4 y A01. El runner fija AIPerf 0.13.0, crea fingerprint del comando, conserva hashes de salida, exige telemetría del proceso servidor y elimina el log bruto por defecto.
- **Adaptadores y C07 importer:** integrados en main mediante [LEONES PR #198](https://github.com/robertosantosx2/LEONES/pull/198), merge commit 8812aa6c0d2dea972acb8fd27508146d74fd0c2e. CI acumulado verde: AIPerf/telemetría, importador llama.cpp, monitor upstream y gates de repositorio.
- Incluye adaptadores llama-server, muestreo NVML/energía, exportación OTLP y transporte HTTP seguro, informes comparativos y el importador de trazas llama.cpp con tokens explícitos y calibración de reloj.
- **No aceptado físicamente:** todavía no hay captura real emparejada llama.cpp + NVTX + Nsight ni campaña C08 baseline/instrumentado en la RTX 3050. CI valida código y contratos; no mide overhead de ejecución real.
- **llama.cpp RC1:** [PR #6 del fork](https://github.com/robertosantosx2/llama.cpp/pull/6) mantiene la instrumentación sobre upstream actual. El fork `master` está sincronizado con `ggml-org/llama.cpp` en `9a080f44b503c64f66c84a6274b9d9ee5d5b09d5`; [PR #7](https://github.com/robertosantosx2/llama.cpp/pull/7) integró en la rama RC1 el último cambio upstream de OpenVINO. La rama RC1 está 31 commits por delante y 0 por detrás de `master`, con 23 archivos de diff. El HEAD `d692b04bac286d89cc8ea394728e54149f5fa3c7` incluye la corrección del coste de reloj cuando la traza está desactivada, la cobertura de triggers CI para el puente CPU/C ABI y el guard de opt-in NVTX para que no haya marcadores con tracing desactivado. En el HEAD anterior `246fbbd4...` GitHub expuso CI: runtime trace, CUDA dedicada y general, HIP, CPU, server, WASI/WASM y checks de calidad pasaron; MUSA falló por descarga externa y los runners self-hosted quedaron queued/pending. El nuevo HEAD `d692b04bac286d89cc8ea394728e54149f5fa3c7` añade una corrección de opt-in NVTX: no emite marcadores si tracing está desactivado. CI para el nuevo HEAD ya se ha disparado (runs 44589790856, 44589790779 y checks asociados); runtime trace, CUDA dedicada/general, CPU, server, WASI/WASM y calidad estaban in progress en la última consulta. Aún no hay conclusiones para este HEAD. PR #6 sigue en borrador. El gitlink de LEONES no se actualiza hasta aceptar CI y revisión.

**Próximo límite de hardware:** cuando PR #6 tenga CI verde y la integración de software esté revisada, el siguiente trabajo que no puede cerrarse en GitHub será compilar en MSI, ejecutar una inferencia instrumentada, capturar Nsight y completar las repeticiones emparejadas C07/C08.


### AIPerf warm-up provenance correction — 2026-11-19

Post-merge audit found that the wrapper had not explicitly passed AIPerf's warm-up request count. LEONES PR #199 is now merged as `109e3073cd0040a5ba86b906e71e003959f72d3c`: the runner defaults to one explicit warm-up request, records it in the workload command fingerprint and manifest, and the evidence builder rejects manifests without that field. CI passed **572 tests** plus all release/runtime gates. This is still software acceptance only; no C08 performance result is claimed.


### Perfiles adaptativos — 2026-11-19

LEONES PR #200 se integró como `ed0535c2bf1bc7025cde1534e395ed1c3bbac581` tras **575 pruebas pasadas** y gates de release/runtime verdes. `moe-deep` muestrea host a 100 ms mientras hay requests activos y a 1 s en reposo, usando únicamente eventos explícitos `request_start/request_end`; activa Nsight automáticamente si está instalado. `latency-critical` desactiva muestreo periódico de host y Nsight. La selección de sondas internas del motor aún no está filtrada por perfil; se mantiene como trabajo pendiente en la capa llama.cpp. Ninguno de estos perfiles tiene todavía medición física de overhead en MSI.


### Actualización llama.cpp RC1 — 2026-11-19 (corte 16:34 UTC)

- Fork `robertosantosx2/llama.cpp` `master` sincronizado exactamente con upstream `ggml-org/llama.cpp` en `9a080f44b503c64f66c84a6274b9d9ee5d5b09d5`.
- [PR #7](https://github.com/robertosantosx2/llama.cpp/pull/7) fusionada; incorpora el commit upstream OpenVINO a la rama NEPENTHES RC1 sin solapar los 23 archivos de instrumentación.
- [PR #6](https://github.com/robertosantosx2/llama.cpp/pull/6) sigue abierta como borrador. HEAD `246fbbd4b81cb8c307fa12aeed6d86317f53d3cc`; comparación: 31 commits ahead, 0 behind, 23 archivos.
- Corregido el camino desactivado de `ScopedEvent`: no lee el reloj monotónico si NEPENTHES está apagado; test de regresión añadido.
- Ajustados los filtros `push` del workflow para incluir `ggml/src/ggml-cpu/ggml-cpu.c` y `ggml/include/ggml-nepenthes-c.h`.
- El HEAD `d692b04bac286d89cc8ea394728e54149f5fa3c7` añade guard opt-in NVTX. Aún no hay CI visible para este HEAD. En el HEAD anterior, runtime trace y compilaciones CPU/CUDA pasaron; MUSA falló por descarga externa y los runners self-hosted quedaron pendientes. No hay build local ni aceptación MSI declarados.


## Actualización CI llama.cpp RC1 — 2026-11-19

La PR [llama.cpp #6](https://github.com/robertosantosx2/llama.cpp/pull/6), HEAD `246fbbd4b81cb8c307fa12aeed6d86317f53d3cc`, ya tiene resultados de CI asociados (run IDs 44567511681 y 44567511961): NEPENTHES runtime trace pasó con contrato, sink JSONL, puente CPU, build de llama-server CPU y CUDA, además de verificación NVTX v3. También pasan CUDA general, HIP, CPU, server, WASI, WASM, Behavior Check, Code Style y EditorConfig.

El workflow combinado CUDA/HIP/MUSA aparece como fallido exclusivamente en la preparación de dependencias MUSA: el runner no pudo conectar con `dl.mthreads.com` y después no encontró los paquetes MUSA. Los jobs CUDA y HIP de ese mismo workflow pasaron. Por tanto, no es un fallo del build CUDA. Los jobs self-hosted CUDA, Vulkan, OpenVINO, WebGPU y CPU seguían queued/pending en la última consulta; no se cuentan como aceptados. La PR #6 permanece draft hasta clasificar/terminar esos jobs y completar la revisión final.


### Auditoría adicional del diff RC1 — 2026-11-19 (última revisión)

- La inspección del diff detectó una eliminación ajena a NEPENTHES: `GGML_OP_CONV_2D` había desaparecido de `ggml_op_alloc_size_may_expand()`, aunque permanece en el upstream sincronizado. Se restauró en la rama de la PR #6 mediante commit `33e0d0a578c48b0a31616fd1b72fd255f12e39a4`.
- El diff actual de `ggml-backend.cpp` queda limitado a la instrumentación de allocation/free; la eliminación de `GGML_OP_CONV_2D` ya no aparece.
- Nuevo HEAD de PR #6: `33e0d0a578c48b0a31616fd1b72fd255f12e39a4`; 33 commits ahead, 0 behind, 23 archivos. PR sigue draft y no fusionada.
- Los resultados de CI del HEAD anterior `d692b04...` no validan este nuevo commit. La consulta inmediata aún no devuelve runs asociados al nuevo HEAD. No declarar CI verde ni solicitar todavía validación MSI.


### CI RC1 — commit corregido `33e0d0a578c48b0a31616fd1b72fd255f12e39a4` (sondeo 2026-11-19 18:49 UTC)

- Pasa `trace-and-cpu-build`: contrato de trazas, sink JSONL acotado, puente CPU y build instrumentado de llama-server CPU.
- Pasa la verificación estática de NVTX v3 para los marcadores CUDA; la compilación CUDA específica de llama-server seguía en curso en el último sondeo.
- Pasan CUDA e HIP del workflow general; Behavior Check (Ubuntu/Windows), WASI, WASM, WebGPU, Code Style y EditorConfig.
- CPU general y Server seguían en curso; runners self-hosted restantes estaban en cola o ejecución.
- MUSA falla de nuevo en `Dependencies`, antes de compilar: timeout al conectar con `dl.mthreads.com` y paquetes `musa-mualg-5-2`, `musa-muthrust-5-2` y `libmthreads-compute` no localizados. Clasificación: bloqueo de infraestructura/repositorio externo; no atribuirlo a regresión de NEPENTHES ni a CUDA.
- Estado parcial, no CI global verde. PR #6 permanece draft. Sin build local/MSI, C07, C08 ni actualización de gitlink.

### Actualización CI llama.cpp RC1 — HEAD `33e0d0a578c48b0a31616fd1b72fd255f12e39a4` (sondeo 2026-11-19 19:16 UTC)

Esta sección sustituye los estados parciales anteriores para la aceptación del HEAD indicado; los resultados de otros commits siguen siendo históricos.

- [x] Workflow NEPENTHES runtime trace completo: contrato de trazas, bounded JSONL sink, puente CPU y build CPU instrumentado.
- [x] Build CUDA específico de `llama-server` completo para sm_86; verificación de NVTX v3 habilitado correcta.
- [x] CI general CPU completo: Ubuntu x64/arm64 y Windows x64/arm64.
- [x] Server completo: Ubuntu y Windows; tests y backend sampling de Ubuntu pasan.
- [x] CUDA y HIP generales; HIP quality (Werror y VGPR spill check); Behavior Check, WASI, WASM, Code Style y EditorConfig.
- [!] Workflow CUDA/HIP/MUSA globalmente fallido solo en `musa/Dependencies`: timeout de `dl.mthreads.com`, paquetes SDK ausentes y compilación MUSA omitida. Los jobs CUDA y HIP del mismo workflow pasan. Clasificación: infraestructura/dependencia externa; no es fallo del build CUDA.
- [~] Siguen queued los runners self-hosted KleidiAI, CPU high-performance, IBM, Vulkan, OpenVINO, Metal, CUDA y WebGPU, además de Models Backend Check. No se cuentan como aceptados.
- PR #6 permanece abierta, draft, mergeable y no fusionada. Comparación actual: 33 commits ahead, 0 behind; 23 archivos. La descripción de la PR está sincronizada con este estado.
- No se ha actualizado el gitlink ni se ha solicitado intervención del MSI. C07 real (NVTX + Nsight) y C08 overhead siguen pendientes de hardware.

**Decisión:** aceptación remota todavía abierta. El CI de CPU/CUDA instrumentado principal ya está validado, pero no hay CI global verde mientras MUSA siga fallido y los runners restantes permanezcan queued. Continuar la auditoría final y volver a consultar esos jobs antes de promover la PR.

## Estado de integración actualizado — 2026-11-19 (post-merge #203/#205)

### Gate de datos LEONES

- [x] Commit post-merge `28de2459a76433b90628bb5dff7e7703a789d9a1`: **8/8 workflows** completados con éxito.
- [x] Importador específico: 118 pruebas pasadas.
- [x] Regresión runtime: 582 + 15 pruebas pasadas.
- [x] Migración 006 y el importador v1.1 están en `main`; CI cubre persistencia de metadatos tipados, preservación de `raw_json`, compatibilidad v1.0, validación de enums e idempotencia. Esto es evidencia de software/CI, no importación de una captura real del nuevo productor.

### Fork y submódulo llama.cpp

- [x] [LEONES PR #206](https://github.com/robertosantosx2/LEONES/pull/206) fusionada en `main`: commit `c98deebfc169b8d860d4e887b1f3ffb068342b00`.
- [x] `subprojects/llama.cpp` registrado como gitlink modo `160000`, URL del fork personal y CI de integridad.
- [x] Corregido el invariante del manifiesto: `fork_head_commit` describe el HEAD móvil de origin/master; `leones_submodule_commit` describe el pin independiente y revisado. No deben ser necesariamente iguales.
- Upstream actual: `c406f4367e19bea7930e7f74e1984c9acc6d44bf`.
- Fork `master`: `9a080f44b503c64f66c84a6274b9d9ee5d5b09d5`, **3 commits detrás** de upstream.
- Gitlink LEONES: `76f186df71a41abb3ee20fffedee31ca5dbc7d9f`. Se mantiene deliberadamente en el último pin limpio revisado; no se avanza a la rama instrumentada.
- La diferencia upstream desde el pin 76f186df abarca 14 commits y 75 archivos; hay solapamientos con graph/context, CPU y CUDA. No hacer fast-forward ni rebase ciego.

### PRs nativas del fork y elección de integración

- [llama.cpp #1](https://github.com/robertosantosx2/llama.cpp/pull/1): contrato/sink, request, graph, sync, MoE y KV. CPU/servidor y checks generales pasan; CUDA, Vulkan, ROCm, Metal y otros runners siguen queued.
- [llama.cpp #2](https://github.com/robertosantosx2/llama.cpp/pull/2): backend/allocaciones/transferencias CUDA. CUDA e HIP pasan; MUSA falla en descarga de dependencias externas antes de compilar; varios self-hosted siguen queued.
- [llama.cpp #3](https://github.com/robertosantosx2/llama.cpp/pull/3): workers CPU. Tests CPU y checks básicos pasan; la mayoría de runners backend y Models Backend Check siguen queued.
- Las PRs #1 → #2 → #3 siguen abiertas y en borrador; sus bases son antiguas y necesitan rebase/revisión contra upstream actual antes de merge.
- La PR acumulativa [llama.cpp #6](https://github.com/robertosantosx2/llama.cpp/pull/6) es una implementación paralela sobre la base posterior del fork. Comparte archivos con #1–#3, pero los historiales y algunos blobs difieren (sink, event header, CUDA, CPU y server); KV/MoE comparten blobs. No fusionar ambas rutas sin reconciliar el código para evitar duplicar sondas.
- Decisión pendiente: revisar semántica y cobertura de ambos candidatos, escoger una única pila canónica y cerrar la alternativa solo cuando la integración elegida esté aceptada. MUSA y los runners queued se clasifican explícitamente, no como verdes.

### Contrato JSONL productor ↔ importadores LEONES

- El sink nativo de RC1 emite actualmente `schema_version=1.0`, `source=llama.cpp`, campos unsigned de evento y `sink_summary` final; puede incluir `correlation_token`, `attribution_level` y `clock_domain` opcionales.
- `scripts/nepenthes_llama_trace_import.py` acepta ese contrato 1.0 y los campos opcionales de correlación/reloj; comprueba balance de token, resumen final, pérdidas, errores y SHA-256 sin modificar el JSONL original.
- `scripts/nepenthes_nsys_import.py` admite además el contrato tipado 1.1 del importador emparejado y preserva `raw_json` y metadatos typed. No confundir el soporte 1.1 del importador emparejado con la versión que emite hoy el sink RC1.
- La antigua PR #176 queda funcionalmente superada por el importador actual; el código, workflow y tests de [PR #180](https://github.com/robertosantosx2/LEONES/pull/180) ya son idénticos a los blobs de `main`. La guía se conserva en [LLAMA-TRACE-IMPORT.md](../../docs/subprojects/NEPENTHES/LLAMA-TRACE-IMPORT.md).

### Estado de PRs LEONES de integración

- [PR #174](https://github.com/robertosantosx2/LEONES/pull/174) fue sustituida por la PR limpia #206 para no arrastrar una cadena de bases antiguas que ya está integrada por otras vías.
- #177 y #179 son documentación apilada sobre esa antigua rama. Sus gates y política se consolidan aquí y en el roadmap canónico; sus commits no se fusionan sin rebase ni duplicación.
- No se ha actualizado el gitlink al runtime instrumentado. No se ha compilado en el MSI, no se ha ejecutado C07, no existe captura Nsight nueva y C08 no está medido.


### Auditoría recursiva de Tandem.cpp — 2026-11-19

Se recorrió el árbol completo de LEONES (`main`, 1.783 archivos; árbol no truncado), se revisaron los archivos del subárbol `research/moe/tandem.cpp`, scripts/tests/migraciones NEPENTHES y la PR de instrumentación en el repositorio Tandem.cpp. La sección 3.3 anterior recoge la implementación, su cobertura, la evidencia CI y los límites de aceptación encontrados. La auditoría confirma que el directorio `research/moe/tandem.cpp` de LEONES es un snapshot de procedencia y del parche base, mientras que la implementación activa del hook/sink y del aplicador de sondas vive en `robertosantosx2/tandem.cpp`, PR #1. No deben confundirse ambas capas.
