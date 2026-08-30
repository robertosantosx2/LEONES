# Scripts deprecated

Este directorio conserva scripts históricos que ya no forman parte del camino mínimo de RC1.

No se eliminan todavía porque pueden ser útiles como referencia histórica. No deben recibir nuevas funcionalidades.

## Regla de migración

Antes de mover un script aquí se comprueba que:

1. no sea parte del camino canónico de RC1;
2. su responsabilidad esté cubierta por una pieza vigente, o que la pieza sea una interfaz histórica sin consumidor activo;
3. no sea necesario mantenerlo en `scripts/` para la interfaz actual;
4. sus pruebas asociadas también puedan salir del conjunto activo sin romper el contrato vigente.

## Componentes migrados

### `router.py`

- Procedencia: router de recomendaciones de una arquitectura anterior.
- Motivo: RC1 usa selección + runtime gate; no necesita una segunda decisión de recomendación.
- Sustituto: `selection_pipeline.py` y `runtime_gate.py`.
- Consumidores activos conocidos: ninguno identificado.
- Recuperación: solo si se recupera el contrato histórico de routing.

### `leones-router.py`

- Procedencia: router heurístico de versiones anteriores.
- Motivo: duplicaba selección, memoria y evidencia fuera de los contratos RC1.
- Sustituto: `selection_pipeline.py` + `runtime_gate.py`.
- Consumidores activos conocidos: ninguno identificado.
- Recuperación: solo con una necesidad contractual nueva y explícita.

### `hardware_discovery.py`

- Procedencia: descubrimiento de hardware combinado con microbenchmarks.
- Motivo: mezclaba observación de hardware y medición; RC1 separa ambas responsabilidades.
- Sustituto: `hardware_profile.py` para hechos observados y el camino runtime para medición.
- Consumidores activos conocidos: ninguno identificado.
- Recuperación: solo si se define de nuevo un contrato explícito para discovery.

### `leones.py`

- Procedencia: dispatcher histórico de scripts.
- Motivo: mantenía una segunda interfaz de orquestación y referenciaba el antiguo punto de entrada LOTB.
- Sustituto: scripts canónicos ejecutados según el recorrido RC1.
- Consumidores activos conocidos: ninguno identificado.
- Recuperación: solo si se define una interfaz CLI agregadora compatible con RC1.

## Corrección importante

`record_benchmark.py` y `run_and_record_benchmark.py` **no están deprecated**. Aunque no sean piezas públicas del núcleo conceptual, tienen consumidores activos en el runner de llama.cpp y deben permanecer disponibles hasta que exista una migración funcional demostrada.
