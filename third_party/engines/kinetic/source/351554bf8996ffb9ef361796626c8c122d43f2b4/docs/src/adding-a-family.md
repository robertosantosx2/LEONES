# Adding a model family

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagrams/add-a-family-dark.svg">
  <img src="diagrams/add-a-family-light.svg" alt="Five steps from left to right: scaffold from a GGUF, map its tensors to blocks in one file, add one line to the registry, check conformance against llama.cpp, open a pull request" width="100%">
</picture>
</p>

A family is one file in `crates/kinetic-models/src/arch/` that maps a GGUF
file's tensors onto shared blocks, plus one line in the family list. The
file declares a `Family`: the GGUF architecture names it answers to, the
function that builds its layers, and the few ways its embedding and head
differ. Loading, `kinetic info`, `kinetic models` and the encoder checks all
read the list, so nothing else needs registering.

## The short path

```sh
python scripts/new_family.py model.gguf          # prints the layout, writes arch/<name>.rs, registers it
# map the tensors of one layer onto blocks in arch/<name>.rs
cargo build --release -p kinetic-cli
python scripts/conformance.py model.gguf --kinetic target/release/kinetic --llama path/to/llama.cpp
KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-models --test architectures -- --ignored
```

`new_family.py` reads only the header. It prints the architecture name, the
`<arch>.*` metadata and the tensors of layer 0 with their shapes, then
writes a starter that builds: a Llama-style stack of attention and a gated
feed-forward. Change what differs and delete what the model lacks.

## Worked example: LFM2

LFM2 is gated short convolutions and attention with query and key norms.
Its pull request touches exactly these files:

```text
crates/kinetic-models/src/arch/lfm2.rs     new, about 80 lines
crates/kinetic-models/src/arch/mod.rs      two lines
docs/src/models.md                         one table row
README.md                                  the model in the supported list
CHANGELOG.md                               one line
```

The registration is the module and one entry in `FAMILIES`:

```diff
 pub(crate) mod lfm2;
 ...
 pub(crate) const FAMILIES: &[Family] = &[
     qwen35::FAMILY,
     lfm3::FAMILY,
+    lfm2::FAMILY,
```

The family file starts with its descriptor. LFM2 stores the final norm
under another name, so it overrides one field of the default decoder:

```rust
pub(crate) const FAMILY: Family = Family {
    output_norm: "token_embd_norm.weight",
    ..Family::decoder(&["lfm2"], |l, b| Ok(layers(l, b.d, b.eps)?.into()))
};
```

and then builds one `Layer` per block; a layer without key-value heads is a
convolution layer:

```rust
pub(crate) fn layers<'a>(l: &Loader<'a>, d: usize, eps: f32) -> Result<Vec<Layer<'a>>, LoadError> {
    let n_layer = l.usize("block_count")?;
    let n_head_kv = l.array("attention.head_count_kv", n_layer, |v| {
        v.as_u64().map(|n| n as usize)
    })?;
    // ...
    (0..n_layer)
        .map(|i| {
            let t = |s: &str| format!("blk.{i}.{s}");
            let mixer = if n_head_kv[i] == 0 {
                Mixer::ShortConv(ShortConv {
                    in_proj: l.matrix(&t("shortconv.in_proj.weight"), d, 3 * d)?,
                    // ...
                })
            } else {
                Mixer::Attention(Attention { /* ... */ })
            };
            Ok(Layer {
                mixer_norm: Some(l.vector(&t("attn_norm.weight"), d)?),
                mixer,
                ffn_norm: Some(l.vector(&t("ffn_norm.weight"), d)?),
                ffn: Some(l.swiglu(i, d, n_ff)?),
                // ...
            })
        })
        .collect()
}
```

## The descriptor

```rust
pub(crate) const FAMILY: Family = Family {
    names: &["myarch"],                    // GGUF general.architecture values it answers to
    body: Body::Decoder(build),            // Decoder, Bidirectional (embeddings only) or Encoder
    output_norm: "output_norm.weight",     // tensor of the norm before the output head
    sqrt_embd_scale: false,                // embeddings times sqrt(width), as in Gemma
    logit_scale: false,                    // logits divided by <arch>.logit_scale, as in Granite
};
```

`Family::decoder(names, build)` fills in the usual values; override a field
with `..Family::decoder(...)` as LFM2 does. A builder gets the `Loader` and
the `Basics` every family reads (`arch`, the width `d`, the norm epsilon
`eps` and the weight folds) and returns a `Stack`: the layers and, for a
model with a multi-token prediction block, that block (see `qwen35.rs`).
Most builders return `layers(...)?.into()`.

One file may declare several descriptors when variants share a builder:
`transformer.rs` declares the Llama-like family, Gemma 3 and EmbeddingGemma,
and its builder reads `b.arch` for the details that differ. A plain
transformer that differs from Llama only in rotary layout, biases or which
norms exist belongs there: add its name to `transformer::FAMILY` and express
the difference with the flags that file already has, the way `olmo2` and
`exaone4` are.

## Blocks

`crates/kinetic-models/src/blocks/` holds the building blocks. A `Layer`
is an optional norm, a mixer, an optional output norm, then the same around
a feed-forward:

| Block | Covers | CPU | CUDA | Vulkan |
|---|---|---|---|---|
| `Mixer::Attention(Attention)` | grouped-query attention: optional biases, query/key norms per head or across heads, before or after the rotation, adjacent or NeoX rotary layout, sliding window, output gates, fixed score scale | yes | yes | norms per head only |
| `Mixer::ShortConv(ShortConv)` | gated short convolution (LFM2, LFM3) | yes | yes | yes |
| `Mixer::DeltaNet(DeltaNet)` | Gated DeltaNet (Qwen3.5) | yes | yes | yes |
| `Mixer::Mamba2(Mamba2)` | Mamba-2 (Granite 4.0 H, Falcon-H1), built by `arch::mamba::mamba2` | yes | yes | refused |
| `Mixer::Parallel(Vec<Mixer>)` | several mixers on one input, outputs summed (Falcon-H1) | yes | yes | refused |
| `SwiGlu` | gated feed-forward, SiLU or GELU (`Loader::swiglu`) | yes | yes | SiLU only |
| `Experts` | routed mixture-of-experts feed-forward, optional shared expert (`arch::moe`) | yes | yes | refused |

`Layer` also has `residual_scale` for models whose residual branches carry
a fixed multiplier (Granite).

## Mapping tensors

The `Loader` reads everything and checks every shape, so a wrong mapping
fails at load time with the tensor's name rather than giving bad output:

| Call | Reads |
|---|---|
| `l.usize("block_count")`, `l.f32(...)` | `<arch>.<key>`, required |
| `l.usize_or(key, default)`, `l.f32_or(...)` | `<arch>.<key>`, optional |
| `l.array(key, n, parse)` | a per-layer array such as `attention.head_count_kv` |
| `l.matrix(name, cols, rows)` | a weight matrix in any supported type; `cols` is the input width |
| `l.vector(name, len)`, `l.optional_vector(...)` | a norm or bias, as f32 |
| `l.swiglu(i, d, n_ff)` | `blk.i.ffn_gate`, `ffn_up` and `ffn_down` |
| `l.experts(...)` | the stacked expert tensors `ffn_*_exps` |

GGUF stores a matrix with the input width first: `blk.0.attn_q.weight
[576, 576]` in the scaffold's listing is `l.matrix(.., 576, 576)`. For what
each tensor does, the model's reference implementation (`modeling_*.py` on
Hugging Face) and llama.cpp's `src/models/` are the specifications. Read
them; do not copy them.

A tensor the blocks have no place for must make loading fail, not be
skipped: list it the way `transformer.rs` lists `UNSUPPORTED`.

## When a new block is needed

Open an issue first. A new mixer or feed-forward lands in this order:

1. The CPU reference in `blocks/`: the plain, obviously correct version,
   with a batch path that gives each token bit for bit what it gets alone.
2. Its state, checkpoint and rollback in `blocks/snapshot.rs`, so drafting
   and Warm Start work.
3. CUDA in `cuda/` and Vulkan in `vulkan/`, each checked against the CPU
   reference; or, until then, a clear refusal at upload
   (`unsupported("...")` in `vulkan/layer.rs`), so the model runs on the
   CPU instead of giving wrong output on the GPU.

## Testing

Compare greedy output with llama.cpp. `scripts/conformance.py` runs
`kinetic serve` and then `llama-server` on the same file, one at a time,
sends a few fixed raw prompts with greedy sampling, and reports how many
tokens agree. Where the two part it prints llama.cpp's two likeliest tokens
there; a gap under 0.1 nats is a near-tie that differently rounded kernels
may break either way, an early divergence without one is a bug, and the
script exits with 1. On an RTX 3060 Laptop, LFM3 and Qwen3.5 part only at
near-ties, and Qwen3.5's fourth answer ends after 32 tokens in both:

```text
$ python scripts/conformance.py LFM3-1.7B-Q4_K_M.gguf --kinetic target/release/kinetic --llama llama-b12001 --device cuda
LFM3-1.7B-Q4_K_M.gguf on cuda, 64 greedy tokens per prompt
prompt 1: 64/64 tokens agree
prompt 2: 64/64 tokens agree
prompt 3: 1/64 tokens agree; near-tie at token 1: llama.cpp top two 'Set' -1.167, 'Create' -1.253 (gap 0.086), kinetic 'Create a dedicated works'
prompt 4: 64/64 tokens agree
total: 193/256 tokens agree

$ python scripts/conformance.py Qwen3.5-4B-MTP-Q4_K_M.gguf --kinetic target/release/kinetic --llama llama-b12001 --device cuda
Qwen3.5-4B-MTP-Q4_K_M.gguf on cuda, 64 greedy tokens per prompt
prompt 1: 3/64 tokens agree; near-tie at token 3: llama.cpp top two 'A' -1.484, 'The' -1.499 (gap 0.014), kinetic 'The capital of France is'
prompt 2: 64/64 tokens agree
prompt 3: 64/64 tokens agree
prompt 4: 32/32 tokens agree
total: 163/224 tokens agree
```

Then run the identity gates, the contract every family meets:

```sh
KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-models --test architectures -- --ignored
KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-models --features cuda --test cuda -- --ignored
```

- a batch gives the logits its tokens give one by one, bit for bit;
- every row of a tree batch gives what its path gives alone;
- speculative decoding reproduces plain greedy decoding token for token.

Last, `kinetic run`, `kinetic bench` (it must print `drafted output
identical to plain decoding: yes`) and `kinetic serve` with a real chat.
The tokenizer and chat template usually need nothing; a new BPE
pre-tokenizer (`tokenizer.ggml.pre`) goes in `crates/kinetic-tokenizer/src/lib.rs`,
tested against `llama-tokenize` on the same file.

## Document it

Add the family to the table in [Models and formats](models.md), to the
README's supported models and to the changelog.
