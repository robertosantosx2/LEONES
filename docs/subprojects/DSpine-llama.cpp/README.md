# DSpine en llama.cpp — auditoría y validación

**Estado:** integración estática encontrada en el fork; pendiente build reproducible y ejecución física.  
**Rama LEONES:** `research/dspine-llama-cpp`.

## Fuentes primarias

- [Tencent/DSpine](https://github.com/Tencent/DSpine): implementación de referencia SGLang y MLX.
- [Paper arXiv:2609.36173](https://arxiv.org/abs/2609.36173).
- [Ajay9o9/llama.cpp, rama dspine](https://github.com/Ajay9o9/llama.cpp/tree/dspine).
- [Drafter oficial Qwen3-8B](https://huggingface.co/tencent/Qwen3-8B-DSpine-b16).
- [Drafter oficial Qwen3.8-27B](https://huggingface.co/tencent/Qwen3.8-27B-DSpine-b16).
- [Conversión GGUF comunitaria Qwen3.8-27B](https://huggingface.co/aj9o9/Qwen3.8-27B-DSpine-b16-GGUF).

## Hallazgo clave: cómo está integrado

El fork **sí implementa DSpine**, pero lo integra como una extensión de la familia de drafter DFlash. No registra un tipo CLI independiente `draft-dspine`.

La ruta de ejecución usa `--spec-type draft-dflash` con el checkpoint DSpine GGUF. El modelo DFlash reconoce los tensores DSpine y construye el grafo específico; el runtime especulativo existente consume la lattice producida por el drafter. Por tanto, no hay que confundir el nombre de dispatch genérico con la semántica del grafo ejecutado.

Evidencia inspeccionada directamente en `Ajay9o9/llama.cpp@dspine`:

| Archivo | Evidencia |
|---|---|
| `gguf-py/gguf/constants.py` | enum y nombres de tensores `DSPINE_CODEBOOK/GATE/PRED_GATE/PREV/READ/WRITE` |
| `gguf-py/gguf/tensor_mapping.py` | mapeo de `selected_prefix_bridge.codebook/gate/predecessor_gate/prev/read/write` |
| `src/llama-model.h` | campos `dspine_codebook`, `dspine_gate`, `dspine_read`, `dspine_write` |
| `src/models/dflash.cpp` | carga/validación de tensores DSpine y dimensiones |
| `src/models/dflash.cpp` | `build_dspine_write()`: puente de código adyacente por capa |
| `src/models/dflash.cpp` | `build_dspine_lattice()`: refinamiento serial/top-k de candidatos |
| `src/models/dflash.cpp` | llamada al puente dentro del bucle de capas y construcción de la lattice al final |
| `common/speculative.cpp` | ruta `draft-dflash` y consumo de `llama_get_embeddings_nextn()` para el selector/lattice |

Blobs de referencia consultados:
- `src/models/dflash.cpp`: `18a5c380fd064bb88df046e7c50ab191ae8924fa`
- `gguf-py/gguf/constants.py`: `3fabed534e335af417f0afd65f36509da1855f21`
- `gguf-py/gguf/tensor_mapping.py`: `5dd8c85be6ab3397085aa4b979c0548a0843309c`
- `src/llama-model.h`: `26307432ffd7ab634430da79a19bde83f7855302`
- `common/speculative.cpp`: `e6290eaad7765abcdff7c778a17e78d21244ddd1`

Son blob SHAs, no el SHA del commit completo. El script de auditoría registra el commit exacto que clona.

## Comportamiento del grafo

1. El loader reconoce el modelo de arquitectura DFlash y detecta tensores de codebook/gate DSpine.
2. Valida dimensiones y exige el selector top-k y bloque compatibles.
3. Carga codebook, gates y pesos read/write por capa.
4. Durante el forward, cada capa ejecuta `build_dspine_write()` cuando existe el peso de escritura.
5. El grafo guarda el estado previo a la última escritura.
6. Al final, `build_dspine_lattice()` vuelve a evaluar el último puente sobre candidatos top-k y produce la lattice.
7. El runtime especulativo lee la lattice por `llama_get_embeddings_nextn()` y recorre las puntuaciones condicionadas por el predecesor.

Esto demuestra una ruta de código DSpine específica, no solo el registro de nombres de tensores.

## Parejas objetivo/drafter disponibles

| Objetivo | Drafter | Observación |
|---|---|---|
| Qwen3-8B | `tencent/Qwen3-8B-DSpine-b16` | Checkpoint oficial Safetensors; conversor del fork implementado en `conversion/qwen.py` |
| Qwen3.8-27B | `tencent/Qwen3.8-27B-DSpine-b16` | Checkpoint oficial Safetensors |
| Qwen3.8-27B | `aj9o9/Qwen3.8-27B-DSpine-b16-GGUF` | Conversión GGUF comunitaria explícitamente destinada al fork |

El fork implementa conversión HF→GGUF en `conversion/qwen.py` (`DFlashModel._is_dspine()` y `_modify_dspine_tensors()`). Requiere directorios locales y `--target-model-dir` para heredar tokenizer/embeddings del target.

Ejemplo: `python convert_hf_to_gguf.py ./models/Qwen3-8B-DSpine-b16 --target-model-dir ./models/Qwen3-8B --outtype bf16 --outfile Qwen3-8B-DSpine-b16.gguf`. LEONES incluye `scripts/prepare_qwen3_8b_dspine_gguf.sh` para convertir y verificar los tensores `dspine_*`. El drafter no es autónomo: necesita su modelo objetivo correspondiente. No intercambiar parejas entre familias.

## Estado para MSI Thin 15 B12UC

Perfil LEONES: i7-12650H, RTX 3050 Laptop 4 GiB (SM 8.6), 14 GiB RAM, Ubuntu.

- La pareja Qwen3.8-27B no es una candidata razonable para 4 GiB VRAM y 14 GiB RAM.
- La pareja Qwen3-8B es la candidata más pequeña oficialmente publicada, y el fork permite convertir el drafter Safetensors a GGUF. El target de 8B también requiere planificación de memoria.
- El fork tiene una build CPU y CUDA, pero la compilación CPU no demuestra que la ruta CUDA ni la pareja de modelos funcionen.
- No descargar ni ejecutar todavía. Primero ejecutar CI, revisar las instrucciones de uso exactas del GGUF y calcular el footprint real de los ficheros elegidos.
- La validación MSI deberá ser aislada, con build en directorio separado, modelo/contexto pequeño, límites de memoria, rollback y medición frente a baseline sin speculative.

## Estados de evidencia

- `SOURCE-VERIFIED`: código específico de DSpine localizado y seguido estáticamente.
- `CI-PASSED`: build/tests en CI con commit y logs.
- `MSI-MEASURED`: ejecución física en el MSI real.
- `PERFORMANCE-MEASURED`: comparación repetible con la misma pareja, prompt, contexto, sampler y backend.

No marcar la funcionalidad como validada por el mero hecho de compilar el fork.

## Fases

1. **Completada:** inspección de tensores, loader, code bridge, lattice y dispatch especulativo.
2. **En curso:** auditor estático automatizado y pruebas unitarias en LEONES.
3. **Pendiente:** build CPU del fork y build CUDA/SM86 en CI adecuado.
4. **Completada:** confirmar y automatizar conversión GGUF de Qwen3-8B; falta ejecutarla sobre los checkpoints exactos.
5. **Pendiente:** gate de memoria y comandos reproducibles.
6. **Pendiente:** ejecución física y benchmark en MSI.
