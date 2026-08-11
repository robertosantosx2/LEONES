#!/usr/bin/env python3
"""Validate a LEONES report before optional publication.

One job only: privacy/safety validation followed by an explicitly requested
publication. It does not benchmark or generate reports.
"""

from __future__ import annotations

import argparse
import base64
import re
import subprocess
from pathlib import Path

PATTERNS = {
    "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "email": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "token": r"(?i)\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]+",
    "secret-like field": r"(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[^\s`]+",
    "home path": r"(?:/(?:home|Users)/[^\s`]+|[A-Za-z]:\\Users\\[^\s`]+)",
    "MAC address": r"\b(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}\b",
    "IPv4 address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}


def validate(text: str) -> list[str]:
    return [name for name, pattern in PATTERNS.items() if re.search(pattern, text)]


def publish(path: Path, repo: str, target: str) -> int:
    encoded = base64.b64encode(path.read_bytes()).decode()
    try:
        subprocess.run(["gh", "auth", "status"], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=10)
        subprocess.run([
            "gh", "api", f"repos/{repo}/contents/{target}", "--method", "PUT",
            "--field", f"message=metaLEONES: add {path.name}",
            "--field", f"content={encoded}",
        ], check=True, timeout=30)
    except Exception as exc:
        print(f"Publication failed: {exc}")
        print("Authenticate with: gh auth login")
        return 1
    print(f"Published: https://github.com/{repo}/blob/main/{target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and optionally publish a LEONES report")
    parser.add_argument("report")
    parser.add_argument("--publish", action="store_true", help="Actually publish after validation")
    parser.add_argument("--repo", default="robertosantosx2/LEONES")
    parser.add_argument("--path", default="")
    args = parser.parse_args()

    path = Path(args.report)
    findings = validate(path.read_text(encoding="utf-8", errors="replace"))
    if findings:
        print("Privacy check FAILED:")
        for finding in findings:
            print(f"- {finding}")
        return 2

    print("Privacy check: OK")
    print("NOTE: this detects common patterns; it does not prove anonymity or verification.")
    if not args.publish:
        return 0

    target = args.path or f"results/metaLEONES/{path.name}"
    return publish(path, args.repo, target)


if __name__ == "__main__":
    raise SystemExit(main())
