# Validación de la integración DSpine en llama.cpp

**La implementación del port ya existe en el fork Ajay9o9/llama.cpp.** Este documento fija cómo validar su ruta real antes de trasladar cualquier build al MSI.

## Contrato observado

La integración utiliza el modelo DFlash como arquitectura contenedora, con tensores DSpine opcionales. El checkpoint GGUF contiene los pesos del puente de código y la configuración DFlash de bloque/selector.

### Tensores del puente

- Globales: `dspine_codebook`, `dspine_gate`, `dspine_gate_b`, `dspine_pred_gate`, `dspine_prev`.
- Por capa: `blk.{bid}.dspine_read`, `blk.{bid}.dspine_write`.
- Mapeo HF: `model.selected_prefix_bridge.*` y `model.layers.{bid}.selected_prefix_bridge.*`.

### Grafo

- `build_dspine_write()`: obtiene códigos normalizados de cada fila, usa el codebook en la fila ancla, calcula un mensaje gated desde la fila predecesora y aplica el delta mediante el peso write de esa capa.
- `build_dspine_lattice()`: reconstruye el último write para candidatos top-k condicionados por el predecesor y empaqueta candidatos/puntuaciones para el verificador.
- El grafo invoca el write durante cada capa que tenga el tensor y construye la lattice al final si existe `model.dspine_codebook`.

### Runtime

El CLI usa el tipo especulativo `draft-dflash`. La clase compartida reconoce el selector top-k y consume `llama_get_embeddings_nextn()`; el modelo DSpine proporciona la lattice especializada desde el grafo. No añadir un tipo CLI ficticio `draft-dspine` salvo que el upstream lo adopte por separado.

## Validación necesaria

### 1. Integridad del checkpoint

- Confirmar el repositorio y revisión exacta del target y drafter.
- Comprobar que el GGUF contiene todos los tensores DSpine requeridos.
- Verificar que ningún tensor de puente se omite, renombra o cuantiza de forma incompatible.
- Verificar block size, target layers, selector top-k y dimensiones contra el modelo card/config original.
- Confirmar que el target y drafter comparten tokenizer, vocabulario y arquitectura compatibles.

### 2. Build y pruebas automáticas

- Ejecutar auditor estático de LEONES.
- Build CPU limpio del fork.
- Ejecutar tests existentes de llama.cpp y pruebas del parser GGUF.
- Build CUDA SM86 en el MSI, en directorio aislado; la build CPU de CI no sustituye este gate.
- Registrar SHA exacto del commit externo, compiler, CMake flags, CUDA, driver y artefactos.

### 3. Validación funcional de referencia

- Carga del target y drafter sin warnings de tensores faltantes.
- Primera generación con `draft-dflash` y checkpoint DSpine.
- Confirmar en logs que el loader informa el code bridge DSpine.
- Comparar greedy tokens contra target sin speculative.
- Validar aceptación parcial, rechazo completo, EOS y resets KV.
- Validar sampling solo después de greedy.
- Comprobar que desactivar el drafter devuelve al baseline sin residuos.

### 4. Rendimiento

Medir por separado:
- prefill tokens/s;
- decode tokens/s;
- latencia al primer token;
- longitud media aceptada;
- ratio de aceptación;
- VRAM máxima;
- RSS y swap;
- consumo y estabilidad térmica.

Usar mismo modelo objetivo, prompt, contexto, sampler, seed y backend para baseline y speculative. Registrar al menos tres repeticiones; no comparar resultados de máquinas distintas como si fueran equivalentes.

## Candidato MSI

El checkpoint GGUF comunitario publicado es Qwen3.8-27B DSpine y su target obligatorio es Qwen3.8-27B. El target Q4 no cabe en el MSI; solo se contempla la cuantización IQ2_XXS en un ensayo híbrido de baja calidad.

El checkpoint oficial Qwen3-8B-DSpine-b16 (1.2378B parámetros) no es compatible con la implementación actual del fork: carece de `code_bridge_second_pass.mode=serial_table` y de `selected_prefix_last_write_refine.head_topk`. El conversor falla de forma intencional y segura con `DSpine: only the serial_table refinement of the last write is supported`. No añadir metadatos ficticios ni forzar la conversión. La pareja compatible confirmada es Qwen3.8-27B + Qwen3.8-27B-DSpine-b16. El GGUF comunitario del drafter Q4_K_M es de 1.26 GB. El target IQ2_XXS pesa 8.88 GB, por lo que los pesos suman unos 10.14 GB antes de KV/buffers. Esta pareja es el único candidato para el ensayo MSI, con offload híbrido, contexto 512 y calidad reducida; la viabilidad no está demostrada.

## Criterio de habilitación MSI

No pedir intervención hasta:
- auditor estático positivo;
- build CPU CI verde;
- build CUDA SM86 completado en el MSI sin tocar el runtime instalado;
- pareja exacta y hashes definidos;
- preflight de memoria conservador;
- script de benchmark y rollback preparados.

El gate MSI no se ha abierto todavía.
