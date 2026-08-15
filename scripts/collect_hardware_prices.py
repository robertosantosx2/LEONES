#!/usr/bin/env python3
"""LEONES multi-source hardware price collector.

Prices are market-order-of-magnitude observations. The recommender uses
10-euro precision: values are rounded to the nearest €10 after observation.
Unknown prices are never estimated.
"""
from __future__ import annotations
import csv, json, re, time
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
OBS=ROOT/'data/hardware/hardware_price_observations.csv'; SUMMARY=ROOT/'data/hardware/hardware_prices.csv'; MARKET=ROOT/'data/hardware/hardware_price_market_summary.csv'; TARGETS=ROOT/'data/hardware/price_source_targets.json'; TODAY=date.today().isoformat()
FIELDS=['observed_at','component_type','vendor','category','model','capacity_gb','vram_gb','price_eur','price_type','market','currency','source','source_url','notes']
CPU_PAT=re.compile(r'\b(?:Intel\s+)?Core\s+i([3579])\b|\b(?:AMD\s+)?Ryzen\s+([3579])\b',re.I); GPU_PAT=re.compile(r'\b(?:NVIDIA\s+)?(?:GeForce\s+)?(RTX\s*\d{3,4}(?:\s*(?:Ti|SUPER))?)\b',re.I); RAM_PAT=re.compile(r'\bDDR([45])\b[^\n]{0,120}?\b(\d{1,3})\s*GB\b|\b(\d{1,3})\s*GB\b[^\n]{0,120}?\bDDR([45])\b',re.I); PRICE_PAT=re.compile(r'(?<!\d)(\d{1,5}(?:[.,]\d{2})?|\d{1,5}\s*\^\{\d{2}\})\s*(?:€|EUR)',re.I)
class LinkParser(HTMLParser):
 def __init__(self): super().__init__(); self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag.lower()=='a':
   h=dict(attrs).get('href');
   if h:self.links.append(h)
def fetch(url):
 try:
  with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; LEONES-HardwarePriceBot/1.0)'}),timeout=35) as r:return r.read().decode('utf-8','ignore'),url
 except (HTTPError,URLError,TimeoutError) as e:
  proxy='https://r.jina.ai/'+url
  try:
   with urlopen(Request(proxy,headers={'User-Agent':'LEONES-HardwarePriceBot/1.0'}),timeout=60) as r:return r.read().decode('utf-8','ignore'),url
  except Exception as pe: raise RuntimeError(f'direct={e}; jina={pe}') from pe
def parse_price(raw):
 s=raw.replace('€','').replace('EUR','').strip().replace(' ',''); m=re.fullmatch(r'(\d+)\^\{(\d{2})\}',s)
 if m:return float(f'{m.group(1)}.{m.group(2)}')
 if ',' in s:s=s.replace('.','').replace(',','.')
 elif not(s.count('.')==1 and len(s.rsplit('.',1)[1])==2):s=s.replace('.','')
 try:p=float(s)
 except ValueError:return None
 return p if 5<=p<=10000 else None
def round10(price): return float(int(price/10+0.5)*10)
def clean(t):
 t=unescape(re.sub(r'!\[[^\]]*\]\([^)]*\)',' ',t)); t=re.sub(r'\[[^\]]*\]\([^)]*\)',' ',t); return re.sub(r'\s+',' ',t).strip(' #-|:')[:180]
def jsonld_products(text):
 out=[]
 for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',text,re.S|re.I):
  try:o=json.loads(raw.strip())
  except Exception:continue
  items=o if isinstance(o,list) else [o]+(o.get('@graph',[]) if isinstance(o,dict) and isinstance(o.get('@graph'),list) else [])
  for x in items:
   if not isinstance(x,dict) or x.get('@type')!='Product':continue
   off=x.get('offers',{}); off=off[0] if isinstance(off,list) and off else off
   try:p=float(str(off.get('price')).replace(',','.'))
   except Exception:continue
   name=clean(str(x.get('name','')))
   if name:out.append((name,p,str(off.get('url','')),name))
 return out
def text_products(text):
 lines=[re.sub(r'\s+',' ',unescape(x)).strip() for x in re.sub(r'<[^>]+>','\n',text).splitlines() if x.strip()]; out=[]; seen=set()
 for i,line in enumerate(lines):
  for pm in PRICE_PAT.finditer(line):
   p=parse_price(pm.group(0));
   if p is None:continue
   window=lines[max(0,i-16):i+1]; candidates=[c for c in reversed(window[:-1]) if CPU_PAT.search(c) or GPU_PAT.search(c) or RAM_PAT.search(c) or 'procesador -' in c.lower() or 'memoria ram -' in c.lower() or 'tarjeta gráfica -' in c.lower() or 'tarjeta grafica -' in c.lower()]
   if not candidates:continue
   name=clean(candidates[0]); key=(name.lower(),round10(p))
   if key not in seen and len(name)>=4:seen.add(key);out.append((name,p,'',' | '.join(window)))
 return out
def discover_links(seed,html,limit=12):
 parser=LinkParser();
 try:parser.feed(html)
 except Exception:return []
 base=urlparse(seed); keys=('proces','cpu','ryzen','intel','memoria','ram','ddr','grafica','tarjeta','rtx','gpu','component'); c=[]
 for h in parser.links:
  u=urljoin(seed,h); p=urlparse(u)
  if p.netloc!=base.netloc or u.startswith('mailto:'):continue
  score=sum(k in u.lower() for k in keys)
  if score:c.append((score,u))
 return [u for _,u in sorted(set(c),reverse=True)[:limit]]
def classify(name):
 n=name.lower(); m=CPU_PAT.search(n)
 if m:
  f=m.group(1) or m.group(2);v='intel' if m.group(1) else 'amd';return 'cpu',v,f'Core i{f}' if v=='intel' else f'Ryzen {f}','',''
 m=RAM_PAT.search(n)
 if m:
  d=m.group(1) or m.group(4);cap=m.group(2) or m.group(3);return 'ram','memory',f'DDR{d}',cap,''
 m=GPU_PAT.search(n)
 if m:
  v=re.search(r'\b(\d{1,3})\s*GB\b',n);return 'gpu','nvidia',m.group(1).upper(),' ',v.group(1) if v else ''
 return None
def extract_products(text):
 merged=[];seen=set()
 for x in jsonld_products(text)+text_products(text):
  k=(x[0].lower(),round10(x[1]))
  if x[0] and k not in seen:seen.add(k);merged.append(x)
 return merged
def load_targets():return json.loads(TARGETS.read_text(encoding='utf-8'))
def load_obs():
 if not OBS.exists():return []
 with OBS.open(encoding='utf-8',newline='') as f:return [r for r in csv.DictReader(f) if valid_row(r)]
def valid_row(r):
 try:p=float(r.get('price_eur','').replace(',','.'))
 except ValueError:return False
 m=(r.get('model') or '').strip();return bool(m) and len(m)<=180 and 'http' not in m and '###' not in m and 5<=p<=10000 and r.get('component_type') in {'cpu','ram','gpu'}
def save_obs(rows):
 OBS.parent.mkdir(parents=True,exist_ok=True)
 with OBS.open('w',encoding='utf-8',newline='') as f:csv.DictWriter(f,fieldnames=FIELDS).writerows([]) if False else None; w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
def build_outputs(rows):
 latest={}
 for r in rows:
  k=(r['component_type'],r['vendor'],r['category'],r['model'],r['capacity_gb'],r['vram_gb']);latest[k]=r
 sf=['price_id','component_type','vendor','category','model','capacity_gb','price_eur','price_type','market','currency','source','observed_at','valid_until','notes'];summary=[]
 for r in latest.values():summary.append(dict(zip(sf,[f"{r['component_type']}|{r['vendor']}|{r['model']}|{r['capacity_gb']}|{r['vram_gb']}",r['component_type'],r['vendor'],r['category'],r['model'],r['capacity_gb'],r['price_eur'],'observed','Spain','EUR',r['source'],r['observed_at'],'',r['notes']])))
 with SUMMARY.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=sf);w.writeheader();w.writerows(summary)
 groups={}
 for r in rows:groups.setdefault((r['component_type'],r['vendor'],r['category'],r['model'],r['capacity_gb'],r['vram_gb']),[]).append(r)
 mf=['component_type','vendor','category','model','capacity_gb','vram_gb','source_count','sources','min_price_eur','median_price_eur','max_price_eur','latest_observed_at'];market=[]
 for k,vs in groups.items():
  ps=sorted(float(x['price_eur']) for x in vs);med=ps[len(ps)//2] if len(ps)%2 else (ps[len(ps)//2-1]+ps[len(ps)//2])/2;market.append(dict(zip(mf,[*k,len(set(x['source'] for x in vs)),';'.join(sorted(set(x['source'] for x in vs))),f'{min(ps):.0f}',f'{med:.0f}',f'{max(ps):.0f}',max(x['observed_at'] for x in vs)])))
 with MARKET.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=mf);w.writeheader();w.writerows(market)
def main():
 targets=load_targets();rows=load_obs();existing={(r['observed_at'],r['component_type'],r['vendor'],r['model'],r['capacity_gb'],r['vram_gb'],r['source']) for r in rows};added=extracted=failures=0;successful=set()
 # Source priority: Coolmod first, then supporting sources. Missing-price gaps are never estimated.
 order=sorted(targets,key=lambda sid:0 if sid=='ES-COOLMOD' else 1)
 for sid in order:
  conf=targets[sid];name={'ES-PCOMP':'PcComponentes','ES-COOLMOD':'Coolmod','ES-MEDIAMARKT':'MediaMarkt España','EU-LDLC':'LDLC España'}.get(sid,sid);se=sa=0
  for seed in conf.get('urls',{}).values():
   try:
    html,canon=fetch(seed);pages=[(canon,html)]
    if conf.get('strategy')=='discover':pages += [(u,fetch(u)[0]) for u in discover_links(seed,html)]
    for pu,page in pages:
     products=extract_products(page);extracted+=len(products);se+=len(products)
     for name0,price,purl,ctx in products:
      c=classify(f'{name0} | {ctx}');
      if not c:continue
      kind,vendor,cat,cap,vram=c
      if kind=='gpu' and vendor!='nvidia':continue
      price=round10(price);key=(TODAY,kind,vendor,name0,str(cap).strip(),str(vram).strip(),name)
      if key in existing:continue
      rows.append({'observed_at':TODAY,'component_type':kind,'vendor':vendor,'category':cat,'model':name0,'capacity_gb':str(cap).strip(),'vram_gb':str(vram).strip(),'price_eur':f'{price:.0f}','price_type':'observed_order_of_magnitude','market':'Spain','currency':'EUR','source':name,'source_url':purl or pu,'notes':f'monthly observation; price precision=10 EUR; source_id={sid}' });existing.add(key);added+=1;sa+=1
    successful.add(sid)
   except Exception as e:failures+=1;print(f'WARNING: {sid} {seed}: {e}')
   time.sleep(.5)
  print(f'INFO: {sid} {name}: extracted={se} classified_new={sa}')
 save_obs(rows);build_outputs(rows);print(f'LEONES price collector: +{added} observations; extracted={extracted}; sources_ok={len(successful)}/{len(targets)}; source_attempt_failures={failures}; history={len(rows)}')
 if not rows:raise SystemExit('No valid price observations exist after collection.')
if __name__=='__main__':main()
