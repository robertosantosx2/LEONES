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
- Build CUDA en runner con toolkit y GPU compatibles si CI disponible; la build CPU no sustituye este gate.
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

El checkpoint GGUF comunitario publicado es Qwen3.8-27B DSpine y su target obligatorio es Qwen3.8-27B. No se debe intentar en el MSI de 4 GiB VRAM.

La pareja oficial más pequeña es Qwen3-8B + Qwen3-8B-DSpine-b16 (drafter de 1.2378B parámetros). Antes de probarla en el MSI debe existir un GGUF convertido y validado para el drafter, y una cuantización GGUF del target cuya suma de pesos, KV, buffers y workspace quepa en el presupuesto real. No asumir que un drafter de 1.24B cabe gratis.

## Criterio de habilitación MSI

No pedir intervención hasta:
- auditor estático positivo;
- build CPU CI verde;
- build CUDA SM86 disponible o plan local reproducible;
- pareja exacta y hashes definidos;
- preflight de memoria conservador;
- script de benchmark y rollback preparados.

El gate MSI no se ha abierto todavía.
