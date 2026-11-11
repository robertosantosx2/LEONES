# Handoff de validación DSpine en MSI

**No ejecutar hasta que el PR #143 tenga CI y artefacto GGUF validados.** Esta guía evita tocar el llama.cpp que ya está instalado.

## Candidato

- Target: Qwen3-8B GGUF Q4_K_M.
- Drafter: Qwen3-8B-DSpine-b16 convertido a GGUF BF16 por el workflow de LEONES.
- Algoritmo: \`--spec-type draft-dflash\` (la implementación DSpine está integrada en el grafo DFlash y se activa por los tensores del drafter).
- Primera pasada: greedy, contexto corto, una secuencia y pocos tokens especulativos.
- No usar Qwen3.8-27B en la RTX 3050 de 4 GiB.

## 0. Puerta previa

1. Revisar el resultado de los dos jobs del workflow \`DSpine llama.cpp audit\`.
2. Descargar el artefacto \`qwen3-8b-dspine-b16-bf16-gguf\` desde GitHub Actions y verificar SHA-256.
3. Tener el target Qwen3-8B Q4_K_M GGUF local. Si falta, descargarlo explícitamente:
   ```bash
   mkdir -p ~/models/qwen3-8b
   hf download Qwen/Qwen3-8B-GGUF qwen3-8b-q4_k_m.gguf --local-dir ~/models/qwen3-8b
   ```
4. No convertir ni descargar el target HF completo en el MSI si el artefacto draft ya está validado.
5. Ejecutar \`scripts/dspine-msi-preflight.sh\` y conservar el informe.

## 1. Compilación aislada

El fork debe residir en un directorio separado. No reutilizar ni sobrescribir \`~/llama-cpp-cuda\` ni los binarios de \`/usr/local/bin\`.

~~~bash
mkdir -p ~/src
git clone -b dspine --depth 1 https://github.com/Ajay9o9/llama.cpp.git ~/src/llama.cpp-dspine
cd ~/src/llama.cpp-dspine
git rev-parse HEAD

cmake -S . -B build-cuda \\
  -DGGML_CUDA=ON \\
  -DCMAKE_BUILD_TYPE=Release

cmake --build build-cuda --target llama-server llama-cli llama-quantize -j2
~~~

El número de trabajos se mantiene bajo para respetar los 14 GiB de RAM. Si el preflight muestra que CUDA Toolkit, CMake o compilador no son compatibles, detenerse y resolverlo antes de compilar.

## 2. Preflight de modelos y memoria

- Comprobar el tamaño real de ambos GGUF con \`ls -lh\`.
- Comprobar SHA-256 de target y drafter.
- Revisar \`nvidia-smi\` inmediatamente antes de iniciar.
- Confirmar que el proceso no compite con otro runtime GPU importante.
- Empezar con \`-c 1024\`, \`-np 1\` y \`--spec-draft-n-max 3\`.
- Elegir explícitamente \`-ngl\` y \`--spec-draft-ngl\` según VRAM disponible; no copiar \`999\` del ejemplo de RTX 3090.
- Mantener una ruta de rollback simple: cerrar el servidor y borrar únicamente el directorio aislado \`~/src/llama.cpp-dspine\` si fuera necesario.

## 3. Primera ejecución controlada

Plantilla deliberadamente parametrizada; no ejecutar hasta fijar las rutas y los offload counts a partir del preflight:

~~~bash
TARGET=/ruta/Qwen3-8B-Q4_K_M.gguf
DRAFT=/ruta/Qwen3-8B-DSpine-b16-BF16.gguf
TARGET_NGL=<capas_target>
DRAFT_NGL=<capas_drafter>

~/src/llama.cpp-dspine/build-cuda/bin/llama-server \\
  -m "$TARGET" \\
  -md "$DRAFT" \\
  --spec-type draft-dflash \\
  --spec-draft-n-max 3 \\
  -ngl "$TARGET_NGL" \\
  --spec-draft-ngl "$DRAFT_NGL" \\
  -fa on \\
  -c 1024 \\
  -np 1 \\
  --host 127.0.0.1 \\
  --port 18089
~~~

El comando no fija offload arbitrariamente. El valor de las dos variables se decide con el preflight y el log de carga. Si no cabe, reducir primero offload/contexto y registrar el resultado; no activar swap como sustituto de VRAM.

## 4. Smoke test

Con el servidor sano, realizar una sola petición local compatible con la API OpenAI y registrar:
- respuesta HTTP;
- tokens de entrada/salida;
- tiempo total y tokens/s;
- log de carga que confirme DSpine code bridge y selector/lattice;
- VRAM máxima y RAM/swap;
- SHA de target, drafter, binario y commit.

Después ejecutar el mismo prompt y configuración contra el mismo target sin \`-md\`/speculative. La comparación debe usar misma seed, sampler, contexto y temperatura.

## 5. Criterios de parada

Detenerse si:
- el loader no detecta los tensores DSpine;
- faltan capas read/write o hay warnings de tensor no usado;
- la generación no coincide con el baseline greedy;
- hay OOM, CUDA error, corrupción de KV o caída del servidor;
- el proceso consume swap de forma sostenida o el sistema pierde estabilidad.

No pasar a sampling probabilístico ni a contextos mayores hasta superar greedy.

## 6. Evidencia LEONES

Guardar:
- preflight del MSI;
- commit SHA y build log;
- versiones de driver/CUDA/CMake/compiler;
- SHA-256 de ambos GGUF y binario;
- logs completos del servidor;
- request/response JSON;
- telemetría GPU/RAM;
- baseline y DSpine medidos con al menos tres repeticiones.

Etiquetas:
- \`SOURCE-VERIFIED\`: código auditado.
- \`CI-PASSED\`: workflow verde.
- \`MSI-MEASURED\`: smoke test real en el portátil.
- \`PERFORMANCE-MEASURED\`: comparativa controlada.

Una build CUDA correcta no equivale a generación funcional; una generación correcta no equivale a aceleración.
