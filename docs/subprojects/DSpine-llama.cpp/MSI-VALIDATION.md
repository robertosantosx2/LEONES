# Handoff de validación DSpine en MSI

**No ejecutar hasta que el PR #143 tenga CI verde y el artefacto GGUF validado.** Esta guía evita tocar el llama.cpp ya instalado.

## Pareja seleccionada

- Target: Qwen3.8-27B GGUF **IQ2_XXS**, publicado por bartowski (8.88 GB).
- Drafter: Qwen3.8-27B-DSpine-b16 GGUF **Q4_K_M**, publicado para el fork (1.26 GB).
- Algoritmo: \`--spec-type draft-dflash\`; DSpine está integrado en el grafo DFlash y se activa por los tensores del drafter.
- Primera pasada: greedy, contexto 512, una secuencia, bloque especulativo de 3 tokens.
- No usar el target Q4_K_M de 17.44 GB en el MSI.

**Importante:** el checkpoint oficial Qwen3-8B-DSpine-b16 no es compatible con el port actual. Su config carece de \`code_bridge_second_pass.mode=serial_table\` y de un \`head_topk\` de refinamiento. La conversión falló con el rechazo explícito del conversor; no se deben inventar esos metadatos.

## Estimación de memoria previa

| Fichero | Tamaño |
|---|---:|
| Qwen3.8-27B IQ2_XXS target | 8.88 GB |
| Qwen3.8-27B DSpine Q4_K_M drafter | 1.26 GB |
| **Pesos combinados** | **10.14 GB** |

Es una estimación de almacenamiento de pesos, no de memoria residente. KV, buffers, allocator, contexto y runtime se añaden encima. Los 4 GiB de VRAM no pueden alojar la pareja completa: se necesita offload híbrido CPU/GPU. Los 14 GiB de RAM podrían permitir un contexto muy corto, pero no está demostrado.

La cuantización IQ2_XXS es muy agresiva y degrada la calidad; este primer ensayo solo determina si el runtime funciona y si la memoria cabe. No usarlo como evaluación de calidad del modelo.

Fuentes:
- [Target Qwen3.8-27B IQ2_XXS](https://huggingface.co/bartowski/Qwen3.8-27B-GGUF)
- [Drafter DSpine Q4_K_M](https://huggingface.co/aj9o9/Qwen3.8-27B-DSpine-b16-GGUF)

## 0. Puerta previa

1. Revisar que los jobs \`audit-and-build\` y \`verify-qwen3-8-27b-dspine\` del workflow \`DSpine llama.cpp audit\` hayan terminado correctamente.
2. Descargar el artefacto \`qwen3.8-27b-dspine-b16-q4km-gguf\` de GitHub Actions y verificar su SHA-256 con el informe incluido.
3. Descargar el target IQ2_XXS:
   ~~~bash
   mkdir -p ~/models/qwen3.8-27b
   hf download bartowski/Qwen3.8-27B-GGUF Qwen3.8-27B-IQ2_XXS.gguf --local-dir ~/models/qwen3.8-27b
   ~~~
4. Comprobar tamaño y SHA-256 de ambos ficheros.
5. Ejecutar \`scripts/dspine-msi-preflight.sh\` y conservar el informe.

## 1. Compilación aislada

El fork debe residir en un directorio separado. No reutilizar ni sobrescribir \`~/llama-cpp-cuda\` ni los binarios de \`/usr/local/bin\`.

El script \`scripts/build_dspine_llama_cpp_cuda_msi.sh\`:
- exige Git, CMake, nvcc, nvidia-smi y C++;
- aborta si ya existe el directorio destino;
- obtiene el commit fijado d493f841b20241606c47a4e0537d3c786b5cf50b en ~/src/llama.cpp-dspine;
- configura CUDA para \`SM86\` explícitamente;
- compila \`llama-server\`, \`llama-cli\` y \`llama-quantize\` con dos trabajos por defecto;
- guarda el SHA del fork y un log completo;
- no instala ni sustituye binarios existentes.

Ejecutar solo después de revisar el preflight:

~~~bash
bash scripts/build_dspine_llama_cpp_cuda_msi.sh
~~~

Si CUDA Toolkit, CMake o el compilador no son compatibles, detenerse y resolverlo antes de seguir.

## 2. Preflight de modelos y memoria

- Confirmar que el target es Qwen3.8-27B y el drafter es Qwen3.8-27B-DSpine-b16.
- Revisar \`nvidia-smi\` inmediatamente antes de iniciar.
- Empezar con \`-c 512\`, \`-np 1\` y \`--spec-draft-n-max 3\`.
- Elegir explícitamente \`-ngl\` y \`--spec-draft-ngl\` según VRAM disponible; no copiar \`999\` del ejemplo de RTX 3090.
- Usar KV Q8_0 en target y drafter para reducir presión de memoria.
- Mantener una ruta de rollback simple: cerrar el servidor y borrar únicamente el directorio aislado \`~/src/llama.cpp-dspine\` si fuera necesario.
- No habilitar swap deliberadamente para forzar la carga.

## 3. Primera ejecución controlada

Plantilla parametrizada; no ejecutar hasta fijar las rutas y offload counts a partir del preflight:

~~~bash
TARGET=~/models/qwen3.8-27b/Qwen3.8-27B-IQ2_XXS.gguf
DRAFT=/ruta/Qwen3.8-27B-DSpine-b16-Q4_K_M.gguf
TARGET_NGL=<capas_target>
DRAFT_NGL=<capas_drafter>

~/src/llama.cpp-dspine/build-cuda/bin/llama-server \\
  -m "$TARGET" \\
  -md "$DRAFT" \\
  --spec-type draft-dflash \\
  --spec-draft-n-max 3 \\
  -ngl "$TARGET_NGL" \\
  --spec-draft-ngl "$DRAFT_NGL" \\
  --cache-type-k q8_0 \\
  --cache-type-v q8_0 \\
  --spec-draft-type-k q8_0 \\
  --spec-draft-type-v q8_0 \\
  -fa on \\
  -c 512 \\
  -np 1 \\
  --host 127.0.0.1 \\
  --port 18089
~~~

El valor de las dos variables se decide con el preflight y el log de carga. Si no cabe, reducir primero offload/contexto y registrar el resultado; no continuar si hay OOM o presión sostenida de swap.

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
- la generación greedy no coincide con el baseline;
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
