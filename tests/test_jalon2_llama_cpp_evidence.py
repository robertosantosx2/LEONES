from scripts.jalon2_llama_cpp_evidence import parse_log


LOG = '''\
execution_id=jalon2-test-qwen3-20260827T140609Z
timestamp_utc=2026-08-27T14:06:09Z
host=Aspire-A515-55
os=PRETTY_NAME="Ubuntu 26.04 LTS"
kernel=7.0.0-30-generic
cpu=Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz
cpu_threads=8
physical_cores=4
runtime=llama.cpp
runtime_version=8681
runtime_package=8681+dfsg-1
runtime_binary=/usr/bin/llama-cli
runtime_binary_sha256=123c4dcb01f01aef5db4b8337720ccbddcd4b6243b8971f56c06a8da2ae1b7af
model=Qwen3-0.6B-Q4_K_M.gguf
model_size_bytes=396704416
model_sha256=b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e
threads=4
threads_batch=4
ctx_size=2048
n_predict=128
warmup=enabled
perf=enabled
single_turn=enabled
prompt_sha256=4771f1d9be162823f42164c1bc1e26dbbce2921f3d1e2eaee731915bbca51f9e

===== MEMORY BEFORE =====
Mem:           7.0Gi       5.9Gi       584Mi       418Mi       1.4Gi

llama_perf_context_print: prompt eval time = 100.00 ms / 20 tokens (200.00 tokens/s)
llama_perf_context_print: eval time = 500.00 ms / 128 tokens (256.00 tokens/s)
Command being timed: "llama-cli -m artifacts/models/Qwen3-0.6B-Q4_K_M.gguf -t 4 -tb 4 -c 2048 -n 128 --warmup --perf --single-turn -p Explain in one concise paragraph."
Elapsed (wall clock) time (h:mm:ss or m:ss): 0:05.86
Maximum resident set size (kbytes): 888148
Exit status: 0
'''


def test_physical_log_becomes_v11_evidence():
    evidence = parse_log(LOG + "timestamp_end_utc=2026-08-27T14:06:14Z\n")

    assert evidence["schema"] == "runtime-benchmark-evidence.v1.1"
    assert evidence["execution_id"].startswith("jalon2-test-")
    assert evidence["model"]["quantization"] == "Q4_K_M"
    assert evidence["artifact"]["sha256"] == "b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e"
    assert evidence["runtime"]["binary_sha256"] == "123c4dcb01f01aef5db4b8337720ccbddcd4b6243b8971f56c06a8da2ae1b7af"
    measurement = evidence["measurements"][0]
    assert measurement["ttft_ms"] == 100.0
    assert measurement["generation_time_ms"] == 500.0
    assert measurement["output_tokens"] == 128
    assert measurement["tokens_per_second"] == 256.0
    assert round(measurement["peak_memory_mb"], 2) == 867.33
    assert measurement["exit_code"] == 0


def test_parser_does_not_invent_missing_performance_metrics():
    log = LOG.replace("llama_perf_context_print: prompt eval time = 100.00 ms / 20 tokens (200.00 tokens/s)\n", "")
    log = log.replace("llama_perf_context_print: eval time = 500.00 ms / 128 tokens (256.00 tokens/s)\n", "")
    evidence = parse_log(log + "timestamp_end_utc=2026-08-27T14:06:14Z\n")
    measurement = evidence["measurements"][0]
    assert measurement["ttft_ms"] is None
    assert measurement["generation_time_ms"] is None
    assert measurement["tokens_per_second"] is None


def test_parser_accepts_real_llama_cpp_summary_format():
    log = LOG + """
[ Prompt: 174,3 t/s | Generation: 50,4 t/s ]
timestamp_end_utc=2026-08-27T14:06:14Z
"""

    evidence = parse_log(log)
    measurement = evidence["measurements"][0]

    assert evidence["protocol"]["prompt_tokens_per_second"] == 174.3
    assert measurement["tokens_per_second"] == 50.4

    # El throughput de prompt NO es TTFT.
    assert measurement["ttft_ms"] is None


def test_parser_extracts_full_prompt_from_command_section():
    evidence = parse_log(
        LOG + "timestamp_end_utc=2026-08-27T14:06:14Z\n"
    )

    assert evidence["protocol"]["prompt"] == (
        "Explain in one concise paragraph."
    )


def test_parser_extracts_comma_decimal_llama_summary():
    log = LOG + """
[ Prompt: 188,7 t/s | Generation: 34,5 t/s ]
timestamp_end_utc=2026-08-27T14:06:14Z
"""

    evidence = parse_log(log)

    assert evidence["protocol"]["prompt_tokens_per_second"] == 188.7
    assert evidence["measurements"][0]["tokens_per_second"] == 34.5


def test_parser_extracts_wall_clock_time():
    evidence = parse_log(
        LOG + "timestamp_end_utc=2026-08-27T14:06:14Z\n"
    )

    assert evidence["provenance"]["wall_seconds"] == 5.86
    assert evidence["measurements"][0]["total_time_ms"] == 5860.0
