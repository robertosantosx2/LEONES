#!/usr/bin/env python3
"""Mobile-LLMs-ARM prospecting and standalone HTML generator."""
import datetime as dt, html, json, os, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"research/mobile-llms-arm/sources.json"
OUT=ROOT/"web/data/mobile-llms-arm.json"
PAGE=ROOT/"web/mobile-llms-arm.html"
NOW=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
UA="LEONES-Mobile-LLMs-ARM/1.0"
QUERIES=[("android","Android on-device LLM inference","android"),("termux","Termux llama.cpp local LLM","linux-mobile"),("arm","ARM mobile LLM inference","arm"),("npu","mobile NPU LLM inference","accelerators"),("hexagon","Qualcomm Hexagon LLM inference","accelerators"),("embedded","embedded ARM local LLM","embedded"),("runtimes","LiteRT ExecuTorch MLC LLM Android","runtime")]
REDDIT=["LocalLLaMA","LocalLLM","termux"]
X=[("X · on-device LLM ARM","https://x.com/search?q=%22on-device%20LLM%22%20ARM&src=typed_query"),("X · Android Hexagon LLM","https://x.com/search?q=Android%20Hexagon%20LLM&src=typed_query"),("X · Termux local AI","https://x.com/search?q=Termux%20local%20AI&src=typed_query"),("X · mobile inference NPU","https://x.com/search?q=mobile%20inference%20NPU&src=typed_query")]
def get(url,headers=None):
 h={"User-Agent":UA,"Accept":"application/vnd.github+json, application/json"};h.update(headers or {})
 with urlopen(Request(url,headers=h),timeout=20) as r:return json.loads(r.read().decode())
def main():
 reg=json.loads(REG.read_text());token=os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN","");items=[];gh=[];reddit=[]
 for x in reg["seed_projects"]:items.append({**x,"source":"curated research lead","status":"pending_review","discovered_at":NOW})
 for key,q,cat in QUERIES:
  headers={"X-GitHub-Api-Version":"2022-11-28"}
  if token:headers["Authorization"]="Bearer "+token
  url="https://api.github.com/search/repositories?"+urlencode({"q":q+" fork:false","sort":"updated","order":"desc","per_page":12})
  try:
   data=get(url,headers);gh.append({"query":key,"status":"ok","total_count":data.get("total_count",0)})
   for x in data.get("items",[]):items.append({"name":x["full_name"],"url":x["html_url"],"category":cat,"platforms":[],"description":x.get("description") or "","stars":x.get("stargazers_count",0),"pushed_at":x.get("pushed_at"),"license":(x.get("license") or {}).get("spdx_id"),"language":x.get("language"),"source":"GitHub Search API","status":"discovered","discovered_at":NOW})
  except Exception as e:gh.append({"query":key,"status":"error","error":str(e)[:300]})
 for sub in REDDIT:
  url="https://www.reddit.com/r/"+sub+"/search.json?"+urlencode({"q":"Android OR mobile OR ARM OR Snapdragon OR Hexagon OR llama.cpp","restrict_sr":"1","sort":"new","limit":15})
  try:
   data=get(url,{"User-Agent":"LEONES research bot"})
   children=data.get("data",{}).get("children",[])
   for c in children:
    x=c.get("data",{});items.append({"name":x.get("title","Reddit post"),"url":"https://www.reddit.com"+x.get("permalink",""),"category":"community-report","platforms":["community"],"description":(x.get("selftext") or "")[:450],"source":"Reddit public search","status":"community-lead","created_utc":x.get("created_utc")})
   reddit.append({"subreddit":sub,"status":"ok","items":len(children)})
  except Exception as e:reddit.append({"subreddit":sub,"status":"unavailable","error":str(e)[:250]})
  time.sleep(1)
 merged={}
 for x in items:
  key=x.get("url","").rstrip("/")
  if key:merged.setdefault(key,{}).update(x)
 payload={"schema_version":1,"project":"Mobile-LLMs-ARM","generated_at":NOW,"publication_is_not_approval":True,"automatic_recommendation":False,"items":sorted(merged.values(),key=lambda x:(x.get("category",""),x.get("name","").lower())),"sources":{"github":gh,"reddit":reddit,"x":"search links only; no authorized API ingestion configured"},"social_searches":[{"label":n,"url":u} for n,u in X]+[{"label":"Reddit · "+s,"url":"https://www.reddit.com/r/"+s+"/search/?q=Android%20OR%20ARM%20OR%20LLM&sort=new"} for s in REDDIT]}
 OUT.parent.mkdir(parents=True,exist_ok=True);PAGE.parent.mkdir(parents=True,exist_ok=True)
 data=json.dumps(payload,ensure_ascii=False,separators=(",",":")).replace("</","<\\/")
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
 page='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mobile-LLMs-ARM · LEONES</title><style>
:root{color-scheme:dark;--bg:#0b1117;--panel:#14232e;--line:#2a3c49;--text:#eaf2f7;--muted:#9bb0bd;--cyan:#62d7d0;--gold:#f2c879}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 75% -10%,#16434b,transparent 40%),linear-gradient(#101b24,var(--bg) 55%);color:var(--text);font:15px/1.6 system-ui,sans-serif}.wrap{max-width:1200px;margin:auto;padding:28px 20px 60px}a{color:var(--cyan);text-decoration:none}.top{display:flex;justify-content:space-between}.hero{padding:55px 0 25px}.eyebrow,.tag{color:var(--cyan);font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.hero h1{font-size:clamp(42px,7vw,76px);line-height:1;margin:12px 0}.hero h1 span{color:var(--cyan)}.hero p{font-size:18px;color:#b7c8d2;max-width:800px}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.metric,.card,.panel{background:linear-gradient(145deg,#172833,#101922);border:1px solid var(--line);border-radius:15px}.metric{padding:16px}.metric strong{display:block;color:var(--gold);font-size:27px}.muted{color:var(--muted)}.toolbar{display:flex;gap:10px;margin:22px 0;flex-wrap:wrap}input,select{background:#101a23;color:var(--text);border:1px solid var(--line);border-radius:9px;padding:12px;font:inherit}.search{flex:1;min-width:230px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.card{padding:17px;min-height:210px;display:flex;flex-direction:column}.card h3{font-size:17px;margin:8px 0}.card p{font-size:13px;color:#b7c8d2}.meta{margin-top:auto;padding-top:10px;border-top:1px solid var(--line);font-size:11px;color:var(--muted);overflow-wrap:anywhere}.panel{padding:20px;margin:22px 0}.links{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}.links a{padding:10px;border:1px solid var(--line);border-radius:8px}.notice{background:#29271f;border-color:#695a39;color:#d3c9b1}footer{margin-top:35px;border-top:1px solid var(--line);padding-top:15px;color:var(--muted);font-size:12px}@media(max-width:800px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.grid,.links,.metrics{grid-template-columns:1fr}.wrap{padding:18px 13px}}</style></head><body><main class="wrap"><nav class="top"><a href="../index.html">LEONES / RESEARCH</a><a href="https://github.com/robertosantosx2/LEONES">Repositorio ↗</a></nav><header class="hero"><div class="eyebrow">Android · Linux ARM · Edge AI</div><h1>Mobile-LLMs-<span>ARM</span></h1><p>Observatorio de LLMs e IA local en teléfonos, Linux móvil y sistemas embebidos ARM. Runtimes, CPU/GPU/NPU, modelos, benchmarks, energía y clústeres.</p></header><section class="metrics"><div class="metric"><strong id="count">—</strong>Entradas</div><div class="metric"><strong id="gh">—</strong>GitHub</div><div class="metric"><strong id="date">—</strong>Actualización</div></section><div class="toolbar"><input id="q" class="search" placeholder="Buscar proyecto, SoC, runtime…"><select id="cat"><option value="">Todas las categorías</option></select></div><div id="catalog" class="grid"></div><section class="panel"><h2>Roadmap técnico</h2><p>G0 inventario · G1 matriz SoC/OS · G2 runtimes/modelos · G3 benchmark NEPENTHES · G4 Linux móvil · G5 clústeres REDIL · G6 curación.</p><a href="../docs/subprojects/Mobile-LLMs-ARM/ROADMAP.md">Roadmap completo ↗</a> · <a href="../docs/subprojects/Mobile-LLMs-ARM/README.md">Documentación ↗</a></section><section class="panel"><h2>Prospección comunitaria</h2><p class="muted">Reddit se consulta mediante endpoints públicos cuando están disponibles. X se ofrece como búsquedas directas, sin simular acceso automatizado.</p><div class="links" id="social"></div></section><section class="panel notice"><b>Descubierto ≠ aprobado ≠ medido.</b> Las pistas sociales no son pruebas de ejecución. Los resultados físicos requieren dispositivo identificado, protocolo y artefactos. No se aprueba ni recomienda automáticamente software.</section><footer>LEONES · Mobile-LLMs-ARM · Catálogo autocontenido · <span id="stamp"></span></footer></main><script id="data" type="application/json">__DATA__</script><script>
const d=JSON.parse(document.getElementById('data').textContent),$=x=>document.getElementById(x);$('count').textContent=d.items.length;$('gh').textContent=d.items.filter(x=>(x.source||'').includes('GitHub')).length;$('date').textContent=new Date(d.generated_at).toLocaleDateString('es-ES');$('stamp').textContent=new Date(d.generated_at).toLocaleString('es-ES');[...new Set(d.items.map(x=>x.category||'other'))].sort().forEach(c=>{let o=document.createElement('option');o.value=c;o.textContent=c;$('cat').append(o)});
function render(){let q=$('q').value.toLowerCase(),c=$('cat').value;let xs=d.items.filter(x=>(!c||x.category===c)&&[x.name,x.description,x.category,(x.platforms||[]).join(' ')].join(' ').toLowerCase().includes(q));$('catalog').replaceChildren();xs.forEach(x=>{let a=document.createElement('article');a.className='card';let t=document.createElement('div');t.className='tag';t.textContent=x.category||'other';let h=document.createElement('h3');h.textContent=x.name;let p=document.createElement('p');p.textContent=x.description||'';let m=document.createElement('div');m.className='meta';m.textContent=(x.status||'discovered')+' · '+(x.source||'source pending');let l=document.createElement('a');l.href=x.url;l.target='_blank';l.rel='noopener';l.textContent='Abrir fuente ↗';a.append(t,h,p,m,l);$('catalog').append(a)});if(!xs.length)$('catalog').textContent='No hay resultados.'}
$('q').addEventListener('input',render);$('cat').addEventListener('change',render);render();d.social_searches.forEach(x=>{let a=document.createElement('a');a.href=x.url;a.target='_blank';a.rel='noopener';a.textContent=x.label+' ↗';$('social').append(a)});
</script></body></html>'''
 PAGE.write_text(page.replace("__DATA__",data),encoding="utf-8")
 print(json.dumps({"items":len(payload["items"]),"github_queries":len(gh),"reddit_sources":len(reddit)}))
if __name__=="__main__":main()
