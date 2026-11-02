# LEONES Lab Agent — benchmark manifest v1

Each approved invocation of the guarded llama.cpp runner creates a new evidence directory containing:

- manifest.json — machine-readable run manifest.
- stdout.json — raw llama-bench JSON output.
- stderr.log — raw diagnostics from llama-bench.

The agent never overwrites an existing evidence directory.

## Manifest fields

| Field | Type | Meaning |
|---|---|---|
| schema_version | integer | Manifest schema version, currently 1 |
| state | string | MEASURED, RUN_COMPLETED_UNPARSED, FAILED or TIMEOUT |
| engine | string | llama-bench |
| model_path | string | Canonical local GGUF path |
| model_bytes | integer | Model file size in bytes |
| prompt_tokens | integer | Configured prompt length |
| generation_tokens | integer | Configured generation length |
| repetitions | integer | Number of repetitions |
| timeout_seconds | integer | Maximum run duration |
| timestamp_unix_ns | integer | Manifest creation timestamp |
| elapsed_ms | integer | Observed wall-clock duration |
| exit_code | integer or null | Process exit code |
| arguments | array of strings | Exact arguments passed to llama-bench |
| results | array or null | Parsed llama-bench JSON results |
| parse_error | string or null | Why metrics were not accepted |
| stdout_file | string | Raw stdout filename |
| stderr_file | string | Raw stderr filename |

## MEASURED acceptance

A run receives state MEASURED only if all of these are true:

1. llama-bench exits successfully.
2. stdout parses as a non-empty JSON array.
3. Every result row contains a positive finite avg_ts value.
4. Every result row contains a finite non-negative stddev_ts value.
5. Every result row identifies model_filename, backends and test_time.

A successful process without validated metrics is RUN_COMPLETED_UNPARSED. A non-zero exit is FAILED. Exceeding the configured timeout is TIMEOUT. Raw logs remain available in all completed-run states.

## Safety boundary

- The runner invokes only the discovered llama-bench executable.
- It builds arguments internally; there is no shell and no free-form command option.
- It accepts only an existing non-empty GGUF file with GGUF magic bytes.
- It defaults to dry-run. Execution requires the explicit --approve flag.
- Limits are enforced for prompt length, generation length, repetitions and timeout.
- Child environment is cleared and only PATH, HOME, LD_LIBRARY_PATH, CUDA_VISIBLE_DEVICES, CUDA_HOME and OMP_NUM_THREADS may be inherited.
- The conversational LLM tool loop cannot invoke benchmark execution.
