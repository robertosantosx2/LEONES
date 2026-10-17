# ODS CI plan

ODS validation is split into software CI and local hardware validation.

## CI gates

1. Build/install the ODS package from its pinned upstream snapshot.
2. Import the package without network credentials.
3. Import the real ranking classes: `BaseSemanticSearcher`, `InfinitySemanticSearcher`, and `JinaReranker`.
4. Exercise `Chunker` with a deterministic local input.
5. Exercise `BaseSemanticSearcher` with a fake embedding implementation; no network calls.
6. Validate the public return contract of `rerank()` and `get_reranked_documents()`.
7. Validate `SourceProcessor` with a small fake source payload and mocked scraper/reranker boundaries.
8. Run packaging/build checks.
9. Keep Infinity/Jina network tests in a separate optional job.

## CPU policy

The baseline CI job must use CPU PyTorch only. It must never install CUDA packages merely because `torch` is present in an optional ranking path.

GPU/CUDA testing is a separate concern and must be opt-in.

## Local hardware gate

After CI is green, the Debian machine is used only for measured local capabilities:

- CPU model/features and thread scaling
- available RAM
- disk throughput/cache behavior
- GPU/SYCL/CUDA availability
- local model loading
- inference latency and tokens/s

This keeps software defects out of the hardware benchmark results.
