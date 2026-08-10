#!/usr/bin/env python3
"""Discover recent GitHub repositories that may be useful to LOAS.

This is a candidate-discovery mechanism, not an automatic admission mechanism.
Every result must be manually/licence-verified before entering the LOAS stack.
"""
import json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('research/copyleft-discoveries.md')
QUERIES = [
    'license:GPL agent AI pushed:>=%s' % datetime.now(timezone.utc).date(),
    'license:AGPL agent AI pushed:>=%s' % datetime.now(timezone.utc).date(),
    'license:LGPL agent AI pushed:>=%s' % datetime.now(timezone.utc).date(),
    'license:GPL local LLM agent pushed:>=%s' % datetime.now(timezone.utc).date(),
    'license:AGPL local LLM pushed:>=%s' % datetime.now(timezone.utc).date(),
    'license:GPL llama.cpp agent pushed:>=%s' % datetime.now(timezone.utc).date(),
]

def api(path):
    url = 'https://api.github.com' + path
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'LOAS-copyleft-discovery',
    })
    token = os.environ.get('GH_TOKEN')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

seen = {}
for q in QUERIES:
    data = api('/search/repositories?' + urllib.parse.urlencode({'q': q, 'sort': 'updated', 'order': 'desc', 'per_page': 20}))
    for item in data.get('items', []):
        seen[item['full_name']] = item

lines = [
    '# Daily Copyleft Discovery',
    '',
    '> Automated candidate discovery. **These are candidates, not approved LOAS components.** Licence, activity, architecture, hardware relevance and reproducibility must be checked before adoption.',
    '',
    'Updated: ' + datetime.now(timezone.utc).isoformat(),
    '',
    '| Repository | License | Stars | Updated | Description |',
    '|---|---|---:|---|---|',
]
for name, item in sorted(seen.items(), key=lambda kv: kv[1].get('updated_at',''), reverse=True):
    license_name = (item.get('license') or {}).get('spdx_id') or 'UNVERIFIED'
    desc = (item.get('description') or '').replace('|', '\\|').replace('\n', ' ')[:180]
    lines.append(f"| [{name}]({item['html_url']}) | {license_name} | {item['stargazers_count']} | {item['updated_at'][:10]} | {desc} |")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
