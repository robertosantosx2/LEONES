"""Fail-closed adapter prototype for the optional cafe-llama runtime.

This module is staged against the current ODS Model Switchboard adapter
contract. It intentionally does not select cafe by itself: the host agent must
construct it only after explicit runtime selection, and keep llama-server as
the default. Artifact and running-build provenance are mandatory.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from .adapters import ContainerLlamaAdapter, result


_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class CafeLlamaAdapter(ContainerLlamaAdapter):
    """Compose-managed cafe-llama runtime with pinned artifact/build proof.

    `inspect_artifact` must inspect the installed artifact manifest, not merely
    echo environment variables. `probe_runtime_build` must query the running
    process/container's reported build identity. The activation transaction
    still owns snapshots, route publication and rollback orchestration.
    """

    kind = "cafe-llama"

    def __init__(
        self,
        *,
        restart: Callable[[dict[str, str]], None],
        wait_ready: Callable[[dict[str, str], str, int], dict[str, Any]],
        expected_gguf: str,
        context_length: int,
        expected_build_id: str,
        expected_sha256: str,
        architecture: str,
        backend: str,
        inspect_artifact: Callable[[], dict[str, Any]],
        probe_runtime_build: Callable[[dict[str, str]], dict[str, Any]],
        capabilities: dict[str, bool] | None = None,
        rollback: Callable[[dict[str, str]], None] | None = None,
    ) -> None:
        super().__init__(
            restart=restart,
            wait_ready=wait_ready,
            expected_gguf=expected_gguf,
            context_length=context_length,
            capabilities=capabilities,
            rollback=rollback,
        )
        if not expected_build_id.strip():
            raise ValueError("expected cafe build identity is required")
        if not _SHA256_RE.fullmatch(expected_sha256):
            raise ValueError("expected cafe artifact SHA-256 must be 64 lowercase hex characters")
        if not architecture.strip() or not backend.strip():
            raise ValueError("cafe architecture and backend must be explicit")
        self._expected_build_id = expected_build_id.strip()
        self._expected_sha256 = expected_sha256
        self._architecture = architecture.strip().lower()
        self._backend = backend.strip().lower()
        self._inspect_artifact = inspect_artifact
        self._probe_runtime_build = probe_runtime_build
        self._artifact_verified = False
        self._running_build_verified = False

    def stage(self, env: dict[str, str]) -> dict[str, Any]:
        try:
            artifact = self._inspect_artifact()
        except Exception as exc:
            return result(False, f"cafe artifact inspection failed: {exc}")
        if not isinstance(artifact, dict):
            return result(False, "cafe artifact inspection returned no manifest")
        checks = {
            "build_id": self._expected_build_id,
            "sha256": self._expected_sha256,
            "architecture": self._architecture,
            "backend": self._backend,
        }
        for key, expected in checks.items():
            actual = artifact.get(key)
            if not isinstance(actual, str) or actual.strip().lower() != expected.lower():
                return result(False, f"cafe artifact {key} does not match the pinned runtime profile")
        self._artifact_verified = True
        staged = super().stage(env)
        if not staged.get("ok"):
            self._artifact_verified = False
        return staged

    def verify_identity(self, env: dict[str, str]) -> dict[str, Any]:
        if not self._artifact_verified:
            return result(False, "cafe artifact provenance was not verified before startup")
        identity = super().verify_identity(env)
        if not identity.get("ok"):
            return identity
        try:
            running = self._probe_runtime_build(env)
        except Exception as exc:
            return result(False, f"cafe running-build probe failed: {exc}")
        if not isinstance(running, dict):
            return result(False, "cafe running-build probe returned no proof")
        build_id = running.get("build_id")
        artifact_sha256 = running.get("artifact_sha256")
        if build_id != self._expected_build_id:
            return result(False, "running cafe build identity does not match pinned build")
        if artifact_sha256 != self._expected_sha256:
            return result(False, "running cafe artifact digest does not match pinned artifact")
        self._running_build_verified = True
        identity.update(
            runtimeBuildId=build_id,
            artifactSha256=artifact_sha256,
            runtimeKind=self.kind,
        )
        return identity

    def verify_completion(self, env: dict[str, str]) -> dict[str, Any]:
        if not self._running_build_verified:
            return result(False, "cafe running-build provenance was not verified")
        completion = super().verify_completion(env)
        if completion.get("ok"):
            completion.update(
                runtimeBuildId=self._expected_build_id,
                artifactSha256=self._expected_sha256,
                runtimeKind=self.kind,
            )
        return completion


__all__ = ["CafeLlamaAdapter"]
