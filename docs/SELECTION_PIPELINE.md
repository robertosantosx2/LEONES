# LEONES selection pipeline

`selection_pipeline.py` is the operational entry point for the selection
layer. It is deliberately a **dry-run planner**: it observes the host,
selects models and creates runtime plans, but it does not download or execute a
model.

```text
hardware_profile
      ↓
Atlas feed + optional LLMFit
      ↓
model_selector
      ↓
TOP_N / BENCHMARK_REQUIRED
      ↓
runtime_gate
      ↓
execution plan
```

Run on Debian/Ubuntu:

```bash
python3 scripts/selection_pipeline.py \
  --workload chat \
  --out data/prospection/selection_pipeline.json
```

For a real LLMFit feed, add `--llmfit <json>`.

The output is the hand-off consumed by GGUF resolution and artifact
acquisition. Physical inference remains a separate step so planning never
masquerades as measurement.
