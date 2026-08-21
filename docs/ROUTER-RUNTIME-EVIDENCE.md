# Router + runtime evidence

Runtime measurements now become a **ranking signal**, never a replacement for the original LLMFit estimate.

For a candidate we keep both:

- `estimated_tps`: LLMFit estimate;
- `measured_tps`: LEONES physical measurement.

The Router signal is computed only from `evidence_status=measured` and applies freshness decay. Default half-life is 30 days. Throughput is normalized against the 10 tok/s LEONES usability reference and multiplied by freshness.

```text
LLMFit estimate ───────────────┐
                               ├─ candidate identity
physical benchmark → evidence ─┤
                               ↓
                         Router signal
                               ↓
                  ranking / runtime choice
```

An `estimated` result contributes zero runtime-evidence score. Missing or invalid measurements also contribute zero. This prevents a speculative throughput figure from silently outranking measured evidence.

The Router integration is intentionally small and deterministic so it can later be consumed by LOTB, Atlas and the task router without changing the evidence contract.
