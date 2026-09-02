#!/usr/bin/env python3
"""Read-only ODS preflight for LEONES.

The script deliberately does not install anything and does not contact ODS.
It detects Docker/Podman without assuming that Docker must be rootless.

ODS currently consumes a Docker-compatible CLI/Compose contract.  Podman is
therefore detected explicitly on Fedora/RHEL-family hosts, but is not silently
reported as an ODS-compatible runtime unless a Docker-compatible command is
actually available.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess


def run_command(command: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    text = (result.stdout or result.stderr).strip()
    return result.returncode, text


def command_version(command: list[str]) -> str | None:
    rc, text = run_command(command)
    if rc != 0:
        return None
    lines = text.splitlines()
    return lines[0] if lines else None


def working_command(command: list[str]) -> bool:
    rc, _ = run_command(command)
    return rc == 0


def ram_gb() -> float | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / (1024**3), 2)
    except (AttributeError, OSError, ValueError):
        return None


def detect_container_runtime() -> dict[str, object]:
    docker = shutil.which("docker")
    podman = shutil.which("podman")

    docker_direct = bool(docker and working_command(["docker", "info"]))
    docker_sudo = bool(
        docker
        and shutil.which("sudo")
        and working_command(["sudo", "docker", "info"])
    )
    podman_direct = bool(podman and working_command(["podman", "info"]))

    if docker_direct:
        runtime = "docker"
        command = "docker"
        access = "direct"
    elif docker_sudo:
        runtime = "docker"
        command = "sudo docker"
        access = "sudo"
    elif podman_direct:
        runtime = "podman"
        command = "podman"
        access = "direct"
    else:
        runtime = "none"
        command = None
        access = None

    rootless: bool | None = None
    rootless_source = None
    if runtime == "docker":
        # Docker's canonical signal.  With sudo, query through the same access
        # path that the installer will use.
        prefix = ["sudo", "docker"] if access == "sudo" else ["docker"]
        rc, text = run_command(prefix + ["info", "--format", "{{json .SecurityOptions}}"])
        if rc == 0 and text:
            rootless = "rootless" in text.lower()
            rootless_source = "docker.security_options"
        else:
            # Podman's docker-compatible shim exposes this field instead.
            rc, text = run_command(prefix + ["info", "--format", "{{.Host.Security.Rootless}}"])
            if rc == 0 and text.lower() in {"true", "false"}:
                rootless = text.lower() == "true"
                rootless_source = "docker.host.security.rootless"
    elif runtime == "podman":
        rc, text = run_command(["podman", "info", "--format", "{{.Host.Security.Rootless}}"])
        if rc == 0 and text.lower() in {"true", "false"}:
            rootless = text.lower() == "true"
            rootless_source = "podman.host.security.rootless"

    compose = None
    compose_version = None
    if runtime == "docker":
        prefix = ["sudo", "docker"] if access == "sudo" else ["docker"]
        if working_command(prefix + ["compose", "version"]):
            compose = "docker compose"
            compose_version = command_version(prefix + ["compose", "version"])
        elif shutil.which("docker-compose"):
            compose = "sudo docker-compose" if access == "sudo" else "docker-compose"
            compose_version = command_version(
                ["sudo", "docker-compose", "version"] if access == "sudo" else ["docker-compose", "version"]
            )
    elif runtime == "podman":
        if working_command(["podman", "compose", "version"]):
            compose = "podman compose"
            compose_version = command_version(["podman", "compose", "version"])
        elif shutil.which("podman-compose"):
            compose = "podman-compose"
            compose_version = command_version(["podman-compose", "version"])

    return {
        "runtime": runtime,
        "command": command,
        "access": access,
        "rootless": rootless,
        "rootless_source": rootless_source,
        "docker_path": docker,
        "podman_path": podman,
        "docker_direct": docker_direct,
        "docker_sudo": docker_sudo,
        "podman_direct": podman_direct,
        "compose": compose,
        "compose_version": compose_version,
        # ODS's current Linux installer is Docker/Compose based.  Podman is
        # evidence for host capability, not a false ODS PASS.
        "ods_container_compatible": runtime == "docker" and compose is not None,
    }


def main() -> None:
    runtime = detect_container_runtime()
    payload = {
        "profile": "ods-server",
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or "unknown",
        "ram_gb": ram_gb(),
        "container_runtime": runtime,
        "docker": command_version(["docker", "--version"]) if shutil.which("docker") else None,
        "docker_compose": runtime.get("compose_version"),
        "podman": command_version(["podman", "--version"]) if shutil.which("podman") else None,
        "nvidia_smi": command_version(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"]
        ),
        "git": shutil.which("git") is not None,
        "curl": shutil.which("curl") is not None,
        "ready": bool(runtime.get("ods_container_compatible")),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
