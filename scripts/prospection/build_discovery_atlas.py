#!/usr/bin/env python3
"""Build a standalone, offline-capable HTML snapshot of the LEONES discovery feed."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEED = ROOT / "web/data/prospeccion.json"
OUTPUT = ROOT / "web/discovery-atlas.html"

LOGO_SVG = r"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" role="img" aria-labelledby="title"><title id="title">LEONES · dos leones</title><defs><linearGradient id="b" x1="0" x2="1"><stop stop-color="#12304a"/><stop offset="1" stop-color="#1769aa"/></linearGradient></defs><rect width="800" height="800" rx="90" fill="#f3f6f9"/><g transform="translate(150 80)"><path d="M60 210C25 150 65 75 125 92C160 35 240 35 275 92C335 75 375 150 340 210C380 260 360 350 305 380C275 445 105 445 75 380C20 350 0 260 60 210Z" fill="#1769aa"/><path d="M105 205C105 135 295 135 295 205L278 330C250 370 150 370 122 330Z" fill="#f3f6f9" stroke="#12304a" stroke-width="11"/><circle cx="165" cy="240" r="14" fill="#12304a"/><circle cx="235" cy="240" r="14" fill="#12304a"/><path d="M166 285Q200 310 234 285" fill="none" stroke="#12304a" stroke-width="11" stroke-linecap="round"/><g fill="none" stroke="#f0c85a" stroke-width="13" stroke-linecap="round"><path d="M65 175C20 140 25 90 68 75C104 63 126 91 107 118C90 142 58 126 58 100"/><path d="M335 175C380 140 375 90 332 75"/><path d="M82 348C35 370 38 415 80 430"/><path d="M318 348C365 370 362 415 320 430"/></g><path d="M69 166A55 55 0 1 1 86 112" fill="none" stroke="#f0c85a" stroke-width="12" stroke-linecap="round"/><path d="M86 112l-3 31 27-13" fill="#f0c85a"/></g><g transform="translate(415 95)"><path d="M35 225C0 180 30 120 82 112C110 72 185 78 213 125C265 135 285 190 254 226C268 295 215 340 155 345C92 350 48 310 42 267C18 255 17 237 35 225Z" fill="#607d8b"/><path d="M88 165C118 125 184 136 200 178C210 195 225 204 265 212C235 234 210 235 190 230L178 288C145 315 103 295 90 260C80 235 78 190 88 165Z" fill="#f3f6f9" stroke="#12304a" stroke-width="10"/><circle cx="170" cy="188" r="8" fill="#12304a"/><path d="M199 220l30 8" stroke="#12304a" stroke-width="8" stroke-linecap="round"/></g><g transform="translate(210 550)"><rect width="380" height="92" rx="15" fill="url(#b)"/><rect x="30" y="22" width="320" height="48" rx="8" fill="#172b3d"/><rect x="135" y="31" width="110" height="30" rx="5" fill="#eaf4fb"/><text x="190" y="53" text-anchor="middle" font-family="Arial" font-size="17" font-weight="800" fill="#12304a">AI</text></g><text x="400" y="700" text-anchor="middle" font-family="Arial,sans-serif" font-size="58" font-weight="900" letter-spacing="8" fill="#12304a">LEONES</text><text x="400" y="730" text-anchor="middle" font-family="Arial,sans-serif" font-size="15" letter-spacing="2" fill="#607d8b">LOCAL ECOSYSTEM OF OPEN NEURAL EXPERT SYSTEMS</text></svg>"""

TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="LEONES Discovery Atlas: catálogo autónomo de software, modelos y papers descubiertos por la prospección federada.">
<meta name="theme-color" content="#102f49">
<title>LEONES · Discovery Atlas</title>
<style>
:root{color-scheme:light;--navy:#102f49;--blue:#1769aa;--cyan:#dceef8;--gold:#e7bd4b;--ink:#172b3d;--muted:#607486;--line:#dbe4eb;--paper:#f4f7fa;--white:#fff;--green:#16734b}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.shell{max-width:1240px;margin:auto;padding:28px 22px 64px}
.hero{position:relative;overflow:hidden;border-radius:28px;background:linear-gradient(120deg,#102f49,#174d70 64%,#1769aa);color:#fff;padding:32px;box-shadow:0 18px 48px #102f4928}
.hero:after{content:"";position:absolute;width:390px;height:390px;border:1px solid #ffffff22;border-radius:50%;right:-100px;top:-190px;box-shadow:0 0 0 36px #ffffff09,0 0 0 76px #ffffff08}
.brand{display:flex;align-items:center;gap:18px;position:relative;z-index:1}.brand-logo{width:82px;height:82px;border-radius:18px;background:#fff;padding:5px;flex:none}.eyebrow{text-transform:uppercase;letter-spacing:.16em;font-size:11px;font-weight:850;color:#b9d9ee}.hero h1{font-size:clamp(30px,5vw,52px);line-height:1.04;letter-spacing:-.04em;margin:5px 0 9px}.hero p{max-width:760px;color:#e2eff8;margin:0;font-size:16px}.hero-note{position:relative;z-index:1;margin-top:24px;display:flex;gap:10px;flex-wrap:wrap}.pill{border:1px solid #ffffff45;background:#ffffff12;border-radius:999px;padding:7px 12px;font-size:12px;font-weight:750}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}.metric{background:#fff;border:1px solid var(--line);border-radius:18px;padding:17px 19px;box-shadow:0 5px 18px #102f4908}.metric strong{display:block;font-size:29px;letter-spacing:-.04em;color:var(--navy)}.metric span{font-size:12px;color:var(--muted);font-weight:750}
.panel{background:#fff;border:1px solid var(--line);border-radius:20px;padding:18px;margin-top:16px}.panel h2{font-size:18px;margin:0 0 12px;color:var(--navy)}.filters{display:grid;grid-template-columns:minmax(220px,2fr) repeat(3,minmax(130px,1fr));gap:10px}.filters input,.filters select{width:100%;min-width:0;border:1px solid #cbd8e2;border-radius:12px;padding:12px 13px;font:inherit;background:#fff;color:var(--ink);outline-color:var(--blue)}.hint{font-size:12px;color:var(--muted);margin:11px 2px 0}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:22px 2px 12px}.toolbar h2{margin:0;font-size:21px;color:var(--navy)}.result-count{font-size:12px;color:var(--muted);font-weight:750}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.item{background:#fff;border:1px solid var(--line);border-radius:17px;padding:17px;display:flex;flex-direction:column;min-height:220px;box-shadow:0 5px 18px #102f4908;transition:transform .16s,border-color .16s}.item:hover{transform:translateY(-2px);border-color:#a9c7db}.item-top{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px}.tag{display:inline-flex;border-radius:999px;padding:4px 9px;background:#eaf3f9;color:#174d70;font-size:10px;text-transform:uppercase;letter-spacing:.07em;font-weight:850}.status{font-size:10px;font-weight:800;color:#805b0b;background:#fff4d6;border-radius:999px;padding:4px 8px}.item h3{font-size:16px;line-height:1.25;margin:0 0 8px;overflow-wrap:anywhere}.item p{font-size:13px;color:#536879;margin:0 0 14px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}.meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:auto;padding-top:10px}.meta span{font-size:10px;color:#5d7181;border:1px solid #e3eaf0;border-radius:7px;padding:3px 7px}.open{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:850;margin-top:13px}.empty{grid-column:1/-1;text-align:center;padding:40px;border:1px dashed #cbd8e2;border-radius:16px;color:var(--muted);background:#fff}.more{text-align:center;margin:20px 0}.more button{border:1px solid #b9d2e2;background:#eaf3f9;color:#164d70;border-radius:999px;padding:11px 20px;font-weight:850;cursor:pointer}.foot{margin-top:22px;padding:18px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:12px}.governance{background:#fff8e7;border:1px solid #f0dfb3;color:#70561c;border-radius:14px;padding:13px 15px;font-size:12px;margin-top:14px}
@media(max-width:900px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.filters{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:580px){.shell{padding:14px 12px 42px}.hero{padding:22px;border-radius:20px}.brand-logo{width:62px;height:62px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.cards{grid-template-columns:1fr}.filters{grid-template-columns:1fr}.toolbar{align-items:flex-start;flex-direction:column}}
</style>
</head>
<body>
<main class="shell">
<header class="hero">
 <div class="brand">
  <div class="brand-logo">__LOGO__</div>
  <div><div class="eyebrow">LEONES · Prospección federada</div><h1>Discovery Atlas</h1><p>El mapa de proyectos, modelos e investigación que encuentra la prospección de LEONES en múltiples forjas y repositorios abiertos.</p></div>
 </div>
 <div class="hero-note"><span class="pill">Catálogo autónomo · datos embebidos</span><span class="pill">Sin APIs ni CDN</span><span class="pill">Descubrimiento ≠ aprobación</span></div>
</header>
<section class="metrics" aria-label="Resumen">
 <div class="metric"><strong id="total">—</strong><span>DESCUBRIMIENTOS</span></div>
 <div class="metric"><strong id="software">—</strong><span>SOFTWARE</span></div>
 <div class="metric"><strong id="models">—</strong><span>MODELOS</span></div>
 <div class="metric"><strong id="papers">—</strong><span>PAPERS</span></div>
</section>
<section class="panel">
 <h2>Explorar el universo descubierto</h2>
 <div class="filters">
  <input id="q" type="search" placeholder="Buscar proyecto, descripción, repositorio…" aria-label="Buscar">
  <select id="type" aria-label="Tipo"><option value="">Todos los tipos</option></select>
  <select id="source" aria-label="Fuente"><option value="">Todas las fuentes</option></select>
  <select id="license" aria-label="Licencia"><option value="">Todas las licencias</option></select>
 </div>
 <p class="hint">Busca por nombre, descripción, origen o licencia. Los filtros se aplican localmente sobre los datos incluidos en este archivo.</p>
</section>
<div class="toolbar"><h2>Descubrimientos</h2><span class="result-count" id="count" aria-live="polite"></span></div>
<section class="cards" id="cards" aria-live="polite"></section>
<div class="more"><button id="more" type="button" hidden>Mostrar más</button></div>
<div class="governance"><strong>Importante:</strong> esta página presenta hallazgos automáticos en estado de revisión. Una licencia declarada no es una auditoría legal; un repositorio descubierto no está verificado, recomendado ni probado. Comprueba la fuente y sus condiciones antes de utilizar cualquier proyecto.</div>
<footer class="foot"><span>LEONES · Discovery Atlas · <span id="generated"></span></span><span><a href="agent-use-cases.html">Ir al Agent Use Case Observatory</a> · <a href="../README.md">Repositorio LEONES</a></span></footer>
</main>
<script>
"use strict";
const DATA=__DATA__;
const $=id=>document.getElementById(id);
const esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const labelType=t=>({software:"Software",model:"Modelo",paper:"Paper"}[t]||t||"Sin tipo");
const labelSource=s=>({"github":"GitHub","gitlab":"GitLab","huggingface":"Hugging Face","huggingface-papers":"Hugging Face Papers","framagit":"Framagit"}[s]||String(s||"").replace(/^(forgejo-instance|fossil-instance|cgit-instance):/,"").replaceAll("-"," "));
const items=Array.isArray(DATA.items)?DATA.items:[];
$("total").textContent=items.length;
$("software").textContent=items.filter(x=>(x.type||x.category)==="software").length;
$("models").textContent=items.filter(x=>x.type==="model").length;
$("papers").textContent=items.filter(x=>x.type==="paper").length;
$("generated").textContent="Actualizado: "+(DATA.generated_at||"fecha no disponible");
function fill(id,values){const el=$(id);[...new Set(values.filter(Boolean))].sort((a,b)=>String(a).localeCompare(String(b),"es")).forEach(v=>{const o=document.createElement("option");o.value=v;o.textContent=id==="type"?labelType(v):id==="source"?labelSource(v):v;el.appendChild(o);});}
fill("type",items.map(x=>x.type||x.category));
fill("source",items.map(x=>x.source));
fill("license",items.map(x=>x.license||"Desconocida"));
let limit=48;
function filtered(){
 const q=$("q").value.trim().toLowerCase(),t=$("type").value,s=$("source").value,l=$("license").value;
 return items.filter(x=>{
  const hay=[x.name,x.repository,x.description,x.url,x.source,x.license,x.type,x.category].join(" ").toLowerCase();
  return (!q||hay.includes(q))&&(!t||(x.type||x.category)===t)&&(!s||x.source===s)&&(!l||(x.license||"Desconocida")===l);
 }).sort((a,b)=>String(b.updated||"").localeCompare(String(a.updated||""))||String(a.name||"").localeCompare(String(b.name||"")));
}
function render(){
 const rows=filtered(),shown=rows.slice(0,limit);
 $("count").textContent=rows.length+" resultados · mostrando "+shown.length;
 $("cards").innerHTML=shown.length?shown.map(x=>{
  const url=String(x.url||x.repository||"");
  const safeUrl=/^https:\/\//i.test(url)?url:"#";
  const license=x.license||"Licencia no indicada";
  const status=x.status||x.publication_status||"review";
  const description=x.description||"Sin descripción aportada por la fuente.";
  return '<article class="item"><div class="item-top"><span class="tag">'+esc(labelType(x.type||x.category))+'</span><span class="status">'+esc(status==="pending"||status==="review"?"Pendiente de revisión":status)+'</span></div><h3>'+esc(x.name||x.repository||"Sin nombre")+'</h3><p>'+esc(description)+'</p><div class="meta"><span>'+esc(labelSource(x.source))+'</span><span>'+esc(license)+'</span>'+(x.stars!=null?'<span>★ '+esc(x.stars)+'</span>':"")+'</div><a class="open" href="'+esc(safeUrl)+'" target="_blank" rel="noopener noreferrer">Abrir fuente ↗</a></article>';
 }).join(""):'<div class="empty">No hay coincidencias. Cambia los filtros o prueba otra búsqueda.</div>';
 $("more").hidden=rows.length<=limit;
 $("more").textContent="Mostrar más ("+Math.min(48,rows.length-limit)+")";
}
["q","type","source","license"].forEach(id=>$(id).addEventListener(id==="q"?"input":"change",()=>{limit=48;render();}));
$("more").addEventListener("click",()=>{limit+=48;render();});
render();
</script>
</body>
</html>
"""


def main() -> None:
    if not FEED.exists():
        raise SystemExit(f"Missing prospection feed: {FEED}")
    feed = json.loads(FEED.read_text(encoding="utf-8"))
    items = feed.get("items", [])
    if not isinstance(items, list):
        raise SystemExit("Feed items must be a list")
    payload = json.dumps(feed, ensure_ascii=False, separators=(",", ":"))
    payload = (payload.replace("<", r"\u003c").replace(">", r"\u003e")
               .replace("&", r"\u0026").replace("\u2028", r"\u2028")
               .replace("\u2029", r"\u2029"))
    html = TEMPLATE.replace("__LOGO__", LOGO_SVG).replace("__DATA__", payload)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)} with {len(items)} discoveries")


if __name__ == "__main__":
    main()
