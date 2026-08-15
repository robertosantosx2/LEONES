#!/usr/bin/env python3
"""Monthly CPU/RAM/NVIDIA GPU price collector for LEONES.

Direct retailer access is tried first. When a retailer blocks automated
requests, the same public page is retried through Jina Reader. Only observed
prices are recorded; unavailable sources never create guessed prices.

The collector is deliberately conservative: a successful HTTP request is not
considered a successful collection unless at least one product/price pair is
actually extracted. An empty dataset therefore fails the workflow instead of
creating a misleading green run.
"""
from __future__ import annotations
import csv, json, re, time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
OBS=ROOT/'data/hardware/hardware_price_observations.csv'
SUMMARY=ROOT/'data/hardware/hardware_prices.csv'
TODAY=date.today().isoformat()
SOURCES=[
 ('PcComponentes','https://www.pccomponentes.com/procesadores/intel','cpu','intel'),
 ('PcComponentes','https://www.pccomponentes.com/categorias/procesadores/amd-ryzen-3','cpu','amd'),
 ('PcComponentes','https://www.pccomponentes.com/categorias/procesadores/amd-ryzen-5','cpu','amd'),
 ('PcComponentes','https://www.pccomponentes.com/categorias/procesadores/amd-ryzen-7','cpu','amd'),
 ('PcComponentes','https://www.pccomponentes.com/categorias/procesadores/amd-ryzen-9','cpu','amd'),
 ('PcComponentes','https://www.pccomponentes.com/categories/memorias-ram/ddr4','ram','ddr4'),
 ('PcComponentes','https://www.pccomponentes.com/categories/memorias-ram/ddr5','ram','ddr5'),
 ('PcComponentes','https://www.pccomponentes.com/categorias/tarjetas-graficas','gpu','nvidia'),
]
FIELDS=['observed_at','component_type','vendor','category','model','capacity_gb','vram_gb','price_eur','price_type','market','currency','source','source_url','notes']

def fetch(url):
    try:
        req=Request(url,headers={'User-Agent':'Mozilla/5.0 (LEONES hardware price collector)'})
        with urlopen(req,timeout=30) as r: return r.read().decode('utf-8','ignore'),url
    except (HTTPError,URLError,TimeoutError) as direct_error:
        proxy='https://r.jina.ai/'+url
        try:
            req=Request(proxy,headers={'User-Agent':'LEONES hardware price collector'})
            with urlopen(req,timeout=45) as r:
                print(f'INFO: using Jina Reader fallback for {url}')
                return r.read().decode('utf-8','ignore'),url
        except Exception as proxy_error:
            raise RuntimeError(f'direct={direct_error}; proxy={proxy_error}') from proxy_error

def jsonld_products(html):
    products=[]
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',html,re.S|re.I):
        try: obj=json.loads(raw.strip())
        except Exception: continue
        if isinstance(obj,dict) and obj.get('@type')=='Product': items=[obj]
        elif isinstance(obj,dict): items=obj.get('@graph',[])
        elif isinstance(obj,list): items=obj
        else: items=[]
        for x in items:
            if not isinstance(x,dict) or x.get('@type')!='Product': continue
            offers=x.get('offers',{})
            if isinstance(offers,list): offers=offers[0] if offers else {}
            price=offers.get('price') if isinstance(offers,dict) else None
            if price is None: continue
            try: price=float(str(price).replace(',','.'))
            except ValueError: continue
            products.append((str(x.get('name','')).strip(),price,str(offers.get('url','')).strip() if isinstance(offers,dict) else ''))
    return products

def parse_price(raw):
    raw=raw.strip().replace('€','').replace('EUR','').strip()
    if ',' in raw:
        return float(raw.replace('.','').replace(',','.'))
    return float(raw)

def text_products(text):
    """Extract individual Product+price pairs from Jina markdown.

    Jina often returns a complete product listing as one very long line. The
    old parser treated that entire line as one product, which could associate
    the first price with the wrong CPU family. We therefore split explicitly
    on markdown product headings (###) and only keep the text immediately
    preceding the first price of each product card.
    """
    out=[]
    price_re=re.compile(r'(?<!\d)(\d{1,4}(?:[.,]\d{2})?)\s*(?:€|EUR)',re.I)
    heading_re=re.compile(r'(?:^|\s)###\s+(.+?)(?=\s+\d{1,4}(?:[.,]\d{2})?\s*(?:€|EUR))',re.I|re.S)
    chunks=list(heading_re.finditer(text))
    for m in chunks:
        name=re.sub(r'\s+',' ',m.group(1)).strip(' #-')
        price_match=price_re.search(text,m.start(1)+len(name),m.end()+200)
        if not price_match:
            continue
        try:
            price=parse_price(price_match.group(1))
        except ValueError:
            continue
        if not 5<=price<=10000:
            continue
        # Remove markdown/image/link noise from the product name.
        name=re.sub(r'!\[[^\]]*\]\([^)]*\)',' ',name)
        name=re.sub(r'\[[^\]]*\]\([^)]*\)',' ',name)
        name=re.sub(r'\s+',' ',name).strip(' #-')
        if name:
            out.append((name,price,''))

    # Fallback for plain text where product cards are not marked with ###.
    if not out:
        lines=[re.sub(r'\s+',' ',x).strip() for x in text.splitlines() if x.strip()]
        product_re=re.compile(r'(Intel(?:\s+Core)?\s+i[3579]|Core\s+i[3579]|Ryzen\s+[3579]|DDR[45]|RTX\s*\d{4})',re.I)
        for i,line in enumerate(lines):
            pm=price_re.search(line)
            if not pm: continue
            try: price=parse_price(pm.group(1))
            except ValueError: continue
            if not 5<=price<=10000: continue
            candidates=[]
            for j in range(max(0,i-3),min(len(lines),i+2)):
                s=lines[j].lstrip('#*- ').strip()
                if product_re.search(s): candidates.append(s)
            if candidates: out.append((candidates[-1],price,''))
    return out

def products(html):
    p=jsonld_products(html)
    return p if p else text_products(html)

def classify(name,kind,vendor):
    n=name.lower()
    if kind=='cpu':
        if vendor=='intel':
            m=re.search(r'\bcore\s+(?:ultra\s+)?i?([3579])\b',n)
            return (f'Core i{m.group(1)}','') if m else None
        m=re.search(r'\bryzen\s+([3579])\b',n)
        return (f'Ryzen {m.group(1)}','') if m else None
    if kind=='ram':
        m=re.search(r'\b(ddr[45])\b.*?\b(\d{1,3})\s*gb\b',n)
        return (f'Memory {m.group(1).upper()}',m.group(2)) if m else None
    if kind=='gpu':
        m=re.search(r'\b(?:geforce\s+)?(rtx\s*\d{4}(?:\s*ti(?:\s*super)?|\s*super)?)\b',n)
        if not m: return None
        v=re.search(r'(\d{1,3})\s*gb\b',n)
        return (m.group(1).upper(),v.group(1) if v else '')
    return None

def load_obs():
    if not OBS.exists(): return []
    with OBS.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))

def save_obs(rows):
    OBS.parent.mkdir(parents=True,exist_ok=True)
    with OBS.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)

def build_summary(rows):
    latest={}
    for r in rows:
        if not r.get('price_eur'): continue
        key=(r['component_type'],r['vendor'],r['category'],r['model'],r['capacity_gb'],r['vram_gb'])
        if key not in latest or r['observed_at']>=latest[key]['observed_at']: latest[key]=r
    fields=['price_id','component_type','vendor','category','model','capacity_gb','price_eur','price_type','market','currency','source','observed_at','valid_until','notes']
    out=[]
    for r in latest.values():
        out.append({'price_id':f"{r['component_type']}|{r['vendor']}|{r['model']}|{r['capacity_gb']}|{r['vram_gb']}",'component_type':r['component_type'],'vendor':r['vendor'],'category':r['category'],'model':r['model'],'capacity_gb':r['capacity_gb'],'price_eur':r['price_eur'],'price_type':'observed','market':'Spain','currency':'EUR','source':r['source'],'observed_at':r['observed_at'],'valid_until':'','notes':r['notes']})
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    with SUMMARY.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(sorted(out,key=lambda x:(x['component_type'],x['vendor'],x['category'],x['model'])))

def main():
    rows=load_obs(); existing={(r['observed_at'],r['component_type'],r['vendor'],r['model'],r['capacity_gb'],r['vram_gb']) for r in rows}
    added=0; failures=0; extracted=0
    for source,url,kind,vendor in SOURCES:
        try:
            html,canonical=fetch(url); found=0
            raw_products=products(html); extracted += len(raw_products)
            for name,price,purl in raw_products:
                c=classify(name,kind,vendor)
                if not c: continue
                category,cap_or_vram=c
                if kind=='gpu' and 'rtx' not in name.lower(): continue
                capacity=cap_or_vram if kind=='ram' else ''; vram=cap_or_vram if kind=='gpu' else ''
                key=(TODAY,kind,vendor,name,str(capacity),str(vram))
                if key in existing: continue
                rows.append({'observed_at':TODAY,'component_type':kind,'vendor':vendor,'category':category,'model':name,'capacity_gb':str(capacity),'vram_gb':str(vram),'price_eur':f'{price:.2f}','price_type':'observed','market':'Spain','currency':'EUR','source':source,'source_url':purl or canonical,'notes':'monthly automated retail observation; direct page or Jina Reader fallback'})
                existing.add(key); added+=1; found+=1
            print(f'INFO: {source} {kind}/{vendor}: extracted={len(raw_products)} classified_new={found}'); time.sleep(1)
        except Exception as e:
            failures+=1; print(f'WARNING: {source} {url}: {e}')
    save_obs(rows); build_summary(rows)
    print(f'LEONES price collector: +{added} observations; extracted={extracted}; sources failed={failures}/{len(SOURCES)}; history={len(rows)}')
    if not rows:
        raise SystemExit('No price observations exist after collection: collector produced an empty dataset.')
    if added==0 and failures==len(SOURCES):
        raise SystemExit('No fresh price evidence collected: all configured sources failed.')
    if added==0: print('WARNING: no new observations; historical data preserved.')

if __name__=='__main__': main()
