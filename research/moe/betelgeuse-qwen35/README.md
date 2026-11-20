# Betelgeuse × Qwen3.5-35B-A3B — LEONES workstream

Estado: **preparación técnica remota; validación de empaquetado e inferencia pendiente**.

Este directorio concentra el trabajo LEONES para adaptar el paginador MoE de Betelgeuse al GGUF Qwen3.5-35B-A3B-IQ2_XXS disponible en el MSI. No contiene pesos, copias del repositorio upstream ni artefactos binarios.

## Objetivo

Preparar un bundle trunk-only que permita que el runtime pagine los expertos de las 40 capas principales desde almacenamiento, manteniendo intacto el bloque auxiliar MTP/NextN del GGUF. El primer ensayo de inferencia se hará con MTP desactivado, si el runtime lo permite.

## Fuentes de referencia

- Betelgeuse upstream: https://github.com/Betelgeuse-AI/Betelgeuse
- Commit de referencia inspeccionado: `a6b46ade3ab307273b33274b47d76fba1ef57831`
- Packer upstream: `tools/moe_pack.py`
- Paginador upstream: `src/moe_pager.cpp`
- Cargador Qwen3.5 MoE: `src/models/qwen35moe.cpp`

## Estado del modelo de prueba

Archivo: `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`

- SHA-256: `479cc80b2500f7ba5f6131986da188ecb406cf7855094c5d8ae0ec332a715105`
- Tamaño: 10,676,139,840 bytes
- GGUF v3; arquitectura `qwen35moe`; 41 bloques declarados.
- 256 expertos, top-8; dimensión de embedding 2048; FFN experto 512.
- Capas 0–40 tienen gate/up/down. La capa 40 es el bloque auxiliar MTP/NextN.
- No contiene `per_layer_token_embd.weight` (PLE).
- Conserva tensores `blk.40.nextn.*`; no eliminarlos ni sintetizar PLE.

## Decisión de particionado

- **Paginación:** exclusivamente expertos `blk.0`–`blk.39` (40 capas).
- **GGUF denso:** conservar los tensores expertos de `blk.40` asociados a MTP/NextN. Para los expertos de `blk.0`–`blk.39`, retirar los datos del GGUF denso solo según el contrato exacto de Betelgeuse y mantener los descriptores requeridos por el cargador.
- **Bundle:** `experts.bin` + índice nativo explícito; el índice debe enumerar 40 × 256 × 3 entradas en el orden que consume `moe_pager`.
- **Metadata:** conservar la metadata original. No añadir `betelgeuse.ple_file` ni campos PLE.
- **MTP:** preservar `blk.40.nextn.*`; primera ejecución con MTP apagado. Si el cargador no permite apagarlo de forma segura, detenerse y resolverlo antes de inferencia.

No se debe asumir que el packer actual acepta 40 capas: su `expert_layout()` exige capas contiguas y el paginador se dimensiona con `n_layer()`. Esta es precisamente la frontera que debe validarse.

## Entregables previstos

1. Adaptador/packer con modo explícito `qwen35-trunk-only`.
2. Tests sintéticos de layout, índices, preservación MTP y round-trip byte-exact.
3. Auditoría del GGUF real y manifiesto SHA-256.
4. Bundle generado fuera del repositorio (no subir pesos).
5. Ejecución de humo y benchmark en el MSI; resultados reproducibles en LEONES.

## Estado y límites

Esta rama de LEONES es el espacio de integración y documentación. **No es un fork de Betelgeuse.** La conexión GitHub disponible no expone la operación de crear forks; el fork real debe crearse desde GitHub y después vincularse aquí como upstream. No se hará pasar un overlay por un fork ni se copiarán fuentes upstream a LEONES para simularlo.

No se declara compatibilidad funcional hasta completar las pruebas del packer, cargador y runtime con el GGUF real.
