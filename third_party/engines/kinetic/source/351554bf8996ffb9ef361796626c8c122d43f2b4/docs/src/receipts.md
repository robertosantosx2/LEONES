# Receipts

Kinetic's output does not depend on anything outside the request: not on
speculative drafting, not on other users sharing the batch, not on the
prompt cache, not on a prompt run ahead while it was typed. A request gives
the same tokens alone on an idle machine as on a server answering four
users at once with every speed technology on. A receipt turns that into
something you can keep and check.

## Same input, same output

`scripts/same_answer_demo.py` sends one chat request ten times at
temperature 0.8 with a fixed seed while three other clients keep the server
busy with different long requests, and hashes every answer. LFM3-1.7B
Q4_K_M on a Ryzen 5 6600H, CPU only, both servers with `--parallel 4`:

```text
Kinetic, kinetic serve --parallel 4
run  answer (first 40 characters)                sha256 of the full answer
  1  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
  2  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
  3  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
  4  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
  5  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
  6  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
  7  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
  8  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
  9  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
 10  **Lunar Lattice Café** — its name evokes    070ad8ff1e6fc95f
     1 distinct answer in 10 runs

llama.cpp, llama-server --parallel 4
run  answer (first 40 characters)                sha256 of the full answer
  1  **Lunar Bean & Crater Café**  The name e    cac5bf18cb341aad
  2  **Lunar Bean & Crater Café**  The name e    cac5bf18cb341aad
  3  **Lunar Bean & Crater Café**  The name e    cac5bf18cb341aad
  4  **Lunar Bean & Crater Café**  The name e    9b21683015c20844
  5  **Lunar Bean & Crater Café**  The name e    cac5bf18cb341aad
  6  **Lunar Bean & Crater Café**  The name e    cac5bf18cb341aad
  7  **Lunar Bean & Crater Café**  The name e    cac5bf18cb341aad
  8  **Lunar Bean & Crater Café**  The name e    30430d6b74effe9b
  9  **Lunar Bean & Crater Café**  The name e    cac5bf18cb341aad
 10  **Lunar Bean & Crater Café**  The name e    cac5bf18cb341aad
     3 distinct answers in 10 runs
```

Kinetic gives the same answer every time. llama-server gives the same first
words but three different answers in ten runs (which runs differ, and how, changes from one try to the next), most likely because how a request is batched with
the others changes how its sums are rounded, and sampling turns a tiny
difference into another token. Run it yourself:

```sh
python scripts/same_answer_demo.py --model LFM3-1.7B-Q4_K_M.gguf \n    --kinetic kinetic --kinetic-args "--device cpu" --receipt last.json \n    --llama-server llama-server --llama-args "-dev none -ngl 0 -c 16384"
```

The receipt of Kinetic's last run, made on the busy server, then verifies
as identical when rerun alone with drafting off. On an RTX 3060 Laptop GPU
(`--kinetic-args "--device cuda"`, class `cuda-sm86`) Kinetic also gives one
distinct answer in ten runs, and that receipt verifies the same way.

Making inference batch-invariant is not a new idea: it has been described
before (Thinking Machines, 2025) and vLLM has a batch-invariant mode. What
Kinetic adds is that it is the default, together with drafting, the prompt
cache, several users and run-ahead, at full speed.

## Making a receipt

```sh
kinetic run model.gguf "Name three rivers." --temp 0.8 --seed 42 --receipt answer.json
```

In `kinetic chat`, `/receipt answer.json` saves the receipt of the last
answer. On the server, `"receipt": true` on `/v1/chat/completions` or
`/v1/completions` adds a `receipt` object to the response; see
[Server API](server.md#receipts). A request without a seed gets a fresh one,
which the receipt records.

A real receipt, signed:

```json
{
  "receipt": 1,
  "kinetic": {
    "version": "0.1.0",
    "build": "378534cb64f30a15"
  },
  "model": {
    "file": "LFM3-1.7B-Q4_K_M.gguf",
    "path": "LFM3-1.7B-Q4_K_M.gguf",
    "size": 1099627808,
    "blake3": "f4240740be2392a21da1668fab289a441684b47db70bd96d8f863b576f44bfb4"
  },
  "device": {
    "class": "cpu-x86_64-avx2",
    "name": "the CPU",
    "settings": {
      "ctx-size": 32768
    }
  },
  "input": [
    {
      "role": "user",
      "content": "Name three rivers."
    }
  ],
  "prompt": {
    "count": 15,
    "blake3": "591484bfe2293f5c7603c970515f9d044a607c9e5ef92bbdc51c05e474672f73",
    "ids": [124894, 124899, 5922, 207, 2617, 1703, 15311, 22, 124900, 207, 124899, 63514, 207, 124901, 124902]
  },
  "sampling": {
    "temperature": 0.8,
    "top_k": 50,
    "top_p": 0.95,
    "min_p": 0.05,
    "repeat_penalty": 1.1,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "repeat_last_n": 64,
    "seed": 42,
    "max_tokens": null,
    "stop": []
  },
  "output": {
    "finish": "stop",
    "text": "1. The Nile River  \n2. The Amazon River  \n3. The Mississippi River",
    "tokens": {
      "count": 18,
      "blake3": "7bd0632303b6fcbdb7f440d8c19415fa73e0afacd6e941137104bf438ebd8662",
      "ids": [25, 22, 440, 35844, 5094, 3103, 26, 22, 440, 12225, 5094, 3103, 27, 22, 440, 17939, 5094, 124900]
    }
  },
  "signature": {
    "public_key": "8e79e51c11472a6cffd70635753a7cce14c4335e1f18435459c3ebb35b3f720b",
    "ed25519": "2dcfee41a820c6294aa1dbf60c916f1dc5ebab6b9575cb87b3f07f3f29f079dcd40020e0423be7df33f53471840ccd1bdcb604763b03ceeb89dfa2a741f2af00"
  }
}
```

| Field | Holds |
|---|---|
| `kinetic` | the version, and the build: the first 16 hex digits of the BLAKE3 of the `kinetic` executable, which pins every kernel compiled into it |
| `model` | the model file's name, path, size and BLAKE3; the hash is cached by path, size and modification time in `kinetic/hashes.json` in the user's cache directory, so a large file is hashed once |
| `device` | the device class that decides the bits (`cpu-x86_64-avx2`, `cpu-x86_64-scalar`, `cuda-sm86`, `vulkan-<GPU>`), its name, and load settings that change the bits: the context size, a quantized CUDA cache, `--gpu-layers`, rotary overrides |
| `input` | the chat messages or the prompt text, as sent |
| `prompt` | the exact tokens the model was given, with their count and BLAKE3 |
| `sampling` | every sampler setting: temperature, top-k, top-p, min-p, typical-p, top-n-sigma, the repeat, presence and frequency penalties, logit bias, XTC, DRY with its sequence breakers, Mirostat; the seed, the token limit, stop strings and any grammar or `response_format` |
| `output` | why it ended, the text, and the generated tokens with their count and BLAKE3 |
| `signature` | optional: an Ed25519 public key and the signature over the rest |

Token hashes are BLAKE3 over the ids as little-endian 32-bit integers.

## Verifying

```sh
kinetic verify-receipt answer.json
```

```text
receipt:   LFM3-1.7B-Q4_K_M.gguf, 15 prompt and 18 output tokens, seed 42, made on cpu-x86_64-avx2 by Kinetic 0.1.0 (build 378534cb64f30a15)
signature: valid, public key 8e79e51c11472a6cffd70635753a7cce14c4335e1f18435459c3ebb35b3f720b
model:     LFM3-1.7B-Q4_K_M.gguf matches (BLAKE3 f4240740be2392a2)
rerun:     identical, 18 of 18 output tokens on cpu-x86_64-avx2 (BLAKE3 7bd0632303b6fcbd)
```

`verify-receipt` checks the token hashes and the signature, hashes the model
file (or takes the hash from the cache) and refuses a file that is not the
receipt's, then reruns the recorded prompt tokens with the recorded
settings on one slot with RAD-1 drafting, Warm Start, Zero Wait and Convoy
off: the plainest way Kinetic can decode. It prints `identical`, or the
first output token that differs together with what differs between the two
runs. `--model` points at the model when it moved, and `--device` reruns
elsewhere.

## Signing

```sh
openssl rand -hex 32 > receipt.key
kinetic run model.gguf "Name three rivers." --receipt answer.json --sign-key receipt.key
kinetic serve model.gguf --sign-key receipt.key
```

The key file holds an Ed25519 secret key as 32 bytes or 64 hex digits; keep
it private. The signature covers every other field of the receipt as compact
JSON, so changing the seed, a setting, a token or the text breaks it.
`verify-receipt` prints the public key it checked against: a signature only
says who made the receipt if you know that key is theirs.

## What a receipt proves, and what it does not

A receipt that verifies as identical proves that this model file, run by
this build on this device class with these settings, turns these prompt
tokens into these output tokens. Anyone with the same file and build can
check it, on any machine of the same class, without trusting the server
that made it.

It does not prove:

- **Anything across device classes.** The CPU, CUDA and Vulkan paths sum in
  different orders, so they round differently; bits are promised only
  within one class and one build. A receipt from a GPU reruns on the same
  compute capability (sm_86 to sm_86). `verify-receipt` says so when the
  class or build differs, and a difference then is expected rather than a
  bug. Different CPU core counts are fine: threads split rows, not sums.
  On Vulkan the driver compiles the shaders, so a different driver version
  may round differently too.
- **That the answer is correct.** A receipt pins how an answer was made,
  not whether it is true.
- **That the server ran the receipt's model**, unless you rerun it. A
  receipt is a claim until `verify-receipt` reproduces it; a signature only
  shows who made the claim.
- **Images.** Requests with images cannot have a receipt yet.

The text in `output.text` is decoded from the output tokens after stop
strings and reasoning are split off; the tokens are what is compared.
