from pathlib import Path
import ast

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "harden_cafe_artifact.py"

def test_hardening_script_is_syntax_valid_and_fail_closed():
    ast.parse(SCRIPT.read_text())
    source = SCRIPT.read_text()
    assert "CAFE_LLAMA_RELEASE_SHA256" in source
    assert "sha256sum -c -" in source
    assert "file coreutils unzip" in source
    assert "expected one anchor" in source
    assert "536ec49ec1de5277578be976a5c161bb985857d5f8066e74889afff6c3f5920c" in source
    assert "https://github.com/quimmedes/cafe-llama.cpp/releases/download/0.75/llama-0.75-bin-linux-cuda-12.4-x64.tar.gz" in source
    assert "exact official release asset" in source
