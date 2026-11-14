#!/usr/bin/env python3
"""Copy NEPENTHES experiment evidence into LEONES without altering source files.

Only evidence/configuration files are collected. Model weights, checkpoints,
build outputs, caches and symlinks are excluded. Existing archive runs are
never overwritten; each invocation creates a timestamped directory.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

DEFAULT_ROOTS = (
    "NEPENTHES_TANDEM_QWEN35_20261113_pilot",
    "NEPENTHES_TANDEM_QWEN35_20261113_full",
    "NEPENTHES_QWEN35_CORRELATED_20261114",
    "NEPENTHES_CUDA_TOOLING_20261114",
)
EVIDENCE_SUFFIXES = {
    ".py", ".sh", ".log", ".txt", ".json", ".jsonl", ".sqlite", ".db",
    ".nsys-rep", ".qdrep", ".qdstrm", ".ncu-rep", ".csv", ".tsv",
    ".md", ".yaml", ".yml", ".xml", ".html", ".out", ".err", ".trace",
    ".prof", ".dat",
}
EXCLUDED_SUFFIXES = {
    ".gguf", ".safetensors", ".pt", ".pth", ".onnx", ".model",
    ".so", ".a", ".o", ".pyc", ".whl", ".deb", ".rpm",
}
EXCLUDED_DIRS = {
    ".git", "__pycache__", "node_modules", ".cache", "huggingface",
    "hub", "models", "checkpoints", "build", "dist", "target",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_files(root: Path):
    if root.is_file():
        if root.is_symlink():
            return
        if root.name.lower().endswith(".tar.gz") or root.suffix.lower() in EVIDENCE_SUFFIXES:
            yield root, Path(root.name)
        return
    if not root.is_dir():
        return
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        dirs[:] = [
            name for name in dirs
            if name not in EXCLUDED_DIRS and not (current_path / name).is_symlink()
        ]
        for name in sorted(files):
            path = current_path / name
            if path.is_symlink():
                continue
            lower = name.lower()
            if lower.endswith(".tar.gz") or path.suffix.lower() in EVIDENCE_SUFFIXES:
                if path.suffix.lower() not in EXCLUDED_SUFFIXES:
                    yield path, path.relative_to(root)


def collect_archive(
    home: Path,
    repo_root: Path,
    roots: list[Path],
    archive_parent: Path,
    timestamp: str,
) -> dict:
    run_dir = archive_parent / timestamp
    if run_dir.exists():
        raise FileExistsError(f"Archive run already exists; refusing to overwrite: {run_dir}")
    run_dir.mkdir(parents=True)
    entries = []
    missing = []
    seen_hashes = {}

    for index, source in enumerate(roots):
        source = source.expanduser().resolve()
        if not source.exists():
            missing.append({"source": str(source), "status": "missing"})
            continue
        label = (source.parent.name if source.is_file() else source.name) or f"source-{index + 1}"
        if any(item["label"] == label for item in entries):
            label = f"{label}-{index + 1}"
        for original, relative in evidence_files(source):
            digest = sha256_file(original)
            if digest in seen_hashes:
                entries.append({
                    "source": str(original),
                    "archive_path": seen_hashes[digest],
                    "sha256": digest,
                    "size_bytes": original.stat().st_size,
                    "status": "duplicate_content",
                })
                continue
            target_rel = Path(label) / relative
            target = run_dir / target_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
            # Verify the copied bytes before recording the archive entry.
            copied_digest = sha256_file(target)
            if copied_digest != digest:
                raise IOError(f"SHA-256 mismatch after copy: {original}")
            archive_path = target.relative_to(run_dir).as_posix()
            seen_hashes[digest] = archive_path
            entries.append({
                "source": str(original),
                "archive_path": archive_path,
                "sha256": digest,
                "size_bytes": target.stat().st_size,
                "status": "copied",
            })

    manifest = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_roots": [str(p.expanduser()) for p in roots],
        "archive_directory": str(run_dir),
        "source_files": len(entries),
        "copied_files": sum(x["status"] == "copied" for x in entries),
        "duplicate_files": sum(x["status"] == "duplicate_content" for x in entries),
        "total_copied_bytes": sum(x["size_bytes"] for x in entries if x["status"] == "copied"),
        "missing_roots": missing,
        "excluded": {
            "model_and_checkpoint_suffixes": sorted(EXCLUDED_SUFFIXES),
            "directory_names": sorted(EXCLUDED_DIRS),
            "symlinks": True,
        },
        "files": entries,
    }
    (run_dir / "ARCHIVE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    sums = [
        f"{item['sha256']}  {item['archive_path']}"
        for item in entries if item["status"] == "copied"
    ]
    (run_dir / "SHA256SUMS").write_text("\n".join(sums) + ("\n" if sums else ""), encoding="utf-8")
    return manifest


def find_repo_root(path: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        check=True, capture_output=True, text=True,
    )
    return Path(result.stdout.strip()).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--extra-root", action="append", default=[], type=Path,
                        help="Additional evidence file/directory to include (repeatable)")
    parser.add_argument("--stage", action="store_true",
                        help="Stage only this newly created archive directory with git add -f")
    parser.add_argument("--timestamp", default=None,
                        help="Archive directory name; defaults to local YYYYMMDD-HHMMSS")
    args = parser.parse_args()

    repo_root = find_repo_root(args.repo_root.resolve())
    home = args.home.expanduser().resolve()
    roots = [home / name for name in DEFAULT_ROOTS]
    roots.append(home / "Descargas/tandem-research/engines/tandem.cpp/tandem/report1.nsys-rep")
    roots.extend(p.expanduser() for p in args.extra_root)

    stamp = args.timestamp or dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    archive_parent = repo_root / "artifacts/benchmarks/nepenthes-raw-archive-2026-11-14"
    manifest = collect_archive(home, repo_root, roots, archive_parent, stamp)
    run_dir = Path(manifest["archive_directory"])
    if args.stage:
        relative = run_dir.relative_to(repo_root).as_posix()
        subprocess.run(["git", "-C", str(repo_root), "add", "-f", "--", relative], check=True)
    print(json.dumps({
        "archive_directory": str(run_dir),
        "copied_files": manifest["copied_files"],
        "duplicate_files": manifest["duplicate_files"],
        "missing_roots": manifest["missing_roots"],
        "total_copied_bytes": manifest["total_copied_bytes"],
        "git_staged": args.stage,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
