#!/usr/bin/env python3
"""Inject the LEONES visual identity into the main documentation pages.

The script is deliberately idempotent: running it repeatedly does not add
another logo rail or duplicate the stylesheet. It is intended for local use
and GitHub Actions.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
ASSET = "assets/graphics/logos/"
CSS = '<link rel="stylesheet" href="assets/graphics/brand.css">'
MARKER = '<!-- LEONES-VISUAL-IDENTITY -->'

PAGES = {
    "index.html": ("LEONES", "leones-logo-principal.jpg"),
    "pilares.html": ("Pilares", "leones-prospection.svg"),
    "arquitectura.html": ("Arquitectura", "leones-arquitectura.svg"),
    "operacion.html": ("Operación", "leones-herramientas.svg"),
}

RAIL = '''<div class="leones-logo-rail">\n  <a class="leones-logo-link" href="pilares.html"><img src="assets/graphics/logos/leones-prospection.svg" alt="Prospección">Prospección</a>\n  <a class="leones-logo-link" href="pilares.html#atlas"><img src="assets/graphics/logos/leones-atlas.svg" alt="Atlas">Atlas</a>\n  <a class="leones-logo-link" href="pilares.html#router"><img src="assets/graphics/logos/leones-router.svg" alt="Router">Router</a>\n  <a class="leones-logo-link" href="pilares.html#runtime"><img src="assets/graphics/logos/leones-hardware.svg" alt="Hardware">Hardware</a>\n  <a class="leones-logo-link" href="arquitectura.html#lotb"><img src="assets/graphics/logos/leones-agents.svg" alt="Agents / LOTB">Agents / LOTB</a>\n  <a class="leones-logo-link" href="app.html#manada"><img src="assets/graphics/logos/leones-manada.svg" alt="Manada">Manada</a>\n</div>'''

for filename, (label, logo) in PAGES.items():
    path = WEB / filename
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        continue
    text = text.replace("</head>", f"{CSS}\n</head>", 1)
    body = f'{MARKER}\n<div class="wrap">\n  <div class="leones-section-brand"><img src="{ASSET}{logo}" alt="LEONES · {label}"><div><strong>LEONES · {label}</strong><br><span class="small">Identidad funcional del ecosistema</span></div></div>\n  {RAIL}\n</div>\n'
    text = text.replace("<main", body + "<main", 1)
    path.write_text(text, encoding="utf-8")
print("LEONES visual identity integrated into: " + ", ".join(PAGES))
