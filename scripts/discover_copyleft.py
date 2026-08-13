#!/usr/bin/env python3
"""Discover recent GitHub repositories that may be useful to LEONES.

Candidate discovery only: results are not automatically admitted to the stack.
Use PROSPECTION_SINCE=YYYY-MM-DD to define the lower date bound.
"""
import json, os, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUT_MD = Path('research/copyleft-discoveries.md')
OUT_JSON = Path('web/data/prospeccion.json')

since = os.environ.get('PROSPECTION_SINCE')
if not since:
    since = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()

# GitHub's license: qualifier expects an SPDX identifier, not generic names
# such as "GPL" or "AGPL". Keep the queries explicit so the daily bot does
# not fail with HTTP 422 when GitHub validates the search syntax.
QUERIES = [
    f'license:GPL-2.0 agent AI pushed:>={since}',
    f'license:GPL-3.0 agent AI pushed:>={since}',
    f'license:AGPL-3.0 agent AI pushed:>={since}',
    f'license:LGPL-2.1 agent AI pushed:>={since}',
    f'license:LGPL-3.0 agent AI pushed:>={since}',
    f'license:GPL-3.0 local LLM agent pushed:>={since}',
    f'license:AGPL-3.0 local LLM pushed:>={since}',
    f'license:GPL-3.0 llama.cpp agent pushed:>={since}',
]

def api(path):
    url = 'https://api.github.com' + path
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'LEONES-prospection',
    })
    token = os.environ.get('GH_TOKEN')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')[:1000]
        raise RuntimeError(f'GitHub API HTTP {exc.code} for {url}: {detail}') from exc

seen = {}
failed_queries = []
for q in QUERIES:
    try:
        data = api('/search/repositories?' + urllib.parse.urlencode({
            'q': q, 'sort': 'updated', 'order': 'desc', 'per_page': 20
        }))
    except RuntimeError as exc:
        # One malformed/temporarily rejected query must not discard all the
        # other discovery results. Record it and continue.
        failed_queries.append({'query': q, 'error': str(exc)})
        print(f'WARNING: discovery query failed: {q}\n{exc}')
        continue
    for item in data.get('items', []):
        seen[item['full_name']] = item

items = []
for name, item in sorted(seen.items(), key=lambda kv: kv[1].get('updated_at',''), reverse=True):
    license_name = (item.get('license') or {}).get('spdx_id') or 'UNVERIFIED'
    items.append({
        'repository': name,
        'url': item.get('html_url'),
        'license': license_name,
        'stars': item.get('stargazers_count', 0),
        'updated': item.get('updated_at', '')[:10],
        'description': (item.get('description') or '').replace('\n', ' ')[:300],
    })

now = datetime.now(timezone.utc).isoformat()

lines = [
    '# Daily Open/Copyleft Discovery', '',
    '> Automated candidate discovery. **These are candidates, not approved LEONES components.**',
    f'> Search window: >= {since}', '',
    'Updated: ' + now, '',
    '| Repository | License | Stars | Updated | Description |',
    '|---|---|---:|---|---|',
]
for item in items:
    desc = item['description'].replace('|', '\\|')
    lines.append(f"| [{item['repository']}]({item['url']}) | {item['license']} | {item['stars']} | {item['updated']} | {desc} |")

if failed_queries:
    lines.extend(['', '## Query diagnostics', '', f'{len(failed_queries)} discovery queries failed; successful queries were still processed.', ''])
    for failure in failed_queries:
        lines.append(f"- `{failure['query']}` — `{failure['error']}`")

OUT_MD.parent.mkdir(parents=True, exist_ok=True)
OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps({
    'updated': now,
    'since': since,
    'count': len(items),
    'items': items,
    'diagnostics': {'failed_queries': failed_queries},
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print(f'Discovered {len(items)} candidates since {since}')
if failed_queries:
    print(f'Completed with {len(failed_queries)} failed queries; see diagnostics in the generated report.')
