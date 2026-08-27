#!/usr/bin/env python3
import json, os, urllib.request
from datetime import datetime, timezone

url = "https://huggingface.co/api/models?sort=createdAt&direction=-1&limit=50&pipeline_tag=text-generation"
req = urllib.request.Request(url, headers={"User-Agent": "LEONES-Atlas-Prospector/1.0"})
data = json.load(urllib.request.urlopen(req, timeout=30))
out = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "kind": "models",
    "status": "external-unvalidated",
    "items": data,
}
os.makedirs("data/discovery", exist_ok=True)
with open("data/discovery/models.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
