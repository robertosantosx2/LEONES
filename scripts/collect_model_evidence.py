#!/usr/bin/env python3
"""Collect model evidence from Hugging Face and Artificial Analysis for RC4 FitLLM.

The collector is an evidence feeder, not the final recommender and not a physical benchmark.
It prepares up to 100 model evidence records for FitLLM/LLMFit.
"""
from __future__ import annotations
import argparse, json, math, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

SCHEMA = "leones.rc4.model-evidence.v1"
HF_API = "https://huggingface.co/api"
AA_API = "https://artificialanalysis.ai/api/v2"
MAX_FITLLM_INPUT = 100
PURPOSE_ALIASES = {"coding":"programming", "code":"programming", "science":"research", "analysis":"research"}
PURPOSE_METRICS = {
 "programming": ("artificial_analysis_coding_index", "livecodebench", "terminalbench_hard", "terminalbench_v2_1"),
 "research": ("artificial_analysis_intelligence_index", "gpqa_diamond", "gpqa", "scicode", "mmlu_pro", "hle"),
 "reasoning": ("artificial_analysis_intelligence_index", "gpqa_diamond", "gpqa", "math_500", "aime", "hle")}
QUANT_BITS = {"fp32":32.0,"fp16":16.0,"bf16":16.0,"fp8":8.0,"int8":8.0,"q8":8.0,"q6":6.0,"q5":5.5,"q4":4.5,"q3":3.5,"q2":2.5}

def _json_request(url: str, *, headers: Mapping[str,str]|None=None, timeout: float=30.0) -> Any:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=dict(headers or {})), timeout=timeout) as r: return json.load(r)
    except urllib.error.HTTPError as e: raise RuntimeError(f"GET {url} failed with HTTP {e.code}") from e
    except urllib.error.URLError as e: raise RuntimeError(f"GET {url} failed: {e.reason}") from e

def _norm(v: Any) -> str: return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", "" if v is None else str(v).lower())).strip()
def _float(v: Any) -> float|None:
    try: n=float(v); return n if math.isfinite(n) else None
    except (TypeError,ValueError): return None
def _first(m: Mapping[str,Any], *keys: str) -> Any: return next((m[k] for k in keys if m.get(k) is not None), None)
def _nested(m: Mapping[str,Any], *path: str) -> Any:
    v: Any=m
    for k in path:
        if not isinstance(v, Mapping): return None
        v=v.get(k)
    return v

def normalize_purposes(purposes: Iterable[str]) -> list[str]:
    out=[]
    for p in purposes:
        p=PURPOSE_ALIASES.get(_norm(p),_norm(p))
        if p and p not in out: out.append(p)
    if not out: raise ValueError("RC4 requires at least one user_intent purpose")
    return out

def extract_parameter_count(info: Mapping[str,Any]) -> float|None:
    for v in (_nested(info,"safetensors","parameters"),_nested(info,"config","num_parameters"),_nested(info,"config","num_params"),info.get("num_parameters")):
        if isinstance(v,Mapping): v=_first(v,"total","all","num_parameters")
        n=_float(v)
        if n is not None: return n/1e9 if n>1e6 else n
    return None

def extract_context(info: Mapping[str,Any]) -> int|None:
    for path in (("config","max_position_embeddings"),("config","max_sequence_length"),("config","seq_length"),("config","max_seq_len")):
        try:
            v=_nested(info,*path)
            if v is not None and int(v)>0: return int(v)
        except (TypeError,ValueError): pass
    return None

def detect_formats(info: Mapping[str,Any]) -> list[str]:
    out=set(); tags=[str(x).lower() for x in info.get("tags",[]) or []]
    if isinstance(info.get("gguf"),Mapping) or any("gguf" in x for x in tags): out.add("gguf")
    if isinstance(info.get("safetensors"),Mapping) or any("safetensors" in x for x in tags): out.add("safetensors")
    for s in info.get("siblings",[]) or []:
        n=str(s.get("rfilename","") if isinstance(s,Mapping) else s).lower()
        for f in ("awq","gptq","exl2"): 
            if f in n: out.add(f)
        if n.endswith(".gguf"): out.add("gguf")
        if n.endswith(".safetensors"): out.add("safetensors")
        if "q4_k_m" in n: out.add("q4_k_m")
        if "q8_0" in n: out.add("q8_0")
    return sorted(out)

def detect_quantizations(info:dict[str,Any])->list[str]:
    text=json.dumps(info,ensure_ascii=False).lower()
    found=[]

    # Match the most specific quantization names first so q4_k_m
    # is not truncated to q4_k.
    quantizations=(
        "q4_k_m",
        "q4_k_s",
        "q4_k",
        "q8_0",
        "q8_k",
        "q6_k",
        "q5_k_m",
        "q5_k_s",
        "q5_k",
        "q4_0",
        "q4_1",
        "q3_k_m",
        "q3_k_s",
        "q3_k_l",
        "q2_k",
        "f16",
        "f32",
        "bf16",
        "awq",
        "gptq",
        "exl2",
    )

    for q in quantizations:
        if q in text and q not in found:
            found.append(q)

    return found

def extract_hf_info(info: Mapping[str,Any]) -> dict[str,Any]:
    config=info.get("config") if isinstance(info.get("config"),Mapping) else {}
    ti=info.get("transformers_info") or info.get("transformersInfo")
    if not isinstance(ti,Mapping):
        ti={}
    return {
        "model_id":info.get("id") or info.get("modelId"),
        "revision":info.get("sha"),
        "author":info.get("author"),
        "pipeline_tag":info.get("pipeline_tag") or info.get("pipelineTag"),
        "library":info.get("library_name") or info.get("libraryName"),
        "parameters_b":extract_parameter_count(info),
        "dtype":_first(config,"torch_dtype","dtype"),
        "architecture":_first(config,"architectures","model_type"),
        "context_window_tokens":extract_context(info),
        "formats":detect_formats(info),
        "quantizations":detect_quantizations(info),
        "downloads_30d":info.get("downloads"),
        "downloads_all_time":info.get("downloads_all_time") or info.get("downloadsAllTime"),
        "likes":info.get("likes"),
        "trending_score":info.get("trending_score") or info.get("trendingScore"),
        "last_modified":info.get("last_modified") or info.get("lastModified"),
        "created_at":info.get("created_at") or info.get("createdAt"),
        "gated":info.get("gated"),
        "tags":info.get("tags") or [],
        "used_storage_bytes":info.get("used_storage") or info.get("usedStorage"),
        "transformers_info":dict(ti),
        "source":"huggingface",
    }


def fetch_hf_models(*, limit: int, search: str|None=None) -> list[dict[str,Any]]:
    # HF accepts individual expand fields but the combined expand list is
    # rejected by the live API endpoint used by LEONES. Discovery therefore
    # deliberately uses the stable default /api/models payload.
    p={
        "pipeline_tag":"text-generation",
        "sort":"downloads",
        "direction":"-1",
        "limit":str(limit),
    }
    if search:
        p["search"]=search
    raw=_json_request(
        HF_API+"/models?"+urllib.parse.urlencode(p),
        headers={"Accept":"application/json"},
    )
    if not isinstance(raw,list):
        raise RuntimeError("Hugging Face models endpoint returned a non-list payload")
    return [
        extract_hf_info(x)
        for x in raw
        if isinstance(x,Mapping)
    ]

def fetch_aa_models(api_key: str) -> tuple[float|None,list[dict[str,Any]]]:
    if not api_key:return None,[]
    raw=_json_request(AA_API+"/language/models/free?page=1",headers={"Accept":"application/json","x-api-key":api_key})
    if not isinstance(raw,Mapping):raise RuntimeError("Artificial Analysis returned a non-object payload")
    return _float(raw.get("intelligence_index_version")),[dict(x) for x in raw.get("data",[]) or [] if isinstance(x,Mapping)]

def aa_index(item: Mapping[str,Any], metric: str)->float|None:return _float(_nested(item,"evaluations",metric))
def aa_purpose_score(item: Mapping[str,Any], purposes: list[str])->float|None:
    scores=[]
    for p in purposes:
        for metric in PURPOSE_METRICS.get(p,("artificial_analysis_intelligence_index",)):
            v=aa_index(item,metric)
            if v is not None:
                if v<=1.0 and metric not in {"artificial_analysis_intelligence_index","artificial_analysis_coding_index"}:v*=100
                scores.append(v);break
    return sum(scores)/len(scores) if scores else None

def match_aa(hf: Mapping[str,Any], aa_models: list[Mapping[str,Any]])->Mapping[str,Any]|None:
    mid=_norm(hf.get("model_id")); exact=mid.replace(" ",""); best=(0,None)
    for item in aa_models:
        names=[_norm(item.get("name")),_norm(item.get("slug"))]
        if item.get("huggingface_url"):names.append(_norm(str(item["huggingface_url"]).rstrip("/").split("huggingface.co/")[-1]))
        compact=[x.replace(" ","") for x in names if x]
        if exact and exact in compact:return item
        score=70 if any(x and (x in exact or exact in x) for x in compact) else 0
        if not score:score=max([min(60,len(set(mid.split())&set(x.split()))*20) for x in names if x] or [0])
        if score>best[0]:best=(score,item)
    return best[1] if best[0]>=40 else None

def _bits(q: str|None)->float:
    text=_norm(q).replace(" ","") if q else "fp16"
    for k,b in sorted(QUANT_BITS.items(),key=lambda x:-len(x[0])):
        if k in text:return b
    return 16.0

def estimate_weight_memory_gb(parameters_b: float, bits_per_weight: float) -> float:
    """Estimate model weight memory in GiB.

    This is intentionally weights-only and is a prefilter, not a runtime
    memory prediction. Runtime buffers, KV cache, context and offload are
    evaluated later.
    """
    if parameters_b < 0:
        raise ValueError("parameters_b must be >= 0")
    if bits_per_weight <= 0:
        raise ValueError("bits_per_weight must be > 0")
    return (parameters_b * 1_000_000_000 * bits_per_weight / 8) / (1024 ** 3)


def estimate_fit(*,parameters_b:float|None,ram_gb:float|None,vram_gb:float|None,quantization:str|None,memory_margin:float=1.2)->dict[str,Any]:
    bits=_bits(quantization); weights=parameters_b*1e9*bits/8/(1024**3) if parameters_b and parameters_b>0 else None; req=weights*memory_margin if weights is not None else None
    gpu=vram_gb is not None and req is not None and req<=vram_gb; cpu=ram_gb is not None and req is not None and req<=ram_gb
    return {"assumed_quantization":quantization,"bits_per_weight":bits,"weight_memory_gb":round(weights,3) if weights is not None else None,"estimated_memory_with_margin_gb":round(req,3) if req is not None else None,"gpu_weight_fit":gpu,"cpu_weight_fit":cpu,"prefilter_status":"fits" if gpu or cpu else "unknown_or_exceeds","method":"weights_only_prefilter_1.20x"}

def score_candidate(hf:Mapping[str,Any],aa:Mapping[str,Any]|None,purposes:list[str],fit:Mapping[str,Any])->tuple[float,dict[str,float|None]]:
    ps=aa_purpose_score(aa,purposes) if aa else None; intel=aa_index(aa,"artificial_analysis_intelligence_index") if aa else None; coding=aa_index(aa,"artificial_analysis_coding_index") if aa else None
    speed=_float(_nested(aa or {},"performance","median_output_tokens_per_second")) or _float((aa or {}).get("median_output_tokens_per_second")); downloads=_float(hf.get("downloads_30d")) or 0; adoption=min(100,math.log10(downloads+1)*10); bonus=10 if fit.get("prefilter_status")=="fits" else 0
    return (ps or 0)+adoption*.05+bonus,{"aa_purpose_score":ps,"aa_intelligence_index":intel,"aa_coding_index":coding,"aa_median_output_tps":speed,"hf_adoption_signal":adoption,"hardware_prefilter_bonus":float(bonus)}

def build_feed(*,hardware:Mapping[str,Any],purposes:list[str],hf_models:list[Mapping[str,Any]],aa_models:list[Mapping[str,Any]],aa_index_version:float|None,limit:int=MAX_FITLLM_INPUT,memory_margin:float=1.2)->dict[str,Any]:
    purposes=normalize_purposes(purposes)
    if not 1<=limit<=MAX_FITLLM_INPUT:raise ValueError("FitLLM input limit must be 1..100")
    ram=_float(hardware.get("ram_gb"));vram=_float(hardware.get("vram_gb"));scored=[]
    for hf in hf_models:
        aa=match_aa(hf,aa_models); q=next((x for x in ("q4_k_m","q4","awq","gptq","int8","bf16","fp16") if x in hf.get("quantizations",[])),None)
        if q is None and hf.get("parameters_b") is not None:q="q4_k_m_hypothetical"
        fit=estimate_fit(parameters_b=_float(hf.get("parameters_b")),ram_gb=ram,vram_gb=vram,quantization=q,memory_margin=memory_margin); score,breakdown=score_candidate(hf,aa,purposes,fit)
        aa_e={"id":aa.get("id"),"name":aa.get("name"),"slug":aa.get("slug"),"release_date":aa.get("release_date"),"evaluations":aa.get("evaluations",{}),"performance":aa.get("performance",{}),"context_window_tokens":aa.get("context_window_tokens"),"parameters":aa.get("parameters"),"licensing":aa.get("licensing"),"huggingface_url":aa.get("huggingface_url")} if aa else None
        scored.append({"model_id":hf.get("model_id"),"rank_score":round(score,4),"evidence_level":"estimated","hf":dict(hf),"artificial_analysis":aa_e,"hardware_prefilter":fit,"score_breakdown":breakdown})
    scored.sort(key=lambda x:x["rank_score"],reverse=True); selected=scored[:limit]
    for rank,item in enumerate(selected,1):item["evidence_rank"]=rank
    return {"schema":SCHEMA,"generated_at":datetime.now(timezone.utc).isoformat(),"user_intent":{"required":True,"selection_mode":"multiple","purposes":purposes},"hardware":dict(hardware),"fitllm_input":{"hardware":dict(hardware),"user_intent":{"required":True,"selection_mode":"multiple","purposes":purposes},"model_evidence":selected,"max_models":MAX_FITLLM_INPUT,"model_count":len(selected)},"sources":{"huggingface":{"kind":"model_repository_metadata","models_considered":len(hf_models)},"artificial_analysis":{"kind":"independent_benchmark_and_performance","models_available":len(aa_models),"intelligence_index_version":aa_index_version}},"candidates":selected,"candidate_count":len(selected),"status":"estimated","measurement_required":True}

def parse_args(argv:list[str])->argparse.Namespace:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--ram-gb",type=float,required=True);p.add_argument("--vram-gb",type=float);p.add_argument("--cpu");p.add_argument("--gpu");p.add_argument("--purpose",dest="purposes",action="append",required=True);p.add_argument("--hf-limit",type=int,default=100);p.add_argument("--limit",type=int,default=100);p.add_argument("--memory-margin",type=float,default=1.2);p.add_argument("--aa-api-key",default=os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY"));p.add_argument("--output",default="-");return p.parse_args(argv)

def main(argv:list[str]|None=None)->int:
    a=parse_args(argv or sys.argv[1:])
    try:
        purposes=normalize_purposes(a.purposes)
        if a.hf_limit<1 or not 1<=a.limit<=MAX_FITLLM_INPUT:raise ValueError("--hf-limit must be >=1 and --limit must be 1..100")
        if a.memory_margin<1:raise ValueError("--memory-margin must be >=1.0")
        hardware={"cpu":a.cpu,"ram_gb":a.ram_gb,"gpu":a.gpu,"vram_gb":a.vram_gb}; hf=fetch_hf_models(limit=max(a.hf_limit,a.limit)); version,aa=fetch_aa_models(a.aa_api_key)
        feed=build_feed(hardware=hardware,purposes=purposes,hf_models=hf,aa_models=aa,aa_index_version=version,limit=a.limit,memory_margin=a.memory_margin); payload=json.dumps(feed,ensure_ascii=False,indent=2)+"\n"
        if a.output=="-":sys.stdout.write(payload)
        else:
            with open(a.output,"w",encoding="utf-8") as f:f.write(payload)
        return 0
    except (RuntimeError,ValueError) as e:print(f"[ERROR] {e}",file=sys.stderr);return 2

if __name__=="__main__":raise SystemExit(main())
