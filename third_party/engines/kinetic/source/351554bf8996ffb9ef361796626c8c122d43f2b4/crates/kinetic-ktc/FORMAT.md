# The .ktc model format, version 1

A `.ktc` file holds everything needed to run a model: weights, tokenizer,
chat template, an optional execution profile and a manifest that describes and
hashes all of it. The manifest can be signed with Ed25519. Because the manifest
carries the hash of every section, one signature covers the whole file.

All integers are little-endian. Sizes and offsets are in bytes.

## Layout

| Offset | Size | Field |
|-------:|-----:|-------|
| 0 | 4 | magic `KTC1` |
| 4 | 4 | `version`, `u32`, = 1 |
| 8 | 4 | `flags`, `u32`: bit 0 set means signed; all other bits are zero |
| 12 | 4 | reserved, zero |
| 16 | 8 | `manifest_len`, `u64` |
| 24 | 8 | `data_offset`, `u64` = `manifest_len + 96` rounded up to a multiple of 4096 |
| 32 | 64 | Ed25519 signature of the manifest bytes; all zero when unsigned |
| 96 | `manifest_len` | manifest, UTF-8 JSON |
| | | zero padding up to `data_offset` |
| `data_offset` | | sections |

Each section starts at `data_offset + section.offset`, where `section.offset`
is a multiple of 4096. Sections do not overlap, bytes between them are zero
and the file ends exactly where the last section ends. A reader rejects a file
that breaks any of these rules, so every byte is either the header, the
manifest, zero padding or a hashed section.

## Manifest

```json
{
  "name": "Qwen3.5 4B",
  "architecture": "qwen35",
  "hyperparameters": { "block_count": { "type": "u32", "value": 32 } },
  "tokenizer": {
    "metadata": { "ggml.model": { "type": "string", "value": "gpt2" } },
    "section": null
  },
  "chat_template": "{% for message in messages %}...",
  "metadata": { "general.license": { "type": "string", "value": "apache-2.0" } },
  "tensors": [
    { "name": "token_embd.weight", "type": "Q4_K", "dims": [2560, 248320], "offset": 0, "size": 357580800 }
  ],
  "sections": [
    { "name": "tensors", "offset": 0, "size": 2700000000, "blake3": "<64 hex digits>" }
  ],
  "execution_profile": { "target": "cuda-sm86", "settings": { "batch": 512 } }
}
```

Unknown fields are an error; new fields come with a new version.

- `name`, `architecture`: the model's display name and its architecture id.
  Architecture ids and hyperparameter keys follow GGUF conventions
  (`qwen35`, `block_count`) for models converted from GGUF, and Hugging Face
  conventions (`qwen3`, `num_hidden_layers`, nested keys joined with `.`) for
  models converted from safetensors.
- `hyperparameters`, `tokenizer.metadata`, `metadata`: typed values, keyed
  without their GGUF prefix (`{architecture}.` and `tokenizer.` respectively).
  A typed value is `{"type": T, "value": V}` where `T` is one of `u8`, `i8`,
  `u16`, `i16`, `u32`, `i32`, `u64`, `i64`, `f32`, `f64`, `bool`, `string`, or
  an array type written `[T]`. Floats are finite.
- `tokenizer.section`: name of a section holding a tokenizer file such as
  `tokenizer.json`, or `null` when the tokenizer is fully described by
  `tokenizer.metadata`.
- `chat_template`: optional Jinja template.
- `tensors`: `dims` are innermost first (`dims[0]` is the contiguous row
  length), one to four of them. `type` is a GGUF tensor type name (`F32`,
  `F16`, `BF16`, `Q4_K`, ...) and its block layout is GGUF's. `offset` is
  relative to the start of the `tensors` section and a multiple of 4096;
  `size` is exactly the bytes the type needs for that shape. Tensors do not
  overlap.
- `sections`: every section in the file, with its BLAKE3 hash in lowercase
  hex. Names are unique. Defined names:
  - `tensors` (required): the tensor data;
  - `config.json`, `tokenizer.json`, `tokenizer_config.json`: source files
    kept verbatim by the safetensors converter;
  - `draft_head` (reserved): a speculative-decoding draft head, layout to be
    defined in a later version. Readers ignore it.

  Other names are allowed, hashed and verified like any section.
- `execution_profile`: optional settings tuned for one device. `target`
  names the device class; `settings` is a free-form JSON object.

## Reading the GGUF view

A reader presents a `.ktc` with GGUF-style metadata so GGUF loaders can use
it unchanged: `general.architecture` and `general.name` come from
`architecture` and `name`, hyperparameters are prefixed with
`{architecture}.`, tokenizer keys with `tokenizer.`, the chat template is
`tokenizer.chat_template`, and `metadata` keys are used as they are.
Tensor data is mapped in place, with no copy.

## Verification

`verify` recomputes the hash of every section and compares it with the
manifest. If the file is signed and a public key is given, it checks the
signature over the manifest bytes exactly as stored. An unsigned file is
valid and is reported as unsigned.
