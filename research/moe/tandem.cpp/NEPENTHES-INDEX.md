# NEPENTHES — documento maestro único: plan, estado y motores

> **Fuente única de verdad del proyecto.** Este documento reúne el estado global, la arquitectura, las prioridades, los gates de aceptación y el plan/estado de cada motor de inferencia. Toda actualización de estado debe reflejarse aquí. Los documentos especializados enlazados son anexos técnicos, contratos o expedientes de evidencia; no mantienen un roadmap paralelo ni prevalecen sobre este documento.

**Última actualización:** 2026-11-20.
**Estado global:** el contrato común multi-motor #207 está aceptado en `main` mediante [PR #210](https://github.com/robertosantosx2/LEONES/pull/210); el registry cerrado incluye `llama.cpp`, `tensorfold` y `tandem.cpp`. llama.cpp [PR #10](https://github.com/robertosantosx2/llama.cpp/pull/10) fue fusionada mediante merge commit `d4d0b9eeb2bd0035f525a90aefed111e5d74edcb`, tras workflow exacto `44682285336` con CPU/CUDA success, importer LEONES y checks generales aplicables Ubuntu/Windows/arm64/CUDA; MUSA falló durante instalación de dependencias y no ejecutó su build, por lo que no se declara matriz upstream completa verde. La aceptación de llama.cpp cubre contrato/host tests/importer y compilación CPU/CUDA, no runtime GPU/Nsight, C07/C08 ni overhead. Tandem.cpp PR #1–#5 y LEONES #218/#219 están fusionadas; el productor NVTX batch fue fusionado en [Tandem.cpp PR #7](https://github.com/robertosantosx2/tandem.cpp/pull/7), merge commit `7c4300eb754d94737c6aa8d7ffa0077aac7ddcb9`, tras workflow exacto `44682021976` con `trace-smoke` y `cuda-compile` SM86 success. La instrumentación es opt-in, disabled por defecto, delimita el decode batch en el queue worker y preserva token explícito; importer mantiene atribución `windowed`, many-to-many y no causal. LEONES issue #212 sigue abierta para validar end-to-end con captura física y completar correlación request/worker/batch/CUDA; no cerrar ni declarar causalidad por la mera compilación. TensorFold host-only está aceptado mediante TensorFold PR #6 y LEONES #217/#220; no implica CUDA/NVTX/Nsight, C07/C08 ni overhead. Los gates remotos de compilación de llama.cpp y Tandem están cerrados. El 2026-11-20 se ejecutó en MSI un smoke CUDA de llama.cpp con JSONL y Nsight Systems en la misma ejecución: 14.646 eventos drenados, 0 descartados, 0 errores de escritura, calibraciones de reloj start/end, 2 filas en `NVTX_EVENTS` y actividad CUDA API/kernel/memcpy observada. La inspección posterior confirmó que las dos filas NVTX son `nepenthes.request.start/end token=1 request=1`, en el mismo `globalTid`, y coinciden por `(scope, token, phase)` con los dos `nvtx_marker` JSONL y sus `request_start/end` (`request_id=1`, `correlation_token=1`, `attribution_level=exact`). Aplicando el algoritmo existente del importer (midpoint de `value0/value1`), los offsets `Nsight-host` son -106184657289381 ns y -106184657366718 ns; la diferencia observada es -77337 ns en 642891129 ns (−120,30 ppm), con incertidumbre máxima de semibracket de 80311 ns. Los intervalos de offset permitidos por ambos brackets se solapan en 2764 ns. Esto confirma la identidad de los marcadores y una primera calibración compatible con los brackets, pero la muestra es corta y no sustituye el import emparejado real ni una caracterización robusta de deriva. C08 tampoco está medido. No hay aceptación física C07/C08 aún.

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
| Contrato común multi-motor | Integrado en main por [PR #210](https://github.com/robertosantosx2/LEONES/pull/210), merge `fcaf170`; issue [#207](https://github.com/robertosantosx2/LEONES/issues/207) cerrada; 8 checks verdes en HEAD sincronizado `73c7cb9` | Mantener regresiones del contrato compartido |
| llama.cpp | PR #10 fusionada en `d4d0b9e`; workflow exacto CPU/CUDA e importer LEONES pasaron; checks generales aplicables Ubuntu/Windows/arm64/CUDA pasaron. MUSA dependency setup falló y su build se omitió | Mantener aceptación remota; MSI C07/C08: validar NVTX/Nsight y overhead |
| TensorFold 1.2.10 | Host-only adapter accepted: TensorFold PR #6 merged; LEONES PR #217/#220 and five cross-repo checks passed | Mantener como aceptado host-only; futuras sondas CUDA/NVTX y C07/C08 solo tras priorización explícita |
| tandem.cpp (distribución patch-based sobre llama.cpp) | PR #1–#5 y PR #7 fusionadas; producer NVTX opt-in aceptado tras CI exacta `44682021976` (`trace-smoke` + CUDA SM86). Importer permanece `windowed`, many-to-many y no causal | MSI C07/C08; issue #212 sigue abierta hasta validar end-to-end |
| Otros motores | No hay conector aceptado registrado | Incorporar solo mediante el contrato común y una fila de estado/evidencia |

### Orden de trabajo vigente
1. **Completar validación física MSI — C07/C08 para llama.cpp y Tandem.cpp.** Los gates remotos exactos están cerrados: llama.cpp PR #10 merge `d4d0b9e`, Tandem.cpp PR #7 merge `7c4300e`. Para llama.cpp ya existe un smoke CUDA+JSONL+Nsight del 2026-11-20 con actividad GPU y dos filas NVTX; falta validar el contenido/token de los marcadores e importar el par con calibración host↔Nsight. Después ejecutar C07 end-to-end y C08 con al menos tres pares baseline/instrumented. Repetir la cadena equivalente para Tandem.cpp. Conservar artefactos, manifiestos, hashes y límites de atribución `windowed`.
2. **LEONES issue #212 — validar correlación end-to-end.** La PR #7 añade producer NVTX, pero no demuestra por sí misma el token a través de captura Nsight/CUPTI ni ownership causal por request.
3. **Mantener aceptación remota llama.cpp/Tandem/TensorFold** sin expandirla más allá de los gates demostrados.

## 3. Estado y plan por motor/

### 3.1 llama.cpp

**Estado remoto 2026-11-20:** [PR #10](https://github.com/robertosantosx2/llama.cpp/pull/10) fue fusionada el 2026-11-20 mediante merge commit `d4d0b9eeb2bd0035f525a90aefed111e5d74edcb`, desde HEAD `da0fa44d6445f692b2fdb281d2c95210aeea75ac` sobre base `c406f4367e19bea7930e7f74e1984c9acc6d44bf`. El workflow exacto [NEPENTHES runtime trace #44682285336](https://github.com/robertosantosx2/llama.cpp/actions/runs/44682285336) terminó success: `trace-and-cpu-build` y `cuda-compile`. Los checks generales Ubuntu/Windows/arm64 y CUDA consultados también pasaron; MUSA falló durante instalación de dependencias y el build nativo fue omitido, sin evidencia de fallo de código NEPENTHES/CUDA. El contrato task-ID 0→request-ID no-cero quedó corregido en `da0fa44`, raw ID preservado y tests -1/0/41/INT64_MAX; el importer compartido LEONES pasó. Aceptación limitada a contrato/host tests/importer y compilación CPU/CUDA; no hay evidencia de ejecución GPU/Nsight, C07 ni overhead.

**Evidencia física inicial MSI — 2026-11-20 (smoke, no aceptación C07):** En el checkout independiente `llama.cpp-pr10`, HEAD `d4d0b9eeb2bd0035f525a90aefed111e5d74edcb`, se compiló `llama-server` CUDA SM86 y se ejecutó MiniCPM5-2B-Q4_K_M con `NEPENTHES_TRACE_JSONL` y Nsight Systems (`cuda,nvtx,osrt`) en la misma sesión. Artefactos locales generados: `nepenthes-c07-llama-smoke.jsonl` (14.647 líneas), `.nsys-rep` y SQLite. El resumen JSONL registra 14.646 eventos drenados, `dropped_events=0`, `write_errors=0`, además de `clock.calibration.start/end`; SQLite contiene `NVTX_EVENTS` con 2 filas. `nsys stats` mostró actividad CUDA API, kernels GPU y transferencias HtoD/DtoH. El servidor completó una petición de 17 tokens de prompt y 48 generados; el resultado de texto fue repetitivo y esta ejecución no sirve como benchmark C08. La fuente del HEAD contiene llamadas `nvtxMarkA` en el inicio y fin del lifecycle de `server_task`, con mensajes `nepenthes.request.start/end token=… request=…`; la inspección posterior confirmó los mensajes exactos `nepenthes.request.start/end token=1 request=1`, ambos en `globalTid=283216116290916`, y su correspondencia con JSONL `nvtx_marker`/`request_start`/`request_end` bajo `request_id=1`, `correlation_token=1`, `attribution_level=exact`. La calibración midpoint del importer produce offsets Nsight-host de -106184657289381 ns y -106184657366718 ns (drift observado -77337 ns / -120,30 ppm en 642891129 ns; semibracket máximo 80311 ns); los intervalos de offset de ambos brackets se solapan en 2764 ns. Esta muestra breve confirma compatibilidad, no una caracterización robusta de deriva. **Estado:** marcadores físicos y correspondencia de identidad confirmados; C07 sigue pendiente de importar los artefactos reales mediante el importer compartido, verificar DB/manifest/hashes/cobertura y ejecutar los checks end-to-end. C08 pendiente de tres o más pares baseline/instrumented y umbral de overhead. No atribuir kernels a requests por proximidad temporal.

**Ya conseguido:** contrato de eventos/sink, puente CPU, instrumentación NVTX opt-in y port de cambios NEPENTHES sobre upstream actual en PR #10. Los históricos RC1/#6 y #1–#3 son candidatos/antecedentes, no deben tratarse como línea aceptada ni fusionarse sin reconciliación.

**Siguientes pasos:**
- [x] Consultar CI exacta del HEAD `0f3fa24`: workflow propio `44616676979` con `trace-and-cpu-build` + `cuda-compile` en éxito, NVTX v3 detectado y build CUDA SM86 completado; CI general self-hosted `gpu-cuda` y otros jobs GPU cancelados. No declarar runtime GPU ni C07.
- [x] Revisión remota registrada en PR #10 (review `5987953833`): identidad aclarada como lifecycle de `server_task` (no HTTP request 1:1); sink cambiado a creación exclusiva; test verifica rechazo sin truncar/append; workflow incorpora importación cross-repo y regresiones LEONES.
- [x] Corregir metadata de `cuda.device_copy_async_attempt`: clasificar same-device/cross-device mediante physical device IDs, no por desigualdad de backend handles.
- [x] Cerrar contrato común LEONES #207 y comprobar compatibilidad del source `tandem.cpp`: PR #210 fusionada; registry explícito y fixture positivo/negativo incluidos.
- [x] Conseguir evidencia remota de compilación CUDA/NVTX del HEAD exacto: workflow propio `44616676979`, `cuda-compile` success y NVTX v3 detectado.
- [x] Añadir gate cross-repo que importe el JSONL generado mediante `scripts/nepenthes_llama_trace_import.py` y ejecute las regresiones del importer LEONES, fijado a commit `c2151bba23fb4a9a3d746e696283d4e599f2e332`.
- [x] Revisión de contrato adicional: review `5988039065` detectó colisión task ID 0/request_id 0; corregido con `request_id_from_task_id()` y fixtures de -1/0/41/INT64_MAX (commits `364ad1e`, `dd9a895`, `da0fa44`).
- [x] Ejecutar `NEPENTHES runtime trace` sobre HEAD `da0fa44d6445f692b2fdb281d2c95210aeea75ac`: run `44682285336`, `trace-and-cpu-build` y `cuda-compile` success; importer cross-repo pasó.
- [x] Verificar checks generales aplicables Ubuntu/Windows/arm64/CUDA; anotar MUSA failure y targets exóticos queued como matriz no completamente verde.
- [x] Revisión final de diff/contrato; PR #10 fusionada en `d4d0b9e` tras gates exactos. Mantener separados C07/C08 físicos.
- [ ] Merge solo tras aceptación; actualizar el gitlink LEONES después de la aceptación.
- [ ] MSI: build Linux/CUDA, C07 real NVTX+Nsight y C08 emparejado; conservar artefactos y métricas.

**Límite de aceptación:** la CI remota no demuestra overhead, cobertura real ni correlación con CUPTI; hacen falta C07/C08 físicos.

### 3.2 TensorFold 1.2.10

**Estado remoto 2026-11-20:** Contrato/auditoría publicados mediante TensorFold PR #5 (merge `9355b0a`). El conector runtime host-only fue fusionado en [TensorFold PR #6](https://github.com/robertosantosx2/TensorFold/pull/6), merge `50f1a34cbc1f111fa6e7afbedc199eee0d8643e5`, para [issue #3](https://github.com/robertosantosx2/TensorFold/issues/3), completada tras la aceptación. El HEAD probado `c258ec930b4ea8f0d0bc785a984d2114bf041fb9` pasó los cinco checks del workflow cross-repo `tensorfold-host` en LEONES [PR #217](https://github.com/robertosantosx2/LEONES/pull/217) antes de ambos merges. La aceptación cubre exclusivamente el conector host-only y sus fixtures/importación; no implica CUDA/NVTX/Nsight, C07/C08 ni overhead.

**Contrato común aceptado:** [LEONES #207](https://github.com/robertosantosx2/LEONES/issues/207) quedó cerrado tras fusionar [PR #210](https://github.com/robertosantosx2/LEONES/pull/210) en `main`, merge commit `fcaf17005f7771c2521fc07387409a79c47f1b7b`. HEAD final pre-merge `73c7cb9cd89648aa6cdb2fbae70f63c803760a7d`: 8/8 checks `completed/success`; 29 tests enfocados; suite completa **602 passed, 14 subtests passed**. El registry cerrado cubre `llama.cpp`, `tensorfold` y `tandem.cpp`, con perfiles `steady_clock`, límites unsigned, privacidad, correlación explícita y `sink_summary` final. TensorFold y Tandem.cpp requieren request_id no cero en request_start/request_end; eventos internos pueden usar cero. No hay importer TensorFold paralelo. El contrato común y el runtime TensorFold host-only están aceptados por separado: el validador compartido quedó integrado mediante LEONES PR #210; el conector runtime quedó integrado mediante TensorFold PR #6 y validado por LEONES PR #217. Esta aceptación no cubre captura GPU, NVTX/Nsight, correlación física ni overhead.

**Auditoría de fuente 1.2.10:** se revisaron `server/http_conn.zig`, `server/routes.zig`, `server/server.zig`, `server/request_journal.zig`, `cuda/launch.zig`, `cuda/graph.zig`, `cuda/stream.zig`, `cuda/memory.zig`, `cuda/driver.zig` y `cuda/abi.zig`. La identidad lógica debe nacer por petición en `routes.dispatch`, no por conexión; keep-alive reutiliza conexiones y los IDs existentes son IDs de respuesta. El journal puede contener contenido privado y no es un sink. CUDA expone límites host para launch/graph/memoria/copias/errores, pero launch/graph return solo demuestran submission; los contadores de memoria son agregados. No añadir sincronizaciones para telemetría. En el corte de esta auditoría no se encontró productor/sink NEPENTHES runtime en los archivos auditados; la implementación host-only posterior quedó aceptada mediante TensorFold PR #6.

**Secuencia obligatoria:**
1. [x] Revisar y aceptar LEONES #207 mediante PR #210: merge `fcaf170`; registry cerrado `llama.cpp`/`tensorfold`/`tandem.cpp`; CI host-only y fixtures positivos/negativos superados.
2. [x] Completar ATC overlap previo desde el checkout TensorFold correcto: `complete=true`, `limitations=[]`, `overlaps=[]`, `worktrees=3`, `worktreeOverlaps=[]`. El scan precede a la rama de implementación y no se presenta como ejecución posterior.
3. [x] Implementar y fusionar el adaptador host-only mediante TensorFold PR #6, merge `50f1a34`; opt-in, no-op disabled, sink acotado, IDs por request, privacidad, keep-alive y lifecycle de trabajo detached; sin sondas CUDA.
4. [x] Validar el HEAD exacto `c258ec930b4ea8f0d0bc785a984d2114bf041fb9`: cinco checks `completed/success` del workflow cross-repo `tensorfold-host` en LEONES PR #217, incluyendo formato Zig, pruebas host/security y fixtures positivo, source-mismatch e incomplete a través del importer común.
5. [ ] Reconciliar llama.cpp PR #10 sobre upstream vigente; revisar semántica/diff y cerrar todos los checks relevantes, incluidos build CUDA/backend que actualmente están cancelados o no concluyentes.
6. [ ] Implementar y probar Tandem producer-side NVTX sobre la frontera exacta `BatchScope`, con NVTX opcional y RAII; no inferir request→kernel por proximidad.
7. [ ] Solo después de cerrar los gates remotos, planificar C07/C08 físicos en MSI. No actualizar gitlink ni declarar aceptación GPU antes de los gates correspondientes.

**Límite actual:** El conector TensorFold host-only está aceptado tras merge y CI exacta del HEAD fijado. No hay aceptación CUDA/NVTX/Nsight, captura física, C07/C08 ni overhead. El gitlink no se actualiza hasta que los gates de integración correspondientes estén cerrados.

### 3.3 tandem.cpp — distribución patch-based sobre llama.cpp

**Naturaleza:** `robertosantosx2/tandem.cpp` es una distribución patch-based sobre llama.cpp, no un motor independiente. Su identidad de evidencia es `source=tandem.cpp`; LEONES mantiene el runner, contrato, importadores, manifiestos y aceptación. La instrumentación activa vive en el repositorio Tandem.cpp; `research/moe/tandem.cpp` de LEONES conserva snapshot/procedencia y documentación subordinada.

**Estado remoto auditado — 2026-11-20:**
- [Tandem.cpp PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1) está fusionada en `fcf8c837b05e0c80c3539d6c1d0c317ba2f40456`. HEAD de implementación validado por CI: `170d3af9918e2cdf3b5c72f6bb61ab0c3b7b6b52`. Implementa hook C++17, timestamps monotónicos, scoped durations, sink JSONL asíncrono con cola bounded de 8192 entradas, writer separado, shutdown seguro y aplicador determinista de sondas.
- [Tandem.cpp PR #2](https://github.com/robertosantosx2/tandem.cpp/pull/2) está fusionada en `ecfbae9fb23dae8904ccaa981ee115f9b17c56bd`; añade la guía inglesa y navegación bidireccional entre documentación española/inglesa, sin cambios runtime.
- [Tandem.cpp PR #3](https://github.com/robertosantosx2/tandem.cpp/pull/3) está fusionada en `e2bf8fccab05a0ffe87f526a77606e3f941d172d`. Reserva `request_id=0` para eventos no correlacionados y transforma task IDs del servidor mediante `request_id_from_task_id()`: task ID 0 pasa a request ID 1, preservando el ID original en `value0`. La corrección se aplica a eventos server request start/end y routing; no atribuye IDs a workers, CUDA asíncrono ni eventos de shared batch sin identidad segura.
- Dependencia cerrada en orden: #1 aporta la instrumentación; #3 corrige la semántica de identidad sobre esa base; #2 añade la guía inglesa. Las PR #1/#2/#3 están fusionadas; PR #4 y #5 también quedaron aceptadas posteriormente. PR #6 es especificación documental; PR #7 implementa el productor runtime NVTX y ya está fusionada mediante merge `7c4300eb754d94737c6aa8d7ffa0077aac7ddcb9`.

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
- La validación del bundle (6.569 eventos fusionados) es distinta de la importación emparejada. Esta última sí quedó demostrada posteriormente por la validación final de LEONES #153: dos capturas emparejadas preservadas (PR1 y PR3), cada una con 6.569 eventos del motor y 24.211 actividades Nsight importadas.
- La PR #3 reportó inicialmente un overflow al importar unsigned de 64 bits a `SQLite INTEGER`. Ese diagnóstico quedó obsoleto tras LEONES #153: el importer actual convierte valores uint64 al dominio signed de SQLite mediante complemento a dos y conserva el valor original en `raw_json`. La prueba `test_import_converts_all_jsonl_uint64_integer_fields` cubre `2^64−1`; `test_import_rejects_integer_outside_uint64_range` rechaza `2^64`. La validación final de #153 importó dos capturas emparejadas (PR1/PR3), cada una con 6.569 eventos y 24.211 actividades, con integridad SQLite correcta.
- La antigua captura Qwen3.5-4B CPU-only con 3.683 eventos y todos los request-window IDs en cero se conserva como evidencia histórica independiente; no debe mezclarse con la nueva captura de #3.

**Pendiente / plan de aceptación:**
- [x] Revisar diffs/dependencias y fusionar en orden: #1 runtime (`fcf8c83`) → #3 request-ID correction (`e2bf8fc`). CI exacto de ambos HEADs pasó; las dos PR quedaron cerradas como merged. #2 documentación inglesa se retargeteó a `main` y fusionó (`ecfbae9`).
- [x] Importación emparejada y uint64→SQLite: resuelta y validada en LEONES #153 con dos capturas PR1/PR3; pruebas de límite uint64 y rechazo fuera de rango; integridad SQLite correcta. No duplicar esta corrección.
- [x] Importación emparejada real demostrada por LEONES #153: dos bundles PR1/PR3, cada uno con 6.569 eventos del motor y 24.211 actividades Nsight; hashes/procedencia e integridad SQLite validados.
- [x] Cerrar Tandem.cpp PR #4: `sink_summary` final, contadores drained/drop/errors, validación del JSONL producido por `import_trace(source="tandem.cpp")` y barrera de callbacks en vuelo del header aplicado. Merge `ccc92a2`; CI run `44630264984` pasó `trace-smoke` y `cuda-compile` (SM86).
- [x] Aceptar Tandem.cpp [PR #5](https://github.com/robertosantosx2/tandem.cpp/pull/5), squash `7b2da756c442251639f12047e8df00d79773362b`: token por decode slice, evento `server.batch_member` por slot/request, propagación host a graph + `job_layer`/`la_job`/`fh_job`, token JSONL `exact/steady_clock` y fixture many-to-many aceptada por importer. CI exacta HEAD `d27f295`: `trace-smoke` y CUDA SM86 `cuda-compile` pasaron en run `44635442942`.
- [x] Aceptar LEONES [PR #218](https://github.com/robertosantosx2/LEONES/pull/218), merge `705db222ca3d535663870995852b09a51115215c`: importer request/batch NVTX scope, columnas de atribución batch y vista many-to-many; CI exacta HEAD `ce9f4ab` passed 120 importer tests y V1 regression 604 + 14 subtests.
- [x] Aplicar guard conservador de host-thread en atribución batch del importer: LEONES [PR #219](https://github.com/robertosantosx2/LEONES/pull/219), merge `53010c7e7b7471d429fd67b96b83537a8349ba15`. Exact HEAD `35fdb569` pasó importer/AIPerf, Contract Tests y RC3 Release Gate. La atribución batch exige coincidencia process + thread + contención temporal + ventana única; mismatched/missing thread identity queda explícitamente no atribuida. Esto es un filtro conservador, no prueba causal de ownership GPU.
**Seguimiento remoto actualizado (2026-11-20):** Tandem.cpp [PR #6](https://github.com/robertosantosx2/tandem.cpp/pull/6), draft, conserva la especificación. La implementación producer-side NVTX está fusionada mediante [PR #7](https://github.com/robertosantosx2/tandem.cpp/pull/7), merge commit `7c4300eb754d94737c6aa8d7ffa0077aac7ddcb9`, desde HEAD `6c5b252ee41949ed5ea57d02ba443feb248c30f6`. El workflow exacto [44682021976](https://github.com/robertosantosx2/tandem.cpp/actions/runs/44682021976) terminó success: `trace-smoke` y `cuda-compile` SM86 pasaron; tests C++17, NVTX disabled/enabled, sink JSONL, validación LEONES y aplicación de runtime patches correctos. La revisión confirmó NVTX opt-in, resolución runtime sin dependencia de link-time, RAII `BatchNvtxScope` dentro del queue worker, token por decode slice y membresía validada antes de emitir `server.batch_member`. La PR #7 acepta producer markers y compilación, no runtime NVTX/Nsight, causalidad ni overhead. Issue LEONES #212 permanece abierta para la captura emparejada end-to-end y la validación física C07/C08.

- [x] Inspeccionar logs de los dos fallos y corregir el aplicador como transformación idempotente.
- [x] Añadir `workflow_dispatch` y push para la rama `feat/**`.
- [x] Repetir el intento 2 del run exacto #44682027808: tests, NVTX, sink e importer superados.
- [x] Confirmar aplicación de runtime patches sobre el pinned llama.cpp: run `44682021976`.
- [x] Reejecutar y pasar `cuda-compile` SM86 sobre el mismo HEAD: run `44682021976`.
- [x] Revisar `BatchNvtxScope`: RAII dentro del queue worker alrededor de la llamada `llama_process()`; no se añade ninguna sincronización explícita. No afirmar una frontera de sincronización más específica que la verificada por el código.
- [x] Completar revisión final y fusionar PR #7: merge `7c4300e`; CI exacta `44682021976` verde.
- [ ] Ejecutar C07 paired NVTX+Nsight/CUPTI en MSI y validar el token end-to-end; mantener atribución `windowed` hasta que haya evidencia suficiente.
- [ ] Ejecutar C08 con baseline y tratamientos repetidos; medir overhead con umbrales del INDEX.
- [ ] Cerrar issue LEONES #212 solo tras evidencia física y aceptación de los gates correspondientes.
- [ ] Después de aceptación remota, planificar C07/C08 físicos en MSI; atribución `windowed`, no causal.

**Límite de aceptación:** instrumentación, CI de #1/#3/#4, inferencia real Qwen3.5-4B y dos importaciones emparejadas históricas están demostradas; el contrato del productor (`sink_summary`) y el shutdown seguro quedaron aceptados en PR #4. La correlación host batch está aceptada en Tandem PR #5 (`7b2da75`); importer batch attribution requiere además match process/thread (PR #219), con nivel `windowed`, nunca causal/exact GPU ownership. El soporte importer batch NVTX y vista many-to-many están integrados en LEONES PR #218 (fixtures sintéticos); aún no hay productor NVTX batch en Tandem ni captura física C07. No hay correlación GPU aceptada, cobertura completa de sondas ni overhead C08. Tandem sigue siendo una distribución derivada de llama.cpp, no un motor independiente a efectos de duplicar colectores/importadores.

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
