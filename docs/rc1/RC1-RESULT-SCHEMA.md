# RC1 normalized task result

> Schema contract: `leones.rc1.agentic-result.v1`

The result is deliberately small. It records what LEONES needs to compare a task execution and then hand it to the existing evidence/promotion pipeline.

## Required identity

```text
schema
benchmark_id
benchmark_version
task_id
task_version
execution_id
started_at
finished_at
product
agent
model
runtime
hardware
```

## Outcome

```text
task_status: success | failure | error | not_comparable
task_success: boolean
failure_reason: string | null
```

## Measurements

```text
wall_time_seconds
turns
warmup_count
measurement_index
tool_calls
tool_errors
recovery_count
input_tokens: integer | null
output_tokens: integer | null
measured_tps: number | null
```

## Evidence

```text
prompt_hash
fixture_sha256
result_artifact
result_sha256
logs: [string]
```

Unknown values are represented as `null`; they are never fabricated.

## Promotion rule

`task_success=true` is necessary but not sufficient for promotion. The execution must also have valid identity, timestamps, fixture/result hashes and a compatible hardware/runtime record.

Runtime throughput is optional for agentic results because not every harness exposes it. When present, it remains a secondary observation and must not be confused with task success.
