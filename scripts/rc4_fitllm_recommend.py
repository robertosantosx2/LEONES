#!/usr/bin/env python3
"""RC4 evidence-bounded LLMFit recommender.

External catalogs may be bounded for collection efficiency, but that bound is
never exposed as a human model-selection limit. Results are ESTIMATED only.
"""
from __future__ import annotations
import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Mapping, Sequence
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from runtime_selection import llmfit as llmfit_mod
from scripts import collect_model_evidence as evidence_mod
SCHEMA="leones.rc4.fitllm_recommendation.v1"
EVIDENCE_INPUT_LIMIT=100
SELECTION_BOUNDARY="evidence_backed_intersection"

def _normalise_user_intent(purposes: Sequence[str])->list[str]: return evidence_mod.normalize_purposes(purposes)
def _llmfit_use_case(purposes: Sequence[str])->str:
    mapping=(("programming","coding"),("reasoning","reasoning"),("multimodal","multimodal"),("chat","chat"),("embedding","embedding"),("research","general"),("general","general"))
    for purpose,use_case in mapping:
        if purpose in purposes:return use_case
    return "general"
def _identity(value:Any)->str:
    text="" if value is None else str(value); text=unicodedata.normalize("NFKC",text).strip().lower()
    for prefix in ("https://huggingface.co/","http://huggingface.co/"):
        if text.startswith(prefix):text=text[len(prefix):]
    return "".join(ch for ch in text if ch.isalnum())
def _evidence_keys(item:Mapping[str,Any])->set[str]:
    hf=item.get("hf") if isinstance(item.get("hf"),Mapping) else {}; values=(item.get("model_id"),hf.get("model_id"),hf.get("name")); return {_identity(v) for v in values if _identity(v)}
def _llmfit_keys(item:Mapping[str,Any])->set[str]:
    values=(item.get("id"),item.get("name"),item.get("model"),item.get("model_id")); return {_identity(v) for v in values if _identity(v)}
def _build_live_evidence_feed(*,purposes:Sequence[str],timeout_seconds:int,memory_margin:float=1.2):
    system_raw=llmfit_mod.run_system(timeout_seconds=timeout_seconds); hardware=llmfit_mod.normalise_hardware(system_raw)
    hf_models=evidence_mod.fetch_hf_models(limit=EVIDENCE_INPUT_LIMIT); aa_key=evidence_mod.os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY")
    aa_version,aa_models=evidence_mod.fetch_aa_models(aa_key or "")
    feed=evidence_mod.build_feed(hardware=hardware,purposes=list(purposes),hf_models=hf_models,aa_models=aa_models,aa_index_version=aa_version,limit=EVIDENCE_INPUT_LIMIT,memory_margin=memory_margin)
    return feed,hardware
def _base_envelope(purposes:list[str])->dict[str,Any]:
    return {"schema":SCHEMA,"user_intent":{"required":True,"selection_mode":"multiple","purposes":purposes},"phase":"RC4","provider":"fitllm_llmfit","kind":"ESTIMATED","candidate_count":0,"execution_authorized":False,"measurement_authorized":False,"measured":False,"user_choice_required":True,"fitllm_required_for_boot":False,"selection_boundary":SELECTION_BOUNDARY,"evidence_input_limit":EVIDENCE_INPUT_LIMIT,"recommendations":[],"status":"ok","message":None}
def recommend(*,user_intent:Sequence[str],max_context:int|None=None,timeout_seconds:int=30,evidence_feed:Mapping[str,Any]|None=None)->dict[str,Any]:
    purposes=_normalise_user_intent(user_intent); base=_base_envelope(purposes)
    if llmfit_mod.executable() is None:
        base.update(status="unavailable",message="FitLLM/LLMFit no está en PATH. LEONES puede continuar: elige el modelo a mano. La preselección automática queda omitida."); return base
    try:
        if evidence_feed is None: evidence_feed,hardware=_build_live_evidence_feed(purposes=purposes,timeout_seconds=timeout_seconds)
        else: hardware=evidence_feed.get("hardware",{})
        fit_input=evidence_feed.get("fitllm_input",{}); feed_models=fit_input.get("model_evidence",[]) if isinstance(fit_input,Mapping) else []
        if not isinstance(feed_models,list): raise RuntimeError("evidence feed model_evidence must be a list")
        feed_models=feed_models[:EVIDENCE_INPUT_LIMIT]; sources=evidence_feed.get("sources",{}); aa_source=sources.get("artificial_analysis",{}) if isinstance(sources,Mapping) else {}
        base["evidence"]={"schema":evidence_feed.get("schema"),"model_count":len(feed_models),"max_models":EVIDENCE_INPUT_LIMIT,"sources":sources,"hardware":dict(hardware) if isinstance(hardware,Mapping) else {}}
        if not feed_models: base.update(status="insufficient",message="El feed de evidencia no contiene modelos válidos."); return base
        results=[]
        for purpose in purposes: results.append(llmfit_mod.run_recommend(limit=EVIDENCE_INPUT_LIMIT,use_case=_llmfit_use_case([purpose]),max_context=max_context,timeout_seconds=timeout_seconds))
        merged=[]; seen_llmfit=set()
        for r in results:
            for raw in r.models:
                keys=sorted(_llmfit_keys(raw)); identity=keys[0] if keys else ""
                if identity and identity in seen_llmfit: continue
                if identity: seen_llmfit.add(identity)
                merged.append(raw)
        first=results[0]
        result=llmfit_mod.LLMFitResult(command=tuple(first.command),version=first.version,system=first.system,models=tuple(merged),raw={"results":[getattr(r,"raw",{}) for r in results],"commands":[list(r.command) for r in results]})
    except (llmfit_mod.LLMFitError,RuntimeError,ValueError) as exc:
        base.update(status="error",message=f"RC4 no pudo completar la preselección: {exc}"); return base
    evidence_by_key={}
    for item in feed_models:
        if isinstance(item,Mapping):
            for key in _evidence_keys(item): evidence_by_key.setdefault(key,item)
    rows=[]; seen=set()
    for raw in result.models:
        if not isinstance(raw,Mapping): continue
        matches=[evidence_by_key[k] for k in _llmfit_keys(raw) if k in evidence_by_key]
        if not matches: continue
        evidence=matches[0]; model_id=raw.get("name") or raw.get("id") or raw.get("model"); key=_identity(model_id)
        if not model_id or not key or key in seen: continue
        seen.add(key); aa=evidence.get("artificial_analysis")
        rows.append({"rank":len(rows)+1,"model_id":model_id,"kind":"ESTIMATED","evidence_level":"estimated","source":"llmfit","raw":dict(raw),"evidence_provenance":{"selection_boundary":SELECTION_BOUNDARY,"huggingface":dict(evidence.get("hf",{})) if isinstance(evidence.get("hf"),Mapping) else None,"artificial_analysis":dict(aa) if isinstance(aa,Mapping) else None,"evidence_rank":evidence.get("evidence_rank")}})
    base["recommendations"]=rows; base["candidate_count"]=len(rows); base["provider_version"]=result.version; base["command"]=list(result.command); base["llmfit"]=dict(result.raw); base["llmfit_catalog_count"]=len(result.models); base["evidence_backed_intersection_count"]=len(rows); base["artificial_analysis_available"]=bool(aa_source.get("models_available",0)) if isinstance(aa_source,Mapping) else False
    if not rows: base["status"]="insufficient"; base["message"]="No hay coincidencias válidas entre LLMFit y el feed de evidencia."
    return base

def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--purpose",dest="purposes",action="append",required=True); parser.add_argument("--max-context",type=int,default=None); parser.add_argument("--json",action="store_true"); args=parser.parse_args(argv); envelope=recommend(user_intent=args.purposes,max_context=args.max_context)
    if args.json: print(json.dumps(envelope,ensure_ascii=False,indent=2)); return 0 if envelope["status"] in {"ok","unavailable"} else 1
    print(f"RC4 FitLLM recommendation: {envelope['status']}"); print(f"  candidates: {envelope['candidate_count']}"); print(f"  kind: {envelope['kind']}  execution_authorized: {envelope['execution_authorized']}"); print(f"  selection boundary: {envelope['selection_boundary']}");
    if envelope.get("message"): print(f"  {envelope['message']}")
    for i,row in enumerate(envelope.get("recommendations") or [],1): print(f"  [{i}] {row.get('model_id')}")
    return 0 if envelope["status"] in {"ok","unavailable"} else 1
if __name__=="__main__": raise SystemExit(main())
