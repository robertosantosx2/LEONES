#!/usr/bin/env python3
"""Validate that the engine registry and benchmark adapters remain in sync."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def fail(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    raise SystemExit(1)

def main() -> None:
    registry = json.loads((ROOT / "configs/engines.registry.json").read_text())
    config = json.loads((ROOT / "configs/engine-comparison.example.json").read_text())
    registry_entries = registry.get("engines", [])
    config_entries = config.get("engines", [])
    registry_ids = [e.get("id") for e in registry_entries]
    config_ids = [e.get("id") for e in config_entries]
    if len(registry_ids) != len(set(registry_ids)) or None in registry_ids:
        fail("registry engine IDs must be present and unique")
    if len(config_ids) != len(set(config_ids)) or None in config_ids:
        fail("benchmark engine IDs must be present and unique")
    if set(registry_ids) != set(config_ids):
        fail(f"registry/config IDs differ; missing config={sorted(set(registry_ids)-set(config_ids))}, unregistered config={sorted(set(config_ids)-set(registry_ids))}")
    profile_names = {p.get("name") for p in config.get("profiles", [])}
    by_id = {e["id"]: e for e in registry_entries}
    for source in registry_entries:
        eid = source["id"]
        meta_path = ROOT / "third_party" / "engines" / eid / "SOURCE.json"
        if not meta_path.is_file():
            fail(f"{eid}: vendored SOURCE.json is missing")
        meta = json.loads(meta_path.read_text())
        commit = meta.get("commit", "")
        tree = meta.get("git_commit_tree", "")
        if meta.get("engine_id") != eid or meta.get("repository") != source.get("repository"):
            fail(f"{eid}: SOURCE.json identity/repository does not match registry")
        if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit.lower()):
            fail(f"{eid}: SOURCE.json does not contain a full commit SHA")
        if len(tree) != 40 or any(ch not in "0123456789abcdef" for ch in tree.lower()):
            fail(f"{eid}: SOURCE.json does not contain a full Git tree SHA")
        source_tree = meta.get("source_tree", "")
        if not source_tree.startswith("source/") or ".." in pathlib.PurePosixPath(source_tree).parts:
            fail(f"{eid}: invalid source_tree path in SOURCE.json")
        if not (meta_path.parent / source_tree).is_dir():
            fail(f"{eid}: vendored source tree is missing")
        for notice in meta.get("license_files", []):
            if not (meta_path.parent / source_tree / notice).is_file():
                fail(f"{eid}: declared license/notice file is missing: {notice}")
    for engine in config_entries:
        eid = engine["id"]
        if not isinstance(engine.get("command"), list) or not engine["command"] or not all(isinstance(x, str) for x in engine["command"]):
            fail(f"{eid}: command must be a non-empty argv list")
        unknown = set(engine.get("profiles", [])) - profile_names
        if unknown:
            fail(f"{eid}: unknown profile names {sorted(unknown)}")
        expected_source = f"third_party/engines/{eid}/SOURCE.json"
        if engine.get("source_meta") != expected_source:
            fail(f"{eid}: source_meta must be {expected_source}")
        expected_build = f"artifacts/engine-builds/{eid}/build.json"
        if engine.get("build_meta") != expected_build:
            fail(f"{eid}: build_meta must be {expected_build}")
        if engine.get("enabled") and any("/ABS/PATH/" in arg for arg in engine["command"]):
            fail(f"{eid}: enabled engine still has a placeholder executable path")
    tandem = by_id.get("tandem-cpp", {})
    base_id = tandem.get("tandem_base_engine")
    base = by_id.get(base_id)
    if not base or base.get("default_ref") != tandem.get("tandem_base_commit"):
        fail("Tandem.cpp must reference a separately registered exact llama.cpp base commit")
    if len(tandem.get("tandem_base_commit", "")) != 40:
        fail("Tandem.cpp base commit must be a full 40-character SHA")
    tandem_cfg = next(e for e in config_entries if e["id"] == "tandem-cpp")
    required = {"-ngl", "-cmoe", "--moe-cache-mib", "--cache-ram"}
    if not required.issubset(set(tandem_cfg["command"])):
        fail("Tandem.cpp command is missing its documented MoE/cache flags")
    print(f"[OK] {len(registry_ids)} registry engines match {len(config_ids)} adapters; all source snapshots, license notices, profiles and Tandem base checks passed")

if __name__ == "__main__":
    main()
