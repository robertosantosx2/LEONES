from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "harden_cafe_artifact.py"
spec = spec_from_file_location("harden_cafe_artifact", SCRIPT)
patcher = module_from_spec(spec)
spec.loader.exec_module(patcher)


def test_patcher_transforms_candidate_artifact_contract(tmp_path, monkeypatch):
    root = tmp_path / "ods-src/ods/extensions/library/services/cafe-llama"
    root.mkdir(parents=True)
    dockerfile = root / "Dockerfile"
    compose = root / "compose.yaml"
    dockerfile.write_text(
        "FROM ubuntu:24.04\n"
        + patcher.OLD_INSTALL
        + "\n"
        + patcher.OLD_BLOCK_START
        + "\nRUN curl -fsSL \\\n    -o /tmp/cafe-asset\n"
        + patcher.OLD_BLOCK_END
        + "\n"
    )
    compose.write_text(
        "services:\n  cafe-llama:\n    build:\n      args:\n"
        + patcher.OLD_INSTALL.replace("RUN apt-get update \\\n && apt-get install -y --no-install-recommends ca-certificates curl tar \\\n && rm -rf /var/lib/apt/lists/*", "")
        + patcher.OLD_BLOCK_START.replace("ARG ", "        CAFE_LLAMA_RELEASE_URL: ")
        + "\n"
        + "        CAFE_LLAMA_RELEASE_URL: ${CAFE_LLAMA_RELEASE_URL:-}\n"
    )
    monkeypatch.setattr(patcher, "ROOT", root)
    monkeypatch.setattr(patcher, "DOCKERFILE", dockerfile)
    monkeypatch.setattr(patcher, "COMPOSE", compose)

    patcher.main()

    docker = dockerfile.read_text()
    compose_text = compose.read_text()
    assert "file coreutils unzip libgomp1" in docker
    assert "FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04" in docker
    assert "sha256sum -c -" in docker
    assert 'file --mime-type -b /tmp/cafe-asset' in docker
    assert '= "application/zip"' in docker
    assert 'test "${#CAFE_LLAMA_RELEASE_SHA256}" -eq 64' in docker
    assert "/usr/local/bin/llama-server --version" in docker
    assert "/etc/ld.so.conf.d/cafe-llama.conf" in docker
    assert "ldconfig" in docker
    assert 'org.osmantic.cafe.artifact-sha256="${CAFE_LLAMA_RELEASE_SHA256}"' in docker
    assert 'org.osmantic.cafe.build-id="${CAFE_LLAMA_BUILD_ID}"' in docker
    label_lines = [
        line for line in docker.splitlines()
        if line.lstrip().startswith((
            "LABEL org.osmantic.cafe.build-id=",
            "org.osmantic.cafe.artifact-sha256=",
            "org.osmantic.cafe.architecture=",
        ))
    ]
    assert len(label_lines) == 3
    assert all(len(line) - len(line.rstrip(chr(92))) == 1 for line in label_lines)
    assert "CAFE_LLAMA_ARCHITECTURE: ${CAFE_LLAMA_ARCHITECTURE:-linux-x64}" in compose_text
    assert "CAFE_LLAMA_BACKEND: ${CAFE_LLAMA_BACKEND:-cuda-12.4}" in compose_text
    assert "CAFE_LLAMA_RELEASE_SHA256: ${CAFE_LLAMA_RELEASE_SHA256:-536ec49ec1de5277578be976a5c161bb985857d5f8066e74889afff6c3f5920c}" in compose_text
    assert "https://github.com/quimmedes/cafe-llama.cpp/releases/download/0.75/llama-0.75-bin-linux-cuda-12.4-x64.tar.gz" in compose_text
    assert '536ec49ec1de5277578be976a5c161bb985857d5f8066e74889afff6c3f5920c' in docker


def test_patcher_fails_closed_when_expected_anchors_move(tmp_path, monkeypatch):
    root = tmp_path / "ods-src/ods/extensions/library/services/cafe-llama"
    root.mkdir(parents=True)
    dockerfile = root / "Dockerfile"
    compose = root / "compose.yaml"
    dockerfile.write_text("FROM ubuntu:24.04\n# changed upstream layout\n")
    compose.write_text("services: {}\n")
    monkeypatch.setattr(patcher, "ROOT", root)
    monkeypatch.setattr(patcher, "DOCKERFILE", dockerfile)
    monkeypatch.setattr(patcher, "COMPOSE", compose)

    try:
        patcher.main()
    except SystemExit as exc:
        assert "expected one anchor" in str(exc)
    else:
        raise AssertionError("patcher must fail closed when the Dockerfile anchor moves")
