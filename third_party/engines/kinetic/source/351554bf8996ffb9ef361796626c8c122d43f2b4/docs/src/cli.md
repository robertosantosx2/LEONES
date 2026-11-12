# Command line

```text
kinetic <COMMAND> [OPTIONS] [MODEL] ...
```

| Command | Does |
|---|---|
| [`run`](#run) | answers one prompt, streamed to stdout |
| [`chat`](#chat) | chats in the terminal |
| [`serve`](#serve) | serves OpenAI- and Ollama-compatible APIs |
| [`bench`](#bench) | measures load time, prompt, generation and edit speed, and peak memory |
| [`info`](#info) | shows what a model file contains |
| [`models`](#models) | lists the models on this computer, Ollama's and LM Studio's included |
| [`pull`](#pull) | downloads a model from Hugging Face, the only command that uses the network |
| [`doctor`](#doctor) | checks the CPU, memory, GPUs, drivers and disk, and says what to fix |
| [`fit`](#fit) | shows where each model would run and roughly how fast |
| [`verify`](#verify) | checks every hash of a `.ktc` file and reports its signature |
| [`verify-receipt`](#verify-receipt) | reruns the request a receipt records and checks every output token |
| [`quantize`](#quantize) | writes a GGUF model in another type, as `llama-quantize` does |
| [`perplexity`](#perplexity) | measures perplexity and KL divergence over a text file, as `llama-perplexity` does |

`kinetic` alone in a terminal checks the computer, lists two or three models
that run well on it with their size and expected speed, models already on
disk first, and waits for one key: `1`-`3` or Enter picks, `q` quits. A model
not on disk yet is downloaded as [`pull`](#pull) does, then [`chat`](#chat)
opens. Nothing is downloaded before you pick. With input or output
redirected, `kinetic` prints the help as before.

Every command except `verify` and `verify-receipt` takes the model as its first argument or with
`-m`/`--model`, as a `.gguf` or `.ktc` file. `kinetic --version` prints the
version and `kinetic <command> --help` the options of a command.

Kinetic exits with 0 on success, 1 when the command fails (a missing file, a
model that cannot load) and 2 for an invalid command line, including a
llama.cpp flag it does not take; see [llama.cpp flags](llama-flags.md).

## run

```sh
kinetic run model.gguf "Explain recursion in two sentences."
kinetic run -m model.gguf -p "Explain recursion."
kinetic run model.gguf < prompt.txt
```

The prompt goes through the model's chat template as one user message, after
the `--system` prompt if there is one, and the answer streams to stdout.
Without a prompt, `run` reads it from stdin. When the answer is done, a
status line on stderr gives the number of tokens, the speed of the answer
and of the prompt, and the device:

```text
[45 tokens at 25.5 tok/s; prompt 37 tokens at 62.8 tok/s on the CPU]
```

When stdout goes to a file or a pipe, the speed is also shown live on
stderr. Only the answer goes to stdout, so `kinetic run ... > answer.txt`
captures just the text.

`--receipt FILE` also writes a [receipt](receipts.md) for the answer: the
model's hash, the build, the device class, the prompt tokens, every sampling
setting with the seed, and the output tokens. Without `--seed`, a fresh seed
is picked and recorded.

```sh
kinetic run model.gguf "Name three rivers." --temp 0.8 --receipt answer.json
kinetic verify-receipt answer.json
```

### Generation options

`run` and `chat` take these:

| Option | Meaning |
|---|---|
| `--system <TEXT>` | system prompt |
| `-n`, `--n-predict <N>` | most tokens per answer; `-1` or `0` for no limit [default: no limit] |
| `--temp <T>` | temperature; 0 always picks the likeliest token [default: the model's] |
| `--top-k <N>` | sample from the N likeliest tokens; 0 for all |
| `--top-p <P>` | sample from the likeliest tokens that add up to P |
| `--min-p <P>` | skip tokens less than P times as likely as the best |
| `--repeat-penalty <X>` | penalty for repeating recent tokens; 1 for none |
| `--reasoning off` | `chat` starts with the model's reasoning off (llama.cpp's `-rea off`); `/think` turns it on |
| `-s`, `--seed <N>` | seed for repeatable sampling |
| `--presence-penalty <X>`, `--frequency-penalty <X>` | subtracted from the logits of recent tokens, once or per time seen |
| `--typical <P>` | locally typical sampling; 1 for none |
| `--top-nsigma <N>` | keep tokens within N standard deviations of the best logit; -1 for none |
| `--xtc-probability <P>`, `--xtc-threshold <P>` | XTC: with that chance, drop every token at least the threshold likely but the least likely |
| `--dry-multiplier <X>`, `--dry-base <X>`, `--dry-allowed-length <N>`, `--dry-penalty-last-n <N>` | DRY repetition penalty; multiplier 0 for none |
| `--dry-sequence-breaker <TEXT>` | text that ends a repetition for DRY, repeatable; `none` for none |
| `--mirostat <N>`, `--mirostat-lr <X>`, `--mirostat-ent <X>` | Mirostat 1 or 2 with its eta and tau, in place of the other samplers |

The sampler flags carry llama.cpp's names and meanings, and samplers run in
its default order: logit bias, penalties, DRY, top-n-sigma, top-k, typical,
top-p, min-p, XTC, temperature; with Mirostat, temperature then Mirostat.
Sampling defaults come from the model file (`general.sampling.*`) where it
has them. Whatever the settings, speculative decoding never changes the
answer: greedy output is token for token what plain decoding gives, and a
seeded answer is the same for the same seed.

### Runtime options

`run`, `chat` and `serve` take these:

| Option | Meaning |
|---|---|
| `-c`, `--ctx-size <N>` | most tokens per conversation, prompt and answer together; 0 uses all the model supports [default: 32768, or less if the model was trained on less, or if its cache would not fit beside the model on the GPU] |
| `-t`, `--threads <N>` | CPU threads [default: all] |
| `--device <auto\|cpu\|cuda\|vulkan>` | where the model runs; `auto` tries CUDA, then Vulkan, then the CPU [default: auto]; see [Devices](devices.md) |
| `--gpu-layers <N>` | most layers on the GPU, the rest on the CPU [default: as many as fit]; see [Devices](devices.md#dense-models-larger-than-the-gpu) |
| `--cache-dir <DIR>` | where Warm Start keeps prompt states [default: `kinetic/warm` in the user's cache directory] |
| `--no-prompt-cache` | run every prompt from its first token; same as `--off warm-start` |
| `--off <LIST>` | turn speed technologies off, comma-separated: `rad1`, `warm-start`, `zero-wait`, `shortlist`, `torque`, `convoy` |
| `--cache-type-k <f16\|q8_0>`, `--cache-type-v <f16\|q8_0>` | how the CUDA cache stores keys and values; `q8_0` takes about half the memory but changes outputs [default: f16]; see [Devices](devices.md#memory) |
| `--rope-scaling <none\|linear\|yarn>` | rotary scaling for contexts longer than the model was trained on; overrides the file |
| `--rope-scale <N>` | context stretch factor (`--rope-freq-scale` takes its inverse, as llama.cpp does) |
| `--rope-freq-base <N>` | rotary base, for NTK-aware scaling |
| `--yarn-orig-ctx <N>` | the context the model was trained on, for YaRN |
| `--sign-key <FILE>` | sign [receipts](receipts.md) with this Ed25519 secret key, 32 bytes or 64 hex digits |
| `--mlock` | keep the model in RAM, so the system never swaps it out (GGUF files) |
| `--no-mmap` | read the model into memory instead of mapping the file (GGUF files) |
| `--chat-template-file <FILE>` | Jinja chat template to use instead of the model's own |
| `--lora <FILE>[,<FILE>...]` | LoRA adapters in llama.cpp's GGUF format, merged into the weights at load |
| `--lora-scaled <FILE>:<SCALE>[,...]` | the same with scales; `--lora-scaled FILE SCALE`, as older llama.cpp builds took it, works too |

Without `-c` and `--gpu-layers`, a context whose cache would not fit next to
the model on the CUDA GPU shrinks to the largest that does, a multiple of 1024
and at least 4096, with one line such as `context 8k to fit the GPU; -c to
change`, rather than moving layers to the CPU. An explicit `-c` always wins.

Every speed technology is exact, so `--off` changes only speed: use it to
measure what each one gives, or to rule one out when reporting a bug.
`kinetic serve` prints which run on the device it picked, for example
`Speed technologies on: RAD-1, Warm Start, Zero Wait, Torque, Convoy; off: Shortlist`.

### LoRA adapters

`--lora` takes adapters as llama.cpp's `convert_lora_to_gguf.py` writes them
(`general.type = adapter`, `adapter.type = lora`, `lora_a` and `lora_b` per
adapted weight). Each adapted matrix becomes `W + scale * alpha / rank * B A`
at load, held in F32, so the model runs as fast as without the adapter on
every device but takes 4 bytes per weight of each adapted matrix. Adapters on
the token embeddings or on expert tensors are refused. Warm Start is off
while an adapter is in use.

## chat

```sh
kinetic chat model.gguf --system "You are a concise assistant."
```

Reads one message per line; end a line with `\` to go on writing on the
next one. Each turn reuses the work of the previous ones, and the message
runs on the model while it is being typed or pasted
([Zero Wait](how-it-is-fast.md#zero-wait)), so after Enter only its last
words are processed. Ctrl+C stops an answer, and the conversation goes on.

| Command | Does |
|---|---|
| `/clear` | starts a new conversation |
| `/system TEXT` | sets the system prompt and starts over; `/system` alone clears it |
| `/think` | turns the model's reasoning on or off (off at start); reasoning is shown dimmed |
| `/temp X`, `/top-p X`, `/top-k N`, `/min-p X` | change sampling for the next answers |
| `/seed N` | makes answers repeatable; `/seed` alone picks a fresh seed each time |
| `/sampling` | shows the sampling settings |
| `/image PATH` | attaches an image to the next message; `/image` alone takes the image on the clipboard |
| `/receipt [FILE]` | writes the [receipt](receipts.md) of the last answer to FILE, or prints it |
| `/help` | lists the commands |
| `/exit`, `/quit` | quits, as Ctrl+D does |

A model with a vision projector, stored with it or given with
`--mmproj FILE`, sees images; the header says so. Drop an image file on the
window (the terminal pastes its path) or use `/image`: the image goes out
with the next message, and the prompt shows how many are waiting. PNG,
JPEG, WebP, BMP and GIF files work. On Linux, `/image` alone reads the
clipboard with `wl-paste` or `xclip`. Images are encoded on the GPU when the
model runs there; turns with an image run whole, without Zero Wait.

When stdin is not a terminal, `chat` reads one message per line and prints
each answer, which is handy for scripted tests. Takes the
[generation](#generation-options) and [runtime](#runtime-options) options.

## serve

```sh
kinetic serve model.gguf
kinetic serve model.gguf --port 9000 -c 8192
kinetic serve Qwen3.5-4B-Q4_K_M.gguf --mmproj Qwen3.5-4B-mmproj-F16.gguf
```

| Option | Meaning |
|---|---|
| `--host <ADDR>` | address to listen on [default: 127.0.0.1] |
| `--port <PORT>` | port [default: 8080, or 11434 with `--ollama`] |
| `--ollama` | listen on Ollama's port, so apps made for Ollama work unchanged |
| `--mmproj <FILE>` | vision projector of a multimodal model, so requests may carry images |
| `--alias <NAME>` | model name the API reports [default: the file's name] |
| `--api-key <KEY>` | require `Authorization: Bearer <KEY>` (or `X-Api-Key: <KEY>`) on every route but `/health`; others get 401 |

and the [runtime options](#runtime-options). The start-up line names the
model, the device and the address:

```text
Serving Qwen3-0.6B-Q8_0 on the CPU at http://127.0.0.1:8080/v1
```

The model's name in the API is its file name without the extension, or
`--alias`. A text
model gets the chat and completion endpoints, an embedding model the
embeddings endpoint and a reranker the rerank endpoint; see the
[server API](server.md). Embedding and reranking models run on the CPU.

Warm Start keeps the states of earlier prompts in memory (up to 1 GiB) and
under `--cache-dir` (up to 2 GiB, least recently used out first), so a
prompt that starts like an earlier one, even from before a restart, only
runs its new tokens. It works on the CPU and on the GPU, resumes only when
that is faster than recomputing, and gives exactly the answer a cold run
gives.

Any `--host` other than a loopback address makes the server reachable by
other computers, which Kinetic warns about; pair it with `--api-key`.

## bench

```sh
kinetic bench model.gguf
kinetic bench model.gguf --device cpu -t 6 -r 5 --json
```

| Option | Meaning |
|---|---|
| `-r`, `--repetitions <N>` | runs of each test; the best is reported [default: 3] |
| `-t`, `--threads <N>` | CPU threads [default: all] |
| `--device <auto\|cpu\|cuda>` | the device to measure [default: auto] |
| `--json` | print the results as one JSON object |
| `--compare [LLAMA_BENCH]` | also run llama.cpp on the same file and print a card with both; see [bench --compare](#bench---compare) |
| `--off <LIST>` | turn speed technologies off, as for `run`; bench measures RAD-1 (`edit256`), Shortlist and Torque |

Three tests, each the best of `-r` runs:

- `pp512`: a 512-token prompt, as in `llama-bench`;
- `tg128`: 128 generated tokens, as in `llama-bench`, with speculative
  decoding off so every token costs one pass over the weights;
- `edit256`: 256 tokens of an answer that rewrites a short Rust file with
  one name changed, with speculative decoding on, the way an editing request
  runs. Its output is compared with plain decoding.

```text
| model | size | params | backend | threads | test | t/s |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| SmolLM2-135M-Instruct-f16 | 0.25 GiB | 0.13 B | CPU | 4 | pp512 | ... |
| SmolLM2-135M-Instruct-f16 | 0.25 GiB | 0.13 B | CPU | 4 | tg128 | ... |
| SmolLM2-135M-Instruct-f16 | 0.25 GiB | 0.13 B | CPU | 4 | edit256 | ... |

on the CPU, best of 3, load 0.53 s
speed technologies on: RAD-1, Shortlist; Warm Start, Zero Wait and Convoy take no part
edit: drafted output identical to plain decoding: yes
peak memory 0.31 GiB
```

To see what one technology gives, run `bench` twice, with and without
`--off` naming it, and compare the rows: `--off rad1` runs `edit256`
without drafting, `--off shortlist` and `--off torque` change `tg128` and
`edit256`. The line under the table says which ran; Warm Start, Zero Wait
and Convoy need repeated, typed or concurrent requests, which `bench`
never sends, so it says they take no part.

If the drafted output ever differs from plain decoding, `bench` says `NO`
and exits with 1; please [report it](https://github.com/Veloresearch/kinetic/issues/new?template=bug.yml).
`--json` prints:

```json
{
  "model": "SmolLM2-135M-Instruct-f16.gguf",
  "backend": "cpu",
  "device": "the CPU",
  "threads": 4,
  "repetitions": 3,
  "load_seconds": 0.0135,
  "size_bytes": 270885952,
  "parameters": 134515008,
  "prefill_tokens": 512,
  "prefill_tokens_per_second": 354.05,
  "decode_tokens": 128,
  "decode_tokens_per_second": 49.01,
  "edit_tokens": 256,
  "edit_tokens_per_second": 118.9,
  "edit_identical": true,
  "technologies": "on: RAD-1, Shortlist",
  "peak_rss_bytes": 333955072
}
```

`backend` is `cpu` or `cuda`, and `device` names the GPU.

## info

```sh
kinetic info model.gguf
```

Name, architecture and whether Kinetic supports it, size and parameter
count, context length, layers and width, whether the file has a prediction
block that drafts for speculative decoding, the weight types with their
tensor counts and sizes, the tokenizer and the size of the chat template.
It reads only the file's header, so it is instant even for large files. See
[Models and formats](models.md) for an example.

## verify

```sh
kinetic verify model.ktc
```

Recomputes the BLAKE3 hash of every section of a `.ktc` file and reports
whether it is signed. Exits with 1 when any hash does not match.

## verify-receipt

```sh
kinetic verify-receipt answer.json
kinetic verify-receipt answer.json --model other/path/model.gguf --device cpu
```

Checks a [receipt](receipts.md): the token hashes and, if it is signed, the
signature; then the model file's BLAKE3 (from a cache, so a large file is
hashed once); then reruns the recorded prompt tokens with the recorded
settings, alone, with drafting, the prompt cache, Zero Wait and Convoy off.
It prints `identical` or the first output token that differs, with the
reason when the build, the device class or a load setting differs. The
rerun goes to the receipt's device unless `--device` says otherwise; `-t`
sets the CPU threads. Exits with 1 when anything does not match.

```text
receipt:   LFM3-1.7B-Q4_K_M.gguf, 15 prompt and 18 output tokens, seed 42, made on cpu-x86_64-avx2 by Kinetic 0.1.0 (build 378534cb64f30a15)
signature: valid, public key 8e79e51c11472a6cffd70635753a7cce14c4335e1f18435459c3ebb35b3f720b
model:     LFM3-1.7B-Q4_K_M.gguf matches (BLAKE3 f4240740be2392a2)
rerun:     identical, 18 of 18 output tokens on cpu-x86_64-avx2 (BLAKE3 7bd0632303b6fcbd)
```

## quantize

```sh
kinetic quantize model-f16.gguf model-Q4_K_M.gguf Q4_K_M
```

Reads a GGUF model with F32, F16, BF16 or Q8_0 weights and writes it as
`Q8_0`, `Q6_K`, `Q5_K_M`, `Q4_K_M` or `Q4_0`. Each tensor gets the type
`llama-quantize` gives it for that target (the `_M` mixtures keep some
`attn_v` and `ffn_down` layers and the output in `Q6_K`; rows that are not
a whole number of 256-value blocks fall back to `Q5_0`, `Q5_1` or `Q8_0`),
and the blocks are encoded as llama.cpp's reference quantizers encode them:
without an importance matrix the output file is byte for byte the one
`llama-quantize` writes, and llama.cpp loads it. `-t` sets the threads.
Importance matrices (`--imatrix`) are not read yet.

## perplexity

```sh
kinetic perplexity model.gguf wiki.test.raw -c 512
kinetic perplexity model-f16.gguf wiki.test.raw --chunks 20 --kl-divergence-base base.kld
kinetic perplexity model-Q4_K_M.gguf --kl-divergence base.kld
```

Scores the text as `llama-perplexity` does: the tokens are cut into chunks
of `-c` tokens (default 512), each chunk starts with BOS where the model
uses one, and only the second half of each chunk is scored. It prints the
running estimate after every chunk and `Final estimate: PPL = ... +/- ...`.
`--kl-divergence-base FILE` saves the log-probabilities in
`llama-perplexity`'s format, and `--kl-divergence FILE` compares another
model against such a file, from either tool, on the tokens stored in it:
mean PPL of both, the mean KL divergence, RMS Δp and how often the top
token agrees. Runs on the CPU; `-t` sets the threads.

## models

```sh
kinetic models
kinetic run qwen3:4b "Hi"
kinetic serve lmstudio-community/Qwen3-4B-GGUF:Q4_K_M
```

Lists the GGUF models already on this computer: Kinetic's own folder
(`KINETIC_MODELS`, or `%LOCALAPPDATA%\kinetic\models` and
`~/.local/share/kinetic/models`), Ollama's store (`OLLAMA_MODELS` or
`~/.ollama/models`), LM Studio's (`~/.lmstudio/models`), the Hugging Face
cache (`HF_HUB_CACHE`, `HF_HOME`), llama.cpp's (`LLAMA_CACHE`) and, on
Windows, `C:\models`. Only file headers are read.

```text
NAME                                     SIZE  QUANT     ARCH            RUNS ON KINETIC         FROM
LFM3-1.7B-Q4_K_M                     1.02 GiB  Q4_K_M    lfm3            yes                     folder
gemma-4-E2B_q4_0-it                  3.12 GiB  Q4_0      gemma4          no                      folder
```

Every command takes such a name in place of a file. A bare Ollama name takes
its `latest` tag, or its only tag; a repository with several files takes
`:<quant>`. A name that matches nothing lists the closest ones. `serve` also
picks up the vision projector stored with the model.

## pull

```sh
kinetic pull ggml-org/gemma-3-1b-it-GGUF
kinetic pull unsloth/Qwen3-4B-GGUF:Q4_K_M
kinetic pull org/repo --file model-Q8_0.gguf --no-mmproj
```

Downloads a GGUF model from Hugging Face into Kinetic's models folder (or
`--dir`) and prints the name to run it by. It takes the file of the named
quantization, or when none is named the largest of Q4_K_M, Q5_K_M, Q6_K and
Q8_0 that fits the GPU's free memory (or half the free RAM without one) with
room for context, Q4_K_M at least, and says which and why; every part of a split model, and the
repository's vision projector unless `--no-mmproj`. Before downloading it
prints the source, the files and their size, and it refuses when the disk
would keep less than 2 GiB free. Downloads resume where they stopped, are
checked against the SHA256 that Hugging Face publishes and are renamed into
place only when they match. `HF_TOKEN` is sent for gated repositories and
`HF_ENDPOINT` names a mirror. The transfer runs through the system's `curl`.

Kinetic never connects to the network, except when you run `kinetic pull`;
`run`, `chat`, `serve` and the others never download anything.

When a command fails, the error ends with a line saying what to do: a path
to check, a smaller model or `-c`, a driver to install, a free `--port`, or a
download to repeat.

## doctor

```sh
kinetic doctor
```

One screen with the operating system, the CPU and its AVX2, FMA and F16C
support, memory and its measured read speed, every GPU that CUDA and Vulkan
report with its driver and free memory, the models found and the free disk,
followed by what to fix.

```text
Kinetic 0.1.0
  system   Windows 11 (build 26300)
  cpu      AMD Ryzen 5 6600H with Radeon Graphics, 12 threads, AVX2 yes, FMA yes, F16C yes
  memory   15.2 GiB, 6.4 GiB available, reads at 40 GB/s (measured)
  gpu      NVIDIA GeForce RTX 3060 Laptop GPU via CUDA: 5.0 of 6.0 GiB free, 336 GB/s nominal; CUDA 13.3, compute 8.6
  gpu      NVIDIA GeForce RTX 3060 Laptop GPU via Vulkan: 5.9 GiB; NVIDIA 610.62, Vulkan 1.4.341
  models   4 found, 1 that Kinetic runs (`kinetic models` lists them)
  disk     7.1 GiB free for C:\Users\me\AppData\Local\kinetic\models

To fix:
  - under 10 GiB of disk is free where models are kept
```

## fit

```sh
kinetic fit
kinetic fit qwen3:4b
kinetic fit D:\models
```

For every model found, or the one or the folder given: whether it fits
wholly on the GPU, needs its experts kept on the CPU (mixture-of-experts
models), or runs on the CPU, with a decode speed range estimated from the
bytes it reads per token and the memory bandwidth. `kinetic bench` measures
the real speed.

```text
MODEL                                    SIZE  RUNS ON               EXPECTED DECODE
LFM3-1.7B-Q4_K_M                     1.02 GiB  GPU                   169-262 t/s
```

## bench --compare

```sh
kinetic bench model.gguf --compare
kinetic bench model.gguf --compare C:\llama.cpp\llama-bench.exe --json
```

Runs Kinetic's bench and then llama.cpp's own `llama-bench` on the same file
with the same threads, device (`-ngl 99`, or `-ngl 0 -dev none` on the CPU)
and repetitions, flash attention on, taking llama.cpp's best run as Kinetic
takes its own. llama.cpp's edit test runs through `llama-server` with its
speculative mode for the model (`draft-mtp` where the model has prediction
layers, otherwise `ngram-simple`). `llama-bench` is looked for on `PATH` and
in the usual install folders; Kinetic never downloads it. The card is a
markdown table with a one-line summary; `--json` prints the same as JSON.

```text
## Kinetic vs llama.cpp: LFM3-1.7B-Q4_K_M

| test | Kinetic 0.1.0 | llama.cpp b12001 (eb4e244be) | ratio |
| --- | ---: | ---: | ---: |
| prompt pp512 | 6780.5 | 6667.7 | 1.02x |
| generate tg128 | 191.0 | 166.8 | 1.15x |
| edit256 | 702.7 | 207.7 | 3.38x |

NVIDIA GeForce RTX 3060 Laptop GPU, AMD Ryzen 5 6600H with Radeon Graphics, Windows 11 (build 26300)
Same file (1.02 GiB, Q4_K_M), all layers on the GPU, 12 threads, flash attention on, best of 2, t/s.
edit256: greedy copy of a file with one rename; llama.cpp speculative mode ngram-simple; Kinetic's output identical to plain decoding: yes.
```

## llama.cpp flags

Common llama.cpp flags work unchanged, and Kinetic explains the ones it does
not need instead of rejecting them blindly; see
[llama.cpp flags](llama-flags.md).
