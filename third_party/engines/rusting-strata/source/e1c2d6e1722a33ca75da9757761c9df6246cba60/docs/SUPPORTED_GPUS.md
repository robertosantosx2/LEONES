# Supported GPUs

Every GPU that has run RustingStrata, what was tested on it, and by whom. "Tested" means a person ran it on that card;
"compiles" means the source builds for that architecture but nobody has run it there. Numbers are from
`rustingstrata bench` on `Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf` unless the row says otherwise, and are only comparable within one
row.

## Tested

| GPU | Arch | Backend | Status | Tested by | Notes |
| --- | --- | --- | --- | --- | --- |
| NVIDIA RTX 3060 12 GB | Ampere, sm_86 | CUDA | Reference, full test suite passes | maintainer | pp 4096 prefill ~1570 tok/s, decode ~108 tok/s (MTP on, all but ~1% of expert reads hit the GPU cache). Int8 tensor-core GEMM. |
| NVIDIA RTX 3060 12 GB | Ampere, sm_86 | Vulkan | Full test suite passes | maintainer | Cooperative matrices (f16 and int8). Prefill is slower than CUDA. |
| NVIDIA Tesla V100-SXM2 32 GB | Volta, sm_70 | CUDA | Runs, parity measured | TheBrutalX | `m8n8k4` tensor cores, no int8 GEMM (f16 GEMM instead), no `cp.async`. Needs the CUDA 12.x NVRTC (CUDA 13 dropped sm_70). Bring-up: pp 512 836 tok/s, decode 116 tok/s. See [V100-results.md](V100-results.md). |
| NVIDIA Tesla V100-SXM2 32 GB | Volta, sm_70 | Vulkan | Runs, parity measured | TheBrutalX | No cooperative matrices, so the `_dp` kernels run. pp 4096 prefill ~1400 tok/s, decode ~110 tok/s. The f16 GEMM input conversion truncates on this driver; run the kernel tests with `STRATA_VK_F16_TRUNC=1` there. |
| AMD Radeon VII (Vega 20) | GCN5, wave64 | Vulkan | Runs | masanork (PR #5) | RADV Mesa 26.0.8. Each 64-lane subgroup runs as two logical 32-lane warps. See [AMD.md](AMD.md). |
| AMD Radeon RX 9070 XT | RDNA 4 | Vulkan | Runs, known issues | user reports | Linux (RADV) and Windows (AMD driver). See [AMD.md](AMD.md) for the issues and what to send. |
| NVIDIA Turing card | Turing, sm_75 | CUDA | Runs | x-Pepsy (PR #6) | `m16n8k8` tensor cores, no int8 GEMM, 64 KB shared memory (16-key prefill tile at head_dim 256). The GPU model was not recorded in the PR. |
| NVIDIA A100-SXM4 80 GB | Ampere, sm_80 | CUDA | Full test suite passes | yugt | pp 4096 prefill 6203 tok/s, decode 174 tok/s (MTP off, whole model in VRAM). See [datacenter-nvidia-results.md](datacenter-nvidia-results.md). |
| NVIDIA A100-SXM4 80 GB | Ampere, sm_80 | Vulkan | Full test suite passes | yugt | Cooperative matrices (f16 and int8). pp 4096 prefill 5589 tok/s, decode 132 tok/s. |
| NVIDIA A30 24 GB | Ampere, sm_80 | CUDA | Full test suite passes | yugt | pp 4096 prefill 3544 tok/s, decode 132 tok/s. |
| NVIDIA A30 24 GB | Ampere, sm_80 | Vulkan | Full test suite passes | yugt | Cooperative matrices (f16 and int8). pp 4096 prefill 3326 tok/s, decode 104 tok/s. |
| NVIDIA L40S 48 GB | Ada, sm_89 | CUDA | Full test suite passes | yugt | pp 4096 prefill 9030 tok/s, decode 213 tok/s. |
| NVIDIA L40S 48 GB | Ada, sm_89 | Vulkan | Full test suite passes | yugt | Cooperative matrices (f16 and int8). pp 4096 prefill 8571 tok/s, decode 185 tok/s. |
| NVIDIA H100 NVL 94 GB, H100 80 GB | Hopper, sm_90 | CUDA | Full test suite passes | yugt | pp 4096 prefill 9131 tok/s, decode 246 tok/s (H100 NVL; the 80 GB card ran the tests only). |
| NVIDIA H100 NVL 94 GB, H100 80 GB | Hopper, sm_90 | Vulkan | Full test suite passes | yugt | Cooperative matrices (f16 and int8). pp 4096 prefill 6428 tok/s, decode 192 tok/s (H100 NVL). |

## Compiles, not run

| GPU class | Arch | Backend | What is checked |
| --- | --- | --- | --- |
| Turing | sm_75 | CUDA | `cargo test` compiles the whole source with NVRTC for sm_75 (`nvrtc_compiles_full_source_for_sm75`). |
| Volta | sm_70 | CUDA | Same with an NVRTC 12.x (`nvrtc_compiles_full_source_for_sm70`); skipped on CUDA 13. |

## Not supported

| GPU | Why |
| --- | --- |
| Intel Arc | Vulkan driver has no `shaderFloat64`. |
| NVIDIA Pascal and older (CUDA) | No tensor cores. Use `--backend vulkan`; not tested. |
| GPUs without Vulkan 1.3 and subgroup size 32 or 64 | The Vulkan backend needs both. |

## Architecture tiers (CUDA)

| Arch | Matrix multiply | Int8 GEMM | Async copy | Shared memory per block |
| --- | --- | --- | --- | --- |
| sm_80 and newer | `mma.m16n8k16` | yes | `cp.async` | 100 KB or more |
| sm_75 | `mma.m16n8k8` (two steps per k16) | no | register copy | 64 KB |
| sm_70 | `mma.m8n8k4` (`GEMM_TC`), or CUDA-core FMA with `STRATA_GEMM_FMA=1` | no | register copy | 96 KB opt-in |

## Add your GPU

Open an issue or PR that adds a row. Please send:

1. The first lines of output (`cuda device ...` or `vulkan: ...`), which name the GPU, driver and capabilities.
2. `rustingstrata bench --model <gguf> --gpu --pp 512,4096 --tg 128 --reps 3` and the model file name.
3. `cargo test --release` result (or the failing test names), and `rustingstrata check --backend vulkan --model <gguf>` for
   Vulkan.
4. Anything that failed: the exact error text.

Mark rows "Tested" only for cards you ran yourself.
