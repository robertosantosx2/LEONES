# M4 results: chunked GPU prefill

Model: Qwen3.6-35B-A3B-UD-Q2_K_XL, RTX 3060 12 GB, Ryzen 5 7600X. Prompt: 3970 tokens (spec + plans text),
`strata generate --gpu --ctx 8192 -n 128`, `--chunk` as listed (1024 until 8d0c3c4, then 4096). Three runs each, GPU otherwise idle.

| Commit | Prefill tok/s | Decode tok/s | Parity (3 runs) |
|---|---|---|---|
| 62ebb6f chunked prefill | ~444 (428-470, noisy) | 43-47 | 98.28% |
| 76a57e2 GEMM/DeltaNet registers | 1001 (961-1022) | 49.6 (49.1-49.9) | 98.18% |
| 8d0c3c4 chunk 4096 default | **1366** (1363-1369) | 49.6 (49.2-50.0) | 98.09% (6 runs, 624-632) |
| 1866f5e split decode attention | 1360 (warm runs 1316-1360) | **60.9** (59.8-62.4) | 98.28% (628-630) |
| 059fd1e vector loads in decode attention | 1350 (noisy: 1002-1350) | **78.6** (76.9-80.0) | 98.49% (629-631) |
| 09edad5 ldmatrix in prefill attention | 1434 (loaded machine: 835-1434) | 64-78 (loaded) | 98.13% (627-629) |
| b57b791 DeltaNet 16 floats per lane | **1581** (1538-1610) | 48-76 (loaded) | 98.44% (629-631) |
| 2dcae33 GQA-shared decode attention | 1608 (1561-1633) | **80.5** (79.8-80.9) | 98.23% (627-630) |
| e087210 min 16 positions per split | 1638 best (loaded) | 77.4 (75.7-80.5, loaded) | 98.07% (625-630) |
| b9d9547 one-head attention below 4096 | 1652 best (loaded) | **80.4** (77.5-80.8) | 98.44% (627-632) |
| a02b4ec MoE gate and up in one launch | 1641 best (loaded) | **81.0** (76.8-81.8) | 98.49% (629-632) |

Short-prompt decode (8-token prompt, -n 128): 85.8 tok/s at 8d0c3c4, 83.3 at 1866f5e, 86.1 at 059fd1e (5 clean runs each); 65-77 at 2dcae33 (regression), 82.7 at e087210 (loaded host), 86.4-86.9 at b9d9547 (~100% expert hits). 88.1 (88.06-88.22) at a02b4ec, 100% hits, host load 2.8.

32K (31768-token prompt, `--ctx 32768`): 09edad5 prefill 1007/1204/1190 tok/s (was 818), decode ~55. b57b791: 1288 (under nsys). 2dcae33: decode best 62.5 (others 12-20 under host load 12), attn_decode 590 -> 314 us per call.
llama.cpp `-d 32768`: pp512 814, tg128 56.4 (marginal rate at depth, not an average).

Gate: prefill >= 1017 tok/s at 4K, decode > 67 tok/s, parity >= 99%.

M5 (MTP): CPU reference draft acceptance 24/25 greedy (6379338). GPU draft head matches it (be8f72b); speculative decode not wired into `generate` yet, so no speed change.
