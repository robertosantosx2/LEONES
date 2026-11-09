# Pithos NVIDIA OpenCL and Vulkan Validation — 2026-11-09

## Scope

This report complements `2026-11-09-intel-opencl-fail-closed.md`.
It records NVIDIA tests performed with Pithos 0.6.0 and
`LFM3-1.7B-Q4_K_M.gguf` on an NVIDIA RTX 3050 Laptop GPU.

## Environment

- Host: MSI Thin 15 B12UC
- CPU: Intel Core i7-12650H
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, 4096 MiB VRAM
- Driver: 580.178.04; CUDA version reported by nvidia-smi: 13.0
- System RAM: 14.8 GB
- Model: LFM3-1.7B-Q4_K_M.gguf (approximately 1.02 GB)
- Benchmark: PP 512 / TG 128
- Real generation: identical 27-token prompt, seed 42, reasoning off,
  maximum 128 new tokens.

## VRAM isolation

The earlier NVIDIA allocation attempts took place while TensorFold
occupied 3214 MiB of GPU memory. OpenCL could not upload its weights;
Vulkan ran out of memory after allocating 55 of 154 matrices.

TensorFold subsequently exited. Before the successful tests,
nvidia-smi reported 16 MiB used out of 4096 MiB, with 4 MiB attributed
to Xorg and no CUDA compute processes listed.

Therefore, the earlier allocation failures do not establish an NVIDIA
backend defect in Pithos.

## NVIDIA OpenCL benchmark

Observed backend: NVIDIA GeForce RTX 3050, int8/dp4a,
all layers in VRAM (1.19 GB), prompt matmuls.

| Metric | First | Warm |
|---|---:|---:|
| PP512 | 407.78 tok/s | 421.84 tok/s |
| TG128 | 103.70 tok/s | 102.81 tok/s |

Exit code: 0.

## NVIDIA Vulkan benchmark

Observed backend: NVIDIA GeForce RTX 3050 discrete GPU,
154 matrices and 1063 MB of weights. Pithos reported the whole
forward pass on GPU, with 176 MB KV cache and 8 MB activations.

| Metric | First | Warm |
|---|---:|---:|
| PP512 | 606.59 tok/s | 643.55 tok/s |
| TG128 | 104.54 tok/s | 104.45 tok/s |

Exit code: 0.

## Real generation

Prompt used for both backends:

"Explain in a few sentences how a GPU accelerates neural network inference."

| Metric | OpenCL | Vulkan |
|---|---:|---:|
| Prompt tokens | 27 | 27 |
| Prompt speed | 180.3 tok/s | 175.9 tok/s |
| Generated tokens | 95 | 100 |
| Generation speed | 104.34 tok/s | 104.05 tok/s |
| Generation time | 0.91 s | 0.96 s |
| Exit code | 0 | 0 |

Both backends produced coherent responses. The model stopped before
the 128-token maximum; this was normal completion, not a failure.

## Interpretation and limitations

1. Both NVIDIA backends loaded the model and completed benchmark and
   real-generation tests when sufficient VRAM was available.
2. Vulkan achieved approximately 52.6% higher warm PP512 throughput
   in this benchmark.
3. Warm TG128 throughput was close: Vulkan was approximately 1.6%
   faster. Real-generation throughput was effectively tied; OpenCL
   was approximately 0.28% faster in this single run.
4. The short real-generation prompt measurements are not directly
   comparable to PP512 benchmark measurements.
5. Vulkan explicitly reports the whole forward pass on GPU. OpenCL
   reports all layers in VRAM and prompt matmuls; this alone does not
   prove that every forward-pass operation runs on GPU.
6. These are local measurements, not repeated statistical benchmarks.
7. The Intel UHD OpenCL read-logits failure remains unresolved.
   Tests with PITHOS_GPU_DOT=emu and PITHOS_GPU_INTELMV=0 still
   reproduced that failure.
8. This report does not validate the complete MoE path and does not
   claim that Intel OpenCL has been fixed.

## Evidence

Full logs and SHA-256 hashes are stored in
`evidence-nvidia-2026-11-09/`:

- `nvidia-opencl-free-vram.log`
- `nvidia-opencl-generation.log`
- `nvidia-vulkan-free-vram.log`
- `nvidia-vulkan-generation.log`

## Conclusion

NVIDIA RTX 3050 validation passed for both OpenCL and Vulkan with
Pithos 0.6.0 and the stated LFM3 model, after TensorFold released
the GPU memory it had occupied.

Vulkan showed a substantial PP512 benchmark advantage, while
generation throughput was practically identical.

The Intel UHD OpenCL read-logits failure remains a separate,
unresolved issue.

---
LEONES engineering validation record. Results are scoped to the
hardware, software, model and conditions stated in this report.
