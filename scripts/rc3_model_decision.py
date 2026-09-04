#!/usr/bin/env python3
"""RC3 model decision CLI: catalog + hardware-profile.v1 -> explainable ranking."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_selection.decision_engine import decide_models

CATALOG = ROOT / "runtime_selection/data/model-evidence.rc3.json"


def _display_ram_gb(hardware: dict) -> float | None:
    ram = hardware.get("ram") or {}
    if ram.get("available_gb") is not None:
        return float(ram["available_gb"])
    memory = hardware.get("memory") or {}
    if memory.get("available_bytes") is not None:
        return float(memory["available_bytes"]) / (1024 ** 3)
    if memory.get("visible_to_os_bytes") is not None:
        return float(memory["visible_to_os_bytes"]) / (1024 ** 3)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank RC3 model candidates against hardware-profile.v1")
    parser.add_argument("--hardware", required=True, help="Path to hardware-profile.v1 JSON")
    parser.add_argument("--profile", default="balanced")
    parser.add_argument("--out")
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    hardware = json.loads(Path(args.hardware).read_text(encoding="utf-8"))

    # Adapt the curated catalog to the decision engine's explicit external
    # evidence boundary. Hosted/external speed remains external evidence;
    # it is never converted into a LEONES measurement.
    candidates = []
    for candidate in catalog.get("candidates", []):
        item = dict(candidate)
        item["external_evidence"] = {
            "hugging_face": item.pop("hugging_face", {}),
            "artificial_analysis": item.pop("artificial_analysis", {}),
        }
        candidates.append(item)

    enriched = {"hardware": hardware, "candidates": candidates}
    result = decide_models(enriched, args.profile, hardware=hardware)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")

    ram_gb = _display_ram_gb(result["hardware"])
    ram_text = f"{ram_gb:.2f}" if ram_gb is not None else "unknown"
    print(f"RC3 MODEL DECISION · profile={args.profile}")
    print(f"RAM available: {ram_text} GB")
    for candidate in result["candidates"]:
        fit = candidate["local_fit_estimate"]
        print(
            f"{candidate['decision_rank']:>2}. {candidate['name']} · "
            f"{candidate['decision_score']:.1f}/100 · {fit['status']} · "
            f"headroom={fit['estimated_headroom_gb']} GB"
        )
    print(f"RECOMMENDED: {result['recommended_model_id'] or 'none'}")
    print("EXECUTION AUTHORIZED: false")
    print("MEASURED: false")
    if args.out:
        print(f"ARTIFACT: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
