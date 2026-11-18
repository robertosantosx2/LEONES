# Falcon3 I2_S AVX2 activation probe

This opt-in probe measures the activation vector and the signed-16-bit lane
accumulator used by `ggml_vec_dot_i2_i8_s_1x1()`. It is intended to answer the
remaining Falcon3 question: do real I8_S activations exceed the int16 lane
range in the AVX2 vec-dot fallback?

## Target revision

The patch is based on the public BitNet integration tree:

- BitNet: `microsoft/BitNet` commit `0b341e582afbf9e1011f24744b554c96a3477eb5`
- llama.cpp submodule: `isHuangXin/llama.cpp` commit `390c307752ab78fd8189f359d6954c9ba1be74af`
- Patch: [0001-i2s-avx2-activation-diagnostics.patch](patches/0001-i2s-avx2-activation-diagnostics.patch)

Do not assume it applies cleanly to another llama.cpp revision. The local
reproduction checkout used a different, unpublished submodule commit.

## What it records

For the first 64 calls to the exported vec-dot wrapper, one stderr line records:

- K and row count;
- activation min/max, positive/negative/zero counts and sum;
- maximum absolute value reached by a scalar shadow of each AVX2 int16 lane;
- number of lane-groups that exceed signed int16 range;
- number of intermediate accumulator updates outside `[-32768, 32767]`.

The shadow follows the AVX2 kernel's reset points: each full 32-block group
starts a new int16 accumulator, and the residual group starts another one.
It checks the accumulator after both `add_epi16` updates per 128-element block.

The patch does not alter the kernel's arithmetic or return value. It adds
diagnostic scalar work and stderr output only when the macro is enabled.

## Build integration

Apply the patch from the llama.cpp submodule root:

```bash
git apply research/bitnet/patches/0001-i2s-avx2-activation-diagnostics.patch
```

Compile the C sources with:

```text
-DGGML_I2S_AVX2_DIAGNOSTICS
```

The build must also enable AVX2 so that `__AVX2__` is defined. If the runtime
uses `GGML_USE_LLAMAFILE`, this vec-dot wrapper may be bypassed; no diagnostic
line then means either that the wrapper was not reached or that the diagnostic
macro was not present in the loaded library.

## CI validation

The patch was applied and compiled in GitHub Actions run
[#44273231378](https://github.com/robertosantosx2/LEONES/actions/runs/44273231378).
The synthetic K=3072 harness produced:

| Input pattern | Maximum absolute shadow lane | Overflow lane-groups | Overflow updates |
|---|---:|---:|---:|
| All +127 | 48,768 | 16 | 256 |
| 90% +127 / 10% -127 | 39,116 | 16 | 128 |
| Alternating 128-element sign blocks | 2,032 | 0 | 0 |
| All +64 | 24,576 | 0 | 0 |

This validates the probe against synthetic data. It does **not** establish the
distribution of real Falcon3 activations. The next use is an instrumented
Falcon3 inference on the user's validation machine after synchronizing the
GitHub artifact.