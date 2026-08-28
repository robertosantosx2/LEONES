## Frontera RC1 de benchmark

El camino mínimo de RC1 no utiliza runners genéricos paralelos. La ejecución debe pasar por el plan runtime autorizado y las piezas canónicas de ejecución, benchmark y evidencia.

Permanecen activos, entre otros:

- `a01_runtime_benchmark.py` — vertical A01 de RC1;
- `runtime_benchmark_v1.py` — contrato común `runtime-benchmark.v1`;
- `runtime_benchmark_evidence.py` — captura/normalización de evidencia;
- los adaptadores y runners de runtime autorizados.

`record_benchmark.py` permanece activo como soporte de registro utilizado por la ejecución actual; `run_and_record_benchmark.py` ha sido trasladado a [`scripts/deprecated/`](deprecated/). Sus pruebas históricas se conservan bajo `tests/deprecated/`. No se deben crear nuevos consumidores de la interfaz deprecated.

La familia histórica `leones-*` también está fuera del núcleo RC1 y se conserva bajo [`scripts/deprecated/`](deprecated/). No forma parte del camino canónico de selección, ejecución, medición ni evidencia.

Los demás scripts antiguos o especializados se conservan hasta que una auditoría de dependencias demuestre que pueden migrarse. **No se elimina por intuición: se depreca cuando existe una sustitución y se conserva la procedencia.**