#!/usr/bin/env python3
"""Daily GitHub discovery for concrete, reusable and reproducible agent use cases.

Discovery is intentionally separate from review and publication. A repository
found by search is a candidate, never an endorsement or a license clearance.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data/prospection/agent_use_cases.ndjson"
SKILLS = ROOT / "data/discovery/skills.json"
PROSPECTION = ROOT / "web/data/prospeccion.json"
OUTPUT = ROOT / "web/data/agent-use-cases.json"
API = "https://api.github.com"
QUERIES = [
    ("agent-framework", "topic:ai-agents stars:>=3 archived:false fork:false"),
    ("agent-skills", '"agent skill" in:description stars:>=2 archived:false fork:false'),
    ("agent-examples", '"agent examples" in:description stars:>=2 archived:false fork:false'),
    ("agent-workflows", '"agent workflow" in:description stars:>=3 archived:false fork:false'),
    ("mcp-tools", '"MCP server" agent in:description stars:>=3 archived:false fork:false'),
    ("prompts-and-recipes", '"agent prompts" OR "agent examples" in:readme stars:>=2 archived:false fork:false'),
]
RELEVANCE = re.compile(
    r"agent|mcp|prompt|skill|workflow|automation|copilot|claude|codex|"
    r"langgraph|autogen|crew.?ai|llm|assistant|tool.?calling|harness",
    re.I,
)
INSTALL = re.compile(
    r"pip install|uv sync|npm install|pnpm install|docker compose|docker run|"
    r"git clone|quick.?start|getting started|installation|installing|setup",
    re.I,
)
EXAMPLES = re.compile(
    r"example|demo|cookbook|prompt|skill|recipe|tutorial|notebook|sample",
    re.I,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def request_json(url: str, token: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LEONES-Agent-Use-Case-Observatory",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def api_get(path: str, token: str):
    return request_json(API + path, token)


def repo_url(full_name: str) -> str:
    return f"https://github.com/{full_name}"


def infer_category(name: str, description: str, topics=None) -> str:
    text = " ".join([name or "", description or "", " ".join(topics or [])]).lower()
    if "mcp" in text:
        return "MCP"
    if "prompt" in text:
        return "Prompt"
    if "skill" in text:
        return "Skill"
    if "workflow" in text or "automation" in text:
        return "Workflow"
    if "example" in text or "cookbook" in text or "demo" in text:
        return "Example"
    return "Agent"


def stable_record(repo: dict, query_id: str, token: str, observed: str) -> dict:
    full_name = repo.get("full_name") or repo.get("name") or "unknown"
    license_obj = repo.get("license") or {}
    license_id = license_obj.get("spdx_id") if isinstance(license_obj, dict) else None
    description = repo.get("description") or ""
    readme = ""
    readme_bytes = 0
    has_readme = False
    readme_url = f"{repo_url(full_name)}/blob/{repo.get('default_branch') or 'main'}/README.md"
    try:
        data = api_get(f"/repos/{full_name}/readme", token)
        has_readme = True
        readme_bytes = int(data.get("size") or 0)
        readme_url = data.get("html_url") or readme_url
        if data.get("content") and data.get("encoding") == "base64":
            readme = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        pass

    install_evidence = bool(INSTALL.search(readme))
    example_evidence = bool(EXAMPLES.search(readme))
    score = 0
    evidence = []
    if has_readme:
        score += 2
        evidence.append("README disponible")
    if readme_bytes >= 1200:
        score += 1
        evidence.append("README con contenido sustancial")
    if license_id and license_id not in {"NOASSERTION", "OTHER"}:
        score += 2
        evidence.append(f"licencia declarada: {license_id}")
    if install_evidence:
        score += 2
        evidence.append("instrucciones de instalación/ejecución detectadas")
    if example_evidence:
        score += 2
        evidence.append("ejemplos, prompts o recetas mencionados en README")
    pushed = repo.get("pushed_at") or ""
    if pushed:
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(pushed.replace("Z", "+00:00"))).days
            if age <= 180:
                score += 1
                evidence.append("actividad en los últimos 180 días")
        except ValueError:
            pass
    if int(repo.get("stargazers_count") or 0) >= 10:
        score += 1
        evidence.append("adopción observable (≥10 stars)")

    score = min(score, 10)
    band = "promising" if score >= 7 else "partial" if score >= 4 else "limited"
    return {
        "id": full_name.lower(),
        "name": full_name,
        "description": description,
        "url": repo_url(full_name),
        "repository": repo_url(full_name),
        "readme_url": readme_url,
        "source": "GitHub",
        "source_query": query_id,
        "category": infer_category(full_name, description, repo.get("topics") or []),
        "license": license_id or "UNKNOWN",
        "license_status": "declared" if license_id and license_id not in {"NOASSERTION", "OTHER"} else "unvalidated",
        "stars": int(repo.get("stargazers_count") or 0),
        "forks": int(repo.get("forks_count") or 0),
        "language": repo.get("language"),
        "topics": repo.get("topics") or [],
        "default_branch": repo.get("default_branch"),
        "pushed_at": pushed,
        "has_readme": has_readme,
        "readme_bytes": readme_bytes,
        "has_install_instructions": install_evidence,
        "has_examples": example_evidence,
        "reproducibility_score": score,
        "reproducibility_band": band,
        "evidence": evidence,
        "publication_status": "discovered",
        "review_status": "pending",
        "discovered_at": observed,
        "last_seen_at": observed,
    }


def seed_existing(records: dict, observed: str) -> None:
    def add(item: dict, source: str):
        name = item.get("name") or item.get("repository") or ""
        url = item.get("url") or item.get("repository") or ""
        if not name or not url or not RELEVANCE.search(
            " ".join([name, str(item.get("description") or ""), str(item.get("category") or "")])
        ):
            return
        key = url.rstrip("/").lower()
        if key in records:
            return
        records[key] = {
            "id": name.lower(),
            "name": name,
            "description": item.get("description") or "",
            "url": url,
            "repository": url,
            "readme_url": url,
            "source": source,
            "source_query": "existing-leones-catalog",
            "category": infer_category(name, str(item.get("description") or ""), []),
            "license": item.get("license") or "UNKNOWN",
            "license_status": "declared" if item.get("license") and item.get("license") not in {"UNKNOWN", "NOASSERTION"} else "unvalidated",
            "stars": item.get("stars"),
            "forks": None,
            "language": None,
            "topics": [],
            "default_branch": None,
            "pushed_at": item.get("updated_at") or item.get("updated"),
            "has_readme": None,
            "readme_bytes": None,
            "has_install_instructions": None,
            "has_examples": None,
            "reproducibility_score": None,
            "reproducibility_band": "unassessed",
            "evidence": ["registro previo de LEONES; requiere evaluación específica de reproducibilidad"],
            "publication_status": item.get("publication_status") or "discovered",
            "review_status": "pending",
            "discovered_at": item.get("discovered_at") or observed,
            "last_seen_at": observed,
        }

    if SKILLS.exists():
        try:
            for item in json.loads(SKILLS.read_text(encoding="utf-8")).get("items", []):
                add(item, "LEONES · catálogo de skills")
        except (json.JSONDecodeError, OSError):
            pass
    if PROSPECTION.exists():
        try:
            for item in json.loads(PROSPECTION.read_text(encoding="utf-8")).get("items", []):
                add(item, "LEONES · prospección existente")
        except (json.JSONDecodeError, OSError):
            pass


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    observed = now_iso()
    records: dict[str, dict] = {}

    if HISTORY.exists():
        for line in HISTORY.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
                key = str(item.get("url") or "").rstrip("/").lower()
                if key:
                    records[key] = item
            except json.JSONDecodeError:
                continue

    seed_existing(records, observed)
    searched = 0
    failures = []
    for query_id, query in QUERIES:
        params = urllib.parse.urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": 10})
        try:
            result = api_get("/search/repositories?" + params, token)
            for repo in result.get("items", []):
                full_name = repo.get("full_name") or ""
                description = repo.get("description") or ""
                if not full_name or not RELEVANCE.search(full_name + " " + description + " " + " ".join(repo.get("topics") or [])):
                    continue
                url = repo_url(full_name).lower()
                try:
                    item = stable_record(repo, query_id, token, observed)
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
                    failures.append(f"{full_name}: {exc}")
                    continue
                old = records.get(url, {})
                item["discovered_at"] = old.get("discovered_at") or observed
                item["first_seen_at"] = old.get("first_seen_at") or item["discovered_at"]
                item["last_seen_at"] = observed
                records[url] = item
                searched += 1
            time.sleep(0.4)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            failures.append(f"{query_id}: {exc}")

    rows = sorted(
        records.values(),
        key=lambda x: (
            x.get("reproducibility_score") is not None,
            x.get("reproducibility_score") or -1,
            x.get("stars") or 0,
            x.get("last_seen_at") or "",
        ),
        reverse=True,
    )
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(
        "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in rows),
        encoding="utf-8",
    )
    payload = {
        "generated_at": observed,
        "source": "GitHub repository search + existing LEONES catalog",
        "publication_is_not_approval": True,
        "automatic_recommendation": False,
        "total": len(rows),
        "new_or_refreshed_from_search": searched,
        "search_queries": [{"id": qid, "query": q} for qid, q in QUERIES],
        "failures": failures,
        "items": rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "total": len(rows),
        "searched_or_refreshed": searched,
        "failures": len(failures),
        "output": str(OUTPUT),
        "history": str(HISTORY),
    }, ensure_ascii=False))
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
