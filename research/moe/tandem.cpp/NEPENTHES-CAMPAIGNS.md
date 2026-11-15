# NEPENTHES — campañas de validación y experimentación

**Language / Idioma:** [English version](NEPENTHES-CAMPAIGNS-EN.md) · [Versión en español](\research/moe/tandem.cpp/NEPENTHES-CAMPAIGNS.md)


**Corte:** 2026-11-15.  
**Regla:** una campaña solo se marca como completada para el alcance demostrado por sus artefactos. Compilar, ejecutar una inferencia, capturar Nsight e importar un par sincronizado son gates distintos.

## Resumen de campañas

| ID | Campaña | Estado | Evidencia / límite |
|---|---|---|---|
| C00 | Sondas MoE/runtime | Parcial / investigación previa | LEONES PR #147; probes de runtime/cache, scheduler, I/O, PSI, CPU y telemetría NVIDIA. No equivale a cobertura universal. |
| C01 | FAST PATH / CAPACITY PATH | Implementación documental/parcial | LEONES PR #149; plan de rendimiento y ejecución out-of-core e inspector SQLite Nsight. No acredita inferencia emparejada. |
| C02 | Contrato universal + sink JSONL | Implementado y CI | Tandem.cpp PR #1; contrato, sink concurrente y aplicación de sondas. |
| C03 | Instalador, CLI y paquete | Validación funcional básica completada | LEONES PR #152; doctor, self-test, smoke inocuo y propagación de exit code 23. |
| C04 | Importación histórica Nsight-only Qwen3.5-35B | Importada y auditada | 151.039 actividades, ocho familias CUPTI; SQLite íntegro. Fuente histórica sin JSONL emparejado. |
| C05 | Build CUDA instrumentado sobre base pinned | Completada | llama.cpp pinned `f5222f25c18da062ab2b8a2dbbfbf4feae398566`; parches Tandem + runtime + probes aplicados; llama-server CUDA sm_86 compilado. |
| C06 | Inferencia real con motor instrumentado | Completada para smoke CPU-only | Qwen3.5-4B Q4_K_M; 3.683 eventos motor, 3.117 dentro de petición y 49 eventos KV dentro de la ventana. Nsight desactivado. |
| C07 | Captura emparejada motor + Nsight | Pendiente | Una misma ejecución/RUN_ID, importación emparejada y correlación/clock mapping demostrados. |
| C08 | Rendimiento comparativo y recomendaciones | Pendiente | Baseline/control, repeticiones, overhead, bytes/latencias y métricas GPU. |

## C03 — CLI y envoltura de proceso

- Instalación user-space en `~/.local`, sin root.
- `nepenthes doctor` y `nepenthes self-test`: correctos.
- Smoke con proceso Python no instrumentado: exit code 0 y paquete verificado.
- Fallo controlado: el código 23 del hijo se propagó al padre y se conservaron hashes, eventos y HTML.

La aceptación con motor instrumentado se completa parcialmente en C06; falta completar el ciclo con Nsight y `nepenthes verify` sobre una captura emparejada.

## C04 — Qwen3.5-35B-A3B IQ2_XXS: Nsight histórico

Origen: `qwen35-correlated-20261114.sqlite`; import standalone, no emparejada con NEPENTHES.

- 151.039 actividades: kernel 8.982; memcpy 44.488; memset 9; runtime 84.116; graph trace 5.207; synchronization 7.864; CUDA event 262; overhead 111.
- Integridad SQLite correcta; sin claves foráneas rotas ni duplicados.
- Los 262 CUDA_EVENT tienen timestamp cero en origen; se conservan sin inventar duración.

Informe: [NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md).

## C05 — Build CUDA del motor instrumentado

Base fijada: llama.cpp `f5222f25c18da062ab2b8a2dbbfbf4feae398566` (2026-10-28). Se aplicaron en orden `tandem.patch`, `nepenthes/runtime.patch` y `apply_runtime_probes.py`. Aplicación limpia, `git diff --check` limpio y build CUDA sm_86 de `llama-server` completado.

Los marcadores del sink JSONL y del ciclo request_start/request_end aparecen en `libllama-server-impl.so`. Esto acredita compilación e inclusión de hooks, no cobertura total de todas las sondas. El checkout shallow `cafe-llama.cpp` no se usó como base porque su commit no coincidía con la revisión fijada.

## C06 — Primera inferencia real Qwen3.5-4B

**RUN:** `20261115_114657_bash_b5fc455f` · **Modelo:** Qwen3.5-4B Q4_K_M.  
**Motor:** servidor instrumentado sobre base pinned. **Configuración:** CPU-only (`--n-gpu-layers 0`), contexto 512, 4 hilos, batch 128, ubatch 64, puerto local 18086. **Nsight:** desactivado (`--nsys off`).

### Rendimiento

| Métrica | Valor |
|---|---:|
| Prompt evaluado / tokens generados | 10 / 16 |
| Prefill / decode | 21,50 / 10,72 tok/s |
| Tiempo servidor | 1.864,85 ms |
| Ventana monotónica request_start → request_end | 1,864918 s |

La respuesta terminó por el límite `n_predict=16` y contenía un bloque de razonamiento; no completó el literal solicitado. La petición HTTP y la generación finalizaron correctamente (`INFERENCE_TEST=SUCCESS`).

### Eventos del motor

| Tipo | Total JSONL | Dentro de petición |
|---|---:|---:|
| transfer | 2.920 | 2.540 |
| kernel | 454 | 290 |
| sync | 232 | 226 |
| kv_cache | 55 | 49 |
| allocation | 9 | 9 |
| free | 10 | No incluido en desglose temporal comunicado |
| routing | 1 | 1 |
| request_start / request_end | 1 / 1 | 1 / 1 |

Total motor: 3.683 eventos; ventana de petición: 3.117. Todos los eventos dentro de la ventana tienen `request_id=0`: delimitación temporal de una única petición, no atribución robusta por ID.

Las 2.540 transferencias se etiquetan H2D/D2H aunque el modelo se ejecutó CPU-only. No asumir que representan tráfico de cómputo GPU; auditar semántica y backend. Los eventos KV son principalmente `apply_ubatch`, `seq_rm` y `seq_rm.range`; los valores UINT64_MAX se conservan como datos crudos hasta confirmar su semántica en el código. El log de cierre advierte diferencias entre tamaños esperados y observados de buffers CUDA0 y CUDA_Host; no impidieron la inferencia y requieren investigación.

Esta captura no contiene Nsight ni muestras de stacks: no permite un flame graph real, tiempos GPU por kernel ni overhead de instrumentación.

## Próximas campañas

### C07 — Captura emparejada
1. Registrar commit, hash del modelo y configuración.
2. Activar JSONL NEPENTHES y Nsight en el mismo RUN_ID.
3. Verificar artefactos, manifiesto, exit code y checksums.
4. Importar el par en LEONES sin mezclar relojes no calibrados.
5. Auditar cobertura por subsistema y pérdidas.

### C08 — Rendimiento controlado
- Comparar baseline sin sondas con variante instrumentada; warm-up y al menos tres repeticiones.
- Fijar modelo/hash, prompt, salida, contexto, cuantización, commit, batch/ubatch, hilos, offload, thinking y caché.
- Registrar TTFT, prefill/decode, RAM/VRAM, swap, energía si se mide, bytes H2D/D2H/D2D, duración kernels y esperas.
- Informar mediana, dispersión y overhead. Cambiar un parámetro cada vez.
- Recomendar ajustes solo cuando una mejora medida no produzca regresión inaceptable.

### C09 — Informes
Timeline con dominios de reloj explícitos; distribuciones de latencia y tamaños; tablas y timeline KV/MoE; flame graph solo con muestras de stacks; comparativa entre runs; HTML, Markdown, CSV, SQLite, SVG/PNG y checksums.

## Criterio de cierre global

NEPENTHES no se declara completo hasta que una instalación limpia pueda envolver una inferencia real, producir eventos del motor y telemetría host/GPU/Nsight, preservar artefactos, importar la captura emparejada, generar informes reproducibles y pasar verificación. Las limitaciones de correlación, cobertura y overhead deben quedar explícitas.
