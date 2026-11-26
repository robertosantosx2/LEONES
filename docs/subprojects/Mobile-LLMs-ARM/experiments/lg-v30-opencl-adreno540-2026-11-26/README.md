# LG V30 — llama.cpp OpenCL / Adreno 540 (2026-11-26)

**Estado: ARCHIVADO — integración llama.cpp/OpenCL fallida; investigación pausada.**

Este expediente conserva el resultado negativo y el estado necesario para retomar el trabajo. No debe interpretarse como una validación de inferencia LLM en GPU: no llegó a ejecutarse ningún token.

## 1. Plataforma física

| Campo | Valor |
|---|---|
| Dispositivo | LG-H930 (LG V30), nombre de dispositivo `joan` |
| SoC | Qualcomm MSM8998 / Snapdragon 835 |
| GPU | Qualcomm Adreno 540 |
| SO | Android 9, API 28 |
| Software | V31a-EUR-XX |
| Kernel | Linux 4.4.153-perf+, AArch64 |
| ABI | arm64-v8a |
| RAM física | 3,806,936 kB (aprox. 3.63 GiB) |
| Swap | 1,885,032 kB (aprox. 1.80 GiB) |
| Acceso | Termux, sin root; SSH local puerto 8022 |

Restricciones: no root, no flasheo, no modificación de /vendor/firmware/drivers, no manipulación de CMA ni reinicio requerido para esta campaña.

## 2. Software y rutas

- Termux: `$PREFIX` = `/data/data/com.termux/files/usr`.
- Fuente llama.cpp: `$HOME/llama.cpp-v1.0.0`.
- Versión de fuente: llama.cpp 1.0.0, commit de origen `b1b770d`.
- Build OpenCL 2.0: `$HOME/llama.cpp-v1.0.0/build-opencl20`.
- Backend: `build-opencl20/bin/libggml-opencl.so` (symlink/versionado según build).
- Ejecutable de prueba: `build-opencl20/bin/llama-simple`.
- Modelo: `$HOME/models/Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf`.
- SHA-256 del modelo: `840490b3171b3e402c35bb488b1c4de1e69efd9a28c10b8b66e05c19ca041514`.
- Log final de ejecución: `$HOME/q4-adreno-final.log`.
- Kernel modificado: `ggml/src/ggml-opencl/kernels/mul_mv_q4_0_f32_8x_flat.cl`.
- Backup anterior: `mul_mv_q4_0_f32_8x_flat.cl.pre-adreno32-20261125`.
- Backup del parche final: `mul_mv_q4_0_f32_8x_flat.cl.pre-final-adreno540`.

No se incluyen el modelo GGUF ni credenciales.

## 3. Configuración de compilación

Build configurado con CMake/Ninja para OpenCL 2.0, evitando símbolos OpenCL 3.0 no disponibles en el controlador Qualcomm:

```bash
cmake -S . -B build-opencl20 -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PREFIX/opt/llama-opencl20" \
  -DGGML_OPENCL=ON \
  -DGGML_OPENCL_TARGET_VERSION=200 \
  -DGGML_VULKAN=OFF \
  -DOpenCL_LIBRARY="$PREFIX/lib/libOpenCL.so" \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=ON \
  -DLLAMA_BUILD_SERVER=OFF
ninja -C build-opencl20 -j1 ggml-opencl llama-simple
```

Variables verificadas en CMakeCache:
- `GGML_OPENCL_TARGET_VERSION=200`
- `OpenCL_INCLUDE_DIR=$PREFIX/include`
- `OpenCL_LIBRARY=$PREFIX/lib/libOpenCL.so`
- `GGML_OPENCL_USE_ADRENO_KERNELS=ON`

La compilación del backend tras el último parche terminó con código 0. La carga dinámica de `libggml-opencl.so` con `RTLD_NOW` también se verificó correctamente.

## 4. Controlador OpenCL Qualcomm

Se comprobó acceso directo a la biblioteca Qualcomm:
- Plataforma: `QUALCOMM Snapdragon(TM)`.
- Dispositivo: `QUALCOMM Adreno(TM)`.
- Driver: OpenCL 2.0 Qualcomm, Adreno 540, build identificado como `#26c925f`, fecha 10/10/18.
- Extensiones relevantes: `cl_khr_fp16`, `cl_khr_subgroups`.
- No aparece `cl_qcom_reqd_sub_group_size` ni `cl_intel_required_sub_group_size` en la lista de extensiones.
- Subgrupos medidos: tamaño 32; grupo local de 64 contiene dos subgrupos.

El ICD estándar `ocl-icd` no pudo enumerar la biblioteca Qualcomm por incompatibilidad con `clIcdGetPlatformIDsKHR` / `clGetPlatformInfo`; se utilizó acceso directo por ctypes y el wrapper de proveedor de Termux.

## 5. Resultados OpenCL nativo — SÍ FUNCIONA

Se ejecutaron kernels OpenCL independientes mediante ctypes en el Adreno 540:

| Prueba | Resultado |
|---|---|
| Vector kernel | Correcto; salida comprobada |
| GEMM FP32 64×64 | Error máximo 0.000002249 |
| GEMM FP32 tiled 128×128 | 30 repeticiones; 0.364 ms promedio; aprox. 11.52 GFLOP/s; error máximo 0.000006261 |
| FP16 a FP32 | Correcto; error máximo 0 |
| Matvec Q4 personalizado | 32 filas × 1024; 100 repeticiones; 0.1536 ms promedio; error absoluto máximo 2.92e-05; error relativo máximo 7.63e-07 |

El formato Q4 personalizado de esa prueba no debe considerarse equivalente a GGML Q4_0 o Q4_K_M.

## 6. Modificaciones de llama.cpp investigadas

Archivo: `ggml/src/ggml-opencl/kernels/mul_mv_q4_0_f32_8x_flat.cl`.

El driver enumera `cl_khr_subgroups`, pero el preprocesador del kernel no dejó disponibles las macros `N_DST`, `N_SIMDGROUP` y `N_SIMDWIDTH` en el código compilado. Se probaron:
- Selección Adreno mediante `cl_khr_subgroups`.
- Definición de `ADRENO_GPU` desde las opciones de compilación del kernel Q4.
- Parámetros de dos subgrupos de 32 lanes: `N_SIMDGROUP=2`, `N_SIMDWIDTH=32`, `N_DST=8`.
- Como último intento, definición incondicional de esas tres macros después de sus `#undef`.

El parche final fue guardado en el backup `*.pre-final-adreno540`; el código fuente actual conserva el intento fallido y debe inspeccionarse antes de continuar.

También se añadió temporalmente una línea de diagnóstico C++ `Q4_ADRENO_DIAG`; no apareció en el log final. La variable usada en esa inserción debe verificarse antes de reutilizarla: hubo una discrepancia de nombre entre `q4_0_8x_opts` y `q4_0x_opts` en los fragmentos de trabajo.

## 7. Prueba final de llama.cpp — FALLIDA

Comando:

```bash
export LD_LIBRARY_PATH="$PREFIX/opt/vendor/lib:$PREFIX/lib:$HOME/llama.cpp-v1.0.0/build-opencl20/bin"
build-opencl20/bin/llama-simple \
  -m "$HOME/models/Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf" \
  -n 4 -ngl 1 \
  "Responde en español: ¿cuánto es 2 + 2?"
```

Resultado:
- Los tensores del modelo se leyeron; 433 tensores adicionales se reportaron junto a `token_embd.weight`.
- Se emitió el aviso de fallback `CPU_REPACK` a `CPU`.
- El backend comenzó a cargar kernels OpenCL.
- La compilación del kernel falló con `err=-11`.
- Código de salida: **1**.
- No hubo evaluación del prompt ni generación de tokens; no es un fallo de memoria ni una prueba de inferencia GPU.

Errores del compilador:

```text
BC-src-code:108:27: error: use of undeclared identifier 'N_SIMDGROUP'
BC-src-code:108:63: error: use of undeclared identifier 'N_DST'
BC-src-code:119:16: error: use of undeclared identifier 'N_DST'
BC-src-code:127:38: error: use of undeclared identifier 'N_SIMDWIDTH'
BC-src-code:138:33: error: use of undeclared identifier 'N_DST'
BC-src-code:148:24: error: use of undeclared identifier 'N_SIMDWIDTH'
BC-src-code:155:15: error: use of undeclared identifier 'N_DST'
BC-src-code:158:29: error: use of undeclared identifier 'N_DST'
8 diagnostic(s) generated.
EXIT_CODE=1
```

## 8. Interpretación y punto de reanudación

Conclusión limitada a la evidencia: **el Adreno 540 ejecuta cómputo OpenCL nativo, pero esta integración concreta del kernel Q4 de llama.cpp no compila con el driver Qualcomm legado probado**. No concluir que la GPU sea incapaz de ejecutar un LLM.

La investigación queda pausada deliberadamente. No continuar con más parches exploratorios en esta campaña.

Al retomarla:
1. Recuperar el snapshot de fuente, los dos backups del kernel, el log final y el build.
2. Inspeccionar el código fuente exacto que llega a `clCreateProgramWithSource` y las opciones de compilación realmente pasadas; guardar el fuente OpenCL expandido.
3. Probar primero un kernel mínimo que defina explícitamente las macros antes del código, sin modificar más rutas de producción.
4. Mantener separadas las pruebas OpenCL nativas de la validación real de llama.cpp.
5. No declarar inferencia acelerada hasta obtener texto generado y métricas de evaluación/generación.

## 9. Artefactos pendientes de transferencia física

Este documento se ha creado a partir de los datos visibles de la sesión. Los siguientes elementos deben copiarse desde Termux al paquete de evidencias antes de marcar el expediente como completo:

- `$HOME/q4-adreno-final.log` (log íntegro).
- Salida de CMake/Ninja y configuración `build-opencl20/CMakeCache.txt`.
- `build-opencl20/bin/llama-simple`.
- Biblioteca `build-opencl20/bin/libggml-opencl.so*`.
- Fuente completa `mul_mv_q4_0_f32_8x_flat.cl` y sus dos backups.
- Diff completo de `ggml-opencl.cpp` y del kernel.
- Scripts Python/ctypes de pruebas vector, GEMM, FP16 y Q4, junto con sus salidas.
- Versiones de herramientas, hashes y listado de archivos.

No copiar el modelo GGUF ni bibliotecas propietarias del sistema Android. Registrar sus rutas, versiones y hashes cuando proceda, sin redistribuirlas.

**Estado de integridad del expediente:** informe técnico inicial creado; transferencia de binarios/logs completos pendiente. No marcar como archivo físico completo hasta verificar hashes y recuento de ficheros.
