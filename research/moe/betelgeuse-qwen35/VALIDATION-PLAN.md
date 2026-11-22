# Plan de validación en MSI

Este documento es el handoff para la fase local. No se ha ejecutado ninguna de estas pruebas desde GitHub.

## Preflight

- Confirmar que el archivo existe y que su SHA-256 coincide con:
  `479cc80b2500f7ba5f6131986da188ecb406cf7855094c5d8ae0ec332a715105`.
- Confirmar que el árbol Betelgeuse checkout corresponde al fork acordado y registra el commit base.
- Confirmar dependencias Python/GGUF del repositorio y versión de compilador.
- Registrar `free -h`, `df -h`, `nvidia-smi`, versión de driver/CUDA y procesos activos.
- No lanzar la carga de 35B antes de terminar las pruebas de empaquetado.

## Fase A — Auditoría GGUF

- Volcar metadatos y tensor info con las herramientas GGUF del repositorio.
- Verificar 41 bloques, 256 expertos y top-8.
- Confirmar exactamente 120 tensores expertos trunk (40 × gate/up/down).
- Confirmar los 3 tensores expertos de `blk.40` y todos los `blk.40.nextn.*`.
- Confirmar ausencia de `per_layer_token_embd.weight`.
- Guardar inventario JSON y salida del hash.

## Fase B — Packer

- Ejecutar primero tests unitarios.
- Ejecutar dry-run sobre el GGUF real.
- Verificar que el layout seleccionado termina en capa 39.
- Generar bundle en un directorio de trabajo separado del modelo original.
- Verificar round-trip de bytes y hashes.
- Reabrir el GGUF denso con el lector GGUF.
- Comparar bytes y metadata de MTP/NextN antes y después.
- Verificar que no se haya generado PLE ni metadata PLE.

**Parada obligatoria:** cualquier discrepancia en número de tensores, offsets, hashes, metadata o lectura posterior invalida el bundle; no pasar a inferencia.

## Fase C — Build/runtime

- Compilar Betelgeuse en modo CUDA para sm_86.
- Confirmar en logs arquitectura `qwen35moe`, trunk de 40 capas y paginador de 40 capas.
- Confirmar que el cargador MTP queda desactivado en el primer ensayo.
- Usar contexto y batch mínimos; no habilitar speculative/NextN.
- Verificar una generación corta y revisar logs de memoria.

## Fase D — Benchmark

Registrar al menos:
- commit exacto de Betelgeuse y SHA del bundle;
- contexto, batch, ubatch, threads, offload y parámetros de paginación;
- tokens prompt/completion;
- prompt eval t/s, generación t/s y latencia al primer token;
- RSS máximo, swap máximo, VRAM pico y temperatura;
- errores, reinicios, fallos de lectura y estado final.

No extrapolar rendimiento a partir del tamaño del archivo. La viabilidad depende de la paginación, ancho de banda de almacenamiento, memoria host, caché y coste de mover expertos.

## Criterio de salida

Solo declarar **funcional** después de completar A, B y C. Solo declarar **viable en MSI** después de un benchmark estable de D. Si el primer smoke test falla por memoria, reducir contexto/batch y revisar política de caché antes de cambiar cuantización.
