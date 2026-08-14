#!/usr/bin/env python3
"""Generate a machine-readable and human-readable daily prospection report."""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_INPUT = Path('data/prospection/classified_discoveries.ndjson')


def main():
    src = DEFAULT_INPUT
    out = Path('data/prospection/daily_report.json')
    md = Path('data/prospection/daily_report.md')
    rows = []
    if src.exists():
        for line in src.read_text(encoding='utf-8').splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    by_type = Counter(x.get('type', x.get('category', 'unknown')) for x in rows)
    by_source = Counter(x.get('source', 'unknown') for x in rows)
    by_status = Counter(x.get('publication_status', 'unknown') for x in rows)
    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'input': str(src),
        'total_discoveries': len(rows),
        'by_type': dict(by_type),
        'by_source': dict(by_source),
        'by_publication_status': dict(by_status),
        'license_unknown': sum(1 for x in rows if not x.get('license')),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    lines = [
        '# Daily Atlas Prospection', '',
        f"Generated: {report['generated_at']}",
        f"Input: `{src}`",
        f"Discoveries: **{len(rows)}**",
        f"Without declared license: **{report['license_unknown']}**", '',
        '## By type'
    ]
    lines += [f'- {k}: {v}' for k, v in sorted(by_type.items())] or ['- none']
    lines += ['', '## By source']
    lines += [f'- {k}: {v}' for k, v in sorted(by_source.items())] or ['- none']
    lines += ['', '## Publication status']
    lines += [f'- {k}: {v}' for k, v in sorted(by_status.items())] or ['- none']
    md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
