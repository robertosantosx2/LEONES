# Roadmap ODS + Magnitude

## Fase 0 — Investigación
- congelar versiones de referencia;
- inventariar funciones, dependencias y lifecycle;
- matriz de compatibilidad;
- seguridad y privacidad.

## Fase 1 — Contratos
- ODS status/doctor machine-readable;
- Magnitude hardware/recommendation machine-readable;
- schema común LEONES;
- estimated/configured/measured separados.

## Fase 2 — Preflight
- OS/arquitectura;
- CPU/RAM/GPU/VRAM;
- almacenamiento;
- Docker/Compose para ODS;
- Node/npm para Magnitude.

## Fase 3 — Instaladores
- perfil servidor ODS;
- perfil asistente Magnitude;
- modo auditable y release/ref fijado cuando sea posible.

## Fase 4 — Validación
- health checks;
- servicios;
- modelo;
- runtime;
- agente/skills controladas.

## Fase 5 — Benchmark
- warm-up;
- TTFT;
- TPOT/tok/s;
- memoria;
- contexto;
- concurrencia.

## Fase 6 — Atlas
- registro con procedencia;
- correlación hardware/model/runtime;
- no convertir recomendaciones en benchmarks.

## Fase 7 — E2E y release
- Debian 12;
- Ubuntu 22.04/24.04;
- Rocky/RHEL compatible;
- GPU por familia cuando exista runner/hardware real;
- CI verde;
- documentación y rollback.

## Definition of Done
Ningún subproyecto se considera terminado hasta disponer de instalación reproducible, health check, benchmark medido, schema validado, privacy test, recuperación/uninstall documentado, CI y documentación publicada.
