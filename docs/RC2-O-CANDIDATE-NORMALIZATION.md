# RC2-O — Candidatos y normalización

**Estado:** 🟢 Contrato fijado · fixtures añadidos

RC2 recibe candidatos del mecanismo de ajuste basado en LLMFit y los transforma al formato canónico de presentación. No recalcula compatibilidad ni crea rankings alternativos.

## Contrato de candidato

Cada candidato conserva:

- `model_id` — identificador técnico canónico;
- `name` — nombre humano;
- `rank` — posición entregada por la fuente;
- `fit` — ajuste entregado por la fuente;
- `estimated_tps` — solo si la fuente lo proporciona;
- `source` y `source_version` — procedencia;
- `evidence_level` — nivel de evidencia.

Una estimación sigue siendo una estimación. RC2 no la convierte en medición.

## Fixtures

`examples/rc2/hardware-profile.json` representa un perfil detectado reproducible.

`examples/rc2/llmfit-candidates.json` representa candidatos procedentes de LLMFit y permite probar la interfaz sin hardware físico.

## Integración

El wizard deberá mostrar los candidatos sin ocultar su procedencia y permitirá al usuario seleccionar uno. Esa elección alimentará el contrato de selección existente; no se crea un segundo selector de modelos.

## Criterio para Ubuntu

La integración física solo comienza cuando CI/fixtures hayan demostrado el contrato. Ubuntu se reserva para verificar detección hardware real y la conexión con la instalación/runtime local.
