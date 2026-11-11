# M2 results: GPU forward

Model: Qwen3.6-35B-A3B-UD-Q2_K_XL, RTX 3060 12 GB, Ryzen 5 7600X. llama.cpp reference commit 5d8ccdf9d.

## Parity (20 prompts x 32 greedy positions vs llama-server)

`python -I tools/parity.py <model> --bin target/release/rustingstrata --extra=--gpu --tag gpu`

- Top-1 agreement 631/640 = **98.59%** (gate: 99%).
- Every miss on a prompt the CPU reference has also scored is the same miss, at the same position, with the same
  llama.cpp top-2 gap (to 1e-3). GPU and CPU reference agree; the shortfall against llama.cpp is shared numerics
  (llama.cpp quantizes activations to Q8 for its matmuls, the reference uses f32 activations), not a GPU defect.
- Misses: top-2 gaps 0.005 to 0.35 logit.

## Speed (static placement, experts of 29/40 layers resident, CPU reference experts)

~0.37 s/token; superseded by M3 (expert cache, CPU integer kernels, mapped-memory CPU worker).
