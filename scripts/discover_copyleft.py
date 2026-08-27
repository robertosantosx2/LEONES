#!/usr/bin/env python3
"""Daily discovery of OSI-approved projects for LEONES.

PRIMARY CRITERION: the candidate must advertise an OSI-approved SPDX license.
Priority copyleft licenses are highlighted separately:
GPL-2.0, GPL-3.0, AGPL-3.0, LGPL-2.1 and LGPL-3.0.

Discovery is not approval. Technical review remains mandatory.
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

OUT_MD = Path("research/copyleft-discoveries.md")
OUT_JSON = Path("web/data/prospeccion.json")
OSI_LICENSES_URL = "https://opensource.org/Licenses"
PRIORITY_COPYLEFT = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL-2.1", "LGPL-3.0"}

# Search broadly for relevant models, runtimes, software, agents, tools,
# benchmarks and hardware-related projects. The OSI license gate is applied
# AFTER discovery, so licensing does not hide relevant technical searches.
DISCOVERY_QUERIES = [
    "local LLM AI pushed:>={since}",
    "local AI inference runtime pushed:>={since}",
    "LLM agent tools pushed:>={since}",
    "AI coding agent pushed:>={since}",
    "LLM model weights pushed:>={since}",
    "LLM quantization pushed:>={since}",
    "AI efficiency inference pushed:>={since}",
    "AI benchmark local hardware pushed:>={since}",
    "AI fine tuning local pushed:>={since}",
    "AI hardware acceleration inference pushed:>={since}",
]


class LicenseTableParser(HTMLParser):
    """Read the SPDX ID from the second cell of each OSI license row."""

    def __init__(self):
        super().__init__()
        self.in_tr = False
        self.in_td = False
        self.current = []
        self.cells = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_tr = True
            self.cells = []
        elif tag == "td" and self.in_tr:
            self.in_td = True
            self.current = []

    def handle_endtag(self, tag):
        if tag == "td" and self.in_td:
            self.cells.append("".join(self.current).strip())
            self.in_td = False
        elif tag == "tr" and self.in_tr:
            self.rows.append(self.cells[:])
            self.in_tr = False

    def handle_data(self, data):
        if self.in_td:
            self.current.append(data)


def fetch_url(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "LEONES-prospection",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def load_osi_licenses():
    """Load the current OSI-approved SPDX IDs from the OSI website."""
    parser = LicenseTableParser()
    parser.feed(fetch_url(OSI_LICENSES_URL))
    licenses = set()
    for row in parser.rows:
        if len(row) < 2:
            continue
        spdx = re.sub(r"\s+", "", row[1])
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", spdx):
            licenses.add(spdx)
    missing = PRIORITY_COPYLEFT - licenses
    if missing:
        raise RuntimeError(
            "OSI parser missing priority licenses: " + ", ".join(sorted(missing))
        )
    return licenses


def github_api(path):
    url = "https://api.github.com" + path
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "LEONES-prospection",
        },
    )
    token = os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"GitHub API HTTP {exc.code} for {url}: {detail}") from exc


since = os.environ.get("PROSPECTION_SINCE")
if not since:
    since = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()

osi_licenses = load_osi_licenses()
seen = {}
failed_queries = []

for template in DISCOVERY_QUERIES:
    query = template.format(since=since)
    try:
        data = github_api(
            "/search/repositories?"
            + urllib.parse.urlencode(
                {
                    "q": query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": 30,
                }
            )
        )
    except RuntimeError as exc:
        failed_queries.append({"query": query, "error": str(exc)})
        print(f"WARNING: discovery query failed: {query}\n{exc}")
        continue
    for item in data.get("items", []):
        seen[item["full_name"]] = item

items = []
for name, item in seen.items():
    license_name = (item.get("license") or {}).get("spdx_id") or "UNVERIFIED"
    # PRIMARY GATE: only OSI-approved licenses enter the discovery dataset.
    if license_name not in osi_licenses:
        continue
    items.append(
        {
            "repository": name,
            "url": item.get("html_url"),
            "license": license_name,
            "osi_approved": True,
            "priority_copyleft": license_name in PRIORITY_COPYLEFT,
            "stars": item.get("stargazers_count", 0),
            "updated": item.get("updated_at", "")[:10],
            "description": (item.get("description") or "").replace("\n", " ")[:300],
        }
    )

# Priority copyleft first, then newest.
items.sort(
    key=lambda item: (not item["priority_copyleft"], item["updated"]), reverse=False
)
now = datetime.now(timezone.utc).isoformat()

lines = [
    "# Daily OSI-Approved Discovery",
    "",
    "> **Primary criterion: OSI-approved license.** Only candidates whose GitHub SPDX license appears in the current OSI-approved license list are included.",
    f"> Source: {OSI_LICENSES_URL}",
    f"> Search window: >= {since}",
    f"> OSI-approved SPDX licenses detected: {len(osi_licenses)}",
    "> Priority copyleft: `GPL-2.0`, `GPL-3.0`, `AGPL-3.0`, `LGPL-2.1`, `LGPL-3.0`.",
    "> Candidates are discoveries, not approved LEONES components.",
    "",
    "Updated: " + now,
    "",
    "| Repository | License | OSI | Priority copyleft | Stars | Updated | Description |",
    "|---|---|---|---|---:|---|---|",
]
for item in items:
    desc = item["description"].replace("|", "\\|")
    priority = "🟢 YES" if item["priority_copyleft"] else "—"
    lines.append(
        f"| [{item['repository']}]({item['url']}) | `{item['license']}` | YES | {priority} | "
        f"{item['stars']} | {item['updated']} | {desc} |"
    )

if failed_queries:
    lines.extend(
        [
            "",
            "## Query diagnostics",
            "",
            f"{len(failed_queries)} queries failed; successful queries were retained.",
            "",
        ]
    )
    for failure in failed_queries:
        lines.append(f"- `{failure['query']}` — `{failure['error']}`")

OUT_MD.parent.mkdir(parents=True, exist_ok=True)
OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(
    json.dumps(
        {
            "updated": now,
            "since": since,
            "criterion": "OSI-approved SPDX license is the primary discovery gate",
            "osi_source": OSI_LICENSES_URL,
            "osi_license_count": len(osi_licenses),
            "priority_copyleft": sorted(PRIORITY_COPYLEFT),
            "count": len(items),
            "items": items,
            "diagnostics": {"failed_queries": failed_queries},
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

print(f"Discovered {len(items)} OSI-approved candidates since {since}")
print(f"OSI license universe: {len(osi_licenses)} SPDX IDs")
print("Priority copyleft:", ", ".join(sorted(PRIORITY_COPYLEFT)))
if failed_queries:
    print(
        f"Completed with {len(failed_queries)} failed queries; see diagnostics in the generated report."
    )
