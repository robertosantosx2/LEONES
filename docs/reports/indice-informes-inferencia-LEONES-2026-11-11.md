# Índice de informes de ejecuciones de motores de inferencia de IA

**Proyecto LEONES — Local Ecosystem of Open Neural Expert Systems**

Documento de inventario canónico de todos los informes generados a partir de ejecuciones físicas o intentos documentados de motores de inferencia locales. Fuente: repositorio `robertosantosx2/LEONES` (rama main y ramas de investigación). Fecha de consolidación: **11 de noviembre de 2026**.

## 1. Criterios de inclusión

- Informes que documentan ejecuciones reales (CLI, API o harness) de motores de inferencia locales (TensorFold, llama.cpp, RustingStrata/Strata, Magnitude, Ollama, etc.).
- Documentos de inventario o consolidación que agregan métricas de prefill / decode / TTFT medidas o reportadas.
- Análisis forenses de intentos fallidos o límites de capacidad (memoria, offload, VRAM).
- Se excluyen: reportes mensuales/semanales de prospección, documentación de arquitectura RC, contratos de benchmark sin ejecución física, y fuentes externas no ejecutadas por LEONES.

> **Regla LEONES obligatoria:** ESTIMATED ≠ MEASURED. Las cifras de esta tabla son las conservadas en los informes; la procedencia (CLI, API, harness propio, estimación derivada) se indica en cada entrada.

## 2. Índice de informes localizados

### 2.1 Informes maestros de consolidación

1. **[report-inferencia-dense_Octubre26.md](../benchmarks/report-inferencia-dense_Octubre26.md)** — `docs/benchmarks/` y `docs/reports/`. Consolidación principal de octubre 2026. TensorFold, llama.cpp, RustingStrata sobre Qwen3.5-2B/4B y Qwen3-30B-A3B. Prefill, decode, TTFT y API.
2. **[inventario-comparativo-ejecuciones-modelos-ubuntu-2026-10-30.md](../benchmarks/inventario-comparativo-ejecuciones-modelos-ubuntu-2026-10-30.md)** — `docs/benchmarks/`. Cuadro comparativo unificado (30-oct-2026) con prefill/decode por modelo y motor en MSI RTX 3050 4 GB y otros equipos.
3. **report-dense-inference_October26.md / report-inference-dense-october-2026.md** — Versiones EN/ES del informe denso de octubre (espejos).

### 2.2 Benchmarks multi-runtime y head-to-head

4. **[qwen35-4b-three-runtimes-2026-10-20.md](../benchmarks/qwen35-4b-three-runtimes-2026-10-20.md)** (+ CSV asociado). Comparación controlada TensorFold / llama.cpp / RustingStrata sobre Qwen3.5-4B (3 peticiones × 32 tokens). Mediana tok/s y TTFT.
5. **head-to-head-20261021 (Qwen3-30B-A3B IQ3_XXS)** — `docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/`. Strata vs llama.cpp; results-summary.csv, logs de repeticiones y manifesto de archivo.
6. **[magnitude-qwen35-4b-2026-10-21.md](../benchmarks/magnitude-qwen35-4b-2026-10-21.md)** — Intento Magnitude 0.2.10 + Qwen3.5-4B. Artefactos verificados; CLI no reconoció el modelo; sin métricas de inferencia.

### 2.3 Informes por modelo / motor

7. **[spark-x26-4b-abliterated-rtx3050-2026-10-30.md](../benchmarks/spark-x26-4b-abliterated-rtx3050-2026-10-30.md)** — Ejecución Spark-X2.6-4B-abliterated en MSI RTX 3050.
8. **[ling-3.0-tiny-ubuntu-msi-rtx3050-2026-10-29.md](ling-3.0-tiny-ubuntu-msi-rtx3050-2026-10-29.md)** — Ling 3.0 Tiny en MSI RTX 3050 (Ubuntu).
9. **[ling-3.0-tiny-ubuntu-gb-bxi7-5500-2026-10-29.md](ling-3.0-tiny-ubuntu-gb-bxi7-5500-2026-10-29.md)** — Ling 3.0 Tiny en equipo GB BXi7-5500 (segundo hardware).
10. **[INFORME-COSMIC-LIGHTNING-2026-10-31.md](../benchmarks/cosmic-lightning/INFORME-COSMIC-LIGHTNING-2026-10-31.md)** — `docs/benchmarks/cosmic-lightning/`. Informe Cosmic Lightning (31-oct-2026).
11. **[analisis-forense-tensorfold-moe-2026-10-24.md](analisis-forense-tensorfold-moe-2026-10-24.md)** (+ versión EN). Análisis forense TensorFold 1.1.3 sobre Nemotron 3.5 Lightning 30B-A3B y Qwen3.6; límites de memoria/VRAM en RTX 3050 4 GB.

### 2.4 Evidencia de runtime y A01

12. **docs/runtime-benchmark-evidence-v1.1.md** — Evidencia de runtime benchmark (contrato v1.1).
13. **docs/evidence/ollama-a01-real.md** + `artifacts/ollama-a01-real-evidence.json` — Evidencia real A01 con Ollama.
14. **docs/completed/BENCHMARK-MEASURED-EVIDENCE.md** y **PHYSICAL-BENCHMARK-VALIDATION.md** — Cierre de evidencia MEASURED y validación física.
15. **docs/completed/RC4-STRICT-MEASURED-CHAIN-2026-09-07.md** — Cadena estricta MEASURED RC4 (E2E físico pendiente en fecha del documento).
16. **artifacts/pithos-0.5.1-2026-11-07/benchmark-results.csv** + session log — Resultados de benchmark Pithos 0.5.1 (7-nov-2026).
17. **[picchio-ram-dual-channel-msi-2026-11-08.md](picchio-ram-dual-channel-msi-2026-11-08.md)** + evidencia asociada — Prueba dual-channel RAM (contexto de rendimiento de inferencia).

### 2.5 Artefactos y logs de ejecución

- `docs/benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/` — results-summary.csv, extracted-console-evidence.txt, logs por repetición (strata/ y llama.cpp/), tar.gz raw.
- `docs/reports/artifacts/tensorfold-moe-forensic-2026-10-24/` — logs de preflight, serve, offload-capability-audit, Nemotron y Qwen.
- `docs/reports/artifacts/inferencia-rtx3050-4gb-oct26-collection-*.tar.gz` — colección de inferencias RTX 305 intensificadas RTX 3050 4 GB octubre.
- `docs/reports/evidence/picchio-dual-channel-2026-11-08/` — evidencia empaquetada.

## 3. Tabla consolidada: motor · modelos · prefill · velocidad de inferencia

Valores tomados de los informes anteriores. Prefill = tok/s de procesamiento de prompt cuando se midió de forma separada. Velocidad de inferencia = tok/s de generación/decode (o mediana de salida API). «N/D» = no documentado de forma comparable. «~» = estimado a partir de tokens / tiempo total (no velocidad interna de decode).

| Motor | Modelo / cuantización | Prefill (tok/s) | Velocidad inferencia (tok/s) | Notas / fuente |
|---|---|---:|---:|---|
| TensorFold 1.1.1 CUDA | Qwen3.5-2B MLX-4bit | N/D | 95,08 (32 tok); 105,71 (128 tok) | Native; informe denso Oct-26 |
| TensorFold 1.1.1 CUDA API | Qwen3.5-2B MLX-4bit | N/D | Mediana ~106,5 (128 tok) | 5 peticiones; inventario 30-oct |
| TensorFold CUDA native | Qwen3.5-4B MLX-4bit | N/D (lat. 190–209 ms) | 53,64 (64); 53,42 (128) | Informe denso + inventario |
| TensorFold CUDA API | Qwen3.5-4B MLX-4bit | ~228–232 | Mediana 54,708 | 3×32 tok; TTFT 0,1303 s; three-runtimes |
| llama.cpp CUDA CLI | Qwen3.5-4B GGUF Q4_K_M | 141,2 | 42,4 | Ejecución CLI; VRAM ~2,8 GiB |
| llama.cpp CUDA API | Qwen3.5-4B GGUF Q4_K_M | N/D comparable | Mediana 47,646 | 3 peticiones; three-runtimes 20-oct |
| RustingStrata CUDA API | Qwen3.5-4B GGUF Q4_K_M | N/D (API) | ~38,17 (estimado) | 32 tok / tiempo total; no tok/s interno |
| RustingStrata bench | Qwen3.5-4B GGUF Q4_K_M | 915,3 (PP=128); 986,5 (PP=512) | N/D en esta prueba | Harness propio; contexto 1024 |
| llama.cpp CUDA | Qwen3-30B-A3B IQ3_XXS | N/D (offload sweep) | Mediana 1,97–2,00 (12–14 capas) | Máx. 15 capas funcionales; RTX 3050 |
| RustingStrata CUDA | Qwen3-30B-A3B IQ3_XXS | N/D | 7,74 (64 tokens) | Generación real; no comparación controlada |
| Magnitude 0.2.10 | Qwen3.5-4B | — | — | Sin inferencia; modelo no reconocido en CLI |
| TensorFold 1.1.3 | Nemotron 3.5 Lightning 30B-A3B MLX-4bit | — | — (intento forense) | Análisis forense 24-oct; límites VRAM 4 GB |

### Notas de interpretación

- Hardware de referencia principal: MSI Thin 15 B12UC, i7-12650H, 14 GiB RAM, RTX 3050 Laptop 4 GiB, Ubuntu, driver 580.178.04, CUDA 13.0.
- Las cifras de TensorFold MLX-4bit y llama.cpp/Strata GGUF Q4_K_M no son comparaciones de artefacto idéntico.
- Prefill de RustingStrata bench usa protocolo distinto (PP fijo, harness propio) y no debe ordenarse directamente frente a prefill API.
- E2E MEASURED de la cadena RC4 A01 seguía abierto en los documentos de cierre de septiembre; los números de esta tabla son mediciones de runtime locales documentadas, no el gate A01 completo.
- Fuentes canónicas en GitHub: https://github.com/robertosantosx2/LEONES (paths indicados en la sección 2).

---

*Documento generado 2026-11-11. Índice de informes de inferencia LEONES.*
