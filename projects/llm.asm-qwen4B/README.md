# llm.asm-qwen4B

Subproyecto de LEONES dedicado a estudiar la adaptación y ejecución
de Qwen3-4B mediante el motor de inferencia llm.asm.

## Objetivo

Ampliar experimentalmente el soporte existente de llm.asm para evaluar
Qwen3-4B, preservando la implementación funcional de Qwen3-0.6B.

## Repositorios

- LEONES: https://github.com/robertosantosx2/LEONES
- Upstream: https://github.com/alesha-pro/llm.asm
- Clon local independiente: `/home/ssantos/leones-work/llm.asm-qwen4B-reference`

## Referencia upstream

- Commit de referencia: `48feccbfd57cb669440f31ff64958d95bb8b848e`
- Rama reportada: `main`
- Clon superficial: profundidad 1

El clon upstream se mantiene fuera del árbol Git de LEONES.
No modificarlo como parte de los experimentos de adaptación.

## Líneas de trabajo

1. Auditoría de arquitectura y dimensiones de Qwen3-4B.
2. Análisis de las limitaciones del formato ASMBIN.
3. Adaptación del exportador de pesos.
4. Adaptación del motor x86-64 y sus límites de memoria.
5. Validación numérica frente a una implementación de referencia.
6. Inferencia, rendimiento y escalado de contexto.
7. Archivo reproducible de resultados y registros.

## Experimento de partida

El antecedente es la campaña Qwen3-0.6B archivada en:

`docs/benchmarks/llm-asm-qwen3-0.6b-context-2026-11-25.md`

Los nuevos experimentos tendrán registros y resultados propios.
No sobrescribirán los datos históricos.

## Estado del trabajo

**Fase actual:** auditoría estática y preparación de compatibilidad Qwen3-4B.

Ya están documentados:
- El experimento reproducible Qwen3-0.6B, incluida la exportación,
  compilación, validación numérica y campaña de contexto.
- La auditoría estática del exportador, ASMBIN y motor NASM.
- La configuración oficial Qwen3-4B y estimaciones iniciales de
  pesos Q8_0 y KV-cache.
- Los riesgos pendientes y los criterios para iniciar pruebas locales.

Documento principal:
`docs/HISTORIAL_TECNICO_Y_VISION.md`

**Estado de validación:** todavía no se ha descargado ni exportado
Qwen3-4B, ni se ha compilado o ejecutado el motor con ese modelo.
La compatibilidad descrita es una hipótesis respaldada por inspección
estática, pendiente de pruebas en el MSI.

El código upstream de referencia se mantiene sin modificaciones.

## Escalado a modelos mayores

La arquitectura del trabajo se prepara para evaluar progresivamente Qwen3-8B, Qwen3-14B y Qwen3-32B, además de Qwen3-0.6B y 4B. Esto es una hoja de ruta, no una declaración de soporte. La estrategia exige perfiles de arquitectura explícitos, validador ASMBIN genérico, exportación incremental, presupuesto de memoria y validación por escalones.

- [Hoja de ruta de escalado Qwen3 0.6B–32B](docs/ROADMAP_ESCALADO_QWEN3_0.6B_A_32B.md)

## Auditoría y especificaciones

- [Historial técnico y visión estratégica](docs/HISTORIAL_TECNICO_Y_VISION.md)
- [Auditoría de kernels, formato ASMBIN y riesgos](docs/AUDITORIA_KERNELS_FORMATO_Y_RIESGOS.md)
- [Especificación del validador ASMBIN v1/v2](docs/ASMBIN_VALIDATOR_SPEC.md)

## Hallazgos actuales

- Las dimensiones de Qwen3-4B caben en el límite estático Q8 del kernel
  inspeccionado (`Q8_MAX_K=16384`), pero falta paridad numérica.
- El loader NASM no demuestra validar el tamaño declarado, offsets,
  solapamientos ni todas las relaciones dimensionales del encabezado.
- El tokenizer requiere comprobar los merges reales del checkpoint.
- El exportador puede tener un pico de memoria superior al tamaño del
  archivo final; se necesita una estrategia de exportación monitorizada.
- El artefacto Q8_0 estimado queda cerca de 4 GiB; el arranque bare-metal
  actual tiene un mapa físico de 4 GiB, módulos Multiboot de 32 bits y un
  allocator bajo 3,75 GiB. Su carga no es viable de forma general sin
  rediseñar el protocolo de carga y la gestión de memoria.

**Siguiente entregable:** implementar el validador ASMBIN independiente
y sus fixtures sintéticos antes de modificar el loader o solicitar
pruebas locales.

Seguimiento de implementación: [Issue #289 — validador ASMBIN v1/v2](https://github.com/robertosantosx2/LEONES/issues/289).
