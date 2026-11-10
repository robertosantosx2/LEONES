# Qwen3.6 CUDA chain: auditoría del ciclo de vida de setup

Fecha: 2026-11-10

## Hallazgo

La revisión de `c/qwen36_cuda_chain.h` encontró que `q36cc_setup()` asignaba `Q36CChain`, lo publicaba inmediatamente en `m->cchain` y después podía salir con `return NULL` desde varios puntos: reserva de tablas, validación de tensores del trunk, inicialización del contexto CUDA, reserva del arena de parámetros y subida de parámetros/estado.

Esas salidas dejaban un objeto incompleto publicado en `m->cchain`. Una llamada posterior veía el puntero no nulo y no podía reintentar correctamente el setup. Además, los arrays auxiliares de host no se liberaban en esos caminos.

## Cambio implementado en el fork

Rama: [research/qwen36-cuda-chain-planner](https://github.com/robertosantosx2/colibri/tree/research/qwen36-cuda-chain-planner)

Commits:
- `5489b4b`: introduce `q36cc_discard_setup()`, que libera los recursos propios de la cadena, los arrays auxiliares y limpia `m->cchain`.
- `540ab1f`: enruta los fallos parciales de setup a la ruta común de limpieza.
- `41f9994`: corrige la salida final de la ruta de error para que retorne `NULL` después de limpiar.
- `6c384c7`: registra `cc_shutdown()` inmediatamente después de un `cc_init()` exitoso, de modo que también se cierre el backend si falla una reserva posterior.
- `673a6b8`: elimina el registro duplicado de `cc_shutdown()` en el llamador; el registro ahora pertenece al punto que inicializa el backend.

La limpieza distingue recursos:
- **Propiedad de la cadena:** tensores CUDA `t_ab`, `t_sg`, `t_gate`; buffers `rec/ring/kc/vc/prm`; tablas auxiliares asignadas por setup.
- **Prestados por el tier:** matrices de proyección y `lm_head` apuntadas por los handles `t_q/t_k/t_v/t_o/t_dnp/t_dno/t_sh*` y otros handles de layer. Se liberan los arrays de punteros, no los tensores del tier.

Los fallos anteriores a la asignación de `Q36CChain` conservan sus salidas directas. Después de publicar `m->cchain`, las salidas de error pasan por `fail:` y `q36cc_discard_setup()`.

## Alcance y límites

- El cambio corrige la limpieza de **fallos durante la inicialización de la cadena**, evita dejar un `m->cchain` envenenado y garantiza el registro de cierre del backend tras inicializarlo.
- No convierte la subida de las matrices del tier en una transacción: las matrices colocadas por el tier siguen siendo propiedad del tier si la cadena no se activa.
- No se ha demostrado todavía el comportamiento de todos los errores asíncronos CUDA ni el rollback de operaciones de upload fallidas.
- No se han ejecutado todavía los tests del repositorio ni una compilación CUDA.
- No se ha probado en la RTX 3050 sm_86; no hay resultados de rendimiento.

## Validación pendiente en el MSI

1. Compilar el target CUDA de Qwen3.6 con warnings habilitados.
2. Ejecutar los tests fake-CUDA de tier y los tests generales disponibles.
3. Ejecutar un caso donde la cadena decline por una matriz ausente/no colocada y comprobar que el proceso continúa por la ruta por-matriz sin corrupción.
4. Forzar un fallo de inicialización del contexto o una reserva insuficiente y comprobar que no queda memoria CUDA/host retenida por la cadena.
5. Arrancar de nuevo el setup en un harness que permita reintento, verificando que `m->cchain == NULL` tras el fallo.
6. Ejecutar un prompt corto con `COLI_CUDA_CHAIN=1`, y repetir con `COLI_CUDA_CHAIN=0` como control.

Registrar comandos, stdout/stderr, commit probado, GPU/driver, VRAM libre, RSS y estado de salida. No publicar cifras de velocidad sin varias repeticiones y una comparación controlada.
