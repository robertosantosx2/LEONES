# ThumbLLM Release 1 — Ubuntu reproduction notes

**Scope:** reproduce the published CPU inference recipe, not run the Windows GUI executable under Linux. The upstream release asset is a Windows x64 `.exe`; this procedure builds a separate Linux `llama-server` from the pinned llama.cpp commit and downloads the same GGUF model.

## Upstream source of truth

- Repository: https://github.com/TeksEdge/ThumbLLM
- Release: https://github.com/TeksEdge/ThumbLLM/releases/tag/Release-1-Ornith-1.5-9B-CPU
- Release tag: `Release-1-Ornith-1.5-9B-CPU`
- Recipe: `recipes/Ornith-1.5-9B-OBLITERATED-Q4_K_M-CPU-Win-x64/README.md`
- llama.cpp commit: `c060ca974` (build b10603; upstream recipe was built for Windows with Clang 20.1.8)
- Model: `OBLITERATUS/Ornith-1.5-9B-OBLITERATED`
- GGUF: `Ornith-1.5-9B-OBLITERATED-Q4_K_M.gguf`
- Model SHA-256: `88ce99bb696fbc921edc4f995c4beb12a66bf94319d00bfd5f44265d02fa6dfb`

## Host adaptation

Target host: Ubuntu on Intel Core i7-12650H, 16 logical CPUs, 14.8 GiB RAM, RTX 3050 Laptop 4 GiB VRAM, 32 GiB swap. The reference system was Windows 11 x64, AMD Ryzen 7 7840HS (8 physical / 16 logical), 16 GB RAM. Linux binaries and performance are not byte-for-byte identical to the Windows release.

The upstream recipe uses automatic thread discovery (0/0 in the app), resolving to 8 decode threads and 16 batch threads on the reference Ryzen. The launch script adapts this intent to the local topology: physical cores for decode, logical CPUs for batch. Record the actual values with each benchmark.

## Install prerequisites

```bash
sudo apt update
sudo apt install -y git cmake build-essential curl ca-certificates
```

## Clone and build

From the LEONES checkout, run:

```bash
bash ThumbLLM-Release-1-Ornith-1.5-9B-CPU/scripts/ubuntu-ornith-cpu-setup.sh
```

The script:
1. Clones the upstream `TeksEdge/ThumbLLM` release tag into an isolated folder.
2. Checks out llama.cpp commit `c060ca974` in a separate directory.
3. Downloads the GGUF and verifies its published SHA-256 before use.
4. Builds llama.cpp with CUDA disabled and native CPU optimizations enabled.

Default isolated working directory: `~/leones-work/thumbllm-ornith-linux`. Override it with `THUMBLLM_LINUX_ROOT=/path`.

## Launch a safe first test

```bash
bash ThumbLLM-Release-1-Ornith-1.5-9B-CPU/scripts/ubuntu-ornith-cpu-serve.sh
```

Default context is 16,384 tokens and port is **18088** so this does not collide with the user's ODS/llama-server port 8080 or other existing services. API binds only to `127.0.0.1`.

After the 16K test is stable, test the recipe's full 65,536-token context:

```bash
CTX_SIZE=65536 PORT=18088 bash ThumbLLM-Release-1-Ornith-1.5-9B-CPU/scripts/ubuntu-ornith-cpu-serve.sh
```

The server command mirrors the recipe's effective CPU flags: one slot, batch 2048, microbatch 512, Q4_0 KV cache for K/V, flash attention, no GPU layers/device, no KV or operation offload, repack, mmap, prompt cache, Jinja templates. If the pinned historical build rejects a flag or cannot load this architecture on Linux, capture the exact error; do not silently substitute a newer engine and call it identical.

## Verify API

In another terminal:

```bash
curl -fsS http://127.0.0.1:18088/health
curl -fsS http://127.0.0.1:18088/v1/models
curl -fsS http://127.0.0.1:18088/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Ornith-1.5-9B-OBLITERATED","messages":[{"role":"user","content":"Say hello in one sentence."}],"temperature":0.7,"top_p":0.9,"max_tokens":64,"stream":false}'
```

Use the model ID returned by `/v1/models` if the server does not accept the alias above.

## Benchmark protocol

Keep separate results for 16K smoke tests and 65K recipe tests. Warm up once, then run at least three measured repetitions with the same prompt and `max_tokens`. Record:

- upstream tag and llama.cpp commit;
- model SHA-256;
- CPU thread counts, context, batch and microbatch;
- model load time, prompt tokens/s, generation tokens/s;
- peak RSS (`/usr/bin/time -v`), `free -h` before/after, swap and `nvidia-smi`;
- exact command, logs, date and exit code.

The upstream recipe reports ~1,302 prompt tok/s and ~13.03 generation tok/s on Ryzen 7 7840HS CPU-only. These are upstream numbers, not a prediction or result for this Intel laptop.

## Important distinctions

- The Windows release asset is a 252 MB executable; do not attempt to run it as a native Ubuntu binary.
- This reproduces the documented inference recipe with a Linux build, not ThumbLLM's Windows desktop GUI, auto-port selection, model downloader UI, or context-trimming application layer.
- Do not expose the local API to LAN; this script binds to loopback.
- Do not use `sudo` to run the model or server.
