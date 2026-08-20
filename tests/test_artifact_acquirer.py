import hashlib
from pathlib import Path

from scripts.artifact_acquirer import acquire_artifact


def test_cache_hit_and_checksum(tmp_path: Path):
    payload = b"small test artifact"
    target = tmp_path / "model-Q4_K_M.gguf"
    target.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()

    result = acquire_artifact(
        url="https://huggingface.co/example/repo/resolve/main/model-Q4_K_M.gguf",
        cache_dir=tmp_path,
        model_id="example/repo",
        quantization="Q4_K_M",
        expected_sha256=digest,
    )
    assert result["status"] == "CACHE_HIT"
    assert result["sha256"] == digest


def test_bad_cached_checksum_is_rejected(tmp_path: Path):
    target = tmp_path / "model-Q4_K_M.gguf"
    target.write_bytes(b"wrong")
    result = acquire_artifact(
        url="https://huggingface.co/example/repo/resolve/main/model-Q4_K_M.gguf",
        cache_dir=tmp_path,
        model_id="example/repo",
        quantization="Q4_K_M",
        expected_sha256="0" * 64,
    )
    assert result["status"] == "CHECKSUM_MISMATCH"
