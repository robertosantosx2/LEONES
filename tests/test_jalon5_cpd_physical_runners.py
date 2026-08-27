from scripts.runtimes.run_sglang_physical import build_command as sglang_command
from scripts.runtimes.run_sglang_physical import build_request as sglang_request
from scripts.runtimes.run_vllm_physical import build_command as vllm_command
from scripts.runtimes.run_vllm_physical import build_request as vllm_request


def test_vllm_runner_is_cpd_gated():
    assert vllm_command("model", "127.0.0.1", 8000)[:2] == ["vllm", "serve"]
    assert vllm_command("model", "127.0.0.1", 8000)[-2:] == ["--tensor-parallel-size", "1"]


def test_sglang_runner_is_cpd_gated():
    assert sglang_command("model", "127.0.0.1", 30000)[:3] == ["python", "-m", "sglang.launch_server"]
    assert "--tp-size" in sglang_command("model", "127.0.0.1", 30000)


def test_requests_share_measurement_shape():
    assert vllm_request("m", "p", 128, 0.0, 1.0) == sglang_request("m", "p", 128, 0.0, 1.0)
