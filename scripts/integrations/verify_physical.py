#!/usr/bin/env python3
"""Physical installation verification for RC2 external stacks.

Read-only checks against the host. Never installs, never invents PASS.
`real_installation` is True only when stack-specific evidence is observed.

For ODS, Docker may be rootful and may require sudo for the current shell.
Podman is detected separately but is not treated as an ODS PASS unless a
Docker-compatible CLI/Compose interface is actually available.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

StackName = Literal["ods", "magnitude"]


@dataclass(frozen=True)
class PhysicalVerification:
    stack: str
    status: Literal["PASS", "FAIL"]
    real_installation: bool
    checks: dict[str, Any] = field(default_factory=dict)
    observed: dict[str, Any] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run(command: list[str], timeout: float = 8.0) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    text = (result.stdout or result.stderr or "").strip()
    first = text.splitlines()[0] if text else ""
    return result.returncode, first


def _which(name: str) -> str | None:
    return shutil.which(name)


def _docker_access() -> tuple[list[str] | None, str | None]:
    """Return the working Docker argv prefix and access mode."""
    if not _which("docker"):
        return None, None
    rc, _ = _run(["docker", "info"])
    if rc == 0:
        return ["docker"], "direct"
    if _which("sudo"):
        rc, _ = _run(["sudo", "docker", "info"])
        if rc == 0:
            return ["sudo", "docker"], "sudo"
    return None, None


def verify_magnitude() -> PhysicalVerification:
    path = _which("magnitude")
    version_rc, version = _run(["magnitude", "--version"]) if path else (1, "")
    checks = {
        "magnitude_in_path": path is not None,
        "magnitude_version_ok": version_rc == 0 and bool(version),
    }
    observed: dict[str, Any] = {}
    if path:
        observed["path"] = path
    if version_rc == 0 and version:
        observed["version"] = version

    missing = [name for name, ok in checks.items() if not ok]
    passed = not missing
    return PhysicalVerification(
        stack="magnitude",
        status="PASS" if passed else "FAIL",
        real_installation=passed,
        checks=checks,
        observed=observed,
        missing=missing,
        message=(
            "Magnitude is present and reports a version."
            if passed
            else "Magnitude is not physically verified on this host."
        ),
    )


def verify_ods() -> PhysicalVerification:
    docker_path = _which("docker")
    docker_cmd, docker_access = _docker_access()
    docker_rc, docker_version = _run(docker_cmd + ["--version"]) if docker_cmd else (1, "")
    compose_rc, compose_version = (
        _run(docker_cmd + ["compose", "version"]) if docker_cmd else (1, "")
    )

    podman_path = _which("podman")
    podman_rc, podman_version = _run(["podman", "--version"]) if podman_path else (1, "")
    podman_info_rc, _ = _run(["podman", "info"]) if podman_path else (1, "")

    # Prefer an explicit ODS CLI when upstream provides one.
    ods_path = _which("ods")
    ods_rc, ods_version = _run(["ods", "--version"]) if ods_path else (1, "")

    # Secondary observation: local Docker images whose name mentions ODS.
    images_rc, images_out = (1, "")
    ods_images: list[str] = []
    if docker_cmd and docker_rc == 0:
        images_rc, images_out = _run(
            docker_cmd + ["images", "--format", "{{.Repository}}:{{.Tag}}"],
            timeout=15.0,
        )
        if images_rc == 0:
            ods_images = [
                line.strip()
                for line in images_out.splitlines()
                if "ods" in line.lower()
            ][:10]

    checks = {
        "docker_in_path": docker_path is not None,
        "docker_accessible": docker_cmd is not None,
        "docker_version_ok": docker_rc == 0 and bool(docker_version),
        "docker_compose_ok": compose_rc == 0 and bool(compose_version),
        "ods_cli_or_image_observed": bool(ods_path and ods_rc == 0) or bool(ods_images),
    }
    observed: dict[str, Any] = {}
    if docker_path:
        observed["docker_path"] = docker_path
    if docker_access:
        observed["docker_access"] = docker_access
    if docker_rc == 0 and docker_version:
        observed["docker_version"] = docker_version
    if compose_rc == 0 and compose_version:
        observed["compose_version"] = compose_version
    if podman_path:
        observed["podman_path"] = podman_path
    if podman_rc == 0 and podman_version:
        observed["podman_version"] = podman_version
        observed["podman_accessible"] = podman_info_rc == 0
    if ods_path:
        observed["ods_path"] = ods_path
    if ods_rc == 0 and ods_version:
        observed["ods_version"] = ods_version
    if ods_images:
        observed["ods_docker_images"] = ods_images

    missing = [name for name, ok in checks.items() if not ok]
    passed = (
        checks["docker_in_path"]
        and checks["docker_accessible"]
        and checks["docker_version_ok"]
        and checks["docker_compose_ok"]
        and checks["ods_cli_or_image_observed"]
    )
    message = (
        "ODS toolchain and at least one ODS artifact were observed."
        if passed
        else "ODS is not physically verified on this host yet."
    )
    if not passed and podman_path and podman_info_rc == 0 and docker_cmd is None:
        message = (
            "Podman is available and working, but the current ODS installer "
            "requires a Docker-compatible CLI/Compose interface."
        )

    return PhysicalVerification(
        stack="ods",
        status="PASS" if passed else "FAIL",
        real_installation=passed,
        checks=checks,
        observed=observed,
        missing=missing,
        message=message,
    )


def verify_stack(stack: StackName | str) -> PhysicalVerification:
    name = str(stack).lower().strip()
    if name == "magnitude":
        return verify_magnitude()
    if name == "ods":
        return verify_ods()
    return PhysicalVerification(
        stack=name,
        status="FAIL",
        real_installation=False,
        missing=["unsupported_stack"],
        message=f"Unsupported stack for physical verification: {name}",
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="LEONES physical stack verification")
    parser.add_argument("stack", choices=("ods", "magnitude"))
    args = parser.parse_args()
    result = verify_stack(args.stack)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
