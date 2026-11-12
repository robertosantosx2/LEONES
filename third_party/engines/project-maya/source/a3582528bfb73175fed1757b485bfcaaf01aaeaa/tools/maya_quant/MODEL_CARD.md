---
license: mit
base_model: zai-org/GLM-5.3-Flash
base_model_relation: quantized
pipeline_tag: text-generation
quantized_by: peasantsmith
tags:
  - gguf
  - imatrix
  - mixture-of-experts
  - glm
  - project-maya
---

<!-- Draft for the Hugging Face repository of Maya-S. The numbers marked TBD come from tools/maya_quant/eval_v1.sh
     (KL against the FP8 model) and loop_test.py; nothing is published before they are filled in. -->

# GLM-5.3-Flash · Maya-S (IQ2_XXS mix, 90 GB)

A GGUF quantization of [zai-org/GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash) (321 B parameters,
a mixture of experts with about 18 B active per token), made for **Project Maya**: the whole model in 64 GB of RAM
plus one 32 GB GPU, or two GPUs, at chat speed.

It is made from Z.ai's own FP8 release (the precision the model is served at), not from a re-quantized file.

## Files

| File | Size |
| --- | ---: |
| `GLM-5.3-Flash-Maya-S-IQ2_XXS-00001-of-00002.gguf` | TBD |
| `GLM-5.3-Flash-Maya-S-IQ2_XXS-00002-of-00002.gguf` | TBD |

The model's NextN (MTP) layer is included, so engines that draft with it (Project Maya does) get speculative decoding.

## What is in it

| Tensors | Type |
| --- | --- |
| Routed experts, gate and up (42 layers) | IQ2_XXS, rounded with error feedback (below) |
| Routed experts, down | IQ2_S in the first and last four MoE layers, IQ2_XXS in the rest |
| Attention (KDA and MLA/DSA), shared experts, the three dense layers, embeddings, output | Q6_K |
| Small KDA projections, DSA indexer | Q8_0 |
| Router, norms, mixing (mHC) weights | F32 |
| NextN draft layer experts | Q2_K (gate/up), Q3_K (down) |

## How it was made

1. **Calibration text** (128 sequences of 2,048 tokens, all in GLM's chat template with its reasoning blocks): chat,
   multilingual chat (Portuguese and others first), reasoning traces, web code - single-file HTML/CSS/JS pages,
   three.js scenes, canvas and WebGL animations - other code, and tool calls.
2. **Statistics from the FP8 model itself**, layer by layer: an importance matrix for every expert separately (not
   one per layer), routing counts and saliency, and each MoE layer's input.
3. **Error-feedback rounding** of the experts' gate and up projections: GPTQ-style, at the granularity of the
   quantizer's 256-weight blocks, with each expert's own input statistics (shrunk toward the layer's, so rarely used
   experts are not fitted to a handful of tokens). On held-out text it lowers the experts' output error by about a
   quarter against plain importance-weighted rounding at the same size.
4. The quantizers themselves are llama.cpp's (ggml), so the file is an ordinary GGUF.

## Quality against the original (FP8)

Measured on held-out text that was not used for calibration (the FP8 model's own predictions as the reference):

| | Maya-S |
| --- | ---: |
| KL divergence from FP8 (mean per token) | TBD |
| Same top token as FP8 | TBD |
| Perplexity (FP8: 3.53 on the same text) | TBD |

Loop test (long answers at temperature 1.0 and greedy: a three.js scene, a canvas animation, a long explanation, a
plan in Portuguese, a proof): TBD.

## Running it

- **Project Maya** (one or two NVIDIA GPUs, the rest of the model in RAM and on the SSD): see the project's README.
- **llama.cpp**: a build with GLM-5.3-Flash (`glm5next`) support loads it as any GGUF.

## License

The model is Z.ai's GLM-5.3-Flash under the MIT license; this quantization is released under the same license.
