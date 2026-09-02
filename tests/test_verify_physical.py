from scripts.integrations import verify_physical as vp


def test_magnitude_fail_when_binary_missing(monkeypatch):
    monkeypatch.setattr(vp, "_which", lambda name: None)
    result = vp.verify_magnitude()
    assert result.status == "FAIL"
    assert result.real_installation is False
    assert "magnitude_in_path" in result.missing


def test_magnitude_pass_when_path_and_version_ok(monkeypatch):
    monkeypatch.setattr(vp, "_which", lambda name: "/usr/bin/magnitude" if name == "magnitude" else None)
    monkeypatch.setattr(vp, "_run", lambda cmd, timeout=8.0: (0, "magnitude 0.1.0"))
    result = vp.verify_magnitude()
    assert result.status == "PASS"
    assert result.real_installation is True
    assert result.observed["version"] == "magnitude 0.1.0"


def test_ods_requires_ods_specific_evidence(monkeypatch):
    def which(name):
        return "/usr/bin/docker" if name == "docker" else None

    def run(cmd, timeout=8.0):
        if cmd[:2] == ["docker", "--version"]:
            return 0, "Docker version 27.0.0"
        if cmd[:3] == ["docker", "compose", "version"]:
            return 0, "Docker Compose version v2.0.0"
        return 1, ""

    monkeypatch.setattr(vp, "_which", which)
    monkeypatch.setattr(vp, "_run", run)
    # No ODS CLI and no ODS images -> FAIL even with healthy docker.
    monkeypatch.setattr(
        vp.subprocess,
        "run",
        lambda *a, **k: type("R", (), {"returncode": 0, "stdout": "ubuntu:latest\n", "stderr": ""})(),
    )
    result = vp.verify_ods()
    assert result.status == "FAIL"
    assert result.real_installation is False
    assert "ods_cli_or_image_observed" in result.missing


def test_ods_pass_with_cli(monkeypatch):
    def which(name):
        if name == "docker":
            return "/usr/bin/docker"
        if name == "ods":
            return "/usr/local/bin/ods"
        return None

    def run(cmd, timeout=8.0):
        if cmd[:2] == ["docker", "--version"]:
            return 0, "Docker version 27.0.0"
        if cmd[:3] == ["docker", "compose", "version"]:
            return 0, "Docker Compose version v2.0.0"
        if cmd[:2] == ["ods", "--version"]:
            return 0, "ods 1.0.0"
        return 1, ""

    monkeypatch.setattr(vp, "_which", which)
    monkeypatch.setattr(vp, "_run", run)
    result = vp.verify_ods()
    assert result.status == "PASS"
    assert result.real_installation is True
    assert result.observed["ods_version"] == "ods 1.0.0"
