# ThumbLLM en Ubuntu: auditoría y reproducción de la edición Qwen3.5-4B CPU

**Estado:** guía de reproducción en curso. La release upstream indicada es un ejecutable Windows x64; no debe tratarse como un binario Linux ni como prueba de que la interfaz de escritorio ya funciona en Ubuntu.

- Proyecto upstream: https://github.com/TeksEdge/ThumbLLM
- Release solicitada: https://github.com/TeksEdge/ThumbLLM/releases/tag/thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0
- Receta publicada: https://github.com/TeksEdge/ThumbLLM/blob/thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0/recipes/Qwen3.5-4-MTP-Q4_K_M-CPU-Win-x64/README.md
- Modelo: https://huggingface.co/unsloth/Qwen3.5-4B-MTP-GGUF
- Licencia del modelo declarada en la receta: Apache-2.0.
- Commit del runtime usado por la release: `c060ca974`, build `10603`, llama.cpp `0.2.0-dev`, originalmente compilado con Clang 20.1.8 para Windows x86_64.
- SHA-256 declarado del GGUF: `3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630`.
- SHA-256 declarado del ejecutable Windows: `FC1446F802A98869746FC24EF7B5E88561336399A0E8EEF01C0A11508427739D`. Este hash solo sirve para validar ese artefacto Windows, no una compilación Linux.

## 1. Qué hace ThumbLLM

ThumbLLM no es solamente un modelo: combina una aplicación de chat de escritorio, un runtime llama.cpp fijado, una receta de inferencia específica, descarga/reanudación del GGUF, validación del encabezado GGUF y verificación SHA-256, métricas de generación y una API compatible con OpenAI.

La API documentada para esta edición escucha por defecto solo en `127.0.0.1:8080`, con base `http://127.0.0.1:8080/v1`. Endpoints documentados: `POST /v1/chat/completions`, `GET /v1/models` y `GET /health`. La receta indica autenticación desactivada: mantener el servicio ligado a localhost y no exponerlo a la LAN sin añadir primero controles de acceso.

## 2. Hallazgo importante: MTP NO está activo en esta release

Aunque el nombre del repositorio Hugging Face contiene `MTP`, la receta de ThumbLLM declara `SPEC_TYPE = none` y no pasa argumentos de speculative decoding al servidor. Por tanto, la reproducción fiel de esta versión es **Qwen3.5-4B Q4_K_M en CPU con MTP especulativo desactivado**. Activar MTP sería un experimento separado y requeriría un runtime compatible y pruebas A/B; no se debe atribuir al ejecutable de la release el beneficio de MTP.

## 3. Parámetros originales de inferencia

La receta publica los siguientes valores:

| Parámetro | Valor publicado |
|---|---|
| Backend | CPU solamente |
| Dispositivo / capas GPU | `--device none`, `--gpu-layers 0` |
| Contexto | 65.536 tokens |
| Máximo de generación configurado | 12.288 tokens |
| Threads de decode | automáticos: núcleos físicos detectados |
| Threads de prompt/batch | automáticos: procesadores lógicos detectados |
| Batch / microbatch | 2048 / 512 |
| Flash Attention | activado |
| Caché K / V | `q4_0` / `q4_0` |
| mmap / repack | activados |
| mlock | desactivado |
| KV / operation GPU offload | desactivados |
| Slots paralelos | 1 |
| Temperature / top-p | 0.7 / 0.9 |
| API | localhost, puerto 8080 |
| Razonamiento | interfaz en modo no-thinking por defecto según la receta |

La receta declara un sistema de prueba AMD Ryzen AI Max+ 395, 16 núcleos/32 hilos, Windows x64. Solo documenta una observación de aplicación de 18.0 tok/s durante una generación todavía activa; no registra prompt processing, tiempos nativos de decode, RAM máxima ni una prueba controlada con varias repeticiones. No comparar esa cifra como si fuese un benchmark nativo de llama.cpp.

## 4. Clonar el código fuente upstream en Ubuntu

Estos comandos están destinados a ejecutarse en el Ubuntu del usuario; ChatGPT no tiene acceso directo a su disco local. Se usa una carpeta separada de LEONES y no se toca `experimental/companion-hub`.

```bash
set -euo pipefail
mkdir -p "$HOME/src"
cd "$HOME/src"
git clone https://github.com/TeksEdge/ThumbLLM.git
cd ThumbLLM
git fetch --tags --prune
git tag -l '*qwen3.5*4b*'
git status --short --branch
git ls-tree -r --name-only thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0 | less
```

Si el tag exacto existe en el remoto, se puede inspeccionar sin alterar la rama principal:

```bash
git switch --detach thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0
git log -1 --oneline --decorate
```

Antes de compilar la aplicación completa, revisar los archivos fuente, manifiestos de dependencias, instrucciones de empaquetado, recursos, licencias y scripts de build. La release .exe de Windows no se puede ejecutar de forma nativa en Ubuntu. Si el código fuente depende de APIs de Windows, será necesario portar esas partes o implementar un frontend Linux equivalente; no basta con renombrar el ejecutable.

## 5. Preparar un runtime llama.cpp Linux CPU

La receta fija el runtime en el commit `c060ca974`. Para reproducir ese runtime en un directorio separado:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git curl ca-certificates
mkdir -p "$HOME/src"
git clone https://github.com/ggml-org/llama.cpp.git "$HOME/src/llama.cpp-thumbllm"
git -C "$HOME/src/llama.cpp-thumbllm" checkout c060ca974
cmake -S "$HOME/src/llama.cpp-thumbllm" \
  -B "$HOME/src/llama.cpp-thumbllm/build" \
  -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=OFF
cmake --build "$HOME/src/llama.cpp-thumbllm/build" \
  --config Release -j2 --target llama-server llama-cli
"$HOME/src/llama.cpp-thumbllm/build/bin/llama-server" --version
```

Este paso compila un runtime Linux CPU; **no compila por sí mismo la interfaz ThumbLLM**. Si el commit no compila con las herramientas actuales, registrar el error exacto y probar primero el toolchain/documentación requeridos por ese commit antes de cambiar de revisión.

## 6. Descargar y verificar el modelo

La receta upstream declara un GGUF de unos 2,83 GB, separado del ejecutable:

```bash
set -euo pipefail
MODEL_DIR="$HOME/models/thumbllm-qwen35-4b"
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"
curl -fL --retry 8 --retry-delay 2 -C - \
  -o Qwen3.5-4B-Q4_K_M.gguf \
  'https://huggingface.co/unsloth/Qwen3.5-4B-MTP-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf'
printf '%s  %s\n' \
  '3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630' \
  'Qwen3.5-4B-Q4_K_M.gguf' | sha256sum -c -
```

No usar el modelo si el hash no coincide. La release también menciona validación del encabezado GGUF; el SHA-256 verifica la integridad del archivo completo, pero no sustituye la comprobación de arquitectura/compatibilidad del runtime.

## 7. Prueba inicial segura en el Ubuntu de destino

Empieza con contexto 8192, no con los 65536 tokens de la receta Windows. Ajusta la memoria disponible después de verificar carga y consumo. El sistema de destino documentado para LEONES tiene aproximadamente 14,8 GiB de RAM y una RTX 3050 Laptop de 4 GiB; este perfil debe usar CPU explícitamente y no ocupar la GPU ni alterar los servicios llama-server ya existentes.

```bash
set -euo pipefail
LLAMA="$HOME/src/llama.cpp-thumbllm/build/bin/llama-server"
MODEL="$HOME/models/thumbllm-qwen35-4b/Qwen3.5-4B-Q4_K_M.gguf"
"$LLAMA" \
  --model "$MODEL" \
  --host 127.0.0.1 --port 18088 \
  --ctx-size 8192 \
  --threads 10 --threads-batch 16 \
  --batch-size 2048 --ubatch-size 512 \
  --gpu-layers 0 --device none \
  --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --no-kv-offload --no-op-offload \
  --repack --mmap --parallel 1
```

El número 10/16 es un punto de partida conservador para el hardware del usuario (logs anteriores indicaban 10 núcleos físicos detectados y 16 procesadores lógicos). Confirmar opciones aceptadas con `"$LLAMA" --help`: los flags disponibles pueden variar por commit/plataforma. Se usa el puerto 18088 para evitar colisionar con el puerto 8080 documentado por ThumbLLM y con servicios ODS/LEONES existentes.

En otra terminal, comprobar que responde:

```bash
curl --fail http://127.0.0.1:18088/health
curl --fail http://127.0.0.1:18088/v1/models
curl --fail http://127.0.0.1:18088/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3.5-4B-Q4_K_M.gguf","messages":[{"role":"user","content":"Responde solo: ThumbLLM Linux OK"}],"temperature":0,"max_tokens":32}'
```

Si el alias del modelo difiere, usar el que devuelve `/v1/models`. No abrir el host a `0.0.0.0`: la receta original se limita a localhost y no configura autenticación.

## 8. Cómo reproducir la aplicación, no solo el modelo

La equivalencia funcional completa exige reproducir o portar estas partes desde el código fuente upstream:

1. Interfaz de chat con streaming, cancelación y control del contexto.
2. Gestión del proceso llama-server (arranque, readiness, apagado limpio y errores).
3. API local compatible con OpenAI.
4. Descarga reanudable con HTTP Range, reintentos/backoff, manejo de espacio libre y limpieza de temporales.
5. Validación GGUF y verificación SHA-256 antes de aceptar el modelo.
6. Detección de hardware y selección de threads por topología CPU.
7. Métricas claramente definidas: separar tokens realmente generados, TTFT, prompt tok/s, decode tok/s, duración total y memoria máxima.
8. Pruebas automáticas de endpoints, integridad de descarga, interrupción/reanudación, apagado y ausencia de exposición de red no deseada.

No copiar binarios Windows, DLL de Windows ni sus hashes como si fueran artefactos Ubuntu. Compilar y publicar un binario Linux requerirá un proceso de build propio y registrar hashes nuevos.

## 9. Protocolo de benchmark para LEONES

- Registrar CPU, núcleos/hilos, RAM, swap, kernel, commit llama.cpp y hash del GGUF.
- Calentar el modelo y ejecutar al menos 3 repeticiones medidas con prompt y generación fijos.
- Mantener temperatura 0 y el mismo prompt/longitud al comparar configuraciones.
- Guardar log completo y métricas nativas de llama.cpp: prompt tokens/s, decode tokens/s, tiempo de carga, TTFT y RSS máxima.
- Comparar primero una línea base CPU sin speculative decoding; evaluar MTP en una rama/experimento aparte.
- Probar contextos 4096/8192 antes de 16384/65536 por el límite de RAM del portátil.
- No usar los 18 tok/s de la captura upstream como objetivo garantizado ni como comparación directa: el hardware y la medición son distintos.

## 10. Pendientes para considerar la réplica terminada

- [ ] Clonar y archivar el código fuente upstream y registrar commit/tag exactos.
- [ ] Auditar dependencias, scripts de build y licencia de cada componente.
- [ ] Compilar llama.cpp CPU Linux y verificar versión/flags disponibles.
- [ ] Verificar SHA-256 y metadatos del GGUF.
- [ ] Probar API localhost y generar una respuesta de extremo a extremo.
- [ ] Portar/implementar el frontend de escritorio para Linux.
- [ ] Añadir pruebas de descarga reanudable, cancelación, apagado limpio y seguridad de red.
- [ ] Medir 3+ ejecuciones repetibles en el hardware real.
- [ ] Documentar comandos, logs, hashes y resultados en LEONES.

**Conclusión:** los datos de la receta permiten reproducir la configuración de inferencia CPU de la release; la réplica integral de ThumbLLM en Ubuntu requiere además clonar y auditar su código de aplicación y portar/compilar su frontend. No se afirma que la aplicación Linux esté ya compilada o probada.
