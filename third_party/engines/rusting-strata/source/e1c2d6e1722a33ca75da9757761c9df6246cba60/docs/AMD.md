# AMD GPUs

All benchmarks in the README were run on an NVIDIA RTX 3060. AMD GPUs run the Vulkan backend
(`--backend vulkan`), and everything known about them comes from user reports (RX 9070 XT on Linux with RADV, and on
Windows with AMD's driver). Expect problems; this page lists the known ones and what to send when you hit a new one.

Needs a Vulkan 1.3 driver and subgroup size 32 or a fixed subgroup size 64. The wave64 path has been tested on
Radeon VII (Vega 20) with RADV Mesa 26.0.8. It runs the same int8 kernels as wave32: each 64-lane subgroup is split
into two logical 32-lane warps. The optimized batched-prefill path can differ from token-by-token inference at near
ties; `--chunk 0` uses token-by-token prefill when closer agreement with the CPU reference matters more than prompt
processing speed.

## First line of the output

Every run on Vulkan starts with a line like:

```
vulkan: AMD Radeon RX 9070 XT (radv Mesa 26.2.5), device-coherent memory yes, cooperative matrix f16 yes int8 no, conditional rendering yes
```

- `device-coherent memory` must be `yes` for models whose experts do not all fit in VRAM (see below).
- `cooperative matrix` speeds up prefill. `int8 no` is normal on RDNA. Without it, prefill attention uses a
  shared-memory tiled fallback; the `_dp` GEMM kernels still run without tensor cores.
- `conditional rendering` lets decode recover when the CPU expert worker is slow. With `no`, a slow worker is an error.

## Known issues

**Slow decode with experts on the CPU, and "GPU waits for the CPU expert worker that timed out and resumed: N".**
While the CPU computes the experts that are not in VRAM, the GPU polls a small mailbox buffer for the answer. On AMD the
GPU caches that buffer unless it comes from device-coherent memory (`VK_AMD_device_coherent_memory`), and then it misses
the answer and waits until it gives up. RADV hides the extension on RDNA4 (RX 9000) unless the driconf option
`radv_device_coherent_memory` is set. RustingStrata sets it before it opens Vulkan (unless you set it yourself) and prints a
warning when an AMD GPU still has no device-coherent memory. If the first line says `device-coherent memory no`, send
the output of `vulkaninfo | grep -i coherent`. A few resumed waits on a busy CPU are normal; hundreds are not.

**The GPU resets during a long prefill.** amdgpu resets a submission that runs for more than 10 s. Prefill submits
each layer separately to stay under that. If it still happens, try a smaller `--chunk`.

**"the forward pass produced NaN or infinite logits".** Seen once on Qwen3-Next 80B with a 15K prompt. Rerun with
`STRATA_NAN_TRACE=1`, which prints per-layer magnitudes and the first layer with a non-finite value, and attach the
output.

**A model split over two cards (`--device 0,1`) is slower than expected.** Each card waits while the other works, and
amdgpu clocks it down in those gaps. `echo high > /sys/class/drm/cardN/device/power_dpm_force_performance_level` (as
root, for each card; `auto` restores the default) keeps the clocks up: 44 to 57 tok/s decode in one two-card report.
The per-device times that `generate` prints on a split show whether a card is slow.

**Load fails for lack of VRAM.** The desktop on the same card takes memory, and the driver's free-memory estimate can
be more than it will allocate. Lower `--ctx`, use `--kv q8`, or a smaller `--chunk`.

## Switches for testing

Environment variables; set any of them to turn the feature off:

- `STRATA_VK_NO_COOP`: no cooperative matrices.
- `STRATA_VK_DP_OLD`: use the old per-query prefill attention fallback instead of the tiled one (A/B and rollback).
- `STRATA_VK_NO_COND`: no conditional rendering.
- `STRATA_VK_NO_TQ`: no separate transfer queue for expert uploads.
- `STRATA_VK_SMEM_LIMIT=49152`: treat the device as allowing this much workgroup shared memory. The AMD proprietary driver reports 32768 on an RX 9070 XT although the card has 64 KB; RustingStrata raises that to 49152 itself on RDNA3/4 cards with this driver (no kernel needs more). For any other card that reports too little, set it by hand. Do not set it above what the card really has (issue #20).
- `radv_device_coherent_memory=false`: undo the RADV option RustingStrata sets.

If one of these makes a problem go away, say which one in the report.

## What to send in an issue

- GPU model, OS, driver and version (Mesa version on Linux).
- The output of `vulkaninfo --summary`.
- The full output of the failing command, including the first `vulkan:` line.
- If decode is slow: `rustingstrata bench --model <file> --gpu --backend vulkan --pp 1024 --tg 128` with the same model.
