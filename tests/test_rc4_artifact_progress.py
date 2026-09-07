from pathlib import Path
from unittest.mock import patch

from scripts.artifact_acquirer import acquire_artifact
from runtime_selection.operation_progress import OperationPhase


class _Response:
    def __init__(self, payload: bytes):
        self.headers = {"Content-Length": str(len(payload))}
        self._payload = payload
        self._read = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        if self._read:
            return b""
        self._read = True
        return self._payload


def test_artifact_install_emits_preparing_download_verify_and_completed(tmp_path: Path):
    events = []
    payload = b"gguf-test-payload"

    with patch("scripts.artifact_acquirer.urllib.request.urlopen", return_value=_Response(payload)):
        result = acquire_artifact(
            url="https://example.test/model.gguf",
            cache_dir=tmp_path,
            model_id="example/model",
            quantization="Q4_K_M",
            progress_callback=events.append,
        )

    assert result["status"] == "ACQUIRED"
    phases = [event.phase for event in events]
    assert phases[0] is OperationPhase.PREPARING
    assert OperationPhase.DOWNLOADING in phases
    assert OperationPhase.VERIFYING in phases
    assert phases[-1] is OperationPhase.COMPLETED
    assert events[-1].operation == "install"


def test_artifact_cache_hit_still_emits_activity_and_terminal_state(tmp_path: Path):
    target = tmp_path / "model.gguf"
    target.write_bytes(b"cached")
    events = []

    result = acquire_artifact(
        url="https://example.test/model.gguf",
        cache_dir=tmp_path,
        model_id="example/model",
        quantization="Q4_K_M",
        progress_callback=events.append,
    )

    assert result["status"] == "CACHE_HIT"
    assert events[0].phase is OperationPhase.PREPARING
    assert events[-1].phase is OperationPhase.COMPLETED
