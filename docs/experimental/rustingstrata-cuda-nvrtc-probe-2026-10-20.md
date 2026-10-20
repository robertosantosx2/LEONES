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

### Inferencia y API

La prueba posterior confirmó inferencia real, no solo carga de bibliotecas:

- `strata serve --model "$MODEL" --gpu --ctx 1024 --addr 127.0.0.1:18083` inició el servidor.
- `GET /v1/models` devolvió el modelo `qwen3.5-4b-Q4_K_M`.
- `POST /v1/chat/completions` devolvió HTTP 200 y una respuesta coherente en español. La respuesta registró 30 tokens de prompt, 32 tokens de completion y 62 tokens totales.
- El servidor se detuvo tras la prueba. Una captura posterior de `nvidia-smi` mostró 15 MiB de uso total de GPU y solo Xorg en la lista de procesos.

### Benchmark GPU

Comando usado:

```bash
LD_LIBRARY_PATH="$NVRTC_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
XDG_CACHE_HOME="$PWD/vendor/nvrtc13/cache-1300" \
timeout 300 ./target/release/strata bench \
  --model "$MODEL" --gpu --pp 128,512 --tg 64 --reps 3 --ctx 1024
```

Resultados del benchmark de RustingStrata:

| Prompt | Prefill medio (rango) | Decode medio (rango) |
|---:|---:|---:|
| 128 tokens | 915,3 (906,2–925,6) tok/s | 46,6 (46,5–46,7) tok/s |
| 512 tokens | 986,5 (985,6–988,0) tok/s | 46,1 (46,1–46,2) tok/s |

El plan de memoria del motor indicó 2.752 MB para pesos/estado/scratch y 32 MB de KV para contexto 1.024. Durante la prueba del servidor, el proceso usó 2.928 MiB según `nvidia-smi`; no se midió el pico de VRAM del benchmark.

### Arquitectura y expertos

La consulta:

```bash
python3 "$HOME/llama.cpp-cuda/gguf-py/gguf/scripts/gguf_dump.py" "$MODEL" \
  | grep -iE 'general.architecture|expert_count|expert_used_count|feed_forward_length'
```

no produjo líneas de metadatos en la salida compartida. Por tanto, **la arquitectura densa/MoE sigue sin verificarse**. El registro `resident experts 0/0` no es suficiente para concluir que el modelo sea denso; primero hay que leer correctamente los metadatos del GGUF.

### Estado

- **NVRTC 13.0.88 aislado cargado:** confirmado.
- **Generación GPU local:** confirmada.
- **API OpenAI-compatible no-streaming:** confirmada para `/v1/models` y `/v1/chat/completions`.
- **Benchmark integrado:** completado con tres repeticiones por tamaño de prompt.
- **Comparación controlada con llama.cpp/TensorFold:** pendiente.
- **Integración E2E con ODS, Magnitude, OpenBot o LEONES Runtime:** pendiente.
- **Licencia de RustingStrata:** no verificada.

## Próximas verificaciones

1. Obtener `general.architecture`, `expert_count` y `expert_used_count` con una herramienta de inspección GGUF compatible.
2. Ejecutar llama.cpp con un protocolo equivalente y varias repeticiones antes de inferir una ventaja de rendimiento.
3. Probar streaming y una integración real con un cliente antes de ampliar el estado de compatibilidad.
