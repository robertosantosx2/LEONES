# Devices and offload

Kinetic runs on x86-64 CPUs, on NVIDIA GPUs through CUDA and on AMD, Intel
and NVIDIA GPUs through Vulkan, on Windows and Linux. A model larger than the
GPU can still use it: a dense model splits its layers between the GPU and the
CPU, and a mixture-of-experts model keeps its experts in system memory.

## Choosing the device

`run`, `chat`, `serve` and `bench` take `--device`:

| `--device` | Does |
|---|---|
| `auto` (default) | CUDA, then Vulkan, then the CPU: the first that can run the model |
| `cuda` | the first NVIDIA GPU through CUDA, or fail with the reason |
| `vulkan` | the first GPU through Vulkan, or fail with the reason |
| `cpu` | the CPU only |

`none` is accepted for `cpu`, `cuda0` for `cuda` and `vulkan0` for `vulkan`,
as llama.cpp spells them. `-ngl 0` means `--device cpu`, and any other
`-ngl N` means `--gpu-layers N` (see [Dense models larger than the
GPU](#dense-models-larger-than-the-gpu)).

With `auto`, Kinetic skips a GPU it cannot use with one line that says why:

```text
kinetic: running on the CPU; CUDA is not usable: <reason>; Vulkan is not usable: <reason>
```

The reasons are: no NVIDIA driver, a build without the CUDA kernels, a model
whose weights and caches do not fit in the GPU's free memory, or a model
that uses something the GPU code does not have yet (see the CUDA column in
[Models and formats](models.md)). The start-up line of `kinetic serve` and
the status line of `kinetic run` name the device that is used:

```text
Serving Qwen3.5-4B-MTP-Q4_K_M on NVIDIA GeForce RTX 3060 Laptop GPU at http://127.0.0.1:8080/v1
[4 tokens at 273.9 tok/s; prompt 13 tokens at 1727.7 tok/s on NVIDIA GeForce RTX 3060 Laptop GPU]
```

Some work always runs on the CPU, whatever `--device` says: prompts that
carry images, and embedding and reranking models.

## CPU

Any x86-64 CPU runs Kinetic. The fast kernels need AVX2, FMA and F16C, which
Intel CPUs have since Haswell (2013) and AMD CPUs since Excavator and every
Ryzen; Kinetic detects them at runtime. Without them it still runs, on a
much slower path.

`-t` sets the number of threads; by default Kinetic uses every logical CPU.
Generation is limited by memory bandwidth, so more threads than physical
cores rarely help, and on some machines fewer threads are faster. Measure
with `kinetic bench model.gguf --device cpu -t N`.

## NVIDIA GPUs

GPUs from the Turing generation (RTX 20 series, GTX 16 series) on are
supported, with kernels for compute capability 7.5, 8.0, 8.6, 8.9, 9.0 and
12.0, and PTX that newer drivers compile for later GPUs.

Kinetic opens the driver library at runtime (`nvcuda.dll` on Windows,
`libcuda.so.1` on Linux) and links nothing from the CUDA toolkit, so:

- you need the NVIDIA driver, not the CUDA toolkit;
- the `cuda` build starts on machines without a GPU and runs on the CPU.

Use a recent driver; the kernels are built with CUDA 12.8, and `nvidia-smi`
shows the highest CUDA version your driver supports in its header. Only the
first GPU is used; two GPUs are [coming](roadmap.md).

## Vulkan

`--device vulkan` runs models on any GPU with a Vulkan driver: AMD, Intel and
NVIDIA. Today it runs `llama`, `qwen2`, `qwen3`, `lfm3` and `qwen35` models,
with drafting and Warm Start; MoE models and the other architectures are
[coming](roadmap.md). Under `auto`, Vulkan is tried after CUDA, so an NVIDIA
GPU uses CUDA and an AMD or Intel GPU uses Vulkan.

## Dense models larger than the GPU

When a dense model does not fit in GPU memory, Kinetic puts as many of its
last layers on the GPU as fit, with the cache, and runs the first layers on
the CPU, exactly as the CPU path runs them. Only one hidden state per token
crosses between the two. The status line says how the model was split:

```text
[... on NVIDIA GeForce RTX 3060 Laptop GPU, 24 of 33 layers, the rest on the CPU]
```

`--gpu-layers N` puts at most `N` layers on the GPU, as llama.cpp's `-ngl N`
does; use it to leave GPU memory for other programs. This works through
CUDA; on Vulkan a model runs wholly on the GPU or on the CPU.

## Memory

**Weights are memory-mapped.** Kinetic does not copy the model into its own
memory; the operating system reads the file's pages as they are used and
keeps them in its file cache. On the CPU, a model needs about its file size
in RAM to run at full speed. On the GPU, the weights are copied to video
memory at load time.

**The context sets the cache size.** Each conversation gets a cache for up
to `-c` tokens, 32768 by default (less if the model was trained on less;
`-c 0` takes everything the model supports). On the GPU that cache is
reserved at load time, so a model that does not fit with the default
context may fit with `-c 8192`. Models with recurrent layers (Qwen3.5,
LFM2, LFM3, Granite 4.0 H, Falcon-H1) need much less cache per token than
pure transformers.

**A quantized cache holds about twice the context.** On CUDA,
`--cache-type-k q8_0` and `--cache-type-v q8_0` (llama.cpp's `-ctk` and
`-ctv`) store keys and values in blocks of 32 int8 values with one f16
scale, 34 bytes where f16 takes 64. Every token stays in the cache, but its
keys and values are rounded, so answers differ from the f16 cache's: close
in quality, not identical, and never what the exactness checks compare
against. It is off by default. The CPU and Vulkan paths ignore it.

**Warm Start keeps prompt states** in up to 1 GiB of RAM and 2 GiB on disk,
under `--cache-dir` (by default `kinetic/warm` in `%LOCALAPPDATA%` on
Windows and `$XDG_CACHE_HOME` or `~/.cache` on Linux). `--no-prompt-cache`
turns it off.

`kinetic bench` reports the peak memory of a run.

## Mixture-of-experts offload

A mixture-of-experts model that does not fit in GPU memory still runs on the
GPU with `--device auto` or `cuda`. Kinetic puts the attention layers, the
shared weights and the cache on the GPU, gives the remaining free memory to
a cache of experts, and leaves the other experts in the memory-mapped file.
Each layer then runs the experts it picks where that is cheapest at the
moment: from the GPU cache, on the CPU, or copied over. See
[Flywheel](how-it-is-fast.md#flywheel) for how it decides.

For this to be fast, the whole file should fit in system RAM next to your
other programs. Kinetic reads the experts into memory at load time when they
fit with 3 GiB to spare, and otherwise lets the first tokens read them as
needed.

When every expert fits on the GPU, there is no offload: routing runs on the
GPU too.

## Coming

- **More on Vulkan**: more architectures, speculative decoding, Warm Start
  and layer splits.
- **Two GPUs.**

See the [roadmap](roadmap.md).
