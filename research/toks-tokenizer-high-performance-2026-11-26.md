# TOKS — evaluación e integración potencial en LEONES

**Fecha de registro:** 2026-11-26  
**Proyecto externo:** [actual-computer/toks](https://github.com/actual-computer/toks)  
**Versión revisada:** v0.3.2  
**Estado LEONES:** investigación prospectiva; no instalado ni validado físicamente en el MSI.

## 1. Resumen

TOKS es una biblioteca de tokenización de alto rendimiento escrita principalmente en C, con kernels de ensamblador optimizados para x86-64 AVX2 y ARM64 NEON. Recibe los artefactos de tokenizer distribuidos con un modelo (principalmente `tokenizer.json`) y produce los mismos IDs que la implementación de referencia de Hugging Face Tokenizers para los casos que declara compatibles.

No es un motor de inferencia ni acelera directamente la generación autoregresiva. Optimiza la conversión de texto a IDs y la operación inversa, por lo que su impacto debe medirse en preparación de prompts, ingestión de documentos, embeddings, RAG, lotes y latencia hasta el primer token.

## 2. Capacidades declaradas por upstream

- ABI C embebible, con buffers de salida y scratch proporcionados por el llamador.
- Implementaciones para BPE byte-level, SentencePiece BPE, Unigram y WordPiece.
- Normalizadores, pre-tokenizers, added tokens, post-processors y decodificación.
- API Python con interfaz de estilo Hugging Face.
- Contexto cargado de solo lectura compartible entre hilos; scratch independiente por hilo.
- Caché de piezas y memo de segmentos configurable.
- `toks_par` para tokenización paralela de entradas grandes o lotes, utilizando puntos de división certificados para conservar el resultado exacto de la llamada serial.
- Rechazo de tokenizers cuyas características no pueda reproducir exactamente, en vez de devolver IDs silenciosamente distintos.
- Identificación del tokenizer mediante información y SHA-256 expuestos por la biblioteca.

La compatibilidad debe comprobarse por artefacto concreto. La existencia de una familia en la tabla de cobertura no demuestra que cualquier repositorio, conversión o formato de esa familia sea cargable.

## 3. Rendimiento publicado y límites de interpretación

Upstream publica comparativas en GB10, AMD Threadripper 9970X y Apple M2 Ultra. En determinadas celdas de una sola hebra comunica mejoras de 13–151× frente a Hugging Face Tokenizers y 4–23× frente a tiktoken; también publica resultados paralelos de hasta 1.608 MB/s en GB10 y 1.804 MB/s en Threadripper con ocho núcleos.

Estas cifras son resultados externos, con corpus, tokenizers, máquinas, estados de caché y commits concretos. **No son resultados medidos por LEONES ni estimaciones transferibles al MSI.** El README upstream detalla las condiciones y recibos de sus pruebas.

La versión v0.3.2 es la primera publicada bajo Apache-2.0. Las versiones 0.3.0 y 0.3.1 se distribuyeron bajo BSL 1.1; cualquier reproducción debe conservar el pin de versión y la licencia correspondiente.

## 4. Adecuación al hardware de referencia LEONES

Equipo de validación propuesto:

- MSI Thin 15 B12UC.
- Intel Core i7-12650H (Alder Lake, x86-64).
- NVIDIA RTX 3050 Laptop GPU, 4 GiB VRAM.
- 14 GiB RAM.
- Ubuntu.

El paquete upstream Linux x86-64 selecciona el nivel AVX2 cuando está disponible y dispone de una ruta C portable. La tokenización se ejecutaría en CPU, sin requerir CUDA ni consumir VRAM. Antes de instalar, verificar en la máquina las flags de CPU, versión de Python y compatibilidad del wheel o bundle elegido.

## 5. Encaje arquitectónico en LEONES

Se propone tratar TOKS como **proveedor/adaptador opcional del subsistema de tokenización**, no como runtime ni como sustituto automático de los tokenizers internos de los motores.

Posición conceptual:

`Texto → tokenizer seleccionado y verificado → IDs → adaptador del motor → inferencia`

Motores candidatos para evaluación: llama.cpp, TensorFold y Strata. La integración inicial debe permanecer fuera de sus rutas críticas: primero medir y verificar paridad de forma independiente; después estudiar si cada motor ofrece un punto de extensión seguro.

No se debe asumir que reemplazar la tokenización interna es transparente. Deben verificarse BOS/EOS, tokens especiales y añadidos, templates/post-processing, truncado, padding, decodificación incremental, vocabulario, normalización y tratamiento de UTF-8.

### Casos de uso potenciales

1. Reducir el coste de tokenización de prompts extensos y repetidos.
2. Acelerar ingestión y segmentación de corpus para RAG.
3. Procesar lotes de documentos o textos para embeddings.
4. Compartir un contexto de tokenizer entre trabajadores con scratch independiente.
5. Explorar memoización de segmentos y cachés de prefijos, siempre respetando los puntos de división certificados.
6. Ofrecer una implementación C ligera para el objetivo de runtime mínimo de llm.asm.

## 6. Plan de validación

### Fase A — inspección y adquisición

- Fijar versión y origen: `actual-computer/toks v0.3.2`.
- Descargar el bundle C Linux x86-64 y/o wheel Python compatible.
- Verificar SHA-256 y manifiesto del bundle.
- Registrar licencia, versión, arquitectura, ABI, dependencias y procedencia.
- No modificar las instalaciones existentes de llama.cpp, TensorFold o Strata.

### Fase B — exactitud

Seleccionar tokenizers reales de modelos ya investigados en LEONES, inicialmente Qwen y Llama cuando sus artefactos requeridos estén disponibles.

Comparar TOKS con el tokenizer de referencia en:
- IDs exactos para corpus español, inglés, código, Unicode y CJK.
- Tokens especiales y added tokens.
- BOS/EOS y post-processing.
- Decode y decode incremental.
- Casos límite: texto vacío, UTF-8 inválido si aplica, espacios, saltos de línea y entradas largas.

Cualquier diferencia bloquea la promoción de ese tokenizer. Guardar corpus, artefactos, hashes, versiones y resultados.

### Fase C — rendimiento en MSI

Comparar, en condiciones controladas:
- Hugging Face Tokenizers de referencia.
- TOKS Python.
- TOKS C nativo.
- Tokenizador interno del motor, cuando sea posible.

Separar primer uso/carga, estado frío, flujo de textos distintos, repetición caliente y procesamiento paralelo. Medir CPU, RAM, temperatura, consumo y contención con la inferencia activa. No extrapolar cifras de otros equipos.

### Fase D — integración

Sólo tras superar exactitud y benchmark:
- Definir interfaz LEONES estable para encode/decode/info.
- Incorporar selector explícito por tokenizer y motor.
- Mantener fallback al tokenizer nativo.
- Registrar procedencia, hash y resultado de paridad en los recibos NEPENTHES.
- Evaluar integración C directa antes de añadir dependencias Python al camino crítico.

## 7. Métricas NEPENTHES propuestas

- `tokenize_ns`: duración de tokenización.
- `input_bytes`: bytes de entrada.
- `output_tokens`: IDs producidos.
- `throughput_mb_s` y `tokens_per_second`.
- `load_ns`: tiempo de carga del tokenizer.
- `cache_hits` / `cache_misses`, si la API expone datos suficientes.
- `threads`, tier SIMD y configuración scratch.
- `tokenizer_sha256`, `toks_version`, versión del tokenizer de referencia.
- `parity_status`: resultado de comparación exacta.
- `ttft_ms`: impacto medido sobre el tiempo hasta el primer token en pruebas end-to-end.

La métrica de tokenización debe distinguirse del throughput de generación. Una mejora en encode no implica por sí misma más tokens/s durante decode.

## 8. Decisión provisional

**Candidato recomendado para validación, no aprobado todavía como dependencia de producción.**

Prioridad experimental: alta por su posible utilidad transversal y por su implementación C/AVX2, pero la incorporación queda condicionada a:
1. Paridad exacta por tokenizer.
2. Rendimiento medido en el MSI.
3. Ganancia end-to-end demostrable en al menos un flujo relevante.
4. Licencia y artefactos fijados.
5. Fallback nativo y ausencia de regresiones.

## 9. Fuentes primarias

- Repositorio y README: https://github.com/actual-computer/toks
- Release v0.3.2: https://github.com/actual-computer/toks/releases/tag/v0.3.2
- Documentación de uso y API: https://github.com/actual-computer/toks/tree/main/docs
- Presentación del proyecto: https://actual.inc/company/blog/introducing-toks
- Página de demostración: https://toks.actual.inc

**Nota de rigor:** las prestaciones, cobertura y paridad citadas en esta ficha son declaraciones/documentación upstream. LEONES no ha ejecutado aún TOKS en el MSI a la fecha de este registro.
