# Final model/runtime selector

The final selector closes the LLMFit → evidence → runtime loop.

1. LLMFit candidates are normalized and capability-gated.
2. Candidates without a usable runtime are rejected.
3. `perfect` and `good` candidates remain eligible.
4. Matching physical runtime evidence is preferred and receives the freshness/throughput signal.
5. If no physical evidence exists, the selector falls back to the deterministic LLMFit score/estimate ordering.
6. `estimated_tps` is never overwritten by `measured_tps`.

This selector is deliberately runtime-agnostic. The selected candidate identifies the runtime; the A01 execution/grader layer remains responsible for executing the task and grading the result.

```text
A01 task
   ↓
final_selector.select()
   ↓
model + runtime
   ↓
A01 execution/grader
   ↓
benchmark/evidence
   ↓
next selection
```

The next integration point is the A01 execution entry point: it should consume the selected candidate rather than independently choosing a model/runtime. This is the point where the two previously parallel paths become one operational pipeline.
