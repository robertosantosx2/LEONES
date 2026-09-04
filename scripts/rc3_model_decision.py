#!/usr/bin/env python3
"""RC3 model decision CLI: catalog + hardware-profile.v1 -> explainable ranking."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from runtime_selection.decision_engine import decide_models

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "runtime_selection/data/model-evidence.rc3.json"

def main() -> int:
    parser = argparse.ArgumentParser(description="Rank RC3 model candidates against hardware-profile.v1")
    parser.add_argument("--hardware", required=True, help="Path to hardware-profile.v1 JSON")
    parser.add_argument("--profile", default="balanced")
    parser.add_argument("--out")
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    hardware = json.loads(Path(args.hardware).read_text(encoding="utf-8"))
    result = decide_models(catalog, args.profile, hardware)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(f"RC3 MODEL DECISION · profile={args.profile}")
    print(f"RAM available: {result['hardware'].get('ram', {}).get('available_gb', 'unknown')} GB")
    for candidate in result["candidates"]:
        fit = candidate["local_fit_estimate"]
        print(f"{candidate['decision_rank']:>2}. {candidate['name']} · {candidate['decision_score']:.1f}/100 · {fit['status']} · headroom={fit['estimated_headroom_gb']} GB")
    print(f"RECOMMENDED: {result['recommended_model_id'] or 'none'}")
    print("EXECUTION AUTHORIZED: false")
    print("MEASURED: false")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
