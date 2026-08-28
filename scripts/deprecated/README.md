# Scripts deprecated

Este directorio conserva scripts históricos que ya no forman parte del camino mínimo de RC1.

No se eliminan todavía porque pueden ser útiles como referencia histórica. No deben recibir nuevas funcionalidades.

## Regla de migración

Antes de mover un script aquí se comprueba que:

1. no sea parte del camino canónico de RC1;
2. su responsabilidad esté cubierta por una pieza vigente;
3. no sea necesario mantenerlo en `scripts/` para la interfaz actual;
4. sus pruebas asociadas también puedan salir del conjunto activo sin romper el contrato vigente.

## Primera migración

- `record_benchmark.py`: sustituido por el contrato `runtime-benchmark.v1` y la capa de evidencia vigente.
- `run_and_record_benchmark.py`: runner genérico sustituido por el camino A01/runtime autorizado.

Sus pruebas históricas se conservan bajo `tests/deprecated/`.

**Importante:** `runtime_benchmark_v1.py`, `runtime_benchmark_evidence.py`, los adaptadores de runtime y `a01_runtime_benchmark.py` permanecen activos. No se deben duplicar con nuevos runners genéricos.
