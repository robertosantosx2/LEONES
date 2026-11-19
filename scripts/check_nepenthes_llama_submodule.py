#!/usr/bin/env python3
"""Validate the NEPENTHES llama.cpp submodule pointer and its provenance."""
from __future__ import annotations

import configparser
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUBMODULE_PATH = "subprojects/llama.cpp"
EXPECTED_URL = "https://github.com/robertosantosx2/llama.cpp.git"
MANIFEST_PATH = ROOT / "docs/subprojects/NEPENTHES/LLAMA-CPP-UPSTREAM.json"


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def validate_manifest(manifest: dict[str, Any], gitlink_sha: str) -> None:
    """Keep the reviewed submodule pin independent from the moving fork master."""
    if manifest.get("local_fork_repository") != EXPECTED_URL:
        raise ValueError("manifest local_fork_repository does not match the expected fork")
    if manifest.get("leones_submodule_path") != SUBMODULE_PATH:
        raise ValueError("manifest leones_submodule_path does not match the gitlink path")
    if manifest.get("leones_submodule_commit") != gitlink_sha:
        raise ValueError("manifest leones_submodule_commit does not match the gitlink")
    fork_head = manifest.get("fork_head_commit")
    if not isinstance(fork_head, str) or re.fullmatch(r"[0-9a-f]{40}", fork_head) is None:
        raise ValueError("manifest fork_head_commit must be a full 40-character commit SHA")
    if not isinstance(manifest.get("local_fork_status"), str) or not manifest["local_fork_status"]:
        raise ValueError("manifest local_fork_status must be a non-empty string")


def main() -> int:
    config = configparser.ConfigParser()
    config.read(ROOT / ".gitmodules")
    section = 'submodule "subprojects/llama.cpp"'
    assert config.has_section(section), "missing llama.cpp submodule section"
    assert config.get(section, "path") == SUBMODULE_PATH, "wrong submodule path"
    assert config.get(section, "url") == EXPECTED_URL, "wrong fork URL"

    tree_entry = git("ls-tree", "HEAD", "--", SUBMODULE_PATH).split()
    assert len(tree_entry) == 4, "submodule gitlink missing from HEAD"
    mode, object_type, gitlink_sha, _ = tree_entry
    assert mode == "160000" and object_type == "commit", "path is not a gitlink"

    checkout = ROOT / SUBMODULE_PATH
    checkout_sha = git("rev-parse", "HEAD", cwd=checkout)
    assert checkout_sha == gitlink_sha, "checked-out submodule does not match gitlink"
    origin = git("remote", "get-url", "origin", cwd=checkout)
    assert origin.rstrip("/") == EXPECTED_URL, f"unexpected submodule origin: {origin}"

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_manifest(manifest, gitlink_sha)

    print(f"llama.cpp submodule OK: {gitlink_sha}")
    print(f"fork master observed at: {manifest['fork_head_commit']}")
    print(f"origin OK: {origin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
