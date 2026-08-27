#!/usr/bin/env python3
"""Route federated forge sources to a compatible API adapter.

The router is registry-driven: adding a Forgejo/Gitea instance to the source
registry does not require a new bot. It emits executable targets while keeping
source provenance intact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "scripts/prospection/sources_registry.json"

FORGE_FAMILIES = {
    "forgejo": {"forgejo.org", "codeberg.org", "forge.disroot.org", "notabug.org"},
    "gitea": {"gitea.io"},
    "gitlab": {
        "about.gitlab.com",
        "framagit.org",
        "gitlab.gnome.org",
        "gitlab.freedesktop.org",
        "invent.kde.org",
    },
    "pagure": {"pagure.io"},
    "sourcehut": {"sourcehut.org", "sr.ht"},
    "savannah": {"savannah.gnu.org"},
}


def hostname(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def adapter_for(url: str, kind: str = "") -> str:
    host = hostname(url)
    if host in FORGE_FAMILIES["forgejo"]:
        return "forgejo"
    if host in FORGE_FAMILIES["gitea"]:
        return "gitea"
    if host in FORGE_FAMILIES["gitlab"]:
        return "gitlab"
    if host in FORGE_FAMILIES["pagure"]:
        return "pagure"
    if host in FORGE_FAMILIES["sourcehut"]:
        return "sourcehut"
    if host in FORGE_FAMILIES["savannah"]:
        return "savannah"
    if "gitlab" in kind.lower():
        return "gitlab"
    return "generic_web"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--registry", default=str(REGISTRY))
    p.add_argument("--output", default="data/prospection/adapter_targets.ndjson")
    args = p.parse_args()

    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for source in registry.get("sources", []):
        url = source.get("url", "")
        rows.append(
            {
                "source_id": source.get("id", ""),
                "source_url": url,
                "adapter": adapter_for(url, source.get("kind", "")),
                "priority": source.get("priority", "medium"),
                "provenance": {
                    "registry_id": source.get("id", ""),
                    "registry_url": url,
                },
                "status": "planned",
            }
        )

    out.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows),
        encoding="utf-8",
    )
    print(json.dumps({"sources": len(rows), "output": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
