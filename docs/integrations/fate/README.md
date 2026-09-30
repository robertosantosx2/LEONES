# FATE — ODS integration analysis

## Executive summary

FATE addresses expert-offload latency by predicting which experts will be needed before the next layer's routing decision is fully available, enabling proactive prefetch.

**ODS classification: P1 — strategic runtime capability.**

## Core idea

```
current layer
   |
routing features
   |
FATE predictor
   |
predicted next experts
   |
async prefetch
   |
GPU expert cache
```

The desired transformation is:

```
route -> load -> compute
```

into:

```
predict -> prefetch || compute
```

## ODS relevance

FATE is better treated as a capability than as a separate server. The Runtime Capability Manifest should eventually expose:

- expert prediction;
- cross-layer prediction;
- temporal prediction;
- asynchronous prefetch;
- cache hit rate;
- storage backend.

A practical FATE-style implementation has also been explored around llama.cpp, making this strategically important: if llama.cpp gains robust expert prediction/paging, ODS can retain a mature runtime instead of maintaining another server.

## LEONES benchmark

Compare load-on-demand with prediction enabled and disabled. Measure prediction accuracy, cache hit rate, storage reads, TTFT and tokens/s.

Do not equate predictor accuracy with end-to-end performance.

## Risks

- Incorrect predictions waste I/O bandwidth.
- Predictor overhead matters.
- Synchronization can erase theoretical gains.
- Behaviour may vary strongly by model/workload.

## Recommendation

**P1 architectural capability.** Investigate FATE-style prediction in llama.cpp and other runtimes before adopting a separate runtime.

## Sources

- Hugging Face paper page for FATE.
- Open implementations/prototypes around llama.cpp.

All published benchmark results are **reported** until reproduced by LEONES.
