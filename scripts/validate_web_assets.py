#!/usr/bin/env python3
"""Validate local web/documentation references before they reach GitHub Pages.

A documented or referenced local asset must exist at the path used by the
source file. The logo manifest is checked separately because it is a common
source of silent 404s.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
LOGO_DIR = WEB / "assets" / "graphics" / "logos"
MANIFEST = LOGO_DIR / "manifest.json"
TEXT_EXTENSIONS = {".html", ".htm", ".css", ".js", ".mjs", ".md"}
SKIP_DIRS = {".git", "node_modules"}


def local_target(value: str) -> str | None:
    value = value.strip().strip("'\"")
    if not value or value.startswith(
        ("#", "/", "//", "data:", "mailto:", "javascript:")
    ):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return None
    return parsed.path or None


def check_file_references(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    candidates: list[str] = []

    if path.suffix in {".html", ".htm"}:
        candidates += re.findall(
            r"(?:src|href)\s*=\s*[\"']([^\"']+)[\"']", text, flags=re.I
        )
    elif path.suffix == ".css":
        candidates += re.findall(
            r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)", text, flags=re.I
        )
    elif path.suffix == ".md":
        candidates += re.findall(r"!?\[[^]]*\]\(([^)]+)\)", text)

    # Also inspect explicit functional-logo references in JS and JSON-like text.
    candidates += re.findall(
        r"(?:assets/graphics/logos/|web/assets/graphics/logos/)([^\s'\"<>?#)]+)", text
    )

    for candidate in candidates:
        target = local_target(candidate)
        if not target:
            continue
        if "assets/graphics/logos/" in target:
            target = target[target.index("assets/graphics/logos/") :]
            resolved = WEB / target
        else:
            resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            continue
        if not resolved.exists():
            errors.append(
                f"{path.relative_to(ROOT)} -> {candidate} (missing: {resolved.relative_to(ROOT)})"
            )
    return errors


def check_logo_manifest() -> list[str]:
    errors: list[str] = []
    if not MANIFEST.exists():
        return ["web/assets/graphics/logos/manifest.json is missing"]
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid logo manifest JSON: {exc}"]
    base = data.get("base")
    if base and not (LOGO_DIR / base).resolve().exists():
        errors.append(f"manifest base missing: {base}")
    for logo in data.get("logos", []):
        filename = logo.get("file")
        if filename and not (LOGO_DIR / filename).exists():
            errors.append(f"manifest logo missing: {filename}")
    return errors


def main() -> int:
    errors = check_logo_manifest()
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        errors.extend(check_file_references(path))

    if errors:
        print("Local reference validation FAILED:")
        for error in sorted(set(errors)):
            print(f"- {error}")
        return 1

    print("Local web/documentation references and logo manifest are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
