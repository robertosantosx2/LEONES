#!/usr/bin/env python3
"""Collect monthly CPU/RAM/NVIDIA GPU retail price observations.

The collector is deliberately conservative: it records only prices that can
be extracted from a configured retailer page. Missing/blocked pages produce
an explicit warning; they never create a guessed price.
"""
from __future__ import annotations
import csv, json, re, time
from datetime import date
from pathlib import Path
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
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (LEONES hardware price collector; +https://github.com/robertosantosx2/LEONES)'})
    with urlopen(req,timeout=30) as r:
        return r.read().decode('utf-8','ignore')

def jsonld_products(html):
    products=[]
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',html,re.S|re.I):
        try:
            obj=json.loads(raw.strip())
        except Exception:
            continue
        items=obj if isinstance(obj,list) else obj.get('@graph',[]) if isinstance(obj,dict) else []
        if isinstance(obj,dict) and obj.get('@type')=='Product': items=[obj]+items
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

def classify(name,kind,vendor):
    n=name.lower()
    if kind=='cpu':
        if vendor=='intel':
            m=re.search(r'\bcore\s+i([3579])\b',n)
            if not m: return None
            return f'Core i{m.group(1)}',None
        m=re.search(r'ryzen\s+([3579])\b',n)
        if not m: return None
        return f'Ryzen {m.group(1)}',None
    if kind=='ram':
        m=re.search(r'(ddr[45]).{0,100}?(\d{1,3})\s*gb',n)
        if not m: return None
        return 'Memory',int(m.group(2))
    if kind=='gpu':
        m=re.search(r'\b(geforce\s+)?(rtx\s*\d{4}(?:\s*ti(?:\s*super)?|\s*super)?)\b',n)
        if not m: return None
        v=re.search(r'(\d{1,3})\s*gb\b',n)
        return m.group(2).upper(), int(v.group(1)) if v else None
    return None

def load_obs():
    if not OBS.exists(): return []
    with OBS.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))

def save_obs(rows):
    OBS.parent.mkdir(parents=True,exist_ok=True)
    with OBS.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)

def build_summary(rows):
    # Latest observation per model/capacity, retaining only verified prices.
    latest={}
    for r in rows:
        if not r.get('price_eur'): continue
        key=(r['component_type'],r['vendor'],r['category'],r['model'],r['capacity_gb'],r['vram_gb'])
        old=latest.get(key)
        if old is None or r['observed_at']>=old['observed_at']: latest[key]=r
    out=[]
    for r in latest.values():
        out.append({
            'price_id':f"{r['component_type']}|{r['vendor']}|{r['model']}|{r['capacity_gb']}|{r['vram_gb']}",
            'component_type':r['component_type'],'vendor':r['vendor'],'category':r['category'],'model':r['model'],
            'capacity_gb':r['capacity_gb'],'price_eur':r['price_eur'],'price_type':'observed','market':'Spain','currency':'EUR',
            'source':r['source'],'observed_at':r['observed_at'],'valid_until':'','notes':r['notes']
        })
    fields=['price_id','component_type','vendor','category','model','capacity_gb','price_eur','price_type','market','currency','source','observed_at','valid_until','notes']
    with SUMMARY.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(sorted(out,key=lambda x:(x['component_type'],x['vendor'],x['category'],x['model'])))

def main():
    rows=load_obs(); existing={(r['observed_at'],r['component_type'],r['vendor'],r['model'],r['capacity_gb'],r['vram_gb']) for r in rows}
    added=0; failures=0
    for source,url,kind,vendor in SOURCES:
        try:
            html=fetch(url)
            products=jsonld_products(html)
            for name,price,purl in products:
                c=classify(name,kind,vendor)
                if not c: continue
                category,cap=c
                if kind=='gpu' and 'rtx' not in name.lower(): continue
                model=name
                key=(TODAY,kind,vendor,model,str(cap or ''),str(c[1] or ''))
                if key in existing: continue
                rows.append({'observed_at':TODAY,'component_type':kind,'vendor':vendor,'category':category,'model':model,'capacity_gb':str(cap or ''),'vram_gb':str(c[1] or '') if kind=='gpu' else '', 'price_eur':f'{price:.2f}','price_type':'observed','market':'Spain','currency':'EUR','source':source,'source_url':purl or url,'notes':'monthly automated retail observation; product listing price'})
                existing.add(key); added+=1
            time.sleep(1)
        except Exception as e:
            failures+=1; print(f'WARNING: {source} {url}: {e}')
    save_obs(rows); build_summary(rows)
    print(f'LEONES price collector: +{added} observations; sources failed={failures}; history={len(rows)}')
    if failures==len(SOURCES): raise SystemExit('All configured price sources failed; no fresh price evidence collected.')

if __name__=='__main__': main()
