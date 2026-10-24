# AI.MANZ.DEV model catalog — knowledge-source policy

**Canonical source note:** [docs/sources/AI-MANZ-DEV-MODELS.md](../sources/AI-MANZ-DEV-MODELS.md)  
**Catalog:** https://ai.manz.dev/models/  
**Reviewed:** 2026-10-24

AI.MANZ.DEV is a useful secondary index for discovering and comparing AI model families, including local/open text, vision, image, audio/speech, video and multimodal models. Use it to identify candidates by publisher, family, parameter count, modality and available quantization information.

### LEONES usage rules

- Treat the catalog as a discovery aid, not as the authoritative model card.
- Verify model names, architecture, license, weights, context length, tokenizer/chat template and supported inference engines using the publisher's official sources.
- Treat quantization and memory figures as estimates. Confirm full runtime memory needs, including KV cache and offloading, on the target hardware.
- Never mark a model as runnable on a user's hardware solely because it appears in the catalog. Require runtime compatibility evidence or a reproducible test.
- Keep cloud-only offerings separate from locally downloadable/open-weight models.
- Cite the specific catalog page and primary source in reports; record the date checked because entries and counts change.

See the source note for scope, caveats and related catalog pages.
