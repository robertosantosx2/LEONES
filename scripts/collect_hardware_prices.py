#!/usr/bin/env python3
"""LEONES multi-source hardware price collector.

Collects CPU, RAM and NVIDIA GPU prices from the configured Spanish/EU
retail sources. Direct HTTP is attempted first; Jina Reader is used only as a
fallback. Each observation keeps source, URL and date. Unknown prices are
never estimated.
"""
from __future__ import annotations
import csv, json, re, time
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, quote_plus, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / 'data/hardware/hardware_price_observations.csv'
SUMMARY = ROOT / 'data/hardware/hardware_prices.csv'
MARKET = ROOT / 'data/hardware/hardware_price_market_summary.csv'
TARGETS = ROOT / 'data/hardware/price_source_targets.json'
TODAY = date.today().isoformat()
FIELDS = ['observed_at','component_type','vendor','category','model','capacity_gb','vram_gb','price_eur','price_type','market','currency','source','source_url','notes']

CPU_PAT = re.compile(r'\b(?:Intel\s+)?Core\s+i([3579])\b|\b(?:AMD\s+)?Ryzen\s+([3579])\b', re.I)
GPU_PAT = re.compile(r'\b(?:NVIDIA\s+)?(?:GeForce\s+)?(RTX\s*\d{3,4}(?:\s*(?:Ti|SUPER))?)\b', re.I)
RAM_PAT = re.compile(r'\bDDR([45])\b[^\n]{0,100}?\b(\d{1,3})\s*GB\b', re.I)
PRICE_PAT = re.compile(r'(?<!\d)(\d{1,5}(?:[.,]\d{2})?|\d{1,5}\s*\^\{\d{2}\})\s*(?:€|EUR)', re.I)

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            d=dict(attrs); href=d.get('href')
            if href: self.links.append(href)


def fetch(url: str) -> tuple[str,str]:
    headers={'User-Agent':'Mozilla/5.0 (compatible; LEONES-HardwarePriceBot/1.0; +https://github.com/robertosantosx2/LEONES)'}
    try:
        req=Request(url,headers=headers)
        with urlopen(req,timeout=35) as r: return r.read().decode('utf-8','ignore'), url
    except (HTTPError,URLError,TimeoutError) as direct_error:
        proxy='https://r.jina.ai/'+url
        try:
            req=Request(proxy,headers={'User-Agent':'LEONES-HardwarePriceBot/1.0'})
            with urlopen(req,timeout=60) as r:
                print(f'INFO: Jina fallback: {url}')
                return r.read().decode('utf-8','ignore'), url
        except Exception as proxy_error:
            raise RuntimeError(f'direct={direct_error}; jina={proxy_error}') from proxy_error


def parse_price(raw: str) -> float | None:
    s=raw.replace('€','').replace('EUR','').strip().replace(' ','')
    m=re.fullmatch(r'(\d+)\^\{(\d{2})\}',s)
    if m: return float(f'{m.group(1)}.{m.group(2)}')
    if ',' in s: s=s.replace('.','').replace(',','.')
    elif s.count('.')==1 and len(s.rsplit('.',1)[1])==2: pass
    else: s=s.replace('.','')
    try: p=float(s)
    except ValueError: return None
    return p if 5 <= p <= 10000 else None


def clean(text: str) -> str:
    text=unescape(re.sub(r'!\[[^\]]*\]\([^)]*\)',' ',text))
    text=re.sub(r'\[[^\]]*\]\([^)]*\)',' ',text)
    text=re.sub(r'\s+',' ',text).strip(' #-|:')
    text=re.sub(r'\b(?:Vendido y enviado|Envío gratis|Comparar|PVPR|opiniones|Stock|Disponible online)\b.*$','',text,flags=re.I)
    return text[:180].strip(' #-|:')


def jsonld_products(text: str):
    out=[]
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',text,re.S|re.I):
        try: obj=json.loads(raw.strip())
        except Exception: continue
        items=[]
        if isinstance(obj,list): items=obj
        elif isinstance(obj,dict): items=[obj]+(obj.get('@graph',[]) if isinstance(obj.get('@graph'),list) else [])
        for x in items:
            if not isinstance(x,dict) or x.get('@type')!='Product': continue
            offers=x.get('offers',{})
            if isinstance(offers,list): offers=offers[0] if offers else {}
            if not isinstance(offers,dict): continue
            p=offers.get('price')
            if p is None: continue
            try: p=float(str(p).replace(',','.'))
            except ValueError: continue
            out.append((clean(str(x.get('name',''))),p,str(offers.get('url',''))))
    return out


def text_products(text: str):
    # Works on ordinary HTML/text and Jina output, including PcComponentes 372 ^{77} €.
    lines=[re.sub(r'\s+',' ',unescape(x)).strip() for x in re.sub(r'<[^>]+>','\n',text).splitlines() if x.strip()]
    out=[]; seen=set()
    for i,line in enumerate(lines):
        for pm in PRICE_PAT.finditer(line):
            p=parse_price(pm.group(0))
            if p is None: continue
            prefix=line[:pm.start()]
            candidates=[prefix]
            candidates += lines[max(0,i-3):i]
            for cand in reversed(candidates):
                if not (CPU_PAT.search(cand) or GPU_PAT.search(cand) or RAM_PAT.search(cand)): continue
                name=clean(cand)
                if len(name)<4: continue
                key=(name.lower(),round(p,2))
                if key not in seen:
                    seen.add(key); out.append((name,p,''))
                break
    return out


def discover_links(seed: str, html: str, limit: int=6):
    parser=LinkParser();
    try: parser.feed(html)
    except Exception: return []
    base=urlparse(seed); candidates=[]
    keywords=('proces','cpu','ryzen','intel','memoria','ram','ddr','grafica','tarjeta','rtx','gpu','component')
    for href in parser.links:
        u=urljoin(seed,href); p=urlparse(u)
        if p.netloc!=base.netloc or u.startswith('mailto:'): continue
        score=sum(1 for k in keywords if k in u.lower())
        if score: candidates.append((score,u))
    return [u for _,u in sorted(set(candidates),reverse=True)[:limit]]


def classify(name: str):
    n=name.lower()
    m=CPU_PAT.search(n)
    if m:
        fam=m.group(1) or m.group(2)
        vendor='intel' if m.group(1) else 'amd'
        return 'cpu',vendor,f'Core i{fam}' if vendor=='intel' else f'Ryzen {fam}','',''
    m=RAM_PAT.search(n)
    if m: return 'ram', 'memory', f'DDR{m.group(1)}',m.group(2),''
    m=GPU_PAT.search(n)
    if m:
        v=re.search(r'\b(\d{1,3})\s*GB\b',n)
        return 'gpu','nvidia',m.group(1).upper(),' ',v.group(1) if v else ''
    return None


def extract_products(text: str):
    merged=[]; seen=set()
    for item in jsonld_products(text)+text_products(text):
        key=(item[0].lower(),round(item[1],2))
        if item[0] and key not in seen:
            seen.add(key); merged.append(item)
    return merged


def load_targets():
    return json.loads(TARGETS.read_text(encoding='utf-8'))


def load_obs():
    if not OBS.exists(): return []
    with OBS.open(encoding='utf-8',newline='') as f:
        return [r for r in csv.DictReader(f) if valid_row(r)]


def valid_row(r):
    model=(r.get('model') or '').strip(); p=r.get('price_eur') or ''
    if not model or len(model)>180 or 'http' in model or '###' in model: return False
    try: value=float(p.replace(',','.'))
    except ValueError: return False
    return 5<=value<=10000 and r.get('component_type') in {'cpu','ram','gpu'}


def save_obs(rows):
    OBS.parent.mkdir(parents=True,exist_ok=True)
    with OBS.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)


def build_outputs(rows):
    latest={}
    for r in rows:
        key=(r['component_type'],r['vendor'],r['category'],r['model'],r['capacity_gb'],r['vram_gb'])
        if key not in latest or r['observed_at']>=latest[key]['observed_at']: latest[key]=r
    sf=['price_id','component_type','vendor','category','model','capacity_gb','price_eur','price_type','market','currency','source','observed_at','valid_until','notes']
    summary=[]
    for r in latest.values():
        summary.append({'price_id':f"{r['component_type']}|{r['vendor']}|{r['model']}|{r['capacity_gb']}|{r['vram_gb']}",'component_type':r['component_type'],'vendor':r['vendor'],'category':r['category'],'model':r['model'],'capacity_gb':r['capacity_gb'],'price_eur':r['price_eur'],'price_type':'observed','market':'Spain','currency':'EUR','source':r['source'],'observed_at':r['observed_at'],'valid_until':'','notes':r['notes']})
    with SUMMARY.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=sf); w.writeheader(); w.writerows(sorted(summary,key=lambda x:(x['component_type'],x['vendor'],x['category'],x['model'])))

    groups={}
    for r in rows:
        key=(r['component_type'],r['vendor'],r['category'],r['model'],r['capacity_gb'],r['vram_gb'])
        groups.setdefault(key,[]).append(r)
    mf=['component_type','vendor','category','model','capacity_gb','vram_gb','source_count','sources','min_price_eur','median_price_eur','max_price_eur','latest_observed_at']
    market=[]
    for key,vals in groups.items():
        prices=sorted(float(x['price_eur']) for x in vals)
        mid=prices[len(prices)//2] if len(prices)%2 else (prices[len(prices)//2-1]+prices[len(prices)//2])/2
        market.append(dict(zip(mf,[*key,len(set(x['source'] for x in vals)), ';'.join(sorted(set(x['source'] for x in vals))),f'{min(prices):.2f}',f'{mid:.2f}',f'{max(prices):.2f}',max(x['observed_at'] for x in vals)])))
    with MARKET.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=mf); w.writeheader(); w.writerows(sorted(market,key=lambda x:(x['component_type'],x['vendor'],x['model'])))


def main():
    targets=load_targets(); rows=load_obs(); existing={(r['observed_at'],r['component_type'],r['vendor'],r['model'],r['capacity_gb'],r['vram_gb'],r['source']) for r in rows}
    added=extracted=failures=0; successful_sources=set()
    for sid,conf in targets.items():
        source_name={'ES-PCOMP':'PcComponentes','ES-AMAZON':'Amazon España','ES-COOLMOD':'Coolmod','ES-MEDIAMARKT':'MediaMarkt España','EU-LDLC':'LDLC España'}.get(sid,sid)
        urls=[]
        strategy=conf.get('strategy')
        if strategy=='search':
            urls=list(conf.get('urls',{}).values())
        elif strategy in {'category','discover'}:
            urls=list(conf.get('urls',{}).values())
        source_extracted=source_added=0
        for seed in urls:
            try:
                html,canonical=fetch(seed); pages=[(canonical,html)]
                if strategy=='discover':
                    for u in discover_links(seed,html):
                        try: pages.append((u,fetch(u)[0]))
                        except Exception: continue
                for page_url,page in pages:
                    products=extract_products(page); extracted+=len(products); source_extracted+=len(products)
                    for name,price,purl in products:
                        c=classify(name)
                        if not c: continue
                        kind,vendor,category,capacity,vram=c
                        if kind=='gpu' and vendor!='nvidia': continue
                        key=(TODAY,kind,vendor,name,str(capacity).strip(),str(vram).strip(),source_name)
                        if key in existing: continue
                        rows.append({'observed_at':TODAY,'component_type':kind,'vendor':vendor,'category':category,'model':name,'capacity_gb':str(capacity).strip(),'vram_gb':str(vram).strip(),'price_eur':f'{price:.2f}','price_type':'observed','market':'Spain','currency':'EUR','source':source_name,'source_url':purl or page_url,'notes':f'monthly automated observation; source_id={sid}'})
                        existing.add(key); added+=1; source_added+=1
                successful_sources.add(sid)
            except Exception as e:
                failures+=1; print(f'WARNING: {sid} {seed}: {e}')
            time.sleep(1)
        print(f'INFO: {sid} {source_name}: extracted={source_extracted} classified_new={source_added}')
    save_obs(rows); build_outputs(rows)
    print(f'LEONES price collector: +{added} observations; extracted={extracted}; sources_ok={len(successful_sources)}/{len(targets)}; source_attempt_failures={failures}; history={len(rows)}')
    if not rows: raise SystemExit('No valid price observations exist after collection.')
    if not successful_sources: raise SystemExit('All configured price sources failed.')
    if added==0: print('WARNING: no new observations; historical data preserved.')

if __name__=='__main__': main()
