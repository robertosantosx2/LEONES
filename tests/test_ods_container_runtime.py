from unittest.mock import patch

from scripts.integrations import ods_preflight
from scripts.integrations import verify_physical


def test_preflight_accepts_rootful_docker_without_rootless_detection():
    def run(command, timeout=5):
        cmd = tuple(command)
        if cmd == ("docker", "info"):
            return 0, "info"
        if cmd == ("docker", "info", "--format", "{{json .SecurityOptions}}"):
            return 0, '["name=seccomp"]'
        if cmd == ("docker", "compose", "version"):
            return 0, "Docker Compose version v2"
        return 1, ""

    with patch.object(ods_preflight.shutil, "which", side_effect=lambda n: "/usr/bin/" + n if n == "docker" else None), patch.object(
        ods_preflight, "run_command", side_effect=run
    ):
        result = ods_preflight.detect_container_runtime()

    assert result["runtime"] == "docker"
    assert result["access"] == "direct"
    assert result["rootless"] is False
    assert result["compose"] == "docker compose"
    assert result["ods_container_compatible"] is True


def test_preflight_recognizes_podman_without_falsely_claiming_ods_compatibility():
    def run(command, timeout=5):
        cmd = tuple(command)
        if cmd == ("podman", "info"):
            return 0, "info"
        if cmd == ("podman", "info", "--format", "{{.Host.Security.Rootless}}"):
            return 0, "true"
        return 1, ""

    with patch.object(ods_preflight.shutil, "which", side_effect=lambda n: "/usr/bin/" + n if n == "podman" else None), patch.object(
        ods_preflight, "run_command", side_effect=run
    ):
        result = ods_preflight.detect_container_runtime()

    assert result["runtime"] == "podman"
    assert result["rootless"] is True
    assert result["ods_container_compatible"] is False


def test_physical_verification_accepts_sudo_docker():
    with patch.object(verify_physical, "_which", side_effect=lambda n: "/usr/bin/" + n if n in {"docker", "sudo"} else None), patch.object(
        verify_physical, "_run", side_effect=lambda command, timeout=8.0: (
            (0, "Docker version 29") if command[-1] == "--version" else
            (0, "Docker Compose version v2") if command[-2:] == ["compose", "version"] else
            (0, "") if command[-1] == "info" else
            (0, "ods:latest") if command[-1] == "{{.Repository}}:{{.Tag}}" else
            (1, "")
        )
    ):
        result = verify_physical.verify_ods()

    assert result.status == "PASS"
    assert result.real_installation is True
    assert result.observed["docker_access"] == "sudo"
