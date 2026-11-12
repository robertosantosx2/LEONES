# FAQ and troubleshooting

## Questions

**Do I need a GPU?** No. Kinetic is built to be fast on an ordinary CPU with
AVX2. An NVIDIA GPU makes it faster.

**Does it run on macOS, or on ARM?** No. Kinetic supports Windows and Linux
on x86-64.

**Is the output really the same with all the speed-ups?** Yes. Greedy
decoding gives the same tokens as plain decoding, and sampling with a seed
gives the same answer for the same seed. The test suite checks this on real
models, and `kinetic bench` checks it on your machine. The CPU and the GPU
round differently, so a CPU answer and a GPU answer to the same prompt can
differ; each is exact for its device.

**Will my llama.cpp models work?** If `kinetic info` lists the architecture
as supported and the file loads, yes, unchanged. See
[Models and formats](models.md).

**Does Kinetic collect data or need an account?** No. Kinetic never connects
to the network, except when you run `kinetic pull`. `run`, `chat` and `serve`
never download anything, and there is no telemetry and no update check.

**What does Kinetic store on my disk?** Only Warm Start's prompt states, in
`kinetic/warm` under your cache directory (`%LOCALAPPDATA%` on Windows,
`~/.cache` on Linux), up to 2 GiB. They are derived from your prompts, so
treat them like your chat history. Delete the folder to clear them, or run
with `--no-prompt-cache` to keep nothing.

**Can I use Kinetic in a commercial product?** Yes, under the Apache License
2.0. The name and logo have their own rules; see
[TRADEMARKS.md](https://github.com/Veloresearch/kinetic/blob/main/TRADEMARKS.md).

**How do I report a bug or a vulnerability?** Bugs in an
[issue](https://github.com/Veloresearch/kinetic/issues/new/choose); security
problems privately to contact@veloresearch.com, see
[SECURITY.md](https://github.com/Veloresearch/kinetic/blob/main/SECURITY.md).

## Troubleshooting

### `--device auto` uses the CPU although I have an NVIDIA GPU

Kinetic prints the reason on one line, starting with `kinetic: running on
the CPU, the GPU is not usable:`. The common ones:

- **The driver is missing or old.** Install the current driver from NVIDIA.
  `nvidia-smi` should list your GPU and, in its header, a CUDA version of
  12.8 or newer.
- **You have the `cpu` archive** or a build made without `nvcc`. Use a
  `cuda` archive, or see [Building from source](building.md).
- **The model does not fit.** Through CUDA, a dense model that does not fit
  runs its first layers on the CPU (the status line says how many are on the
  GPU); through Vulkan it needs to fit whole. If not even one layer fits
  beside the cache, try a smaller context (`-c 8192`), close other programs
  that use the GPU (games, browsers with hardware acceleration, another
  model), or use a smaller quantization.
- **The model uses something the GPU code does not have yet**, such as an
  architecture Vulkan does not run yet. These run on the CPU for now.
- **The GPU is older than Turing** (GTX 10 series and earlier). These are not
  supported.

`--device cuda` turns any of these into an error instead of a fallback.

### Out of memory

- **On the GPU:** lower `-c`; the default context of 32768 tokens reserves
  its cache at load time. Use `--device cpu` to run from system memory.
- **On the CPU:** a model needs about its file size in RAM, plus the cache.
  Close other programs or pick a smaller quantization; a Q4_K_M file is about
  a third of the size of the F16 one.
- **Mixture-of-experts models** larger than GPU memory run with their experts
  in system RAM; they are fast only when the whole file fits in RAM.

### It is slow on the CPU

- Check that your CPU has AVX2 (Intel Core since 2013, every AMD Ryzen).
  Without it Kinetic runs on a much slower path.
- Try fewer threads: `kinetic bench model.gguf --device cpu -t 6` with the
  number of physical cores often beats the default of all logical CPUs.
- On a laptop, plug in and choose the best-performance power mode.
- Other programs using the CPU slow generation down a lot.

### "architecture X is not supported yet" or another load error

See [Files that do not load](models.md#files-that-do-not-load) for what each
message means. Then open a
[model not supported issue](https://github.com/Veloresearch/kinetic/issues/new?template=model-not-supported.yml)
with the output of `kinetic info`.

### The model answers in a strange way

- Check the sampling: some GGUF files carry their own defaults, such as a
  repeat penalty. Compare with `--temp 0 --repeat-penalty 1`.
- Make sure the file has a chat template (`kinetic info` shows its size). A
  base model without one is meant for `/v1/completions`, not chat.
- Compare with llama.cpp on the same file and prompt, greedy on both sides.
  If they differ early in the answer, please file a bug.

### Windows says the file is not commonly downloaded

New releases have no download history yet, so SmartScreen may show
"Windows protected your PC" the first time you run `kinetic.exe`. Check the
archive against `SHA256SUMS` from the release page, then choose **More
info** and **Run anyway**. You can also unblock the archive before you
unpack it: right-click it, **Properties**, tick **Unblock**.

### My antivirus flags or slows down kinetic.exe

Some antivirus programs flag new, unsigned binaries, or scan model files
every time they are read, which makes loading slow. Verify the download
against `SHA256SUMS`, and if you trust it, add an exception for
`kinetic.exe` and the folder that holds your models. Builds from source
behave the same.

### The server cannot be reached from another computer or a container

The server listens on `127.0.0.1` by default. Start it with `--host 0.0.0.0`
to listen on all interfaces, and keep in mind that it has no
authentication: anyone who can reach the port can use the model. Put a
reverse proxy with authentication in front for anything beyond your own
network.

### A web page cannot call the server

That is deliberate: the server refuses requests from web pages, so a
website you visit cannot use your local model. Call it from a backend, an
app or a script instead.

### Split GGUF files

Files split into parts (`model-00001-of-00003.gguf`) are not read yet. Join
them with llama.cpp's `llama-gguf-split --merge model-00001-of-00003.gguf
model.gguf` first.
