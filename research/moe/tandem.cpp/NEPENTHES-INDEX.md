# NEPENTHES — documento maestro único: plan, estado y motores

> **Fuente única de verdad del proyecto.** Este documento reúne el estado global, la arquitectura, las prioridades, los gates de aceptación y el plan/estado de cada motor de inferencia. Toda actualización de estado debe reflejarse aquí. Los documentos especializados enlazados son anexos técnicos, contratos o expedientes de evidencia; no mantienen un roadmap paralelo ni prevalecen sobre este documento.

**Última actualización:** 2026-11-19.
**Estado global:** infraestructura de observabilidad LEONES en evolución; integración llama.cpp en reconciliación/CI remota; implementación host-only del contrato multi-motor #207 en PR #210 con todos los checks remotos verdes y revisión pendiente; TensorFold supera el gate ATC de solapamientos y espera aceptación/revisión de #207; sin aceptación física nueva en MSI para las integraciones en curso.

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
| Contrato común multi-motor | Implementación host-only en [PR #210](https://github.com/robertosantosx2/LEONES/pull/210), issue [#207](https://github.com/robertosantosx2/LEONES/issues/207); 10 checks remotos verdes en HEAD `3602f96`, revisión pendiente | Revisión de semántica/compatibilidad y aceptación; no fusionar antes de review |
| llama.cpp | Integración activa; [PR #10](https://github.com/robertosantosx2/llama.cpp/pull/10) en draft/CI según último estado documentado | Cerrar CI/revisión, aceptar contrato y luego C07/C08 en MSI |
| TensorFold 1.2.10 | Contrato documentado en fork; [issue #1](https://github.com/robertosantosx2/TensorFold/issues/1) reclamada; depende de LEONES #207 | Aceptar validador común; después adaptador host-only y CI |
| tandem.cpp (distribución patch-based sobre llama.cpp) | PR #1 runtime y PR #3 fix de request IDs abiertas; PR #2 documental; CI de #1/#3 verde; inferencia Qwen3.5-4B y bundle de 6.569 eventos validados; importación emparejada bloqueada por overflow uint64→SQLite INTEGER y correlación interna parcial | Revisar #1/#3, reproducir/corregir overflow en importer actual, completar importación emparejada y correlación explícita; después C07/C08 |
| Otros motores | No hay conector aceptado registrado | Incorporar solo mediante el contrato común y una fila de estado/evidencia |

### Orden de trabajo vigente
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

**Dependencias duras:** [LEONES #207](https://github.com/robertosantosx2/LEONES/issues/207) sigue abierta y en revisión mediante [PR #210 draft](https://github.com/robertosantosx2/LEONES/pull/210). La PR extrae `scripts/nepenthes_trace_envelope.py`, registra explícitamente `llama.cpp` y `tensorfold`, conserva `steady_clock` como dominio permitido por ambos contratos, añade `--source tensorfold`, refuerza límites unsigned y valida tipos JSON malformados. Incluye fixtures positivos/negativos y documentación del envelope común en `docs/subprojects/NEPENTHES/TRACE-ENVELOPE.md`; no hay importador TensorFold paralelo. HEAD actual `3602f96fa4907e0885941432b4f6a0a53c2d71d1`. Evidencia remota del HEAD exacto: 10 check runs, todos `completed/success`, incluyendo `trace-import-tests` (run `44625063889`) y la regresión completa `runtime-contracts`; PR `mergeable=true`, `mergeable_state=clean`. PR #210 está lista para revisión (`draft=false`), abierta y sin merge. La última consulta a GitHub tras la actualización del INDEX reportó `mergeable=true` y `mergeable_state=clean`. CI host-only no equivale a runtime TensorFold, GPU capture, correlación ni overhead aceptados. Diagnóstico local aportado el 2026-11-19: el checkout correcto es `/home/ssantos/tensorfold`, con remotos `fork=https://github.com/robertosantosx2/TensorFold.git` y `origin=https://github.com/ashhart/TensorFold.git`. Se descargó `fork/nepenthes/tensorfold` y se creó la rama local de seguimiento `nepenthes/tensorfold`; el usuario ejecutó ATC desde ese checkout. **Resultado ATC concluyente:** `complete=true`, `limitations=[]`, `changedFiles=2`, `myPullRequests=[]`, `overlaps=[]`, `worktrees=3`, `worktreeOverlaps=[]`. El gate de solapamientos queda superado: ATC completó el análisis y no reportó solapamientos en los tres worktrees examinados. Se conserva `changedFiles=2` como dato reportado, sin inferir su significado ni declarar el árbol `clean` por ese campo. No hay PR propia detectada. La dependencia #207 continúa siendo el gate técnico previo al runtime TensorFold.

**Auditoría de fuente 1.2.10:** se revisaron `server/http_conn.zig`, `server/routes.zig`, `server/server.zig`, `server/request_journal.zig`, `cuda/launch.zig`, `cuda/graph.zig`, `cuda/stream.zig`, `cuda/memory.zig`, `cuda/driver.zig` y `cuda/abi.zig`. La identidad lógica debe nacer por petición en `routes.dispatch`, no por conexión; keep-alive reutiliza conexiones y los IDs existentes son IDs de respuesta. El journal puede contener contenido privado y no es un sink. CUDA expone límites host para launch/graph/memoria/copias/errores, pero launch/graph return solo demuestran submission; los contadores de memoria son agregados. No añadir sincronizaciones para telemetría. No se encontró productor/sink NEPENTHES runtime en los archivos auditados.

**Secuencia obligatoria:**
1. [ ] Revisar y aceptar LEONES #207 mediante PR #210: compatibilidad llama.cpp, registry cerrado, fixtures llama.cpp/TensorFold y CI del HEAD exacto verde.
2. [ ] Completar ATC overlap desde el checkout TensorFold correcto; exigir `complete=true` y revisar todos los resultados `conflicts/clean/unknown`. El resultado previo `workingTreeUnavailable` no supera el gate.
3. [ ] Abrir PR pequeña del adaptador host-only: opt-in, no-op real cuando disabled, sink acotado, IDs/run identity, privacidad y metadata namespaced; sin sondas CUDA.
4. [ ] Añadir pruebas host para concurrencia, keep-alive/múltiples peticiones, lifecycle balanceado, sink_summary final, drops/errors y camino disabled; validar fixtures con el importador común.
5. [ ] Separar futuras sondas CUDA por áreas ATC (launch/graph; memoria/copias; sync/errores) y después NVTX/Nsight con tokens explícitos.
6. [ ] Solo después de aceptación host/CI planificar validación física y overhead; MSI no es necesario en esta fase.

**Límite actual:** TensorFold está en fase de contrato/auditoría, no de implementación runtime. No declarar CI, pruebas, captura, correlación u overhead aceptados. No abrir PR runtime hasta superar ambos gates 1 y 2.

### 3.3 tandem.cpp — distribución patch-based sobre llama.cpp

**Naturaleza:** `robertosantosx2/tandem.cpp` es una distribución patch-based sobre llama.cpp, no un motor independiente. Su identidad de evidencia es `source=tandem.cpp`; LEONES mantiene el runner, contrato, importadores, manifiestos y aceptación. La instrumentación activa vive en el repositorio Tandem.cpp; `research/moe/tandem.cpp` de LEONES conserva snapshot/procedencia y documentación subordinada.

**Estado remoto auditado — 2026-11-19:**
- [Tandem.cpp PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1), instrumentación principal, sigue abierta y sin merge. HEAD validado por CI: `170d3af9918e2cdf3b5c72f6bb61ab0c3b7b6b52`. Implementa hook C++17, timestamps monotónicos, scoped durations, sink JSONL asíncrono con cola bounded de 8192 entradas, writer separado, shutdown seguro y aplicador determinista de sondas.
- [Tandem.cpp PR #2](https://github.com/robertosantosx2/tandem.cpp/pull/2) contiene la guía de instrumentación; es documental y no añade runtime.
- [Tandem.cpp PR #3](https://github.com/robertosantosx2/tandem.cpp/pull/3), corrección complementaria apilada sobre #1, sigue abierta y sin merge. HEAD `2da6b222c2c663ebeeeb729e771930153cbabf17`. Reserva `request_id=0` para eventos no correlacionados y transforma task IDs del servidor mediante `request_id_from_task_id()`: task ID 0 pasa a request ID 1, preservando el ID original en `value0`. La corrección se aplica a eventos server request start/end y routing; no atribuye IDs a workers, CUDA asíncrono ni eventos de shared batch sin identidad segura.
- No se debe considerar #3 sustituta de #1: #1 aporta la instrumentación y #3 corrige la semántica de identidad sobre esa base. Ambas requieren revisión y merge coordinados; #2 es documentación.

**Cobertura instrumentada declarada por el código:**
- lifecycle de request/server, graph compute y sincronización;
- MoE cache/prefetch, jobs y workers CPU, publicación de resultados y espera del consumidor GPU;
- KV cache: allocation/teardown/clear/update, ubatch, cell reuse/release y secuencias;
- backend/CUDA device/pool/pinned-host allocation, free, OOM y fallback;
- spans host de submission H2D/D2H/2D/D2D/peer y dispatch por `ggml_op`.
Los spans host describen submission/dispatch, no ejecución GPU. Los kernels individuales y las actividades memcpy CUDA deben proceder de Nsight/CUPTI importado por LEONES. La lista de sondas instrumentadas no equivale a cobertura observada en una captura.

**CI y validación de software:**
- [Actions run #43654679693](https://github.com/robertosantosx2/tandem.cpp/actions/runs/43654679693), para HEAD #1 `170d3af...`, terminó `completed/success`: pruebas C++17 del hook/sink, concurrencia y shutdown, JSONL, aplicador determinista, build CPU y compilación CUDA llama-server para SM86. Es evidencia de CI/build, no de inferencia, cobertura completa ni overhead.
- [Actions run #43739051242](https://github.com/robertosantosx2/tandem.cpp/actions/runs/43739051242), para HEAD #3 `2da6b222...`, terminó `completed/success`: `trace-smoke` y `cuda-compile` pasaron.
- La PR #3 documenta además build CUDA local de llama-server sobre la base pinned, inferencia Qwen3.5-4B real y validación del bundle: 6.569 eventos fusionados, checksums y validación de eventos/informe HTML correctos. Esta evidencia de ejecución y bundle no debe confundirse con aceptación de importación emparejada LEONES.

**Identidad y correlación — evidencia de la captura asociada a #3:**
- 6.522 eventos del motor; exactamente 3 eventos tienen `request_id=1`: `server.request_start`, `server.task_slot` y `server.request_end`. Los tres conservan `value0=0`, el task ID original.
- Los otros 6.519 eventos conservan `request_id=0`; no se inventó correlación para CUDA ni workers.
- Por tanto, la corrección elimina la colisión del task ID cero y correlaciona el lifecycle/routing del servidor, pero **la correlación interna request → worker → CUDA/kernel sigue incompleta**. No usar proximidad temporal para suplirla.

**Captura Nsight e importación:**
- La ejecución real generó artefactos `.nsys-rep` y SQLite de Nsight además del JSONL del motor.
- La validación del bundle (6.569 eventos fusionados) demuestra integridad del paquete y del informe, pero no demuestra por sí sola que LEONES haya completado una importación emparejada JSONL + Nsight.
- La PR #3 reporta que la importación SQLite del flujo emparejado queda bloqueada por overflow al convertir valores unsigned de 64 bits a `SQLite INTEGER`. La importación Nsight-only ya integrada en LEONES (#153, según el estado del proyecto) no prueba que este caso concreto del flujo emparejado esté resuelto. Hay que reproducir el caso contra el importer actual de `main`, identificar el campo y añadir fixture de regresión antes de marcarlo resuelto.
- La antigua captura Qwen3.5-4B CPU-only con 3.683 eventos y todos los request-window IDs en cero se conserva como evidencia histórica independiente; no debe mezclarse con la nueva captura de #3.

**Pendiente / plan de aceptación:**
- [ ] Revisar los diffs y dependencias de #1 y #3 conjuntamente; mantenerlas abiertas hasta confirmar base/head, comentarios, CI del HEAD exacto y semántica. No fusionar ni cerrar ninguna alternativa sin revisión.
- [ ] Reproducir y corregir el overflow unsigned-64 → SQLite INTEGER en el importador emparejado actual de LEONES; añadir fixture que cubra límites unsigned y verificar integridad/foreign keys.
- [ ] Ejecutar importación real emparejada del JSONL y SQLite Nsight generados en la misma ejecución/RUN_ID; verificar manifiesto, hashes, tablas, pérdidas, errores y procedencia.
- [ ] Completar correlación solo mediante identidad explícita por job/batch/worker y tokens compartidos con la captura GPU, más calibración de reloj. Hasta entonces, mantener eventos internos sin correlación.
- [ ] Medir cobertura efectiva por sonda y pérdidas/errores del sink en ejecuciones representativas; no inferirla del inventario de probes.
- [ ] Ejecutar C07 (captura emparejada con IDs/calibración) y C08 (baseline/tratamientos repetidos y overhead) según los gates comunes. No solicitar MSI hasta cerrar los bloqueos remotos que puedan resolverse en GitHub.

**Límite de aceptación:** hay instrumentación implementada, CI verde en los HEAD citados y evidencia de una inferencia real Qwen3.5-4B con bundle validado y artefactos Nsight generados. No hay aceptación demostrada de importación emparejada, correlación robusta request-worker-CUDA-kernel, cobertura completa ni overhead C08. Tandem sigue siendo una distribución derivada de llama.cpp, no un motor independiente a efectos de duplicar colectores/importadores.

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
