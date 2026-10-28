ggml_cuda_init: found 1 CUDA devices (Total VRAM: 3768 MiB):
  Device 0: NVIDIA GeForce RTX 3050 Laptop GPU, compute capability 8.6, VMM: yes, VRAM: 3768 MiB
| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| lfm3 1.7B Q4_K - Medium        |   1.02 GiB |     1.73 B | CUDA       |  99 |           pp512 |     4411.27 ± 116.24 |
| lfm3 1.7B Q4_K - Medium        |   1.02 GiB |     1.73 B | CUDA       |  99 |           tg128 |        117.98 ± 1.17 |

build: c3df4b7 (1)
