from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

# The workflow overlays the staged adapter onto a fresh checkout of ODS main.
ODS_BIN = Path(__file__).resolve().parents[3] / "ods-src" / "ods" / "bin"
if ODS_BIN.exists():
    sys.path.insert(0, str(ODS_BIN))

from model_switchboard.cafe_adapter import CafeLlamaAdapter
from model_switchboard.reconciler import run_runtime_activation


BUILD_ID = "cafe-llama-0.75-linux-x64-cuda12.4"
DIGEST = "536ec49ec1de5277578be976a5c161bb985857d5f8066e74889afff6c3f5920c"
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def adapter(*, artifact=None, running=None, restart_calls=None, plan=None):
    artifact = artifact or {
        "build_id": BUILD_ID, "sha256": DIGEST,
        "architecture": "linux-x64", "backend": "cuda-12.4",
    }
    running = running or {"build_id": BUILD_ID, "artifact_sha256": DIGEST}
    restart_calls = restart_calls if restart_calls is not None else []
    plan = plan or {}

    def wait_ready(env, expected_gguf, context_length, **kwargs):
        return {
            "identity": "model.gguf", "contextLength": context_length,
            "contextVerified": True,
            "capabilities": {"chat": True, "tools": False, "vision": False, "agentViable": False},
            "verifiedAt": NOW,
        }

    return CafeLlamaAdapter(
        restart=lambda env: restart_calls.append("restart"),
        wait_ready=wait_ready,
        expected_gguf="model.gguf",
        context_length=8192,
        expected_build_id=BUILD_ID,
        expected_sha256=DIGEST,
        architecture="linux-x64",
        backend="cuda-12.4",
        inspect_artifact=lambda: artifact,
        probe_runtime_build=lambda env: running,
        rollback=lambda env: None,
    ), restart_calls


def test_cafe_activation_requires_pinned_artifact_and_running_build_proof():
    runtime, calls = adapter()
    result = run_runtime_activation(runtime, {"ODS_INFERENCE_RUNTIME": "cafe-llama"})
    assert result["ok"] is True
    assert calls == ["restart"]
    # The adapter proves artifact/runtime provenance in its own identity result;
    # the host-agent publisher still must persist this proof in model-state.
    assert runtime.verify_identity({"ODS_INFERENCE_RUNTIME": "cafe-llama"})["runtimeKind"] == "cafe-llama"


@pytest.mark.parametrize("field,value", [
    ("sha256", "0" * 64),
    ("build_id", "untrusted-build"),
    ("architecture", "linux-arm64"),
    ("backend", "vulkan"),
])
def test_bad_artifact_manifest_fails_before_restart(field, value):
    manifest = {
        "build_id": BUILD_ID, "sha256": DIGEST,
        "architecture": "linux-x64", "backend": "cuda-12.4",
    }
    manifest[field] = value
    runtime, calls = adapter(artifact=manifest)
    staged = runtime.stage({})
    assert staged["ok"] is False
    assert calls == []


@pytest.mark.parametrize("running", [
    {"build_id": "different-build", "artifact_sha256": DIGEST},
    {"build_id": BUILD_ID, "artifact_sha256": "0" * 64},
    {},
])
def test_running_process_must_prove_same_build_and_digest(running):
    runtime, calls = adapter(running=running)
    assert runtime.stage({})["ok"] is True
    identity = runtime.verify_identity({})
    assert identity["ok"] is False
    assert "build" in identity["detail"] or "digest" in identity["detail"] or "provenance" in identity["detail"]


def test_completion_is_rejected_until_running_build_has_been_verified():
    runtime, _ = adapter()
    completion = runtime.verify_completion({})
    assert completion["ok"] is False
    assert "provenance" in completion["detail"]


def test_invalid_expected_digest_is_rejected_at_construction():
    with pytest.raises(ValueError, match="SHA-256"):
        runtime, _ = adapter()
        CafeLlamaAdapter(
            restart=lambda env: None,
            wait_ready=lambda env, model, context: {},
            expected_gguf="model.gguf", context_length=8192,
            expected_build_id=BUILD_ID, expected_sha256="not-a-hash",
            architecture="linux-x64", backend="cuda-12.4",
            inspect_artifact=lambda: {}, probe_runtime_build=lambda env: {},
        )
