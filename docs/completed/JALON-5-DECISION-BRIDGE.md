# JALÓN 5 — Puente mínimo de decisión

JALÓN 5 fija el contrato `leones-ods-magnitude-decision.v1` y el puente declarativo que lo construye.

## Invariantes

- ODS/Magnitude conserva procedencia y tipo de evidencia.
- LLMFit permanece siempre `estimate_only: true`.
- Ninguna señal externa se convierte automáticamente en `measured`.
- Una decisión `BENCHMARK_REQUIRED` remite a la medición física de JALÓN 3.
- Una medición local solo se referencia mediante un `execution_id` identificado.
- El selector LEONES conserva la autoridad final.

La ejecución real de ODS/Magnitude sigue fuera de CI y se realizará en Ubuntu cuando sea necesaria.
