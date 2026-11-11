# tandem.cpp

tandem.cpp is a patch set for [llama.cpp](https://github.com/ggml-org/llama.cpp). It makes MoE models that don't fit in VRAM run faster in llama.cpp. It keeps the most-used experts on the GPU and lets the CPU help with the rest, for any MoE model llama.cpp supports. Single-user decode is the target.

It is an independent project, not affiliated with ggml-org. Base: llama.cpp `f5222f25c` (2026-10-28, see `BASE_COMMIT`).

On a consumer PC (i5-12400F, 64 GB DDR4, RTX 4090), GSM8K, decode tok/s:

| Model | llama.cpp | tandem.cpp | Strata |
|---|---|---|---|
| Qwen3.8-Flash-Next IQ3_S + MTP, greedy | 29.8 | **97.3** (3.3×) | 103.6 |
| same, Qwen's default sampling | 29.4 | **96.1** (3.3×) | 98.1 |
| gpt-oss-120b, greedy | 27.8 | **51.5** (1.85×) | — |
| gpt-oss-120b, its recommended sampling | 27.7 | **48.0** (1.73×) | — |

We tuned for Qwen3.8 only, but other MoE models that do not fit in VRAM gain too: typically 1.4–2.1× (gpt-oss-120b, GLM-4.5-Air, Qwen3.6-35B-A3B, DeepSeek-V4.1), less when the model nearly fits. Prompt processing is faster as well (1.4–1.8× on a 64k-token prompt).

[Strata](https://github.com/Niko1221/Strata) is a dedicated MoE offload engine for a few models. Its default skips low-ranked experts (`STRATA_ROUTE_TAIL_SKIP`), which is faster but approximate (127.1 tok/s on Qwen3.8 above); the tables show its exact mode (`STRATA_ROUTE_TAIL_SKIP=0`, every routed expert computed, as llama.cpp and tandem.cpp do). Full tables per machine are [below](#results).

## Build

```
bash build.sh            # clones llama.cpp into ./tandem, checks out the base commit, applies tandem.patch, builds llama-server
```

or by hand:

```
git clone https://github.com/ggml-org/llama.cpp tandem && cd tandem && git checkout f5222f25c
git apply ../tandem.patch
cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build -j --target llama-server
```

Tested with CUDA 13.0–13.4 on Ubuntu 22.04 and 24.04, sm_89 (RTX 4090, RTX 6000 Ada) and sm_120 (RTX PRO 6000 Blackwell).

## Run

How it works: the experts live in host RAM, and the GPU memory left over holds a cache of recently used experts. The experts a token needs that are not in the cache are split between the CPU, which computes its share while the GPU runs the cached ones, and an upload into the cache. The split follows the measured CPU and PCIe speeds, using Strata's rule.

Any MoE model whose experts do not fit in VRAM:

```
llama-server -m model.gguf -ngl 99 -cmoe --moe-cache-mib auto -lm none -np 1 -c 16384
```

- `-cmoe` keeps every expert in host RAM. `--moe-cache-mib auto` gives the GPU memory left after the model, the KV cache and the compute buffers to the expert cache, minus `--moe-cache-margin-mib` (default 1024; a draft model's size is added automatically). A fixed size in MiB also works.
- `-lm none` reads the weights into RAM instead of mmapping the file.
- `-np 1 -c 16384`: one conversation with a 16k-token context. Without them llama-server opens 4 slots that share a small context, too short for a thinking model. `-c` is the total context; the KV cache comes out of the GPU memory the expert cache would get, so set it to what you need (on Qwen3.8, about 0.7 GiB per extra 16k tokens).
- The startup line `failed to fit params ... n_gpu_layers already set by user to 99, abort` is expected: `-ngl 99` turns llama.cpp's automatic placement off, and the expert cache does the placement instead.
- **Less RAM than the model** (e.g. Qwen3.8 IQ3_S, 78 GiB, on a 64 GB PC): leave out `-lm none`. The file stays mapped; the experts are copied once into pinned memory when the RAM holds them plus 10 GiB, and the rest is read from the file.
- **Much less RAM (e.g. a 16 GB PC):** also pass `--cache-ram 0`. llama-server's prompt cache otherwise takes up to 8 GiB of RAM and pushes the experts out of the page cache.
- Supported expert types for the CPU path: SwiGLU experts (fused or separate gate/up, optional clamp) and gpt-oss's SwiGLU-OAI with biases. For other types the server logs a warning and uploads every miss instead (correct, slower).

Qwen3.8-Flash-Next with its MTP head (the head as a separate GGUF). Download the model (IQ3_S, 78 GiB, two files) and the head (Q4_K):

```
hf download ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF --include 'IQ3_S/*' --local-dir models
hf download ewhacc/qwen38-mtp-outq4_K-expsq4_K --include '*.gguf' --local-dir models
```

then run:

```
LLAMA_MTP_DRAFT_VOCAB=100000 llama-server -m models/IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf \
  -ngl 99 -cmoe --moe-cache-mib auto -lm none -np 1 -c 16384 \
  --spec-type draft-mtp -md models/qwen38-mtp-outq4_K-expsq4_K.gguf --spec-draft-n-max 3 --spec-draft-sampling probabilistic \
  -bs -ot '^token_embd\.weight=CUDA0'
```

- The head ([ewhacc/qwen38-mtp-outq4_K-expsq4_K](https://huggingface.co/ewhacc/qwen38-mtp-outq4_K-expsq4_K), Qwen Community License 1.0) was made with `convert_hf_to_gguf.py --mtp` on the original checkpoint (Q8_0), then its output and expert tensors to Q4_K: `llama-quantize --allow-requantize --tensor-type output=q4_K --tensor-type _exps=q4_K qwen38-mtp-q8_0.gguf qwen38-mtp.gguf Q8_0`. That takes it from 3.6 to 1.8 GiB of VRAM with the same acceptance; the freed memory goes to the expert cache.
- `--spec-draft-n-max 3` is best on 24 GB cards and 6–10 core CPUs; 4 on a 48 GB card.
- `--spec-draft-sampling probabilistic` keeps sampled output exact (rejection sampling) and acceptance high at the model's default temperature.

gpt-oss-120b with its EAGLE3 draft (`ggml-org/gpt-oss-120b-GGUF`):

```
llama-server -m gpt-oss-120b-MXFP4.gguf -ngl 99 -cmoe --moe-cache-mib auto -lm none -np 1 -c 16384 \
  --spec-type draft-eagle3 -md eagle3-gpt-oss-120b-Q8_0.gguf --spec-draft-n-max 4
```

EAGLE3 helps on 10+ core CPUs and slows things down on a 6-core one (see the consumer PC table).

## Defaults

The server applies these when the variable is unset (logged at startup); `VAR=0` turns one off, `LLAMA_MOE_NO_DEFAULTS=1` turns all off. All are exact or differ only in floating-point rounding (kernel choice); the Qwen3.8-specific ones act only on that architecture.

| Variable | Default | What |
|---|---|---|
| `LLAMA_MOE_CPU` | `auto` | CPU/GPU split for missed experts (`0..1` = fixed share uploaded) |
| `LLAMA_MOE_PREFILL_CPU` | `auto` | the split for prompt batches |
| `LLAMA_MOE_CPU_THREADS` | cores − 1 | CPU threads for missed experts |
| `LLAMA_MOE_CPU_RB`, `LLAMA_MOE_CPU_DOWN_PE` | `64`, `64` | CPU expert job work-item layout |
| `LLAMA_MOE_PIN_EXPS` | auto | mmap mode: copy the mapped experts to pinned memory when the RAM holds them + 10 GiB |
| `GGML_SCHED_BATCH_INPUTS` | `3` | a graph's host inputs in one packed upload |
| `GGML_CUDA_GRAPH_KEY_SHAPE` | `1` | one CUDA graph per batch shape |
| `GGML_CUDA_MMVF_MAX` | `8` | vector kernel for float weights up to 8 columns |
| `GGML_CUDA_Q8_CACHE` | `1` | reuse quantized activations across matvecs |
| `LLAMA_GRAPH_POOL` | `6` | keep allocated graphs for alternating small batch shapes |
| `LLAMA_SRV_USER_BREAK` | `0` | no prompt-cache checkpoint at every user message |
| `LLAMA_MTP_DEFER` | `1` | MTP catch-up decode deferred to the next draft |
| `LLAMA_HC_FUSE`, `GGML_CUDA_HC_MIX_FUSE` | `1` | hyper-connection fusions (Qwen3.8) |
| `LLAMA_GDN_DIRECT`, `LLAMA_GDN_GATES` | `1` | Qwen3.8 gated delta net |
| `LLAMA_CONV_CONT`, `LLAMA_CONV_TAIL` | `1` | Qwen3.8 conv state |
| `LLAMA_PLE_GPU` | `1` | per-layer embeddings read by the GPU from pinned host memory |
| `LLAMA_PLE_GPU_COPY` | auto | Linux 6.8+ (file mmaps cannot be pinned): copy the table to pinned memory, only when the RAM holds the model + 8 GiB |

## Results

Single user, the first 200 GSM8K test questions (zero-shot chat, max 2048 tokens), decode tok/s. Every row gives both engines the same GPU memory and the same draft model, if any. llama.cpp is `f5222f25c` with its default placement (`-fit on`: dense layers on the GPU, then as many layers' experts as fit), with `-fitt` set to tandem.cpp's margin when a draft model is loaded. Each cell is "greedy / sampled", sampled being the model's recommended sampling (Qwen: T 1.0, top-k 20, top-p 0.95; gpt-oss: T 1.0, top-p 1.0; GLM: the server's defaults; DeepSeek: T 1.0, top-p 0.95). Accuracy is within run-to-run noise between the engines in every row. The scripts are in [`bench/`](bench/).

Models: Qwen3.8-Flash-Next [ISTA GSQ-RCO](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) IQ3_S (78 GiB) with the Q4_K MTP head above; gpt-oss-120b MXFP4 (`ggml-org`); Qwen3.6-35B-A3B UD-Q4_K_XL and GLM-4.5-Air Q4_K_M (unsloth); DeepSeek-V4.1-Flash-1017 [ISTA GSQ-RCO](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF) IQ2_XS (139 GiB of routed experts). We tuned for Qwen3.8 only.

### Consumer PC: i5-12400F (6 cores), 64 GB DDR4 (43 GB/s), RTX 4090 24 GB, PCIe 4.0 x16

The models are larger than RAM with the OS, so both engines read them from the mapped file.

| Model, setup | llama.cpp | tandem.cpp | | Strata exact |
|---|---|---|---|---|
| Qwen3.8 IQ3_S, MTP | 29.8 / 29.4 | 97.3 / 96.1 | 3.3× / 3.3× | 103.6 / 98.1 |
| gpt-oss-120b, no draft | 27.8 / 27.7 | 51.5 / 48.0 | 1.85× / 1.73× | |
| gpt-oss-120b, EAGLE3 | 25.2 / 24.2 | 41.1 / 42.0 | 1.63× / 1.74× | |
| DeepSeek-V4.1 IQ2_XS (3× RAM, from the SSD), no draft | 6.86 / – | 5.99 / – | 0.87× | 8.41 / – |

- Strata exact is 6% ahead greedy and 2% sampled on Qwen3.8; its default mode, which skips low-ranked experts, gives 127.1. tandem.cpp's equivalent (`LLAMA_MOE_TAIL_SKIP=7`, approximate, off by default) gives 123.6 / 124.3.
- On 6 cores EAGLE3 slows both engines down: verifying several tokens multiplies the experts the CPU must run.
- DeepSeek-V4.1 is three times this PC's RAM. Here tandem.cpp is slower than llama.cpp: its CPU path does not take misses that have to come from the SSD (to be fixed). Strata keeps a RAM store of the most-used experts.

### Older workstation: i9-10900X (10 cores), 8× DDR4-2666 (78 GB/s), RTX 4090 24 GB, PCIe 3.0 x16

| Model, setup | llama.cpp | tandem.cpp | |
|---|---|---|---|
| Qwen3.8 IQ3_S, MTP | 31.1 / 31.9 | 100.9 / 100.9 | 3.2× / 3.2× |
| gpt-oss-120b, no draft | 31.2 / 30.1 | 49.6 / 49.6 | 1.59× / 1.65× |
| gpt-oss-120b, EAGLE3 | 30.3 / 28.8 | 62.5 / 61.0 | 2.06× / 2.12× |

Drafts do not speed up llama.cpp on this host (Qwen3.8 29.8 without MTP): most of its experts run from system RAM, so verifying several tokens costs nearly as much as it saves.

### Workstation: Threadripper PRO 5955WX (16 cores), DDR4 (~80 GB/s read), RTX 6000 Ada 48 GB, PCIe 4.0 x16

| Model, setup | llama.cpp | tandem.cpp | | Strata exact |
|---|---|---|---|---|
| Qwen3.8 IQ3_S, MTP, whole card | 98.6 / 97.1 | 182.5 / 180.9 | 1.85× / 1.86× | 185.9 / 169.9 |
| Qwen3.8 IQ3_S, MTP, 12 GiB expert cache | | 131.1 / 131.9 | | 129.2 / 119.4 |
| Qwen3.8 IQ3_S, MTP, 4 GiB expert cache | | 91.3 / 89.5 | | 89.3 / 83.7 |
| gpt-oss-120b, whole card | 87.9 / 86.3 | 95.3 / 90.7 | 1.08× / 1.05× | |
| gpt-oss-120b, 24 GB budget | 47.1 / 47.3 | 70.7 / 68.5 | 1.50× / 1.45× | |
| gpt-oss-120b, EAGLE3, whole card | 88.7 / 84.4 | 136.7 / 126.8 | 1.54× / 1.50× | |
| Qwen3.6-35B-A3B (22.4 GB), fits | 173.1 / 173.1 | 179.2 / 179.2 | 1.04× / 1.04× | |
| Qwen3.6-35B-A3B, 16 GB budget | 117.8 / 117.8 | 148.6 / 148.6 | 1.26× / 1.26× | |
| Qwen3.6-35B-A3B, 12 GB budget | 97.2 / 96.5 | 136.5 / 135.4 | 1.40× / 1.40× | |
| Qwen3.6-35B-A3B, 8 GB budget | 79.8 / 80.0 | 115.0 / 114.5 | 1.44× / 1.43× | |
| GLM-4.5-Air (73 GB), whole card | 31.9 / 31.9 | 54.6 / 55.1 | 1.71× / 1.73× | |
| GLM-4.5-Air, 24 GB budget | 20.1 / 20.0 | 34.7 / 34.6 | 1.73× / 1.73× | |

The cache-size rows compare against Strata at the same expert cache; a "budget" is the GPU memory both engines may use. Strata's cache rows are its exact mode as above.

Long context: a 64k-token prompt of real text in a 72k context, two planted code words found in every cell, greedy. Prefill is the prompt's tokens over the time to its first token:

| Model, setup | prefill llama.cpp | prefill tandem.cpp | | decode llama.cpp | decode tandem.cpp | |
|---|---|---|---|---|---|---|
| Qwen3.8 IQ3_S, MTP | 600 tok/s (109 s) | 860 tok/s (76 s) | 1.44× | 88.0 | 158.4 | 1.80× |
| gpt-oss-120b, no draft | 660 tok/s (100 s) | 1150 tok/s (57 s) | 1.75× | 64.9 | 75.4 | 1.16× |
| gpt-oss-120b, EAGLE3 | 560 tok/s (117 s) | 1030 tok/s (63 s) | 1.84× | 85.0 | 125.5 | 1.48× |

On the GSM8K questions (short prompts) the time to first token is 1.6–2.7× lower with tandem.cpp in the rows we checked, except the consumer-PC DeepSeek row (22 s against 12 s, the SSD issue below).

### Server: EPYC 9534 (64 cores), DDR5 (~350 GB/s), RTX PRO 6000 Blackwell 96 GB, PCIe 5.0 x16

DeepSeek-V4.1-Flash-1017 IQ2_XS (139 GiB of experts), whole card, reasoning on:

| Setup | llama.cpp | tandem.cpp | | Strata v0.2.9 |
|---|---|---|---|---|
| no draft | 51.7 / 46.0 | 89.6 / 81.0 | 1.73× / 1.76× | 84.4 / 84.0 (6 experts, no DSpark) |
| DSpark draft (3 tokens) | 63.0 / – | 132.4 / 107.2 | 2.10× | 148.9 / – (its default: DSpark, up to 5 tokens) |

tandem.cpp caches 87 GiB of the experts here (98.7% hit rate). Five draft tokens with a 0.65 confidence cut-off, Strata's default, was slower for tandem.cpp (122.3).

### Quality

Qwen3.8 Q2_0, teacher-forced KL divergence of the next-token distribution against plain llama.cpp `f5222f25c` with the whole model on the GPU, 8-token batches:

| Build | mean KLD | same top token | PPL ratio |
|---|---|---|---|
| tandem.cpp, `LLAMA_MOE_NO_DEFAULTS=1` | 0.000000 | 100% | 1.000 |
| defaults, whole model on the GPU | 0.0091 | 96.1% | 0.999 ± 0.003 |
| defaults, 4 GiB cache + CPU path | 0.0093 | 95.5% | 1.000 ± 0.003 |

With the defaults off the patch computes exactly what llama.cpp does; the defaults change only rounding (fused kernels, kernel choice), and the cache and CPU path add ≤ 0.0002.

## Limits

- Greedy output is not repeatable run to run with an expert cache: which experts are cached, and which misses the CPU computes, depends on timing, and the CPU and GPU round differently. Accuracy is unchanged. A fixed share (e.g. `LLAMA_MOE_CPU=0.2`) makes it repeatable.
- Built for one user at a time. Concurrent requests work (tested at 2 and 4, accuracy unchanged) but gain less, and with a small cache several requests together can be slower in total than one.
- Multi-GPU: only `-sm layer` (the default) works with the cache; checked for correctness on 2 GPUs, not tuned for speed.
- Tested only with CUDA (NVIDIA GPUs) on Linux.
- Qwen3.8 GGUFs converted with a current llama.cpp may be a little slower than the ISTA files we measured (one fusion does not apply to their layout).
- Known issues, to be fixed:
  - models much larger than RAM (read from the SSD): the CPU path does not take the misses, so most of the gain is lost there: about level with llama.cpp for Qwen3.8 IQ3_S on a 32 GB PC with a 16 GB card (16.5 against 15.8 tok/s), slower in the consumer-PC DeepSeek row;
  - the RAM rules (`LLAMA_MOE_PIN_EXPS`, `LLAMA_PLE_GPU_COPY`) look at physical RAM, not a cgroup limit; inside a container with a memory limit set both to 0;
  - with more than 3 draft tokens the auto margin can be too small for the new CUDA graphs (out of memory at the first longer verify); raise `--moe-cache-margin-mib`;
  - DeepSeek-V4.1 with `-lm none` loads very slowly (its 103 GiB Engram tables are copied page by page); run it without `-lm none`.

## Licence

MIT, see [LICENSE](LICENSE). tandem.patch modifies llama.cpp, which is MIT-licensed by the ggml authors.
