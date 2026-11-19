# Betelgeuse — Qwen3.5-35B-A3B trunk-only runtime

Betelgeuse is being evaluated as a native Linux/CUDA MoE runtime for the Qwen3.5-35B-A3B IQ2_XXS model on the MSI Thin 15 B12UC. Work is developed in the GitHub fork `robertosantosx2/Betelgeuse`, with LEONES maintaining the research record, evidence boundaries, and validation gates.

## Current state (2026-11-19)

**Estado: PR draft — integración runtime bajo validación**

- Betelgeuse fork branch: `feat/qwen35-trunk-only-pager-msi`
- Pull request: [#1 — Qwen3.5-35B-A3B trunk-only expert bundle](https://github.com/robertosantosx2/Betelgeuse/pull/1)
- Bundle builder: 40 decoder-trunk layers × 256 experts; block 40 MTP/NextN remains in the dense GGUF.
- PLE companion: not required.
- Real-model pack generation and all 10,240 trunk expert byte checks passed on the MSI.
- CUDA native pager byte-path test passed on the MSI.
- Runtime integration has been hardened to preserve MTP experts and fail closed when the pack is missing or invalid.
- Linux build/test and runtime startup gates are still pending. No Qwen3.5 forward pass or token generation has been run.

## Hardware validation target

- MSI Thin 15 B12UC
- Intel Core i7-12650H
- NVIDIA GeForce RTX 3050 Laptop GPU, 4 GiB VRAM, compute capability `sm_86`
- 14 GiB RAM, 32 GiB swap
- Ubuntu; NVIDIA driver 580.178.04; CUDA Toolkit 13.4

## What has been measured

The source GGUF was 10,676,139,840 bytes. The trunk pack contains 10,240 experts and 8,380,219,392 expert payload bytes. All 10,240 experts passed byte-for-byte verification.

The native CUDA pager test against the original GGUF passed the exercised synchronous reads, asynchronous prefetch/commit, write-allocate, cache reuse, and batch-read checks. These results validate packaging and the pager data path only.

Detailed evidence: [MSI validation record](https://github.com/robertosantosx2/Betelgeuse/blob/feat/qwen35-trunk-only-pager-msi/docs/qwen35-msi-validation-2026-11-18.md).

## Runtime audit findings

The 2026-11-19 source audit identified two correctness hazards:

1. The generic expert-tensor skip predicate also skipped the resident routed-expert payloads in MTP/NextN block 40. The loader now skips only external trunk payloads for stripped bundles and verifies the expected placement of all three expert roles in blocks 0-40.
2. A failed or absent pack could previously leave the runtime continuing toward MoE pool allocation. Stripped bundles now require validated metadata and geometry, direct-I/O/GGUF/pack configuration, successful pager initialization, and active pack mode before pool allocation.
3. External trunk expert tensors receive zero-sized placeholder contexts instead of allocating their absent payloads. The same external classification is used in the memory-fit and real-load passes; resident MTP block 40 remains normally allocated and loaded.

The special path is gated by `betelgeuse.stripped_experts`; ordinary non-stripped model loading retains its prior load-mode behavior.

- [Runtime audit and acceptance checklist](https://github.com/robertosantosx2/Betelgeuse/blob/feat/qwen35-trunk-only-pager-msi/docs/qwen35-runtime-audit-2026-11-19.md)
- [Bundle format and runtime contract](https://github.com/robertosantosx2/Betelgeuse/blob/feat/qwen35-trunk-only-pager-msi/docs/qwen35-trunk-only.md)

## Acceptance gates

- [x] Synthetic Qwen3.5 trunk-only packer regression tests passed in GitHub Actions.
- [x] Real-model pack and 10,240 expert byte verification passed on the MSI.
- [x] Native pager byte-path test passed on the MSI.
- [x] Loader source audit and fail-closed changes committed to the Betelgeuse PR branch.
- [ ] Clean Linux CPU build and tests on the updated runtime branch.
- [ ] Linux CUDA build for `GGML_CUDA=ON`, `CMAKE_CUDA_ARCHITECTURES=86`.
- [ ] Negative startup test: absent/invalid pack must fail before MoE pool allocation.
- [ ] Positive startup test: valid pack must activate before pool allocation.
- [ ] Confirm resident MTP/NextN block 40 remains available through model loading.
- [ ] Preserve non-stripped MoE behavior.

No inference, logits equivalence, throughput, latency, or context-length claims are accepted until these gates pass. MSI inference remains paused until the Linux build and runtime audit are complete and the user is notified.
