# NEPENTHES universal collector — schema 1.0

The collector is engine-agnostic and read-only with respect to the inference workload. It does not launch, stop, signal, reconfigure, or send requests to the server. It creates a new timestamped run directory and refuses to overwrite an existing path.

## Capture

From this directory:

```bash
python3 nepenthes_universal_collector.py \
  --output-root "$HOME/NEPENTHES/runs" \
  --engine "Tandem.cpp 0.8.0-dev" \
  --model "Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
  --process-name llama-server \
  --interval 0.5 \
  --metadata-json '{"build_commit":"<commit>","endpoint":"http://127.0.0.1:18086"}'
```

Use `--pid PID` when the process name is ambiguous. Press Ctrl-C to finish the capture. The collector terminates only its own `nvidia-smi dmon` helper; it does not signal the target process. `--duration SECONDS` is available for bounded capture.

## Output contract

- `run_manifest.json`: run UUID, schema version, wall/monotonic start and end, engine/model identity, host/Python identity, target PID, sampling cadence, metadata, probe capability snapshot and measurement semantics.
- `samples/telemetry.jsonl`: host CPU counters, RAM/swap, vmstat, PSI, CPU frequency, block-device counters, target process stat/status/I/O, per-thread CPU and scheduler counters, FD count, cgroup-v2 counters and GPU/VRAM telemetry. Each row carries run UUID, wall timestamp and monotonic nanoseconds.
- `samples/pcie.jsonl`: raw `nvidia-smi dmon -s t` rows, if supported.
- `events/engine_events.jsonl`: normalized engine events when an adapter emits them.
- `requests/*.json`: optional normalized request/response records.
- `profiles/` and `logs/`: reserved for copied profiler exports and engine logs; copy source artifacts, do not rewrite them.
- `collection_report.json`: probe coverage, counts, errors and limitations.
- `SHA256SUMS`: SHA-256 for every file present at finalization, excluding the checksum file itself.

## Event adapter contract

The Python API is intentionally small:

```python
from nepenthes_universal_collector import UniversalCollector

collector = UniversalCollector(
    output_root="/data/nepenthes",
    engine="engine/build",
    model="model.gguf",
    pid=1234,
    interval=0.5,
    metadata={"engine_commit": "abc123"},
)
run_dir = collector.start()
collector.event("request_start", {"prompt_tokens": 128}, request_id="r-001", source="engine")
collector.event("cache_miss", {"layer": 4, "expert": 19, "bytes": 8388608},
                request_id="r-001", source="moe-cache")
collector.event("transfer", {"direction": "H2D", "bytes": 8388608, "stream": 3},
                request_id="r-001", source="cuda-adapter")
collector.event("stall", {"reason": "host_flag_wait", "duration_ns": 900000},
                request_id="r-001", source="cuda-adapter")
collector.request_record("r-001", {
    "finish_reason": "stop",
    "prompt_tokens": 128,
    "completion_tokens": 256,
    "ttft_ms": 420.0,
    "prefill_ms": 880.0,
    "decode_ms": 7900.0,
})
collector.event("request_end", {"status": "ok"}, request_id="r-001", source="engine")
collector.finish()
```

Allowed event kinds: `request_start`, `request_end`, `model_load`, `model_unload`, `allocation`, `free`, `transfer`, `kernel`, `sync`, `cache_hit`, `cache_miss`, `eviction`, `prefetch`, `routing`, `kv_cache`, `fallback`, `oom`, `stall`, `error`, `checkpoint`, and `custom`.

Every event contains a run UUID, optional request ID, unique event ID, source, wall timestamp, monotonic timestamp and a payload. Payload fields are adapter-defined but must use explicit units (for example `duration_ns`, `bytes`, `layer`, `expert`). Do not encode unknown values as zero.

## Probe coverage and interpretation

| Probe | Current implementation | Scope / limitation |
|---|---|---|
| Host CPU | Raw `/proc/stat` counters | Host-wide; derive deltas between monotonic samples |
| RAM / swap | `/proc/meminfo`, vmstat | Host-wide |
| Process / threads | stat/status/io, per-thread utime/stime, schedstat runtime/runqueue wait/timeslices, context switches, CPU affinity, RSS/HWM, FD count | One PID and up to 512 TIDs; PID reuse/exit must be checked; no stack sampling |
| Scheduler pressure | PSI CPU/memory/I/O and process schedstat | PSI is host/cgroup context, not a per-request attribution |
| CPU frequency | sysfs scaling frequency | Per online CPU where exposed; not proof of effective clock under load |
| Storage | Whole-device `/proc/diskstats`, cgroup-v2 `io.stat` | Device counters are host-wide; map device topology before attribution |
| GPU / VRAM / processes | `nvidia-smi --query-gpu` plus `--query-compute-apps` PID/process/VRAM | Utilization is device-wide; compute-process memory attribution may be unsupported or omit graphics contexts; cadence may miss short peaks |
| PCIe | Persistent `nvidia-smi dmon -s t` | Device-wide MB/s, normally one-second cadence |
| cgroup v2 | memory.current/peak/max/events, cpu.stat/max, io.stat, PSI | Only where process cgroup files are readable |
| Nsight / CUDA | External profile files in `profiles/`; existing SQLite inspector | Collector does not itself start Nsight or instrument CUDA |
| MoE / KV / allocator | Normalized event adapter contract | Requires engine-side hooks; host polling cannot infer routing, cache hits or KV occupancy |

A missing probe is reported unavailable, never as zero. Host PSI, swap, block I/O and GPU PCIe include unrelated workloads. Do not sum physical and virtual block-device counters without understanding the storage stack. The process sampler follows one PID, records up to 512 threads (TIDs) including schedstat runtime and runqueue wait, and does not aggregate descendants or capture CPU call stacks. Short captures may not contain enough samples for meaningful percentiles.

## Current boundary

This is the universal host/GPU capture layer plus an engine-event schema. It does **not** yet implement Tandem.cpp hooks for per-layer expert routing, cache decisions, KV-cache accounting, allocator lifetimes, CUDA API/kernel correlation, worker queue timing or host-flag publication. Those require a separate engine adapter/patch and must be validated against a writable Tandem.cpp repository. Existing `resource_monitor.py`, `moe_runtime_probe.py`, MCT1/log inspectors and Nsight SQLite inspector remain available for the historical battery; this collector does not silently replace their existing output formats.


## Integration with the existing battery runner

The fixed battery keeps its historical per-request monitor outputs. To add the normalized run-level bundle and request-correlated events, pass `--universal-collector`:

```bash
python3 run_battery.py \
  --base-url http://127.0.0.1:18086 \
  --model Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf \
  --engine tandem.cpp \
  --mode same-engine-new-model \
  --model-path "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
  --monitor-interval 0.5 \
  --universal-collector \
  --output "$HOME/Descargas/tandem-monitored-$(date +%Y%m%d-%H%M%S)"
```

The runner binds automatic process discovery to the configured API port (or uses `--server-pid` when supplied), emits request-start/end events and writes each request/response plus the existing metrics into `universal/...`. The option is opt-in so historical runs and monitor overhead remain unchanged unless explicitly requested. The runner does not change server configuration.


## Offline import of Nsight Systems SQLite

After a capture has been exported to SQLite, normalize its activity events into an existing universal run:

\`\`\`bash
python3 import_NEPENTHES_nsys_sqlite.py \\
  --database /path/to/capture.sqlite \\
  --run-dir /path/to/nepenthes-run
\`\`\`

The importer is read-only against the source database. It writes events/nsys_activity.jsonl, profiles/nsys_import_report.json, updates the collection coverage report and regenerates SHA256SUMS. It imports CUDA Runtime API, kernel, memcpy and synchronization tables when their schemas are present; missing tables/columns remain explicitly unavailable.

**Clock-domain rule:** Nsight start/end values are preserved as source_start_ns/source_end_ns with source_clock="nsys_activity_ns". They are not copied into monotonic_ns or assigned wall timestamps because no host-clock correlation marker is inferred. CUDA correlation IDs are preserved but are not guessed to be request IDs. An engine/runner adapter must provide explicit markers before cross-domain timing or request attribution is claimed.


## C++ engine-side hook contract

The header-only adapter surface is in nepenthes_trace.hpp. It is C++17, allocation-free on the emit path, uses steady_clock nanoseconds, and has no dependency on JSON or CUDA. The engine installs a non-blocking, thread-safe sink before starting inference workers; call sites emit fixed-size events for routing/cache/KV/allocation/transfer/kernel/synchronization/host-wait/OOM/fallback. ScopedEvent records a host-side duration without allocating.

The callback is responsible for safely buffering and serializing events into the JSONL contract above. It must not block a worker or call back into inference. Install/disable only at controlled lifecycle boundaries; the current API deliberately does not support hot-swapping a sink while worker threads are active.

The C++ smoke test is test_nepenthes_trace.cpp and runs in the NEPENTHES workflow with g++ C++17. This validates the hook API and no-op/emit/timer behavior, not integration into Tandem.cpp. Actual call sites and a bounded, non-blocking sink still need a writable Tandem.cpp fork and separate review.
