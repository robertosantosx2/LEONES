# Forge ↔ ODS ↔ LEONES
**Perfil:** servidor de inferencia LLM escrito en Rust con CUDA y API OpenAI-compatible.
**Estado LEONES:** 🟡 P3.

## Resumen
Forge implementa desde cero un servidor con continuous batching, chunked prefill, paged KV cache, structured output y speculative decoding, además de soporte GGUF y CPU/CUDA.

## Valor ODS
Sirve como referencia de runtime alternativo de alto rendimiento. No está específicamente centrado en MoE/NVMe paging, por lo que su valor para la línea actual es secundario.

## Encaje
Podría entrar en el Runtime Registry si demuestra compatibilidad con modelos que ODS quiera servir y ofrece health/model endpoints estables.

## LEONES
Comparar con llama-server en los mismos modelos, especialmente batch, context y memoria.

## Veredicto
**Clasificación:** P3 — radar de runtime general.
**Fuente:** https://github.com/willamhou/forge