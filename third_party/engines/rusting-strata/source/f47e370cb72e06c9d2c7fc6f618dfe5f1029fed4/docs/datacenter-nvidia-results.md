# A100, A30, L40S and H100 results

Four data-center NVIDIA cards on one Slurm cluster, one GPU per job. Rocky Linux 8.10, driver 615.71.09 (Vulkan
1.4.351), NVRTC 13.0 from the CUDA 13.0.1 toolkit, Rust 1.99.1, `target-cpu=native`. A job runs on whichever node with
the requested GPU type is free, so the host CPU can differ between jobs, and the `h100` type is either an H100 NVL or an
H100 80GB HBM3. Each section lists the hosts it ran on. Numbers are comparable within one job only.

- [Calibrated runs: Q2_K_XL, Q8_0 and BF16](#2026-11-10--calibrated-runs-q2_k_xl-q8_0-and-bf16)
- [DeepSeek-V4.1-Flash-1017 IQ2_XXS](#2026-11-10--deepseek-v41-flash-1017-iq2_xxs)
- [First round: benchmarks without calibration](#2026-11-10--first-round-benchmarks-without-calibration)
- [Test suite](#2026-11-10--test-suite)
- [Vulkan hang in parallel tests](#2026-11-10--parallel-tests-can-hang-in-vkdestroydevice-on-this-driver)

## 2026-11-10 — calibrated runs: Q2_K_XL, Q8_0 and BF16

Commit `e1c2d6e`. Each job builds, then runs on one card:

```sh
rustingstrata bench --model $M --gpu --backend cuda --pp 512,4096 --tg 128 --reps 3      # uncalibrated
rustingstrata calibrate --model $M --backend cuda
rustingstrata bench --model $M --gpu --backend cuda --pp 512,4096 --tg 128 --reps 3      # calibrated
rustingstrata bench --model $M --gpu --backend cuda --pp 512,4096 --tg 128 --reps 3 --mtp 0
rustingstrata check --model $M --backend vulkan
# then the same four steps with --backend vulkan
```

`XDG_CACHE_HOME` is a new directory per job, so the first bench has no calibration file, and the calibrated runs read
the file `calibrate` wrote. Mean (min-max) of 3 repetitions, tok/s.

| File | Size | sha256 | Job size |
| --- | --- | --- | --- |
| `Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf` | 12.6 GB | `ed7cda7e...f37fb0c` | 8 cores, 48 GB RAM |
| `Qwen3.6-35B-A3B-Q8_0.gguf` (`unsloth/Qwen3.6-35B-A3B-MTP-GGUF`) | 37.8 GB | `c1283d8b...9a76131` | 16 cores, 96 GB RAM |
| `Qwen3.6-35B-A3B-BF16-0000{1,2}-of-00002.gguf` (same repo, `BF16/`) | 71.1 GB | `a172dfea...9ce44a2`, `b90b4d07...c105161` | 16 cores, 160 GB RAM |

| Job | Card | Host CPU |
| --- | --- | --- |
| Q2_K_XL | A100-SXM4-80GB, A30, L40S, H100 80GB HBM3 | EPYC 7413, EPYC 7713, Xeon Gold 6542Y, Xeon Platinum 8470 |
| Q8_0 | A100-SXM4-80GB, A30, L40S, H100 80GB HBM3 | EPYC 7413, EPYC 7413, Xeon Gold 6542Y, Xeon Platinum 8470 |
| BF16 | A100-SXM4-80GB, A30, L40S, H100 NVL | EPYC 7413, EPYC 7713, Xeon Gold 6542Y, EPYC 9224 |

What `calibrate` chose (chunk / MTP drafts / short threshold):

| File | Backend | A100 | A30 | L40S | H100 |
| --- | --- | --- | --- | --- | --- |
| Q2_K_XL | CUDA | 4096 / 1 / 8 | 4096 / 1 / 8 | 4096 / 2 / 8 | 4096 / 2 / 8 |
| Q2_K_XL | Vulkan | 4096 / 2 / 8 | 2048 / 2 / 8 | 4096 / 2 / 8 | 4096 / 2 / 8 |
| Q8_0 | CUDA | 4096 / 1 / 8 | 4096 / 2 / 16 | 4096 / 2 / 8 | 4096 / 2 / 8 |
| Q8_0 | Vulkan | 4096 / 2 / 8 | 4096 / 1 / 16 | 4096 / 2 / 8 | 4096 / 2 / 8 |
| BF16 | CUDA | 4096 / 1 / 8 | 4096 / 0 / 8 | 4096 / 0 / 8 | 4096 / 1 / 8 |
| BF16 | Vulkan | 4096 / 1 / 8 | 4096 / 0 / 8 | 4096 / 0 / 8 | 4096 / 1 / 8 |

What the numbers show:

- **MTP is what calibration adds to decode.** Calibrated with MTP on, decode after 512 is 1.47-1.93x the same run
  with `--mtp 0` for Q2_K_XL, 1.40-1.88x for Q8_0 and 1.18-1.41x for BF16. Calibrated with `--mtp 0` decodes at the
  uncalibrated CUDA speed (within 0.4% wherever all experts are resident and the first repetition was not slower).
  The resident-experts column reads 10496 instead of 10240 when MTP is on: the MTP layer's experts are loaded too.
- **MTP costs prefill.** pp 4096 prefill with MTP on is 4-13% lower than with `--mtp 0` (H100 HBM3 Q2_K_XL CUDA 8304
  against 9530 tok/s), and 23% lower for Q2_K_XL Vulkan on the A30.
- **Calibrated Vulkan decode with MTP varies more.** After 4096 tokens, every MTP-on Vulkan row has a minimum
  17-41% below its maximum (A100 Q2_K_XL 180.3-260.7, H100 HBM3 Q2_K_XL 258.4-415.8), against 0.5-4% for the CUDA
  rows with MTP.
- **Uncalibrated rows include one-time startup work.** In the uncalibrated Vulkan rows, one `pp 512` repetition
  (presumably the first; the JSON keeps only mean, min and max) is far slower: minima of 85-205 tok/s where all
  experts are resident. As in the first round, this is pipeline compilation, and it pulls the means down. The runs
  after `calibrate` do not show it, probably because the driver's shader cache in `$XDG_CACHE_HOME/nvidia/GLCache`
  holds the pipelines by then. Uncalibrated CUDA `pp 512` has a slow repetition on some cards too (minima 707 on the
  L40S and 871 on the H100 HBM3 for Q2_K_XL, 447 on the L40S for Q8_0, 747 on the A100 for BF16), likely the first
  use of kernels the per-job cache does not yet hold. So most of the `pp 512` prefill gain is not calibration: L40S
  Q2_K_XL CUDA is 4607 tok/s uncalibrated and 6518 calibrated with `--mtp 0`, chunk 4096 in both. Compare with the
  `--mtp 0` row or with the uncalibrated maximum, not with the uncalibrated mean.
- **Q8_0 decodes faster than Q2_K_XL** (separate jobs: the A100 and H100 ran on different nodes with the same CPU
  model, the L40S on the same node) with CUDA on the A100 (200 against 179 tok/s with MTP off, 305 against 295
  calibrated) and on the H100 HBM3 (298 against 272, and 532 against 524), and slower on the L40S (169 against 221).
- **BF16 fits on the A100 and H100 NVL** (all 10240 experts resident). There it decodes at 176 / 237 tok/s with CUDA
  (calibrated, `--mtp 0`) and 248 / 330 with MTP 1. Vulkan BF16 decode is 56-60% of CUDA (A100 98 against 176, H100
  NVL 142 against 237, both with `--mtp 0`).
- **Where experts do not fit, the first run is a cold start.** Q8_0 on the A30 (6479 of 10240 experts resident, 98.6%
  hit rate), BF16 on the L40S (6657, 98.8%) and BF16 on the A30 (3133, 83.2%) read the missing experts from the GGUF
  through the page cache. The uncalibrated bench is the first command in the job to touch the file, so some of its
  repetitions read from the cluster file system (pp 512 minima of 17.6, 3.6 and 2.3 tok/s). It also starts without
  a routing profile, so the resident experts are chosen in layer order; later runs load the profile it saved (BF16
  L40S CUDA misses 2995 uncalibrated, 2253 calibrated). On these cards the step from uncalibrated to `--mtp 0`
  (decode after 512: Q8_0 A30 CUDA 126 to 137 tok/s, BF16 L40S 60 to 85) is the warm page cache and the profile, not
  calibration. Past that, Q8_0 on the A30 gains from MTP like the other cards (209 tok/s), and `calibrate` chose MTP 0
  for BF16 on both cards.

### Qwen3.6-35B-A3B UD-Q2_K_XL

| GPU | Backend | Run | MTP | Resident experts | pp 512 prefill | decode after 512 | pp 4096 prefill | decode after 4096 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A100 80 GB | CUDA | uncalibrated | 0 | 10240/10240 | 3454.5 (2395.5-3986.3) | 178.4 (176.1-179.5) | 6414.6 (6412.3-6418.3) | 173.8 (173.4-174.1) |
| A100 80 GB | CUDA | calibrated | 1 | 10496/10496 | 3723.6 (3493.3-3874.6) | 295.0 (293.8-295.6) | 5914.2 (5891.6-5934.9) | 280.2 (278.9-280.8) |
| A100 80 GB | CUDA | calibrated, `--mtp 0` | 0 | 10240/10240 | 3872.0 (3675.0-3991.3) | 179.0 (178.2-179.5) | 6292.7 (6280.3-6305.3) | 173.9 (173.5-174.0) |
| A100 80 GB | Vulkan | uncalibrated | 0 | 10240/10240 | 2370.4 (97.0-3514.3) | 113.5 (48.9-145.9) | 5619.7 (4677.6-6092.3) | 132.9 (116.7-141.0) |
| A100 80 GB | Vulkan | calibrated | 2 | 10496/10496 | 3180.8 (2978.1-3379.1) | 265.8 (257.8-270.0) | 5703.7 (5676.1-5733.5) | 233.7 (180.3-260.7) |
| A100 80 GB | Vulkan | calibrated, `--mtp 0` | 0 | 10240/10240 | 3340.6 (3008.0-3507.6) | 145.4 (144.1-146.1) | 6037.2 (5994.5-6063.1) | 117.5 (68.8-141.9) |
| A30 | CUDA | uncalibrated | 0 | 10240/10240 | 2108.2 (1472.4-2427.6) | 137.5 (136.8-137.9) | 3508.1 (3505.4-3512.1) | 131.9 (131.7-131.9) |
| A30 | CUDA | calibrated | 1 | 10496/10496 | 2260.3 (2114.8-2345.4) | 202.6 (202.3-202.8) | 3302.4 (3302.0-3302.7) | 193.4 (192.9-193.9) |
| A30 | CUDA | calibrated, `--mtp 0` | 0 | 10240/10240 | 2356.4 (2264.1-2412.8) | 137.6 (137.2-137.9) | 3455.4 (3447.9-3460.9) | 131.8 (131.5-132.0) |
| A30 | Vulkan | uncalibrated | 0 | 10240/10240 | 1508.0 (84.8-2221.8) | 91.6 (47.9-113.4) | 3020.2 (2291.3-3388.6) | 102.5 (91.8-108.0) |
| A30 | Vulkan | calibrated | 2 | 10496/10496 | 2016.6 (1847.6-2132.8) | 187.8 (184.0-189.9) | 2410.8 (1798.5-2990.9) | 162.3 (122.1-182.4) |
| A30 | Vulkan | calibrated, `--mtp 0` | 0 | 10240/10240 | 2018.2 (1700.2-2204.0) | 113.6 (112.9-114.0) | 3143.6 (3125.2-3154.2) | 108.1 (108.1-108.3) |
| L40S | CUDA | uncalibrated | 0 | 10240/10240 | 4606.6 (706.9-6566.5) | 220.6 (219.5-221.2) | 9274.9 (9265.2-9293.4) | 213.5 (213.0-213.7) |
| L40S | CUDA | calibrated | 2 | 10496/10496 | 6267.4 (6218.3-6363.6) | 423.6 (421.1-425.0) | 8507.7 (8485.3-8528.3) | 406.8 (402.7-408.9) |
| L40S | CUDA | calibrated, `--mtp 0` | 0 | 10240/10240 | 6518.2 (6476.8-6593.1) | 220.6 (219.5-221.1) | 9100.2 (9085.4-9113.4) | 213.6 (213.1-213.8) |
| L40S | Vulkan | uncalibrated | 0 | 10240/10240 | 3922.3 (105.7-5832.5) | 161.4 (74.0-205.1) | 8477.2 (6687.2-9392.4) | 184.1 (157.9-197.3) |
| L40S | Vulkan | calibrated | 2 | 10496/10496 | 5364.3 (5071.1-5539.8) | 371.7 (361.9-376.9) | 8672.5 (8590.1-8721.4) | 316.5 (220.5-364.6) |
| L40S | Vulkan | calibrated, `--mtp 0` | 0 | 10240/10240 | 5590.6 (5350.6-5791.7) | 205.1 (204.1-205.6) | 9339.6 (9242.9-9419.6) | 197.2 (196.9-197.5) |
| H100 HBM3 | CUDA | uncalibrated | 0 | 10240/10240 | 4479.3 (870.9-6283.8) | 271.6 (268.9-273.2) | 10054.8 (10038.3-10077.9) | 264.9 (263.5-265.8) |
| H100 HBM3 | CUDA | calibrated | 2 | 10496/10496 | 5788.2 (5640.2-6012.9) | 523.9 (516.6-527.6) | 8303.5 (8211.2-8433.2) | 498.3 (485.6-505.9) |
| H100 HBM3 | CUDA | calibrated, `--mtp 0` | 0 | 10240/10240 | 6215.7 (6099.6-6348.2) | 271.7 (269.0-273.2) | 9530.4 (9496.6-9580.2) | 264.5 (263.1-265.3) |
| H100 HBM3 | Vulkan | uncalibrated | 0 | 10240/10240 | 3170.6 (102.4-4730.1) | 167.1 (54.6-223.5) | 6769.7 (5606.3-7351.4) | 197.7 (162.0-215.8) |
| H100 HBM3 | Vulkan | calibrated | 2 | 10496/10496 | 4336.5 (4036.4-4497.7) | 427.6 (413.3-436.5) | 6987.9 (6941.7-7077.1) | 362.7 (258.4-415.8) |
| H100 HBM3 | Vulkan | calibrated, `--mtp 0` | 0 | 10240/10240 | 4600.1 (4362.6-4807.3) | 222.9 (220.6-224.3) | 7575.3 (7483.2-7664.7) | 215.6 (215.1-216.0) |

### Qwen3.6-35B-A3B Q8_0

| GPU | Backend | Run | MTP | Resident experts | pp 512 prefill | decode after 512 | pp 4096 prefill | decode after 4096 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A100 80 GB | CUDA | uncalibrated | 0 | 10240/10240 | 3580.0 (3457.5-3643.2) | 200.2 (199.1-200.7) | 6525.4 (6521.8-6527.3) | 193.5 (193.0-193.7) |
| A100 80 GB | CUDA | calibrated | 1 | 10496/10496 | 3503.0 (3472.4-3546.0) | 304.6 (303.1-305.5) | 6137.6 (6124.7-6147.1) | 288.2 (286.8-289.1) |
| A100 80 GB | CUDA | calibrated, `--mtp 0` | 0 | 10240/10240 | 3606.8 (3583.0-3637.3) | 200.0 (198.9-200.5) | 6506.9 (6486.3-6522.0) | 193.3 (192.8-193.6) |
| A100 80 GB | Vulkan | uncalibrated | 0 | 10240/10240 | 2088.7 (156.6-3057.0) | 117.4 (66.5-142.8) | 5368.0 (4514.3-5797.4) | 128.8 (109.9-138.2) |
| A100 80 GB | Vulkan | calibrated | 2 | 10496/10496 | 2927.0 (2873.4-2982.7) | 256.3 (253.2-258.0) | 5442.5 (5398.5-5475.9) | 225.0 (176.6-249.6) |
| A100 80 GB | Vulkan | calibrated, `--mtp 0` | 0 | 10240/10240 | 3018.2 (2968.2-3053.1) | 142.6 (142.0-143.0) | 5776.7 (5722.1-5819.3) | 138.1 (137.7-138.3) |
| A30 | CUDA | uncalibrated | 0 | 6479/10240 | 792.2 (17.6-1265.3) | 126.1 (118.1-133.3) | 2633.2 (1594.6-3251.6) | 127.6 (126.6-128.8) |
| A30 | CUDA | calibrated | 2 | 6419/10496 | 619.1 (507.6-693.7) | 208.8 (206.5-213.5) | 2735.6 (2374.5-2932.0) | 200.2 (198.8-201.8) |
| A30 | CUDA | calibrated, `--mtp 0` | 0 | 6479/10240 | 778.7 (541.0-908.2) | 136.9 (135.2-138.8) | 2869.9 (2621.5-2998.2) | 130.3 (128.7-131.7) |
| A30 | Vulkan | uncalibrated | 0 | 6538/10240 | 530.4 (95.3-782.0) | 95.9 (77.6-105.5) | 1913.9 (1799.7-2120.2) | 85.6 (59.2-99.9) |
| A30 | Vulkan | calibrated | 1 | 6502/10496 | 608.2 (429.0-732.4) | 149.1 (146.0-152.3) | 2045.7 (1885.6-2139.4) | 135.7 (117.8-145.3) |
| A30 | Vulkan | calibrated, `--mtp 0` | 0 | 6538/10240 | 699.3 (503.1-832.9) | 106.2 (104.8-107.4) | 2209.9 (2035.3-2309.7) | 101.3 (99.9-102.4) |
| L40S | CUDA | uncalibrated | 0 | 10240/10240 | 3224.7 (446.8-4616.1) | 169.1 (168.4-169.5) | 9542.2 (9527.6-9550.4) | 165.0 (164.7-165.2) |
| L40S | CUDA | calibrated | 2 | 10496/10496 | 4476.2 (4423.9-4546.2) | 276.4 (275.4-277.0) | 8945.4 (8936.0-8960.4) | 269.6 (267.7-270.5) |
| L40S | CUDA | calibrated, `--mtp 0` | 0 | 10240/10240 | 4615.4 (4599.4-4641.0) | 169.2 (168.4-169.6) | 9542.4 (9517.5-9560.7) | 165.1 (164.9-165.3) |
| L40S | Vulkan | uncalibrated | 0 | 10240/10240 | 3095.7 (169.0-4577.6) | 130.3 (93.2-149.0) | 8583.3 (6267.8-9751.3) | 126.0 (88.0-145.0) |
| L40S | Vulkan | calibrated | 2 | 10496/10496 | 3999.8 (3046.7-4490.5) | 242.1 (238.2-244.2) | 9063.1 (8859.3-9169.7) | 221.7 (189.1-238.7) |
| L40S | Vulkan | calibrated, `--mtp 0` | 0 | 10240/10240 | 4384.5 (4045.8-4575.1) | 149.0 (148.3-149.4) | 9725.7 (9591.6-9823.9) | 141.5 (133.8-145.4) |
| H100 HBM3 | CUDA | uncalibrated | 0 | 10240/10240 | 5807.0 (4977.4-6226.6) | 298.4 (296.2-299.8) | 11552.6 (11527.6-11572.3) | 290.4 (289.3-291.0) |
| H100 HBM3 | CUDA | calibrated | 2 | 10496/10496 | 5850.7 (5711.2-5998.4) | 531.9 (529.3-534.0) | 10437.0 (10057.1-10690.6) | 508.5 (501.1-512.3) |
| H100 HBM3 | CUDA | calibrated, `--mtp 0` | 0 | 10240/10240 | 6189.1 (6098.4-6295.0) | 298.4 (296.2-300.1) | 11486.4 (11460.1-11510.9) | 290.0 (288.7-290.7) |
| H100 HBM3 | Vulkan | uncalibrated | 0 | 10240/10240 | 3060.1 (197.2-4511.5) | 177.9 (65.7-234.2) | 6040.1 (2692.4-7718.7) | 199.8 (147.8-226.2) |
| H100 HBM3 | Vulkan | calibrated | 2 | 10496/10496 | 3512.2 (1977.8-4302.5) | 437.2 (427.8-442.6) | 6061.8 (4270.7-6957.8) | 362.3 (246.9-421.1) |
| H100 HBM3 | Vulkan | calibrated, `--mtp 0` | 0 | 10240/10240 | 3780.1 (2775.0-4409.8) | 232.7 (226.7-236.0) | 6883.1 (5126.9-7793.6) | 227.3 (227.1-227.6) |

### Qwen3.6-35B-A3B BF16

| GPU | Backend | Run | MTP | Resident experts | pp 512 prefill | decode after 512 | pp 4096 prefill | decode after 4096 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A100 80 GB | CUDA | uncalibrated | 0 | 10240/10240 | 2690.1 (746.6-3662.6) | 165.6 (143.4-176.7) | 5616.6 (5611.2-5620.6) | 171.4 (170.9-171.6) |
| A100 80 GB | CUDA | calibrated | 1 | 10496/10496 | 3454.3 (3422.4-3501.1) | 248.4 (247.5-248.9) | 5137.6 (5125.0-5152.1) | 238.1 (237.2-238.6) |
| A100 80 GB | CUDA | calibrated, `--mtp 0` | 0 | 10240/10240 | 3663.6 (3649.5-3688.2) | 176.3 (175.5-176.7) | 5625.2 (5609.7-5637.8) | 171.4 (171.0-171.6) |
| A100 80 GB | Vulkan | uncalibrated | 0 | 10240/10240 | 2423.0 (204.7-3536.0) | 84.9 (58.2-98.2) | 5731.7 (4940.9-6134.2) | 89.8 (77.5-96.1) |
| A100 80 GB | Vulkan | calibrated | 1 | 10496/10496 | 3238.7 (3162.4-3279.8) | 115.2 (114.6-115.6) | 5516.7 (5503.4-5530.0) | 104.1 (84.9-113.7) |
| A100 80 GB | Vulkan | calibrated, `--mtp 0` | 0 | 10240/10240 | 3451.9 (3308.3-3527.5) | 98.0 (97.5-98.4) | 6123.3 (6118.5-6126.9) | 96.2 (95.8-96.4) |
| A30 | CUDA | uncalibrated | 0 | 3133/10240 | 153.3 (2.3-237.4) | 13.3 (11.9-14.0) | 735.4 (381.1-1199.2) | 11.4 (9.1-12.6) |
| A30 | CUDA | calibrated | 0 | 3133/10240 | 173.0 (50.3-237.6) | 14.4 (12.6-15.3) | 1100.5 (904.9-1208.3) | 12.4 (12.1-12.7) |
| A30 | CUDA | calibrated, `--mtp 0` | 0 | 3133/10240 | 203.9 (140.6-237.9) | 14.9 (14.2-15.3) | 1163.3 (1091.1-1207.2) | 12.5 (12.1-12.7) |
| A30 | Vulkan | uncalibrated | 0 | 3165/10240 | 129.7 (69.6-160.7) | 14.1 (12.8-15.1) | 828.6 (750.8-887.8) | 12.6 (12.0-13.0) |
| A30 | Vulkan | calibrated | 0 | 3165/10240 | 139.4 (97.7-161.9) | 14.9 (14.5-15.3) | 770.7 (727.8-842.7) | 12.6 (12.2-12.8) |
| A30 | Vulkan | calibrated, `--mtp 0` | 0 | 3165/10240 | 142.1 (104.5-160.9) | 15.0 (14.5-15.2) | 849.2 (767.6-896.7) | 12.6 (12.4-13.0) |
| L40S | CUDA | uncalibrated | 0 | 6657/10240 | 69.1 (3.6-179.4) | 59.9 (24.5-79.0) | 767.0 (158.2-1891.5) | 66.6 (37.8-81.4) |
| L40S | CUDA | calibrated | 0 | 6657/10240 | 501.6 (346.5-630.9) | 83.8 (77.8-87.7) | 2051.1 (1585.7-2488.7) | 74.3 (60.8-81.4) |
| L40S | CUDA | calibrated, `--mtp 0` | 0 | 6657/10240 | 509.3 (356.1-634.5) | 84.8 (80.8-87.8) | 2135.6 (1824.6-2495.6) | 79.4 (76.2-81.5) |
| L40S | Vulkan | uncalibrated | 0 | 6721/10240 | 410.8 (158.0-584.3) | 66.8 (38.6-81.0) | 1955.3 (1590.2-2328.2) | 71.0 (59.3-77.1) |
| L40S | Vulkan | calibrated | 0 | 6721/10240 | 453.0 (321.5-558.5) | 78.0 (71.0-82.0) | 2026.5 (1790.2-2233.9) | 73.0 (71.5-75.8) |
| L40S | Vulkan | calibrated, `--mtp 0` | 0 | 6721/10240 | 460.3 (326.9-563.8) | 81.0 (79.5-82.4) | 1983.1 (1740.8-2262.6) | 76.0 (73.6-77.4) |
| H100 NVL | CUDA | uncalibrated | 0 | 10240/10240 | 5206.2 (4093.9-5762.8) | 236.9 (235.9-237.4) | 8684.7 (8661.0-8699.4) | 230.3 (229.8-230.6) |
| H100 NVL | CUDA | calibrated | 1 | 10496/10496 | 5323.9 (5212.6-5439.0) | 329.7 (328.6-330.3) | 7780.5 (7746.9-7802.6) | 324.4 (322.9-325.2) |
| H100 NVL | CUDA | calibrated, `--mtp 0` | 0 | 10240/10240 | 5716.2 (5687.8-5772.3) | 236.9 (235.7-237.5) | 8691.4 (8666.0-8709.8) | 230.4 (229.8-230.7) |
| H100 NVL | Vulkan | uncalibrated | 0 | 10240/10240 | 3002.5 (164.4-4438.0) | 114.1 (61.5-140.7) | 6833.8 (5920.0-7302.8) | 125.6 (101.9-137.4) |
| H100 NVL | Vulkan | calibrated | 1 | 10496/10496 | 3640.9 (2502.5-4212.2) | 170.9 (170.4-171.4) | 6593.0 (6574.9-6615.4) | 158.5 (138.9-168.3) |
| H100 NVL | Vulkan | calibrated, `--mtp 0` | 0 | 10240/10240 | 3694.6 (2281.7-4423.6) | 141.6 (141.4-141.8) | 7297.2 (7271.2-7317.4) | 138.3 (138.1-138.4) |

## 2026-11-10 — DeepSeek-V4.1-Flash-1017 IQ2_XXS

`ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF`: the five `IQ2_XXS` shards (138.2 GB) and
`DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf` (110.6 GB), linked as `...-IQ2_XXS-00006-of-00006.gguf`, 248.8 GB in all,
sha256 checked for each file. Commit `e1c2d6e`. One job per card, 32 cores and 240 GB RAM:

| Job | Card | Host CPU | Node |
| --- | --- | --- | --- |
| A100 | A100-SXM4-80GB | EPYC 7413 | not the node of the earlier DeepSeek attempt on this card type |
| H100 | H100 NVL | EPYC 9224 | same node as an earlier DeepSeek job that ended 4 minutes before, so part of the file was already in its page cache |

```sh
rustingstrata check --model $M
STRATA_DS_PROF=1 rustingstrata generate --model $M --prompt "The capital of France is" -n 16
# twice for each VRAM expert budget B in 9 and 60 (GB):
STRATA_DS_PROF=1 STRATA_DS_GPU_EXPERTS=$B rustingstrata generate --model $M --prompt "$P" -n 128
```

`check`: `check: deepseek41 ok: 40 layers, 384 experts (6 used), 1043 tensors, tensor table valid (CPU reference
only; no GPU path yet)`; `generate` did use the card (`cuda device 0: ...` in every run's log). The first `generate`
printed ` Paris.  The quick brown fox jumps over the lazy dog.  The quick` on both cards. `$P` is "The history of the
printing press begins in East Asia, where woodblock printing was used centuries before movable type appeared in
Europe. The technology spread west along", 30 tokens. Every run on both cards printed the same 33 tokens and then
stopped at the end-of-sequence token: " trade routes, and by the 15th century, Gutenberg's press revolutionized
communication. This timeline traces the evolution from early woodblock methods to modern printing techniques."

`STRATA_DS_PROF` prints one line per forward pass; prefill is one token at a time, so the first 30 lines are the prompt
and the other 33 are decode. The `total` on each line covers the 40 layers only: the output norm, the vocabulary
projection, argmax and detokenizing come after it. So the rates in this table are layer time, an upper bound; the
end-to-end rates are in the next table. Hit rate is the VRAM expert cache over the decode lines, and storage read is
`read_bytes` of `/proc/self/io` at the last line.

| Card | Run | Wall time | Prefill, 30 tokens (layers) | Decode layer time, ms per token: mean (min-max) | Decode tok/s (layers) | VRAM hit rate | Storage read |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A100 | sanity prompt | 16:03 | - | - | - | - | 20881 MB |
| A100 | 9 GB, run 1 | 40:55 | 0.02 tok/s | 31413 (8267-55364) | 0.03 | 23% | 25630 MB |
| A100 | 9 GB, run 2 | 6:21 | 0.12 tok/s | 3675 (178-35744), median 250 | 0.27 | 23% | 3301 MB |
| A100 | 60 GB, run 1 | 0:15 | 4.33 tok/s | 127 (95-170) | 7.9 | 84% | 14 MB |
| A100 | 60 GB, run 2 | 0:14 | 4.61 tok/s | 135 (93-184) | 7.4 | 84% | 14 MB |
| H100 NVL | sanity prompt | 8:39 | - | - | - | - | 6592 MB |
| H100 NVL | 9 GB, run 1 | 11:20 | 0.46 tok/s | 18523 (5431-38001) | 0.05 | 23% | 7589 MB |
| H100 NVL | 9 GB, run 2 | 0:14 | 6.00 tok/s | 152 (121-175) | 6.6 | 23% | 14 MB |
| H100 NVL | 60 GB, run 1 | 0:10 | 7.69 tok/s | 97 (68-130) | 10.3 | 84% | 14 MB |
| H100 NVL | 60 GB, run 2 | 0:10 | 7.67 tok/s | 97 (70-133) | 10.3 | 84% | 14 MB |

### End to end

Two more jobs, built from a docs-only revision of this change (same code as `e1c2d6e`), same files, on other
nodes: A100-SXM4-80GB with an EPYC 7413 (24 CPUs, 200 GB RAM) and H100 NVL with a Xeon Gold 5418Y (16 CPUs, 120 GB
RAM). Each ran the same `generate` once with a 60 GB budget to fill
the page cache, then three pairs of `generate -n 1` and `generate -n 128` per budget, timed with `date +%s.%N`
around each process. `-n 1` stops after the prompt, `-n 128` runs the same prompt plus the 33 decode steps, so model
load and prefill cancel and (mean wall of `-n 128` - mean wall of `-n 1`) / 33 is the end-to-end decode time per token.

| Card (host) | Budget | Wall, `-n 1` (s) | Wall, `-n 128` (s) | End-to-end decode | Per pair | Layer time in the `-n 128` runs |
| --- | --- | --- | --- | --- | --- | --- |
| A100 (EPYC 7413) | 9 GB | 10.97, 10.95 | 17.83, 18.33 | 216 ms, 4.6 tok/s | 4.5-4.8 tok/s | 202 ms, 5.0 tok/s |
| A100 (EPYC 7413) | 60 GB | 9.88, 9.81, 9.71 | 14.95, 14.64, 14.92 | 153 ms, 6.6 tok/s | 6.3-6.8 tok/s | 135 ms, 7.4 tok/s |
| H100 NVL (Xeon Gold 5418Y) | 9 GB | 9.81, 8.38, 9.24 | 15.93, 17.14, 16.31 | 222 ms, 4.5 tok/s | 3.8-5.4 tok/s | 228 ms, 4.4 tok/s |
| H100 NVL (Xeon Gold 5418Y) | 60 GB | 6.40, 6.42, 6.31 | 9.96, 9.75, 10.53 | 112 ms, 8.9 tok/s | 7.8-9.9 tok/s | 104 ms, 9.7 tok/s |

The A100's first 9 GB pair is left out: its `-n 1` read 5.1 GB from storage (109 s). Every other timed run read
14-16 MB. Each process's wall time moves by up to 1.4 s between runs, about 40 ms per decode token, so the difference
between end-to-end and layer time (-6 to 18 ms here) is within that noise: the part after the layers is small next to
the layers. All runs printed the same text as above.

- Until the experts this prompt uses are in the page cache, reading them from the cluster file system decides the
  speed (seconds to a minute per token; the warm-up runs took 44 minutes on the A100 node and 32 on the H100 node).
  After that, end-to-end decode is 4.5-4.6 tok/s with the default 9 GB budget on both cards, and 6.6 (A100) and
  8.9 (H100 NVL) tok/s with 60 GB.
- The host matters at 9 GB: the H100 NVL's layer time was 152 ms per token with 32 CPUs on an EPYC 9224 node and
  228 ms with 16 CPUs on a Xeon Gold 5418Y node (different node, CPU model and core
  count); at 60 GB it was 97 and 104 ms.
- In the warm H100 NVL runs on the EPYC 9224, the expert part of a decode token is 104 ms at 9 GB and 50 ms at
  60 GB; attention is 28-29 ms in both. On the A100 at 60 GB it is 70-78 ms for experts and 36-38 ms for attention.
- Maximum resident set size was 34-36 GiB in the 128-token runs of the first two jobs. Over the 33 decode tokens, the
  60 GB budget raises the VRAM hit rate from 23% to 84%; the misses are read from the page cache.
- These numbers rest on one raw prompt and 33 decode tokens (the model ended there), so they say nothing about long
  prompts or long replies.
- The README's numbers (RTX 3060 12 GB, 30 GB RAM, 2-3.6 tok/s decode) are from another machine and were not re-run
  here, so the two are not a side-by-side comparison.

## 2026-11-10 — first round: benchmarks without calibration

Commit `7264e57` (v1.2.1), one GPU per job with 8 CPU cores and 48 GB RAM. Model: `Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf`
(sha256 `ed7cda7e...f37fb0c`); it fits in VRAM on every card here, so all 10240 experts are resident and the expert
hit rate is 100%.

| GPU | VRAM | Arch | Host CPU |
| --- | --- | --- | --- |
| A100-SXM4-80GB | 81920 MiB | sm_80 | EPYC 7413 |
| A30 | 24576 MiB | sm_80 | EPYC 7413 |
| L40S | 46068 MiB | sm_89 | Xeon Platinum 8458P |
| H100 NVL | 95830 MiB | sm_90 | EPYC 9224 |
| H100 80GB HBM3 (tests only) | 81559 MiB | sm_90 | Xeon Platinum 8470 |

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
