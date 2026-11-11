# DSpine en llama.cpp — auditoría y portabilidad

**Estado: BLOCKED / no existe implementación DSpine confirmada en el fork auditado.** Esta rama de LEONES conserva el trabajo de investigación y no afirma que DSpine funcione en llama.cpp.

## Fuentes primarias

- [Tencent/DSpine](https://github.com/Tencent/DSpine): implementación oficial de inferencia para SGLang y paquete MLX.
- [README oficial](https://github.com/Tencent/DSpine/blob/main/README.md): parejas objetivo/drafter, instalación y resultados.
- [Paper arXiv:2609.36173](https://arxiv.org/abs/2609.36173).
- [Ajay9o9/llama.cpp, rama dspine](https://github.com/Ajay9o9/llama.cpp/tree/dspine): fork que se debe auditar antes de atribuirle soporte.
- [Qwen3-8B-DSpine-b16](https://huggingface.co/tencent/Qwen3-8B-DSpine-b16): checkpoint oficial de drafter.
- [Qwen3.8-27B-DSpine-b16](https://huggingface.co/tencent/Qwen3.8-27B-DSpine-b16): checkpoint oficial de drafter para Qwen3.8-27B.

## Resultado de auditoría estática del fork

Se inspeccionaron en la rama `dspine` los archivos:

- `common/common.h`
- `common/speculative.cpp`
- `common/speculative.h`
- `src/llama-ext.h`
- `src/models/models.h`
- `src/models/qwen3.cpp`

En `common/common.h`, el enum de algoritmos incluye `draft-dflash` y `draft-dspark`, pero no `COMMON_SPECULATIVE_TYPE_DSPINE`. En `common/speculative.cpp`, el registro incluye `draft-dflash` y `draft-dspark`, pero no `draft-dspine` ni una implementación `common_speculative_impl_draft_dspine`.

**Conclusión:** el nombre de la rama y la disponibilidad de conversiones GGUF de terceros no son evidencia de que el runtime implemente DSpine. DFlash/DSpark y DSpine son algoritmos relacionados, pero no equivalentes. Un GGUF de drafter DSpine no debe pasarse a `draft-dflash` sin demostrar compatibilidad matemática y de metadatos; no se debe intentar cargarlo como si fuera equivalente.

Los hashes de blobs inspeccionados y los criterios se conservan en la auditoría automatizada. El SHA exacto del commit de la rama externa debe quedar fijado por la ejecución del script, no inferirse de los hashes de archivos.

## Qué es DSpine

DSpine (*Draft in Parallel, Condition Through Depth*) es una técnica de speculative decoding. En cada capa del drafter, la predicción de una posición se inyecta en la posición sucesora mediante un puente de código aprendido. Las posiciones se actualizan en paralelo mientras la dependencia causal se desarrolla a través de la profundidad.

La implementación oficial usa una familia DFlash-like para el bloque de draft, pero añade un code bridge específico, escritura de características por capa, reglas de atención y verificación. Compartir parte del esqueleto DFlash no convierte a un decodificador DFlash en DSpine.

## Parejas oficiales

| Modelo objetivo | Drafter oficial | Estado |
|---|---|---|
| Qwen3-8B | `tencent/Qwen3-8B-DSpine-b16` | Publicado |
| Qwen3.8-27B | `tencent/Qwen3.8-27B-DSpine-b16` | Publicado en noviembre de 2026 |

No extrapolar estas parejas a Qwen3.5, MiniCPM5 u otras arquitecturas sin pesos entrenados y contrato de inferencia compatible.

## Portar DSpine a llama.cpp: trabajo necesario

No es un simple cambio de nombre de algoritmo. El port necesita, como mínimo:

1. **Contrato de checkpoint:** leer y validar los metadatos DSpine, el tamaño del bloque, capas objetivo, capas de características, dimensiones del puente, top-k de refinamiento, token máscara y modo de segunda pasada. Rechazar configuraciones desconocidas.
2. **Modelo de drafter:** mapear los tensores del checkpoint al grafo GGML; implementar proyecciones, atención, normalizaciones y MLP con dimensiones verificadas.
3. **Code bridge:** implementar cada escritura aprendida de características adyacentes y su refinamiento final. Mantener el orden de redondeo y precisión compatible con el checkpoint.
4. **Features del objetivo:** extraer las capas objetivo requeridas y transferirlas al contexto del drafter sin copias o sincronizaciones ocultas innecesarias.
5. **Máscara y KV:** implementar atención causal dentro del bloque, visibilidad del contexto y tratamiento de KV para prefijo y bloque especulativo.
6. **Propuesta y verificación:** generar el bloque, aplicar selección/top-k según el checkpoint, verificar con el objetivo y confirmar el prefijo aceptado con semántica correcta para greedy y sampling.
7. **Integración runtime:** exponer un tipo inequívoco `draft-dspine`, validación de pareja objetivo/drafter y mensajes de error explícitos. Nunca autodetectar DSpine como DFlash.
8. **Tests:** validación de metadatos, formas y nombres de tensor; pruebas numéricas contra implementación de referencia; aceptación greedy; sampling/rejection; contextos largos; CPU y CUDA.
9. **Benchmarks:** baseline sin speculative, DSpine y, cuando sea posible, DFlash/DSpark, con el mismo objetivo, prompt, contexto, sampler y backend.

## Evaluación MSI Thin 15 B12UC

Perfil LEONES: Intel i7-12650H, NVIDIA RTX 3050 Laptop 4 GiB (SM 8.6), RAM 14 GiB, Ubuntu.

- El fork actual no tiene DSpine confirmado: por tanto no hay binario que probar en el MSI.
- El método oficial SGLang exige CUDA y el stack PyTorch/SGLang; el usuario no tiene PyTorch instalado según el inventario previo.
- Las parejas oficiales empiezan en Qwen3-8B y Qwen3.8-27B. No son candidatas cómodas para 4 GiB de VRAM.
- No descargar los checkpoints ni intentar la ejecución en el MSI hasta disponer de un runtime real, estimación de memoria basada en tensores y un plan explícito de CPU/GPU.
- El objetivo de la futura validación será una prueba pequeña y medible, no reproducir cifras de una RTX 3090.

## Estados de evidencia

- `SOURCE-VERIFIED`: confirmado en fuentes/código primarios.
- `STATIC-AUDIT`: resultado de inspección de código con SHA de fuente.
- `CI-PASSED`: build/test ejecutado en CI con logs y SHA.
- `MSI-MEASURED`: ejecución física en el MSI real.
- `NOT-IMPLEMENTED`: falta el soporte de runtime necesario.

No se marcará como CI-PASSED la funcionalidad DSpine solo porque compile una versión de llama.cpp que contiene DFlash/DSpark.

## Gate actual

La fase de port está bloqueada por ausencia de implementación DSpine en el fork. La CI puede compilar el fork y ejecutar el auditor estático, pero el resultado esperado actual es `NOT_IMPLEMENTED`. El gate MSI permanece cerrado.
