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
    assert "does not invent a digest" in source
