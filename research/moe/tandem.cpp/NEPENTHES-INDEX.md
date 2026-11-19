# NEPENTHES — índice de implementación, validación y evidencias

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
