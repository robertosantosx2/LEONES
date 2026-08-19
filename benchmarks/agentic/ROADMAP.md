# Agentic Benchmark V1 — roadmap

## Fase 0 — Diseño 🟢

- metodología integrada;
- catálogo A01–A10;
- contrato de resultados ampliado;
- política de scoring multidimensional.

## Fase 1 — Runner 🔵

- crear entorno sandbox reproducible;
- implementar adapters de filesystem/shell;
- capturar eventos de trayectoria;
- generar `result.json` compatible con el schema;
- implementar timeout y límites de llamadas.

## Fase 2 — Graders 🔵

- graders deterministas para A01–A05;
- grader de evidencia para A06;
- grader de repositorio para A07;
- grader de sandbox para A08;
- grader de seguridad para A09;
- grader de presupuesto para A10.

## Fase 3 — B01–B05 instrumentados 🔵

- mantener compatibilidad con LOTB;
- transformar pruebas que actualmente sean conversacionales en pruebas con herramientas cuando corresponda;
- registrar trazas y métricas.

## Fase 4 — Primera campaña 🟡

Ejecutar cada tarea contra un conjunto pequeño de modelos/runtimes/hardware y repetir las ejecuciones suficientes para estimar variabilidad.

## Fase 5 — Validación 🟡

- revisar falsos positivos/negativos de graders;
- congelar versiones;
- comparar ejecuciones repetidas;
- excluir resultados incompletos;
- publicar evidencia primaria.

## Fase 6 — Integración Atlas 🔵

Relacionar resultados verificados con:

- identidad de modelo;
- hardware;
- runtime;
- cuantización;
- evidencia;
- recomendación.

## Cierre

No marcar V1 como 🟢 hasta que exista al menos una campaña reproducible completa, CI de los contratos, resultados primarios conservados y documentación de limitaciones.
