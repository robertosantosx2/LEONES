#!/usr/bin/env python3
"""Validate local references in the published LEONES web sources.

The validator deliberately ignores code examples and dynamic template values:
only concrete local links/assets are checked. GitHub Pages root-relative paths
are resolved against the published web root.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
LOGO_DIR = WEB / "assets" / "graphics" / "logos"
MANIFEST = LOGO_DIR / "manifest.json"
TEXT_EXTENSIONS = {".html", ".htm", ".css", ".js", ".mjs", ".md"}
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def strip_markdown_code(source: str) -> str:
    """Remove fenced and inline code so examples are not treated as links."""
    kept: list[str] = []
    fence_char = None
    fence_size = 0
    for line in source.splitlines():
        match = FENCE.match(line)
        if match:
            token = match.group(1)
            if fence_char is None:
                fence_char, fence_size = token[0], len(token)
            elif token[0] == fence_char and len(token) >= fence_size:
                fence_char, fence_size = None, 0
            continue
        if fence_char is None:
            kept.append(line)
    text = "\n".join(kept)
    return re.sub(r"(?<!`)\x60{1,2}[^\x60]*\x60{1,2}(?!`)", "", text)


def local_target(value: str) -> str | None:
    value = value.strip().strip("'\"")
    if not value or any(token in value for token in ("${", "{{", "}}")):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or value.startswith(("//", "data:", "mailto:", "javascript:")):
        return None
    path = unquote(parsed.path)
    if not path or path.startswith("#"):
        return None
    return path


def resolve_target(source: Path, target: str) -> Path:
    if target.startswith("/"):
        return (WEB / target.lstrip("/")).resolve()
    if "assets/graphics/logos/" in target:
        suffix = target[target.index("assets/graphics/logos/"):]
        return (WEB / suffix).resolve()
    return (source.parent / target).resolve()


def check_file_references(path: Path) -> list[str]:
    errors: list[str] = []
    source = path.read_text(encoding="utf-8", errors="replace")
    scan = strip_markdown_code(source) if path.suffix.lower() == ".md" else source
    candidates: list[str] = []

    if path.suffix.lower() in {".html", ".htm"}:
        candidates += re.findall(r"(?:src|href)\s*=\s*[\"']([^\"']+)[\"']", scan, flags=re.I)
    elif path.suffix.lower() == ".css":
        candidates += re.findall(r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)", scan, flags=re.I)
    elif path.suffix.lower() == ".md":
        candidates += re.findall(r"!?(?:\[[^]]*\])\(([^)]+)\)", scan)

    # Keep the full path when checking functional logo references in JS/HTML/MD.
    candidates += re.findall(
        r"((?:web/)?assets/graphics/logos/[^\s'\"<>?#)]+)", scan
    )

    for candidate in candidates:
        target = local_target(candidate)
        if not target:
            continue
        resolved = resolve_target(path, target)
        try:
            relative = resolved.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{path.relative_to(ROOT)} -> {candidate} (path escapes repository)")
            continue
        if not resolved.exists():
            errors.append(f"{path.relative_to(ROOT)} -> {candidate} (missing: {relative})")
    return errors


def check_logo_manifest() -> list[str]:
    if not MANIFEST.exists():
        return ["web/assets/graphics/logos/manifest.json is missing"]
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid logo manifest JSON: {exc}"]
    errors: list[str] = []
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
    # Publication checks are scoped to web/: repository documentation and
    # experimental projects have independent path conventions and lifecycles.
    for path in WEB.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        errors.extend(check_file_references(path)
    if errors:
        print("Local reference validation FAILED:")
        for error in sorted(set(errors)):
            print(f"- {error}")
        return 1
    print("Local web/documentation references and logo manifest are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
