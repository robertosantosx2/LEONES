# NEPENTHES — roadmap técnico subordinado

> **Aviso de gobernanza documental:** el documento maestro único es [NEPENTHES-INDEX.md](NEPENTHES-INDEX.md). El plan general, las prioridades y el estado de cada motor se mantienen exclusivamente allí. Este archivo se conserva como checklist técnico/histórico de tareas y criterios detallados; no debe utilizarse como estado global vigente. Al cerrar o cambiar un gate, actualizar primero el documento maestro.

**Fecha de actualización documental:** 2026-11-20.  
**Estado operativo:** consultar exclusivamente el [NEPENTHES-INDEX.md](NEPENTHES-INDEX.md).

## Reconciliación software P0 — 2026-11-20

**Aceptado en `main` (software/CI):**

- Decodificación dinámica de enums Nsight (`ENUM_CUDA_MEMCPY_OPER`, `ENUM_CUDA_MEM_KIND`) con columnas `copy_kind_*` / `src_kind_*` / `dst_kind_*`, `enum_decode_status` y preservación de sentinelas/valores desconocidos en `raw_json`.
- Correlación NVTX explícita (request + batch), calibración de reloj con incertidumbre de bracket, atribución `windowed` many-to-many no causal; ventanas solapadas rechazadas.
- Implementación: `scripts/nepenthes_nsys_import.py`.
- Tests: `tests/test_nepenthes_nsys_import.py` (enums, sentinelas, reimport, calibración, batch, process/thread scoping).
- Documento de estado: [NEPENTHES-SOFTWARE-P0-STATUS-20261120.md](NEPENTHES-SOFTWARE-P0-STATUS-20261120.md).

Las ramas históricas `feat/nepenthes-nsys-enum-decode-20261119` y `feat/nepenthes-nsys-nvtx-correlation-20261119` están **obsoletas** respecto a `main` y **no deben usarse como fuente de estado**.

**Pendiente físico (no bloquea P0 software):** C07 batch Tandem.cpp, C08 AIPerf-first, issue #212 (ver INDEX).

---

## Leyenda

- [x] Implementado y con evidencia suficiente para el alcance indicado.
- [~] Implementado o validado parcialmente; falta una prueba de aceptación.
- [ ] Pendiente.

## P0 — decodificación de enums Nsight (aceptado en software/CI)

Ver **Reconciliación software P0 — 2026-11-20** al inicio. Implementación y tests en `main`. Ramas feat históricas obsoletas.

## C07 — NVTX request markers and explicit clock pairing (software aceptado; físico parcial)

Ver **Reconciliación software P0 — 2026-11-20** al inicio.

- **Software/CI:** aceptado en `main`.
- **Físico request-level (llama.cpp):** aceptado en MSI 2026-11-20 (INDEX).
- **Físico batch (Tandem) y C08:** pendientes; issue #212 abierta.

## Estado de aceptación actualizado — 2026-11-20

### Aceptado en GitHub (software/CI)

- [x] Decodificación de enums Nsight (software): aceptada en main con tests de sentinelas y mapeo dinámico.
- [x] Correlación NVTX + calibración + atribución windowed (software): en main con tests.
- [x] AIPerf-first C08 scaffolding y adaptadores de telemetría (PRs ya mergeados en main).
- [x] Contrato de evidencia, importer cross-repo, registry multi-motor.

### Pendiente de aceptación física

- [ ] **C07 batch Tandem.cpp** en MSI.
- [ ] **C08 AIPerf-first** (≥3 pares baseline/instrumented + gate overhead).
- [ ] LEONES issue #212 end-to-end físico.
- [ ] Validación adicional de enums contra SQLite de la versión Nsight instalada en MSI (recomendable; no bloquea P0 software).

El checklist histórico detallado de fases A–F permanece subordinado a este estado y al INDEX. No usar ramas `feat/nepenthes-nsys-*` como fuente de verdad.
