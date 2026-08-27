#!/usr/bin/env python3
"""Run registry-driven discovery against queryable public sources.

Adapters are best-effort and conservative: a source that cannot be searched
is reported instead of blocking the federation.
"""

from __future__ import annotations
import argparse, json, os, re, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

UA = "LEONES-Atlas-Prospection/2.6"
QUERIES = ["LLM", "inference", "agent", "MCP", "model", "AI"]
TARGETS = {
    "gitlab": ("gitlab", "https://gitlab.com"),
    "framagit": ("gitlab", "https://framagit.org"),
    "codeberg": ("forgejo", "https://codeberg.org"),
    "disroot-forge": ("forgejo", "https://forge.disroot.org"),
    "notabug": ("gogs", "https://notabug.org"),
    "pagure": ("pagure", "https://pagure.io"),
    "huggingface": ("huggingface-models", "https://huggingface.co"),
    "huggingface-papers": ("huggingface-papers", "https://huggingface.co"),
    "gnu-savannah": ("savannah", "https://savannah.gnu.org"),
    "sourcehut": ("sourcehut", "https://git.sr.ht"),
    "srht": ("sourcehut", "https://git.sr.ht"),
    "gitbucket": ("gitbucket", "https://gitbucket.github.io"),
}
UNSUPPORTED = {
    "forgejo-network": "requires discovery of concrete Forgejo instances",
    "forgejo": "platform site, not a repository instance",
    "gitea": "platform site; concrete instances require discovery",
    "gitlab-ce": "platform site; concrete instances require discovery",
    "onedev": "platform site; concrete instances require discovery",
    "kallithea": "platform site; concrete instances require discovery",
    "phorge": "no public search adapter enabled",
    "fossil": "no common public search API",
    "rhodecode": "platform site; concrete instances require discovery",
    "cgit": "instance-specific crawling required",
    "gitbucket": "requires concrete instance discovery",
}


def get(url, source_id=None, adapter=None, timeout=15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
        },
    )
    token_env = {
        "gitlab": {
            "gitlab": "LEONES_GITLAB_TOKEN",
            "framagit": "LEONES_FRAMAGIT_TOKEN",
        },
        "huggingface-models": {"huggingface": "HF_TOKEN"},
        "huggingface-papers": {"huggingface-papers": "HF_TOKEN"},
        "sourcehut": {"sourcehut": "SOURCEHUT_TOKEN", "srht": "SOURCEHUT_TOKEN"},
    }.get(adapter or "", {}).get(source_id or "")
    token = os.getenv(token_env) if token_env else None
    if token and adapter == "gitlab":
        req.add_header("PRIVATE-TOKEN", token)
    elif token and adapter == "sourcehut":
        req.add_header("Authorization", f"Bearer {token}")
    elif token and adapter.startswith("huggingface"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8"), response.status


def normalize(source_id, adapter, base, item, query, now, kind="software"):
    url = item.get("web_url") or item.get("html_url") or item.get("url") or ""
    name = (
        item.get("path_with_namespace")
        or item.get("full_name")
        or item.get("id")
        or item.get("name")
        or ""
    )
    return {
        "type": kind,
        "name": str(name),
        "url": url,
        "description": item.get("description") or item.get("summary") or "",
        "source": source_id,
        "source_url": base,
        "evidence_url": url,
        "license": item.get("license") or "",
        "license_status": "unvalidated",
        "observed_at": now,
        "query": query,
        "publication_status": "discovered",
        "provenance": {"adapter": adapter, "source_id": source_id},
    }


def search_gitlab(s, b, q):
    raw, status = get(
        b.rstrip("/")
        + "/api/v4/projects?"
        + urllib.parse.urlencode(
            {
                "search": q,
                "order_by": "last_activity_at",
                "sort": "desc",
                "per_page": 20,
            }
        ),
        s,
        "gitlab",
    )
    data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    return [normalize(s, "gitlab", b, x, q, now) for x in data], status


def search_forgejo(s, b, q):
    raw, status = get(
        b.rstrip("/")
        + "/api/v1/repos/search?"
        + urllib.parse.urlencode({"q": q, "limit": 20, "includeDesc": "true"}),
        s,
        "forgejo",
    )
    data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    items = data.get("data", []) if isinstance(data, dict) else []
    return [normalize(s, "forgejo", b, x, q, now) for x in items], status


def search_pagure(s, b, q):
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    # Pagure's public API documents /api/0/projects with a pattern filter.
    urls = [
        b.rstrip("/") + "/api/0/projects?" + urllib.parse.urlencode({"pattern": q}),
        b.rstrip("/")
        + "/api/0/projects?"
        + urllib.parse.urlencode({"pattern": f"*{q}*"}),
    ]
    last_status = 200
    for url in urls:
        try:
            raw, status = get(url, s, "pagure")
            last_status = status
            data = json.loads(raw)
            items = (
                data
                if isinstance(data, list)
                else data.get("projects", [])
                if isinstance(data, dict)
                else []
            )
            if items:
                return [
                    normalize(s, "pagure", b, x, q, now) for x in items[:20]
                ], status
        except Exception:
            continue
    # HTML fallback: Pagure installations expose project search in the web UI.
    html_url = (
        b.rstrip("/") + "/search?" + urllib.parse.urlencode({"search_pattern": q})
    )
    try:
        raw, status = get(html_url, s, "pagure")
        last_status = status
        parser = LinkParser(patterns=("/",))
        parser.feed(raw)
        seen = set()
        for href, label in parser.links:
            if (
                not label
                or href in seen
                or href.startswith(("/api/", "/issues", "/pull-request"))
            ):
                continue
            if href.count("/") >= 2 and not href.startswith("//"):
                seen.add(href)
                rows.append(
                    normalize(
                        s,
                        "pagure",
                        b,
                        {"id": label, "url": urllib.parse.urljoin(b, href)},
                        q,
                        now,
                    )
                )
                if len(rows) >= 20:
                    break
    except Exception:
        pass
    return rows, last_status


def search_gogs(s, b, q):
    now = datetime.now(timezone.utc).isoformat()
    # NotABug is a Gogs instance. Its public API is v1, but the web search
    # endpoint is a useful fallback when the API is temporarily unavailable.
    api = (
        b.rstrip("/")
        + "/api/v1/repos/search?"
        + urllib.parse.urlencode({"q": q, "limit": 20})
    )
    try:
        raw, status = get(api, s, "gogs")
        data = json.loads(raw)
        items = data.get("data", []) if isinstance(data, dict) else data
        if isinstance(items, list):
            return [normalize(s, "gogs", b, x, q, now) for x in items[:20]], status
    except Exception:
        pass
    web = b.rstrip("/") + "/explore/repos?" + urllib.parse.urlencode({"q": q})
    raw, status = get(web, s, "gogs")
    parser = LinkParser(patterns=("/",))
    parser.feed(raw)
    rows = []
    seen = set()
    for href, label in parser.links:
        if (
            not label
            or href in seen
            or not href.startswith("/")
            or href.startswith(("/explore", "/repo", "/user", "/api"))
        ):
            continue
        parts = href.strip("/").split("/")
        if len(parts) >= 2 and all(parts[:2]):
            seen.add(href)
            rows.append(
                normalize(
                    s,
                    "gogs",
                    b,
                    {
                        "id": "/".join(parts[:2]),
                        "url": urllib.parse.urljoin(b, "/".join(parts[:2])),
                    },
                    q,
                    now,
                )
            )
            if len(rows) >= 20:
                break
    return rows, status


def search_huggingface_models(s, b, q):
    raw, status = get(
        b
        + "/api/models?"
        + urllib.parse.urlencode(
            {"search": q, "limit": 20, "sort": "lastModified", "direction": -1}
        ),
        s,
        "huggingface-models",
    )
    data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for x in data if isinstance(data, list) else []:
        rid = x.get("id", "")
        rows.append(
            normalize(
                s,
                "huggingface-models",
                b,
                {
                    "id": rid,
                    "url": f"{b}/{rid}",
                    "license": x.get("cardData", {}).get("license", ""),
                },
                q,
                now,
                "model",
            )
        )
    return rows, status


def search_huggingface_papers(s, b, q):
    raw, status = get(
        b + "/api/daily_papers?" + urllib.parse.urlencode({"limit": 100, "offset": 0}),
        s,
        "huggingface-papers",
    )
    data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    items = (
        data.get("recentPapers", data.get("papers", []))
        if isinstance(data, dict)
        else data
    )
    tokens = [t.lower() for t in q.split() if t]
    rows = []
    for x in items or []:
        blob = json.dumps(x, ensure_ascii=False).lower()
        if tokens and not any(t in blob for t in tokens):
            continue
        p = x.get("paper", x) if isinstance(x, dict) else {}
        pid = p.get("id") or p.get("paperId") or x.get("id", "")
        title = p.get("title") or x.get("title") or pid
        url = f"{b}/papers/{pid}" if pid else b + "/papers"
        rows.append(
            normalize(
                s,
                "huggingface-papers",
                b,
                {"id": title, "url": url, "summary": p.get("summary", "")},
                q,
                now,
                "paper",
            )
        )
    return rows[:20], status


def search_sourcehut(s, b, q):
    if not os.getenv("SOURCEHUT_TOKEN"):
        raise RuntimeError("SOURCEHUT_TOKEN is required for SourceHut search")
    raise RuntimeError("SourceHut adapter requires GraphQL endpoint validation")


class LinkParser(HTMLParser):
    def __init__(self, patterns=()):
        super().__init__()
        self.links = []
        self.href = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.text = []

    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join("".join(self.text).split())))
            self.href = None


def search_savannah(s, b, q):
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    seen = set()
    urls = [
        b.rstrip("/") + "/search/?" + urllib.parse.urlencode({"words": q}),
        b.rstrip("/") + "/search.php?" + urllib.parse.urlencode({"words": q}),
    ]
    for url in urls:
        try:
            raw, status = get(url, s, "savannah")
            parser = LinkParser()
            parser.feed(raw)
            for href, label in parser.links:
                if not label or href in seen:
                    continue
                if "/projects/" in href or href.startswith("/project/"):
                    seen.add(href)
                    rows.append(
                        normalize(
                            s,
                            "savannah",
                            b,
                            {"id": label, "url": urllib.parse.urljoin(b, href)},
                            q,
                            now,
                        )
                    )
                    if len(rows) >= 20:
                        break
            if rows:
                return rows, status
        except Exception:
            continue
    return rows, 200


def load_instances():
    path = Path("data/prospection/forge_instances.ndjson")
    instances = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    instances.append(json.loads(line)["url"].rstrip("/"))
                except (ValueError, KeyError):
                    pass
    env = [
        x.strip().rstrip("/")
        for x in os.getenv("LEONES_FORGEJO_INSTANCES", "").split(",")
        if x.strip()
    ]
    return list(dict.fromkeys(instances + env))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", default="scripts/prospection/sources_registry.json")
    p.add_argument("--output", default="data/prospection/federated_discoveries.ndjson")
    p.add_argument("--queries", type=int, default=2)
    p.add_argument("--only-discovered-instances", action="store_true")
    p.add_argument("--skip-discovered-instances", action="store_true")
    args = p.parse_args()
    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    ids = [x["id"] for x in registry.get("sources", [])]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    unique = {}
    stats = Counter()
    errors = []
    instances = load_instances()
    if not args.skip_discovered_instances:
        for base in instances:
            host = urllib.parse.urlparse(base).netloc
            sid = "forgejo-instance:" + host
            if host == "codeberg.org":
                continue
            for q in QUERIES[: args.queries]:
                try:
                    found, _ = search_forgejo(sid, base, q)
                    for row in found:
                        unique[row["url"] or f"{sid}:{row['name']}"] = row
                    stats[sid] += len(found)
                except Exception as exc:
                    errors.append(
                        {
                            "source_id": sid,
                            "query": q,
                            "status": "error",
                            "error_type": type(exc).__name__,
                            "message": str(exc)[:300],
                        }
                    )
    if args.only_discovered_instances:
        ids = []
    fnmap = {
        "gitlab": search_gitlab,
        "forgejo": search_forgejo,
        "gogs": search_gogs,
        "pagure": search_pagure,
        "huggingface-models": search_huggingface_models,
        "huggingface-papers": search_huggingface_papers,
        "savannah": search_savannah,
        "sourcehut": search_sourcehut,
        "gitbucket": lambda *a: (_ for _ in ()).throw(
            RuntimeError("GitBucket requires concrete instance discovery")
        ),
    }
    if not args.only_discovered_instances:
        for source_id in ids:
            if source_id in UNSUPPORTED:
                errors.append(
                    {
                        "source_id": source_id,
                        "status": "unsupported",
                        "reason": UNSUPPORTED[source_id],
                    }
                )
                continue
            target = TARGETS.get(source_id)
            if not target:
                errors.append(
                    {
                        "source_id": source_id,
                        "status": "no_adapter",
                        "reason": "No concrete public instance configured",
                    }
                )
                continue
            adapter, base = target
            fn = fnmap[adapter]
            for q in QUERIES[: args.queries]:
                try:
                    found, _ = fn(source_id, base, q)
                    for row in found:
                        unique[row["url"] or f"{source_id}:{row['name']}"] = row
                    stats[source_id] += len(found)
                except Exception as exc:
                    errors.append(
                        {
                            "source_id": source_id,
                            "query": q,
                            "status": "error",
                            "error_type": type(exc).__name__,
                            "message": str(exc)[:300],
                        }
                    )
    with out.open("w", encoding="utf-8") as h:
        for row in unique.values():
            h.write(json.dumps(row, ensure_ascii=False) + "\n")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_in_registry": len(ids),
        "sources_successfully_queried": sorted(stats),
        "raw_results_by_source": dict(stats),
        "unique_discoveries": len(unique),
        "errors_or_unsupported": errors,
        "error_count": len(errors),
        "discovered_instances": instances,
        "output": str(out),
        "note": "Savannah, NotABug/Gogs and Pagure adapters use API-first discovery with bounded HTML fallbacks.",
    }
    (out.parent / "federated_discovery_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
