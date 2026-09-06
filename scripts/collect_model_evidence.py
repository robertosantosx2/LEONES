#!/usr/bin/env python3
"""Collect model evidence from Hugging Face Hub and Artificial Analysis.

RC4 role
---------
This module is an evidence feeder for FitLLM/LLMFit.  It does NOT perform a
physical benchmark and it does NOT claim that an estimated model is measured.
It collects two complementary evidence classes:

* Hugging Face: repository/model metadata, architecture/configuration,
  parameter hints, quantization/artifact formats, context hints, adoption and
  maintenance signals.
* Artificial Analysis: independent intelligence/benchmark indices and hosted
  performance medians.

The output is ``leones.rc4.model-evidence.v1`` and is deliberately suitable as
an input payload for the RC4 FitLLM selection layer.

The script uses only Python's standard library so the collector itself does not
add a runtime dependency.  Artificial Analysis requires an API key; Hugging
Face public model metadata does not normally require one.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

SCHEMA = "leones.rc4.model-evidence.v1"
HF_API = "https://huggingface.co/api"
AA_API = "https://artificialanalysis.ai/api/v2"

DEFAULT_PURPOSES = ("programming", "research", "reasoning")
PURPOSE_ALIASES = {
    "coding": "programming",
    "code": "programming",
    "science": "research",
    "analysis": "research",
}

# Artificial Analysis exposes these as composite/task indices.  The exact set
# available depends on the API tier and current AA methodology version, so all
# values are optional and are preserved when present.
PURPOSE_METRICS = {
    "programming": (
        "artificial_analysis_coding_index",
        "livecodebench",
        "terminalbench_hard",
        "terminalbench_v2_1",
    ),
    "research": (
        "artificial_analysis_intelligence_index",
        "gpqa_diamond",
        "gpqa",
        "scicode",
        "mmlu_pro",
        "hle",
    ),
    "reasoning": (
        "artificial_analysis_intelligence_index",
        "gpqa_diamond",
        "gpqa",
        "math_500",
        "aime",
        "hle",
    ),
}

QUANT_BITS = {
    "fp32": 32.0,
    "fp16": 16.0,
    "bf16": 16.0,
    "fp8": 8.0,
    "int8": 8.0,
    "q8": 8.0,
    "q6": 6.0,
    "q5": 5.5,
    "q4": 4.5,
    "q3": 3.5,
    "q2": 2.5,
}


def _json_request(url: str, *, headers: Mapping[str, str] | None = None,
                  timeout: float = 30.0) -> Any:
    request = urllib.request.Request(url, headers=dict(headers or {}), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"GET {url} failed with HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc


def _norm(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _first(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _nested(mapping: Mapping[str, Any], *path: str) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def normalize_purposes(purposes: Iterable[str]) -> list[str]:
    result: list[str] = []
    for purpose in purposes:
        value = PURPOSE_ALIASES.get(_norm(purpose), _norm(purpose))
        if value and value not in result:
            result.append(value)
    if not result:
        raise ValueError("RC4 requires at least one user_intent purpose")
    return result


def extract_parameter_count(info: Mapping[str, Any]) -> float | None:
    """Return parameter count in billions when Hub metadata exposes it."""
    candidates = [
        _nested(info, "safetensors", "parameters"),
        _nested(info, "config", "num_parameters"),
        _nested(info, "config", "num_params"),
        info.get("num_parameters"),
    ]
    for value in candidates:
        if isinstance(value, Mapping):
            value = _first(value, "total", "all", "num_parameters")
        number = _float(value)
        if number is not None:
            # Hub parameter counts are normally absolute; tolerate B-valued
            # metadata as well.
            return number / 1e9 if number > 1e6 else number
    return None


def extract_context(info: Mapping[str, Any]) -> int | None:
    for path in (
        ("config", "max_position_embeddings"),
        ("config", "max_sequence_length"),
        ("config", "seq_length"),
        ("config", "max_seq_len"),
    ):
        value = _nested(info, *path)
        try:
            if value is not None and int(value) > 0:
                return int(value)
        except (TypeError, ValueError):
            pass
    return None


def detect_formats(info: Mapping[str, Any]) -> list[str]:
    formats: set[str] = set()
    tags = [str(x).lower() for x in (info.get("tags") or [])]
    if isinstance(info.get("gguf"), Mapping) or any("gguf" in x for x in tags):
        formats.add("gguf")
    if isinstance(info.get("safetensors"), Mapping) or any("safetensors" in x for x in tags):
        formats.add("safetensors")

    for sibling in info.get("siblings") or []:
        filename = sibling.get("rfilename", "") if isinstance(sibling, Mapping) else str(sibling)
        name = filename.lower()
        if name.endswith(".gguf"):
            formats.add("gguf")
        if name.endswith(".safetensors"):
            formats.add("safetensors")
        if ".awq" in name or "awq" in name:
            formats.add("awq")
        if ".gptq" in name or "gptq" in name:
            formats.add("gptq")
        if ".exl2" in name or "exl2" in name:
            formats.add("exl2")
        if "q4_k_m" in name:
            formats.add("q4_k_m")
        if "q8_0" in name:
            formats.add("q8_0")
    return sorted(formats)


def detect_quantizations(info: Mapping[str, Any]) -> list[str]:
    found: set[str] = set()
    tags = " ".join(str(x).lower() for x in (info.get("tags") or []))
    text = tags + " " + " ".join(
        str(s.get("rfilename", "")) for s in (info.get("siblings") or []) if isinstance(s, Mapping)
    ).lower()
    patterns = (
        r"q[2-8](?:_[0-9]+)?(?:_[a-z0-9]+)?",
        r"fp(?:32|16|8)",
        r"bf16",
        r"int8",
        r"awq",
        r"gptq",
        r"exl2",
    )
    for pattern in patterns:
        found.update(re.findall(pattern, text))
    return sorted(found)


def extract_hf_info(info: Mapping[str, Any]) -> dict[str, Any]:
    config = info.get("config") if isinstance(info.get("config"), Mapping) else {}
    transformers = info.get("transformers_info") if isinstance(info.get("transformers_info"), Mapping) else {}
    return {
        "model_id": info.get("id") or info.get("modelId"),
        "revision": info.get("sha"),
        "author": info.get("author"),
        "pipeline_tag": info.get("pipeline_tag"),
        "library": info.get("library_name"),
        "parameters_b": extract_parameter_count(info),
        "dtype": _first(config, "torch_dtype", "dtype"),
        "architecture": _first(config, "architectures", "model_type"),
        "context_window_tokens": extract_context(info),
        "formats": detect_formats(info),
        "quantizations": detect_quantizations(info),
        "downloads_30d": info.get("downloads"),
        "downloads_all_time": info.get("downloads_all_time"),
        "likes": info.get("likes"),
        "trending_score": info.get("trending_score"),
        "last_modified": info.get("last_modified"),
        "created_at": info.get("created_at"),
        "gated": info.get("gated"),
        "tags": info.get("tags") or [],
        "used_storage_bytes": info.get("used_storage"),
        "transformers_info": dict(transformers),
        "source": "huggingface",
    }


def fetch_hf_models(*, limit: int, search: str | None = None) -> list[dict[str, Any]]:
    params = {
        "pipeline_tag": "text-generation",
        "sort": "downloads",
        "direction": "-1",
        "limit": str(limit),
        "expand": "author,config,downloads,downloadsAllTime,lastModified,likes,model-index,pipeline_tag,safetensors,sha,siblings,tags,transformersInfo,usedStorage,createdAt,gated,gguf",
    }
    if search:
        params["search"] = search
    url = HF_API + "/models?" + urllib.parse.urlencode(params)
    raw = _json_request(url, headers={"Accept": "application/json"})
    if not isinstance(raw, list):
        raise RuntimeError("Hugging Face models endpoint returned a non-list payload")
    return [extract_hf_info(item) for item in raw if isinstance(item, Mapping)]


def fetch_hf_model(model_id: str) -> dict[str, Any]:
    url = HF_API + "/models/" + urllib.parse.quote(model_id, safe="/")
    params = {"expand": "author,config,downloads,downloadsAllTime,lastModified,likes,model-index,pipeline_tag,safetensors,sha,siblings,tags,transformersInfo,usedStorage,createdAt,gated,gguf"}
    raw = _json_request(url + "?" + urllib.parse.urlencode(params), headers={"Accept": "application/json"})
    if not isinstance(raw, Mapping):
        raise RuntimeError(f"Hugging Face model info for {model_id} is not an object")
    return extract_hf_info(raw)


def fetch_aa_models(api_key: str) -> tuple[float | None, list[dict[str, Any]]]:
    if not api_key:
        return None, []
    url = AA_API + "/language/models/free?page=1"
    raw = _json_request(url, headers={"Accept": "application/json", "x-api-key": api_key})
    if not isinstance(raw, Mapping):
        raise RuntimeError("Artificial Analysis returned a non-object payload")
    version = _float(raw.get("intelligence_index_version"))
    data = raw.get("data") or []
    return version, [dict(item) for item in data if isinstance(item, Mapping)]


def aa_index(item: Mapping[str, Any], metric: str) -> float | None:
    return _float(_nested(item, "evaluations", metric))


def aa_best_purpose_score(item: Mapping[str, Any], purposes: list[str]) -> float | None:
    scores: list[float] = []
    for purpose in purposes:
        for metric in PURPOSE_METRICS.get(purpose, ("artificial_analysis_intelligence_index",)):
            value = aa_index(item, metric)
            if value is not None:
                # Indices are already on a useful comparative scale. Raw task
                # probabilities are converted to 0-100 for comparability.
                if value <= 1.0 and metric not in {
                    "artificial_analysis_intelligence_index",
                    "artificial_analysis_coding_index",
                }:
                    value *= 100.0
                scores.append(value)
                break
    return sum(scores) / len(scores) if scores else None


def match_aa(hf: Mapping[str, Any], aa_models: list[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    model_id = _norm(hf.get("model_id"))
    if not model_id:
        return None
    exact = model_id.replace(" ", "")
    best: tuple[int, Mapping[str, Any] | None] = (0, None)
    for item in aa_models:
        names = [item.get("name"), item.get("slug")]
        aa_url = item.get("huggingface_url")
        if aa_url:
            names.append(str(aa_url).rstrip("/").split("/huggingface.co/")[-1])
        normalized = [_norm(x) for x in names if x]
        if exact in {x.replace(" ", "") for x in normalized}:
            return item
        score = 0
        aa_compact = [x.replace(" ", "") for x in normalized]
        if any(x and (x in exact or exact in x) for x in aa_compact):
            score = 70
        else:
            hf_tokens = set(model_id.split())
            for x in normalized:
                overlap = len(hf_tokens & set(x.split()))
                score = max(score, min(60, overlap * 20))
        if score > best[0]:
            best = (score, item)
    return best[1] if best[0] >= 40 else None


def _bits_for_quant(quantization: str | None) -> float:
    if not quantization:
        return 16.0
    text = _norm(quantization).replace(" ", "")
    for key, bits in sorted(QUANT_BITS.items(), key=lambda item: -len(item[0])):
        if text.startswith(key) or key in text:
            return bits
    return 16.0


def estimate_weight_memory_gb(parameters_b: float | None, bits_per_weight: float) -> float | None:
    if parameters_b is None or parameters_b <= 0:
        return None
    return parameters_b * 1e9 * bits_per_weight / 8 / (1024 ** 3)


def estimate_fit(*, parameters_b: float | None, ram_gb: float | None,
                 vram_gb: float | None, quantization: str | None,
                 memory_margin: float = 1.20) -> dict[str, Any]:
    bits = _bits_for_quant(quantization)
    weights = estimate_weight_memory_gb(parameters_b, bits)
    required = weights * memory_margin if weights is not None else None
    # This is intentionally a conservative weight-only prefilter. KV cache,
    # runtime buffers and offload strategy are FitLLM/runtime concerns.
    gpu_fit = vram_gb is not None and required is not None and required <= vram_gb
    cpu_fit = ram_gb is not None and required is not None and required <= ram_gb
    return {
        "assumed_quantization": quantization,
        "bits_per_weight": bits,
        "weight_memory_gb": round(weights, 3) if weights is not None else None,
        "estimated_memory_with_margin_gb": round(required, 3) if required is not None else None,
        "gpu_weight_fit": gpu_fit,
        "cpu_weight_fit": cpu_fit,
        "prefilter_status": "fits" if (gpu_fit or cpu_fit) else "unknown_or_exceeds",
        "method": "weights_only_prefilter_1.20x",
    }


def score_candidate(hf: Mapping[str, Any], aa: Mapping[str, Any] | None,
                    purposes: list[str], fit: Mapping[str, Any]) -> tuple[float, dict[str, float | None]]:
    aa_score = aa_best_purpose_score(aa, purposes) if aa else None
    intelligence = aa_index(aa, "artificial_analysis_intelligence_index") if aa else None
    coding = aa_index(aa, "artificial_analysis_coding_index") if aa else None
    speed = _float(_nested(aa or {}, "performance", "median_output_tokens_per_second"))
    if speed is None and aa:
        speed = _float(aa.get("median_output_tokens_per_second"))

    # Community adoption is a weak tie-breaker, never a substitute for AA.
    downloads = _float(hf.get("downloads_30d")) or 0.0
    adoption = min(100.0, math.log10(downloads + 1) * 10.0)
    fit_bonus = 10.0 if fit.get("prefilter_status") == "fits" else 0.0
    score = (aa_score if aa_score is not None else 0.0) + adoption * 0.05 + fit_bonus
    if aa_score is None:
        score = adoption * 0.05 + fit_bonus
    return score, {
        "aa_purpose_score": aa_score,
        "aa_intelligence_index": intelligence,
        "aa_coding_index": coding,
        "aa_median_output_tps": speed,
        "hf_adoption_signal": adoption,
        "hardware_prefilter_bonus": fit_bonus,
    }


def build_feed(*, hardware: Mapping[str, Any], purposes: list[str], hf_models: list[Mapping[str, Any]],
               aa_models: list[Mapping[str, Any]], aa_index_version: float | None,
               limit: int = 10, memory_margin: float = 1.20) -> dict[str, Any]:
    normalized_purposes = normalize_purposes(purposes)
    ram_gb = _float(hardware.get("ram_gb"))
    vram_gb = _float(hardware.get("vram_gb"))
    scored: list[dict[str, Any]] = []

    for hf in hf_models:
        aa = match_aa(hf, aa_models)
        # For a local-first recommendation we need an executable artifact hint.
        # If no quantization is known, use Q4 as a hypothetical prefilter only;
        # it is never presented as a repository artifact that definitely exists.
        quant = None
        for candidate in ("q4_k_m", "q4", "awq", "gptq", "int8", "bf16", "fp16"):
            if candidate in hf.get("quantizations", []):
                quant = candidate
                break
        if quant is None and hf.get("parameters_b") is not None:
            quant = "q4_k_m_hypothetical"
        fit = estimate_fit(
            parameters_b=_float(hf.get("parameters_b")),
            ram_gb=ram_gb,
            vram_gb=vram_gb,
            quantization=quant,
            memory_margin=memory_margin,
        )
        score, score_breakdown = score_candidate(hf, aa, normalized_purposes, fit)
        aa_evidence = None
        if aa:
            aa_evidence = {
                "id": aa.get("id"),
                "name": aa.get("name"),
                "slug": aa.get("slug"),
                "release_date": aa.get("release_date"),
                "evaluations": aa.get("evaluations", {}),
                "performance": aa.get("performance", {
                    "median_output_tokens_per_second": aa.get("median_output_tokens_per_second"),
                    "median_time_to_first_token_seconds": aa.get("median_time_to_first_token_seconds"),
                }),
                "context_window_tokens": aa.get("context_window_tokens"),
                "parameters": aa.get("parameters"),
                "licensing": aa.get("licensing"),
                "huggingface_url": aa.get("huggingface_url"),
            }
        scored.append({
            "model_id": hf.get("model_id"),
            "rank_score": round(score, 4),
            "evidence_level": "estimated",
            "hf": dict(hf),
            "artificial_analysis": aa_evidence,
            "hardware_prefilter": fit,
            "score_breakdown": score_breakdown,
        })

    scored.sort(key=lambda item: item["rank_score"], reverse=True)
    for rank, item in enumerate(scored[:limit], start=1):
        item["rank"] = rank

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_intent": {
            "required": True,
            "selection_mode": "multiple",
            "purposes": normalized_purposes,
        },
        "hardware": dict(hardware),
        "fitllm_input": {
            "hardware": dict(hardware),
            "user_intent": normalized_purposes,
            "model_evidence": scored[:limit],
        },
        "sources": {
            "huggingface": {
                "kind": "model_repository_metadata",
                "models_considered": len(hf_models),
            },
            "artificial_analysis": {
                "kind": "independent_benchmark_and_performance",
                "models_available": len(aa_models),
                "intelligence_index_version": aa_index_version,
            },
        },
        "candidates": scored[:limit],
        "candidate_count": min(limit, len(scored)),
        "status": "estimated",
        "measurement_required": True,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ram-gb", type=float, required=True)
    parser.add_argument("--vram-gb", type=float, default=None)
    parser.add_argument("--cpu", default=None)
    parser.add_argument("--gpu", default=None)
    parser.add_argument("--purpose", dest="purposes", action="append", required=True,
                        help="Repeat for multiple purposes: programming, research, reasoning")
    parser.add_argument("--hf-limit", type=int, default=100,
                        help="Number of popular HF text-generation repositories to inspect")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--memory-margin", type=float, default=1.20)
    parser.add_argument("--aa-api-key", default=os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY"))
    parser.add_argument("--output", default="-")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        purposes = normalize_purposes(args.purposes)
        hardware = {
            "cpu": args.cpu,
            "ram_gb": args.ram_gb,
            "gpu": args.gpu,
            "vram_gb": args.vram_gb,
        }
        if args.hf_limit < 1 or args.limit < 1:
            raise ValueError("--hf-limit and --limit must be >= 1")
        if args.memory_margin < 1.0:
            raise ValueError("--memory-margin must be >= 1.0")

        hf_models = fetch_hf_models(limit=args.hf_limit)
        aa_version, aa_models = fetch_aa_models(args.aa_api_key)
        feed = build_feed(
            hardware=hardware,
            purposes=purposes,
            hf_models=hf_models,
            aa_models=aa_models,
            aa_index_version=aa_version,
            limit=args.limit,
            memory_margin=args.memory_margin,
        )
        payload = json.dumps(feed, ensure_ascii=False, indent=2) + "\n"
        if args.output == "-":
            sys.stdout.write(payload)
        else:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(payload)
        return 0
    except (RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
