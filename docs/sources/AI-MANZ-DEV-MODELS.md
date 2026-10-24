# AI.MANZ.DEV — AI model catalog

- **Primary URL:** https://ai.manz.dev/models/
- **Publisher:** MANZ.DEV
- **Source type:** Public, curated secondary catalog of AI model families and individual models.
- **Reviewed:** 2026-10-24
- **Language:** Primarily Spanish; some model detail pages may be in English.

## What it covers

The catalog groups models by publisher/company, family and individual model. Its scope includes open/local model families for text, image, vision, speech/audio, video and multimodal use. Model pages can expose parameter counts, model-family classifications (including dense and mixture-of-experts), dates, available quantization choices and rough storage/memory estimates. The site also provides related catalogs and guides for cloud models, local image generation and AI hardware.

The overview currently reports 96 companies and includes, among others, Qwen, DeepSeek, Google, NVIDIA, Microsoft, OpenAI, MiniMax, Moonshot AI, Xiaomi MiMo, Mistral and other publishers. Counts and catalog contents are dynamic and must be rechecked at the time of use.

## How LEONES should use this source

Use this as a **discovery and comparison index**, especially when identifying candidate model families before checking local inference feasibility.

1. Discover candidate models by modality, publisher, family and parameter count.
2. Distinguish dense models, MoE models and extended/draft variants where the source provides that classification.
3. Use listed quantization options and size estimates as initial planning hints, not guarantees.
4. Follow links to the model publisher, official model card, repository and actual weight files.
5. Cross-check architecture, license, context length, tokenizer/template, supported runtimes, quantization format, hardware requirements and release date against primary sources.
6. For LEONES hardware recommendations, validate RAM/VRAM and runtime compatibility on the target Ubuntu system; do not infer that a model runs merely because it appears in this catalog.
7. Record benchmark claims only when accompanied by reproducible measurements and the tested hardware/software configuration.

## Reliability and limitations

This is a secondary catalog, not the canonical authority for model weights, licenses or runtime compatibility. Parameter counts, release dates, quantization availability, model sizes and estimates can be incomplete, stale or approximate. A parameter count alone does not establish peak memory use or practical speed. Quantization changes size and may affect quality; actual memory also depends on architecture, KV cache, context length, runtime, offloading and concurrency.

Treat the site as a **lead-generation/reference source**, and cite the specific model detail page plus primary sources in any LEONES report. Revisit the page periodically because the catalog changes.

## Related pages

- Local/open model catalog: https://ai.manz.dev/models/
- AI home and related guides: https://ai.manz.dev/
- Cloud model catalog (separate scope): https://ai.manz.dev/cloud/
- Local image-generation model catalog: https://ai.manz.dev/models/image/

## Provenance

The overview was checked on 2026-10-24. Its current page describes a catalog of companies and model families and offers filtering/comparison of models. This note records the intended use in LEONES; it is not a snapshot or a mirror of the entire catalog.
