# NEPENTHES — roadmap técnico subordinado

> **Aviso de gobernanza documental:** el documento maestro único es [NEPENTHES-INDEX.md](NEPENTHES-INDEX.md). El plan general, las prioridades y el estado de cada motor se mantienen exclusivamente allí. Este archivo se conserva como checklist técnico/histórico de tareas y criterios detallados; no debe utilizarse como estado global vigente. Al cerrar o cambiar un gate, actualizar primero el documento maestro.

**Fecha de actualización documental:** 2026-11-20.

## Reconciliación software P0 — 2026-11-20

**Aceptado en `main` (software/CI):**

- Decodificación dinámica de enums Nsight (`ENUM_CUDA_MEMCPY_OPER`, `ENUM_CUDA_MEM_KIND`) con columnas `copy_kind_*` / `src_kind_*` / `dst_kind_*`, `enum_decode_status` y preservación de sentinelas/valores desconocidos en `raw_json`.
- Correlación NVTX explícita (request + batch), calibración de reloj con incertidumbre de bracket, atribución `windowed` many-to-many no causal; ventanas solapadas rechazadas.
- Implementación: `scripts/nepenthes_nsys_import.py`.
- Tests: `tests/test_nepenthes_nsys_import.py` (enums, sentinelas, reimport, calibración, batch, process/thread scoping).

Las ramas históricas `feat/nepenthes-nsys-enum-decode-20261119` y `feat/nepenthes-nsys-nvtx-correlation-20261119` están **obsoletas** respecto a `main` y no deben usarse como fuente de estado.

**Pendiente físico (no bloquea P0 software):**
- Validación adicional de enums contra SQLite de la versión exacta de Nsight en MSI.
- C07 batch Tandem.cpp y C08 AIPerf-first (ver INDEX y issue #212).

El resto del checklist histórico de este anexo permanece subordinado al INDEX. Consultar siempre `NEPENTHES-INDEX.md` para el orden de trabajo vigente.
