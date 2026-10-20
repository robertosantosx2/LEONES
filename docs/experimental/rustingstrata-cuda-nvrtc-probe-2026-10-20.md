# Prueba exploratoria de RustingStrata con CUDA/NVRTC — 2026-10-20

## Entorno

- Ubuntu nativo; Intel Core i7-12650H, 14 GiB RAM.
- NVIDIA GeForce RTX 3050 Laptop, 4 GiB VRAM.
- Driver NVIDIA 580.178.04; `nvidia-smi` indica CUDA 13.0.
- Clon independiente: `~/rusting-strata-test`.
- Binario compilado: `target/release/strata`.
- Modelo de prueba: `~/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf`.
- SHA-256 del modelo: `c3c2cf023efdbd913c2363a14d5c7266db5e05c4602f1c0790eaed567d8aff23`.

## Incidencia inicial

RustingStrata fallaba al cargar el módulo CUDA con:

```text
CUDA_ERROR_UNSUPPORTED_PTX_VERSION
the provided PTX was compiled with an unsupported toolchain
```

La instalación del sistema usaba NVRTC 13.4.92, que generaba PTX con `.version 9.4`. Cambiar la característica de `cudarc` de `cuda-13010` a `cuda-13000` y regenerar la caché no resolvió por sí solo el error.

## Prueba con NVRTC 13.0 aislado

Se descargó el paquete oficial NVIDIA `cuda-nvrtc-13-0_13.0.88-1_amd64.deb` y se extrajo, sin instalarlo en el sistema, en:

```text
~/rusting-strata-test/vendor/nvrtc13/root/usr/local/cuda-13.0/targets/x86_64-linux/lib
```

Se añadió el enlace simbólico `libnvrtc.so -> libnvrtc.so.13.0.88` y se ejecutó:

```bash
cd "$HOME/rusting-strata-test"
NVRTC_DIR="$PWD/vendor/nvrtc13/root/usr/local/cuda-13.0/targets/x86_64-linux/lib"
MODEL="$HOME/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf"

LD_LIBRARY_PATH="$NVRTC_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
XDG_CACHE_HOME="$PWD/vendor/nvrtc13/cache-1300" \
LD_DEBUG=libs \
./target/release/strata generate \
  --model "$MODEL" --gpu --ctx 512 \
  --prompt "Responde en español: explica brevemente qué es un modelo de lenguaje local." \
  -n 32 > /tmp/rustingstrata-test.log 2>&1

echo "Código de salida: $?"
grep -E 'calling init: .*libnvrtc|Error:|UNSUPPORTED_PTX|load PTX' \
  /tmp/rustingstrata-test.log | tail -25
tail -25 /tmp/rustingstrata-test.log
```

## Resultado observado

- Código de salida reportado: `0`.
- `LD_DEBUG=libs` confirmó la carga de la biblioteca aislada `vendor/nvrtc13/.../libnvrtc.so` y de `libnvrtc-builtins.so.13.0`.
- En la salida compartida no aparece el texto generado: el `tail` mostró principalmente mensajes de finalización del cargador dinámico. Por tanto, todavía no se afirma que la generación haya producido una respuesta coherente.
- No se ha medido velocidad, TTFT ni VRAM pico de RustingStrata. No comparar su rendimiento con TensorFold o llama.cpp hasta confirmar una respuesta real y repetir la prueba con telemetría.
- El archivo de log permanece local en `/tmp/rustingstrata-test.log`; no se ha subido al repositorio.

## Siguiente verificación

Inspeccionar el log completo buscando las líneas del prompt, texto de respuesta, errores de modelo y métricas. Si no contiene respuesta, repetir sin `LD_DEBUG=libs` para obtener un log limpio, manteniendo `LD_LIBRARY_PATH` y `XDG_CACHE_HOME`. No instalar ni reemplazar las bibliotecas CUDA globales para esta prueba.

## Estado

**Carga de NVRTC 13.0: confirmada. Proceso sin error fatal según código de salida: confirmado. Inferencia coherente de extremo a extremo: pendiente de confirmación.**
