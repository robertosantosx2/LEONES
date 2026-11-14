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
