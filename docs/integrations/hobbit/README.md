# HOBBIT — ODS integration analysis

## Executive summary

HOBBIT combines expert loading, adaptive prefetching, cache management and mixed precision. A key idea is to mitigate an expert-cache miss by making a lower-precision representation available rather than always waiting for the full representation.

**ODS classification: P1 research technique / P2 implementation candidate.**

## Core mechanism

```
expert requested
     |
 cache hit? ---- yes ---> execute cached expert
     |
     no
     |
lower precision available?
     |             |
    yes            no
     |             |
approximate       load full
execution         expert
```

This adds a new dimension to ODS:

**expert residency + expert precision.**

## ODS implications

A future capability manifest could describe:

- expert precision levels;
- precision available in cache;
- fallback precision;
- adaptive prefetch;
- cache policy;
- quality/recovery mechanism.

## Limitations

HOBBIT is primarily a research reference rather than a drop-in production ODS backend. Its reported gains should not be treated as installable capability.

## LEONES benchmark

Compare full-precision misses, low-precision fallback, full prefetch and adaptive prefetch. Measure TTFT, tok/s, cache behaviour, storage reads, VRAM and output quality.

Latency and quality must be measured separately.

## Recommendation

Keep HOBBIT as **P1 research**. Its most useful contribution to ODS is precision-aware expert caching.

## Sources

- Hugging Face HOBBIT paper.
- Related llama.cpp community discussions on expert caching/offload.

Published performance remains **reported** until independently reproduced.
