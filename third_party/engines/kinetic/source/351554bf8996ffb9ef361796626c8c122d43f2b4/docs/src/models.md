# Models and formats

Kinetic reads GGUF files as llama.cpp and the Hugging Face GGUF tools write
them, and its own `.ktc` files. It does not convert anything: you point it
at a file on your disk.

The quickest check for a file is `kinetic info`:

```sh
kinetic info Qwen3.5-4B-MTP-Q4_K_M.gguf
```

```text
Qwen3.5-4B-MTP-Q4_K_M.gguf
  name           Qwen3.5-4B
  architecture   qwen35
  size           2.64 GiB, 4.33 B parameters
  context        262144 tokens
  layers         33, width 2560
  prediction     yes (drafts for speculative decoding)
  weights        Q4_K    149 tensors    1478.0 MiB
                 Q6_K     35 tensors    1018.2 MiB
                 Q5_K     24 tensors     165.0 MiB
                 F32     232 tensors      18.7 MiB
                 Q8_0      1 tensors      13.3 MiB
  tokenizer      gpt2 (qwen35), 248320 tokens, BOS none, EOS <|im_end|>
  chat template  7992 bytes
```

An architecture Kinetic does not know is marked `(not supported yet)`. A
known architecture can still use a feature that is not supported yet, such
as a kind of rotary scaling; `kinetic run` then names it when it loads the
file.

## Architectures

The names are the GGUF `general.architecture` values.

| Architecture | Models | CPU | CUDA |
|---|---|:-:|:-:|
| `qwen35` | Qwen3.5, with its multi-token prediction block | yes | yes |
| `qwen35moe` | Qwen3.5 mixture of experts, such as 35B-A3B | yes | yes, also larger than GPU memory |
| `lfm3` | LFM3 | yes | yes |
| `lfm2` | LFM2 | yes | yes |
| `lfm2moe` | LFM2.5 mixture of experts, such as 8B-A1B (experimental, slower than llama.cpp on CUDA for now) | yes | yes, also larger than GPU memory |
| `llama` | Llama 3, Mistral, SmolLM2 and other models built like Llama | yes | yes |
| `qwen2` | Qwen2.5 | yes | yes |
| `qwen3` | Qwen3 | yes | yes |
| `gemma3` | Gemma 3 | yes | yes |
| `gemma4` | Gemma 4 E2B and E4B; the 26B A4B mixture of experts is not supported yet | yes | yes |
| `ernie4_5` | ERNIE 4.5 | yes | yes |
| `hunyuan-dense` | Hunyuan dense models | yes | yes |
| `exaone4` | EXAONE 4.0 | yes | yes |
| `olmo2` | OLMo 2 | yes | yes |
| `granite` | Granite 3 and 4.0 dense models | yes | yes |
| `granitehybrid` | Granite 4.0 H (Mamba-2 hybrid) | yes | yes |
| `granitemoe` | Granite 3 mixture of experts | yes | yes |
| `falcon-h1` | Falcon-H1 | yes | yes |

With `--device auto`, a model that cannot run on the GPU runs on the CPU and
Kinetic prints why. Through Vulkan (`--device vulkan`), `llama`, `qwen2`,
`qwen3`, `lfm3` and `qwen35` models run today; see [Devices](devices.md#vulkan).

### Embedding and ranking models

`kinetic serve` answers `/v1/embeddings` for these and `/v1/rerank` for
rerankers. They run on the CPU.

| Architecture | Models |
|---|---|
| `bert` | BGE and other BERT-style encoders |
| `nomic-bert` | nomic-embed-text |
| `gemma-embedding` | EmbeddingGemma |
| decoders with a pooling type | Qwen3-Embedding |
| rerankers | Qwen3-Reranker |

A file is served as an embedding model when it is an encoder or its metadata
sets a pooling type (`<arch>.pooling_type`).

### Vision

With `kinetic serve <model> --mmproj <projector>`, chat requests may carry
images. The projector file names its vision tower in `clip.projector_type`
(or `clip.vision.projector_type` when it also holds an audio tower):

| Projector type   | Models                          |
|------------------|---------------------------------|
| `qwen3vl_merger` | Qwen3.5, Ternary Bonsai 2       |
| `gemma4v`        | Gemma 4                         |

When the model runs on a CUDA GPU, images are encoded there too. A prompt with images runs
on the GPU when every layer of the model is there, and on the CPU
otherwise. More projectors are [coming](roadmap.md).

Adding a projector type takes one file in `crates/kinetic-vision/src/`:

1. A struct holding the weights, borrowed from the file through `Loader`.
2. A `load` function that reads the hyperparameters and tensors and returns
   the struct boxed as a `Projector`.
3. `impl Projector`: `n_embd_out`, `prepare` (resize and normalize the way
   the model's processor does) and `encode` (pixels to one row per image
   token, row-major over the token grid).
4. One line in `PROJECTORS` in `lib.rs` mapping the `clip.projector_type`
   string to `load`.

Shared pieces live in `ops.rs` (linear, layer and RMS norms, GELU,
bidirectional attention, patch gathering) and `preprocess.rs` (decoding,
the aspect-keeping resize). Check a new type against llama.cpp's
`llama-mtmd-debug --image rainbow -n <size>` with
`cargo run --release -p kinetic-vision --example encode -- <mmproj> rainbow:<size>`:
the first and last values and the sum of the final embeddings should match
to a few digits. On the text side, an image's rows enter the prompt as
`Input::Image`; models with (time, row, column) rotary positions place them
on the image grid, every other model gives them consecutive positions.

### Tokenizers

The tokenizer is read from the file. Kinetic has byte-level BPE
(`tokenizer.ggml.model` = `gpt2`), SentencePiece (`llama`) and WordPiece
(`bert`). BPE models also name a pre-tokenizer (`tokenizer.ggml.pre`); these
are supported: `qwen35`, `qwen2`, `llama3`, `llama-v3`, `llama-bpe`, `lfm2`,
`falcon-h1`, `dbrx`, `smollm`, `refact`, `gpt-2`, `exaone4` and
`hunyuan-dense`. `kinetic info` names a missing one on its tokenizer line.

### Chat templates and tool calls

The chat template is the file's own Jinja template, rendered as the model's
authors wrote it, or the one `--chat-template-file` names. Tool calls are
read in the formats of Qwen3.5, Qwen3, LFM3, LFM2, Llama 3 and Mistral.

## Weight formats

These are the GGUF tensor types, by the names `kinetic info` prints. A file
mixes several (Q4_K_M, for one, is mostly Q4_K with some Q6_K).

| Type | Bits per weight | CPU | CUDA |
|---|---:|:-:|:-:|
| F32 | 32 | yes | yes |
| F16 | 16 | yes | yes |
| BF16 | 16 | yes | coming |
| Q8_0 | 8.5 | yes | yes |
| Q6_K | 6.56 | yes | yes |
| Q5_K | 5.5 | yes | yes |
| Q5_0, Q5_1 | 5.5, 6 | yes | yes |
| Q4_K | 4.5 | yes | yes |
| Q4_0, Q4_1 | 4.5, 5 | yes | yes |
| IQ4_NL | 4.5 | yes | yes |
| IQ4_XS | 4.25 | yes | experts only |
| MXFP4 | 4.25 | yes | yes |
| Q3_K | 3.44 | yes | yes |
| IQ3_S | 3.44 | yes | yes |
| IQ3_XXS | 3.06 | yes | experts only |
| Q2_K | 2.63 | yes | yes |
| IQ2_S | 2.56 | yes | yes |
| IQ2_XS | 2.31 | yes | experts only |
| IQ2_XXS | 2.06 | yes | experts only |
| TQ2_0 | 2.06 | yes | yes |
| IQ1_M | 1.75 | yes | yes |
| TQ1_0 | 1.69 | yes | yes |
| IQ1_S | 1.56 | yes | yes |

"Experts only" means the type runs on the GPU as the routed experts of a
mixture-of-experts model; in any other tensor it keeps the model on the CPU. The format
definitions follow ggml's, so a GGUF file means the same in Kinetic as in
llama.cpp.

On the CPU, AVX2 kernels cover the common formats; any other type still runs,
through a slower path that dequantizes each row.

## Files that do not load

| Message | Meaning |
|---|---|
| `architecture X is not supported yet` | the architecture is not in the table above |
| `unsupported pre-tokenizer "X"` | a BPE pre-tokenizer Kinetic does not have yet |
| `X rotary scaling is not supported yet` | the file asks for a scaling type other than linear or YaRN |
| `logit softcapping is not supported yet` | Gemma 2 style soft-capped logits |
| `tensor X is not supported yet` | a layout this architecture's loader does not handle, such as fused QKV weights |
| `... is not supported on CUDA yet` | the model runs, but not on the GPU; `--device auto` uses the CPU |

Split files (`model-00001-of-00003.gguf`) are not read yet; join them first
with llama.cpp's `llama-gguf-split --merge`.

If a model you need is missing, open a
["model not supported" issue](https://github.com/Veloresearch/kinetic/issues/new?template=model-not-supported.yml)
with the output of `kinetic info`, or add it: see
[Adding an architecture](contributing.md#adding-an-architecture).

## .ktc files

A `.ktc` file holds everything needed to run a model, weights, tokenizer and
chat template, with a manifest that records the BLAKE3 hash of every
section, an optional Ed25519 signature over the manifest, and an execution
profile tuned for a kind of hardware. Every byte of the file is either the
header, the manifest, zero padding or a hashed section, so nothing can hide
in it.

```sh
kinetic verify model.ktc
```

recomputes every hash and reports whether the file is signed; it exits with 1
when anything does not match. Every command that takes a `.gguf` file takes
a `.ktc` file too. The format is specified in
[FORMAT.md](https://github.com/Veloresearch/kinetic/blob/main/crates/kinetic-ktc/FORMAT.md)
and versioned on its own; see [Versioning](versioning.md).
