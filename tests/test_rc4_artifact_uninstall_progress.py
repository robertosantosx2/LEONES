from pathlib import Path

from scripts.artifact_acquirer import remove_artifact
from runtime_selection.operation_progress import OperationPhase


def test_artifact_uninstall_emits_removing_and_completed(tmp_path: Path):
    target = tmp_path / "model.gguf"
    metadata = tmp_path / "model.gguf.leones.json"
    target.write_bytes(b"cached")
    metadata.write_text("{}", encoding="utf-8")
    events = []

    result = remove_artifact(
        cache_dir=tmp_path,
        filename="model.gguf",
        progress_callback=events.append,
    )

    assert result["status"] == "REMOVED"
    assert not target.exists()
    assert not metadata.exists()
    assert events[0].phase is OperationPhase.PREPARING
    assert any(event.phase is OperationPhase.REMOVING for event in events)
    assert events[-1].phase is OperationPhase.COMPLETED
    assert events[-1].operation == "uninstall"


def test_artifact_uninstall_absent_is_still_explicit(tmp_path: Path):
    events = []
    result = remove_artifact(
        cache_dir=tmp_path,
        filename="missing.gguf",
        progress_callback=events.append,
    )
    assert result["status"] == "ABSENT"
    assert events[-1].phase is OperationPhase.COMPLETED
