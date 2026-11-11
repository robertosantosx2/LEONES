# Upstream llama.cpp reference sources

Vendored verbatim from **ggml-org/llama.cpp @ `272aad8b984a4470d26f14bea8d958be68ac7c0c`**
(master, fetched 2026-09-30; MIT, see third_party/ggml/LICENSE) so the glm5_next spec that
`ref/glm.py` transcribes stays readable and its line references stay stable.

The one file that matters most is `glm5-next.cpp` - the llama.cpp implementation of exactly
this architecture (GLM-5.3-Flash: hybrid KDA + nope-MLA with a k-pool DSA indexer, mHC
residual streams, DeepSeek-style MoE). `ref/glm.py`'s docstrings cite it by line.

| File | Why it is here |
| --- | --- |
| `glm5-next.cpp` | THE spec: load_arch_hparams (metadata keys), load_arch_tensors (tensor names + shapes), the graph (mHC pre/sinkhorn/post, KDA layer, k-pool indexer, nope-MLA layer, MoE) |
| `kimi-linear.cpp` | the KDA-family reference for the linear layers |
| `llama-arch.cpp` | the LLM_KV key strings and LLM_TENSOR GGUF names the conversion will write |
| `llama-graph.cpp` / `llama-graph.h` | build_moe_ffn (sigmoid + selection-bias semantics), build_ffn (swiglu clamp selection), the delta-net base declarations |
| `models.h` / `models.cpp` | build_gdn_l2_norm, the delta-net base class |
| `ggml.h` | the fused-op contracts: ggml_gated_delta_net (state layout, KDA gate axis), ggml_lightning_indexer, ggml_dsv4_hc_comb |
| `ggml.c` / `cpu-ops.cpp` | the reference kernels: gated_delta_net recurrence (ops.cpp L10898-11050), swiglu_clamp (ops.cpp L3408+) |

Re-fetch anything with:
`curl -sL -o <name> https://raw.githubusercontent.com/ggml-org/llama.cpp/<sha>/<path>`
(paths: src/models/, src/, ggml/include/, ggml/src/, ggml/src/ggml-cpu/).

Keep this directory out of any build: these files are documentation, not dependencies
(they do not compile outside llama.cpp, and must not drift into third_party/ggml).
