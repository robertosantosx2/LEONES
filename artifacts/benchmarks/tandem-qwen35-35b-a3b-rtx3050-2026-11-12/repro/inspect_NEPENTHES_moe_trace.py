#!/usr/bin/env python3
"""Summarize llama.cpp MCT1 MoE routing traces and verbose cache logs."""
from __future__ import annotations
import argparse,collections,json,math,pathlib,re,struct

def read_trace(path):
    data=pathlib.Path(path).read_bytes()
    if len(data)<16 or data[:4]!=b'MCT1':raise ValueError('Not a supported MCT1 MoE cache trace')
    pos=4
    def take(fmt):
        nonlocal pos
        n=struct.calcsize('<'+fmt)
        if pos+n>len(data):raise ValueError('Truncated MCT1 trace')
        v=struct.unpack_from('<'+fmt,data,pos);pos+=n;return v
    n_layer,n_used,n_group=take('3I');groups=[];layer_experts={}
    for _ in range(n_group):
        _device,n_exp,n_layers=take('3I');layers=list(take(f'{n_layers}I'));split,split_sum=take('2d');host,dev,align=take('3Q');(nt,)=take('I');sizes=list(take(f'{nt}Q'))
        groups.append({'layers':layers,'experts_per_layer':n_exp,'split':split,'split_sum':split_sum,'host_bytes':host,'device_host_bytes':dev,'alignment':align,'expert_tensor_bytes':sum(sizes)})
        for layer in layers:layer_experts[layer]=n_exp
    counts=collections.defaultdict(collections.Counter);tokens=collections.Counter();records=events=0
    while pos<len(data):
        layer,k,n_ids=take('3i')
        if k<=0 or n_ids<0 or n_ids%k:raise ValueError(f'Invalid routing record at byte {pos}')
        ids=take(f'{n_ids}i')
        if layer<0 or layer>=n_layer:raise ValueError(f'Invalid layer {layer}')
        records+=1;tokens[layer]+=n_ids//k;events+=n_ids;counts[layer].update(ids)
    per={}
    for layer,c in sorted(counts.items()):
        total=sum(c.values());n=layer_experts.get(layer);probs=[v/total for v in c.values()] if total else []
        entropy=-sum(p*math.log2(p) for p in probs if p)
        mean=total/n if n else None
        cv=(math.sqrt(sum((v-mean)**2 for v in c.values())/len(c))/mean) if mean and c else None
        per[str(layer)]={'routing_events':total,'tokens_observed':tokens[layer],'unique_experts_seen':len(c),'experts_in_layer':n,'expert_coverage_pct':100*len(c)/n if n else None,'routing_entropy_bits':entropy,'observed_expert_count_cv':cv,'top_experts':c.most_common(10)}
    return {'format':'MCT1','bytes':len(data),'n_layers':n_layer,'experts_selected_per_token':n_used,'groups':groups,'record_count':records,'routing_events':events,'tokens_observed_by_layer':dict(tokens),'per_layer':per,'limitations':['MCT1 records selected expert IDs by layer but no explicit prefill/decode phase or wall-clock timestamps.','Routing distribution is not cache hit rate, transfer latency, or expert compute time.']}
def read_log(path):
    text=pathlib.Path(path).read_text(errors='replace');r={'cache_log_lines':0,'hits':0,'misses':0,'misses_on_cpu':0,'uploaded_mib':0.0}
    pattern=r'llama_moe_cache: ubatch .*?: hits = (\\d+), misses = (\\d+)(?: \\((\\d+) on the CPU\\))?, hit rate = [0-9.]+%, uploaded = ([0-9.]+) MiB'
    for m in re.finditer(pattern,text):
        r['cache_log_lines']+=1;r['hits']+=int(m.group(1));r['misses']+=int(m.group(2));r['misses_on_cpu']+=int(m.group(3) or 0);r['uploaded_mib']+=float(m.group(4))
    total=r['hits']+r['misses'];r['hit_rate_pct']=100*r['hits']/total if total else None
    r['note']='Requires a server build that emits matching verbose MoE-cache log lines.'
    return r
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trace',type=pathlib.Path);p.add_argument('--server-log',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path);a=p.parse_args()
    if not a.trace and not a.server_log:p.error('provide --trace and/or --server-log')
    r={}
    if a.trace:r['routing_trace']=read_trace(a.trace)
    if a.server_log:r['cache_log']=read_log(a.server_log)
    r['sources']={'trace':str(a.trace) if a.trace else None,'server_log':str(a.server_log) if a.server_log else None}
    out=json.dumps(r,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(out+'\\n',encoding='utf-8')
    print(out)
if __name__=='__main__':main()
