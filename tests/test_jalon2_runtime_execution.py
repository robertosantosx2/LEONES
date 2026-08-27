from pathlib import Path

from scripts.jalon2_runtime_execution import SCHEMA, sha256_file


def test_runtime_execution_schema_identifier():
    schema = Path("schemas/runtime-execution.v1.schema.json").read_text(
        encoding="utf-8"
    )
    assert '"const": "runtime-execution.v1"' in schema
    assert SCHEMA == "runtime-execution.v1"


def test_sha256_is_real_file_hash(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"LEONES-runtime-execution-v1")

    digest = sha256_file(artifact)

    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_detect_cpu_model_from_lscpu():
    from scripts.jalon2_runtime_execution import detect_cpu_model

    cpu = detect_cpu_model()

    assert cpu
    assert cpu != "unknown"
