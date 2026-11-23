#!/usr/bin/env python3
"""Mobile-LLMs-ARM prospecting and standalone HTML generator."""
import datetime as dt, html, json, os, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"research/mobile-llms-arm/sources.json"
OUT=ROOT/"data/observatory/mobile-llms-arm.json"

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
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"items":len(payload["items"]),"github_queries":len(gh),"reddit_sources":len(reddit)}))
if __name__=="__main__":main()
