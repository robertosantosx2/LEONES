# A100, A30, L40S and H100 results

Four data-center NVIDIA cards on one Slurm cluster, one GPU per job (8 CPU cores, 48 GB RAM). Rocky Linux 8.10,
driver 615.71.09 (Vulkan 1.4.351), NVRTC 13.0 from the CUDA 13.0.1 toolkit, Rust 1.99.1, `target-cpu=native`.
Commit `7264e57` (v1.2.1). Model: `Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf` (sha256 `ed7cda7e...f37fb0c`); it fits in VRAM on
every card here, so all 10240 experts are resident and the expert hit rate is 100%.

| GPU | VRAM | Arch | Host CPU |
| --- | --- | --- | --- |
| A100-SXM4-80GB | 81920 MiB | sm_80 | EPYC 7413 |
| A30 | 24576 MiB | sm_80 | EPYC 7413 |
| L40S | 46068 MiB | sm_89 | Xeon Platinum 8458P |
| H100 NVL | 95830 MiB | sm_90 | EPYC 9224 |
| H100 80GB HBM3 (tests only) | 81559 MiB | sm_90 | Xeon Platinum 8470 |

## 2026-11-10 — benchmarks

`rustingstrata bench --model $M --gpu --backend {cuda,vulkan} --pp 512,4096 --tg 128 --reps 3`, no `calibrate` run, MTP
off. Mean (min-max) of 3 repetitions, tok/s.

| GPU | Backend | pp 512 prefill | decode after 512 | pp 4096 prefill | decode after 4096 |
| --- | --- | --- | --- | --- | --- |
| A100 80 GB | CUDA | 3852.3 (3767.5-3916.5) | 178.8 (178.0-179.2) | 6202.5 (6186.2-6213.7) | 173.6 (173.2-173.8) |
| A100 80 GB | Vulkan | 2353.8 (119.2-3473.5) | 120.1 (71.4-144.6) | 5588.8 (4788.0-5990.0) | 131.9 (116.5-139.7) |
| A30 | CUDA | 2261.4 (1924.2-2435.3) | 137.8 (137.3-138.0) | 3543.9 (3539.3-3548.2) | 131.9 (131.6-132.1) |
| A30 | Vulkan | 1516.8 (127.9-2239.9) | 99.7 (70.6-114.3) | 3326.0 (3061.1-3459.0) | 104.0 (94.4-108.8) |
| L40S | CUDA | 6416.6 (6198.4-6566.3) | 220.2 (219.3-220.8) | 9030.3 (9023.1-9039.5) | 213.2 (212.8-213.5) |
| L40S | Vulkan | 3887.7 (143.1-5766.5) | 166.0 (89.9-204.1) | 8570.6 (7243.4-9279.4) | 184.9 (162.3-196.3) |
| H100 NVL | CUDA | 5718.3 (5505.3-5868.2) | 253.1 (251.6-253.8) | 9130.8 (9115.2-9153.7) | 245.8 (245.1-246.1) |
| H100 NVL | Vulkan | 2967.8 (118.2-4396.9) | 174.0 (95.5-213.3) | 6428.2 (5569.7-6857.7) | 191.5 (164.5-205.1) |

The first Vulkan repetition of `pp 512` includes pipeline compilation (the 118-143 tok/s minima), as on the V100.
The numbers are comparable within a row only: the four cards sit in hosts with different CPUs.

Startup lines:

```
cuda device 0: NVIDIA A100-SXM4-80GB, sm_80
cuda shared memory: opt-in 166912 B per block, gemvn_*: 0 B static, dynamic max 166912 B, carveout default
cuda device 0: NVIDIA A30, sm_80
cuda shared memory: opt-in 166912 B per block, gemvn_*: 0 B static, dynamic max 166912 B, carveout default
cuda device 0: NVIDIA L40S, sm_89
cuda shared memory: opt-in 101376 B per block, gemvn_*: 0 B static, dynamic max 101376 B, carveout default
cuda device 0: NVIDIA H100 NVL, sm_90
cuda shared memory: opt-in 232448 B per block, gemvn_*: 0 B static, dynamic max 232448 B, carveout default

vulkan: NVIDIA A100-SXM4-80GB (NVIDIA 615.71.09), cooperative matrix f16 yes int8 yes, conditional rendering yes, maxComputeSharedMemorySize 49152
vulkan: NVIDIA A30 (NVIDIA 615.71.09), cooperative matrix f16 yes int8 yes, conditional rendering yes, maxComputeSharedMemorySize 49152
vulkan: NVIDIA L40S (NVIDIA 615.71.09), cooperative matrix f16 yes int8 yes, conditional rendering yes, maxComputeSharedMemorySize 49152
vulkan: NVIDIA H100 NVL (NVIDIA 615.71.09), cooperative matrix f16 yes int8 yes, conditional rendering yes, maxComputeSharedMemorySize 49152
plan: weights+state+scratch 1984 MB (KV 82 MB for 4224 tokens, prefill 512 MB), expert slots 10002 MB, resident experts 10240/10240
```

`rustingstrata check --backend vulkan --model $M` on each card: 96 (kernel, specialization) pairs checked, largest 49152
bytes (`gemmi`) of 49152 allowed.

## 2026-11-10 — test suite

`STRATA_MODEL=$M cargo test --release --no-fail-fast -- --nocapture` on A100, A30, L40S and H100 80GB HBM3: 185 passed,
0 failed, 5 ignored on each. H100 NVL ran the same suite without `--nocapture` at `7264e57`: 185 passed, 0 failed,
5 ignored. A30 also passed with `--test-threads=1`.

- Both backends were open in every run: each log has 48 `cuda device 0:` lines and 47 `vulkan:` device lines. The only
  skips are `no glslc` (`spirv_is_fresh`) and `STRATA_TEST_BACKENDS does not select cuda`.
- The runs with `--nocapture` include the `tests/common` change that recognises the default model by file name, so the
  default-model checks (the 0.05 logit tolerance of `gpu_forward_matches_cpu_reference`, the type-coverage counts in
  `tests/kernels.rs`, the shapes in `tests/quant.rs` and `tests/gguf.rs`) ran and passed. Before it they were skipped
  on any machine where the file is not at the path in `DEFAULT_MODEL`.

## 2026-11-10 — parallel tests can hang in `vkDestroyDevice` on this driver

One full `cargo test --release` on the A30 stopped in `tests/kernels.rs`: no output for five minutes, GPU utilisation
0%, one thread at 100% CPU. `gdb` on the test process:

```
Thread 6:  pthread_join <- libnvidia-eglcore.so.615.71.09 <- vkDestroyDevice <- <vulkan::Inner as Drop>::drop (src/vulkan/mod.rs:279)
Thread 15: libnvidia-eglcore.so.615.71.09 <- __nptl_deallocate_tsd <- start_thread        (the thread at 100% CPU)
Thread 41: pthread_mutex_lock <- vkCreateInstance <- Vk::new (src/vulkan/mod.rs:333) <- f16_weight_uploads_as_f32
Thread 40: pthread_mutex_lock <- vkCreateInstance <- Vk::new <- elementwise_ops_match_cpu
4 threads: __pthread_mutex_lock_full <- Inner::submit / Inner::buffer (other tests' devices)
```

A test thread destroying its device waits for a driver thread that spins in its thread-local destructor and never
exits; the tests that start next wait on a loader mutex in `vkCreateInstance`.

How often, with the `kernels` test binary run 15 times per card and killed after 240 s (600 s for the serial runs):

| Run | A30 | A100 |
| --- | --- | --- |
| parallel (default test threads) | 2 of 15 hung, the others took 34-40 s | 3 of 15 hung, the others took 31-41 s |
| `--test-threads=1` | 0 of 15 hung (51-85 s) | 0 of 15 hung (53-94 s) |

A hung run stopped after a different number of tests each time (0 to 12 finished). L40S and H100 were not looped. The
results are not affected: every run that finished passed. Until this is solved, `cargo test --release --
--test-threads=1` is the way to run the suite on this driver: it did not hang in these 30 runs.
