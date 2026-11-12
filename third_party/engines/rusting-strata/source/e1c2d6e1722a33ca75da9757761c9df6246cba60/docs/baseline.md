# llama.cpp baseline (M0)

Reference machine: RTX 3060 12 GB (about 1.7 GB used by the desktop), Ryzen 5 7600X, 32 GB RAM, CachyOS.
llama.cpp commit `5d8ccdf9d`, CUDA build (sm_86), flash attention on, all layers on GPU (`-ngl 99`).
Model: `Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf` (11.70 GiB).

## `--n-cpu-moe` sweep (`tools/baseline.sh`, llama-bench, 2 repetitions)

| `--n-cpu-moe` | pp4096 tok/s | tg128 tok/s |
|---|---|---|
| 6, 8, 9 | does not fit (out of VRAM) | |
| **10** | **1017.5 ± 4.5** | **65.8 ± 1.7** |
| 12 | 1005.7 ± 4.7 | 63.9 ± 1.6 |
| 14 | 974.9 ± 4.1 | 63.4 ± 0.9 |
| 16 | 940.7 ± 2.1 | 60.5 ± 1.9 |
| 20 | 883.5 ± 0.8 | 58.4 ± 0.2 |

## Long context (32K)

`-d 32768`: n=10 and n=12 do not fit. n=14: pp512 814.0 tok/s, tg128 56.4 tok/s.

## MTP speculative decoding (`tools/mtp_bench.sh`, llama-server, 256 tokens, temperature 0)

| `--n-cpu-moe` | draft-n-max | decode tok/s | accepted / drafted |
|---|---|---|---|
| 10 | 0 (no MTP) | 67.0 | - |
| 10 | 1, 2 | crash (segfault, likely VRAM) | |
| 12 | 1, 2, 3 | crash | |
| 14 | 1 | 61.6 | 116 / 138 |
| 14 | 2 | 61.1 | 149 / 210 |
| 14 | 3 | crash | |

MTP does not help llama.cpp on this machine: the extra MTP layer forces more experts to the CPU,
and the loss outweighs the gain from accepted drafts.

## Gate for RustingStrata v1

- Decode: faster than **67 tok/s** (llama.cpp best; its MTP is slower than plain decode here).
- Prefill: at least **1017 tok/s** at 4K.
- Top-1 agreement with llama.cpp: at least 99%.

## V100 parity reference (M0-T7, 2026-11-07)

The gate above ("at least 99% top-1 agreement") was measured on the RTX 3060 against a **CPU**
llama.cpp build (`5d8ccdf9d`). The V100 baseline uses the CUDA build available on that host:

- `llama-server` `/srv/llama.cpp/build/bin/llama-server`, `version: 0.9.0-dev (build 12110,
  commit cd959bae9)` (`/props build_info: b12110-cd959bae9`), model fully on CUDA0.
- Flags: `-ngl 99 -fa auto -c 4096 --seed 1234`; `-fa auto` resolved to **disabled**
  (`Flash Attention over K/V rows not supported` in this build), `n_ctx_slot 4096`,
  `n_slots 4`, `kv_unified true`.
- llama.cpp self-agreement (token-by-token vs one-batch context): **630/640 = 98.44%**
  (`tools/selfparity.py`, same server/build, 0 refused positions).
- Strata on Vulkan (commit `d6c2beb`, `--gpu --backend vulkan --llama-numerics
  --fixed-experts`): strict 625/640 = 97.66%, either llama.cpp mode 629/640 = 98.28%
  (below the 634/640 bar - documented deviation in `docs/V100-results.md`, M0-T7).
  Default path: strict 626/640, either 630/640.

Reference numbers and the full per-prompt table: `docs/V100-results.md`, section
"2026-11-07 - M0-T7 Vulkan parity baseline"; machine-readable artifact
`docs/parity/vk-sm70.json`.
