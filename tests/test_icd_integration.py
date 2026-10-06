import pytest

from runtime_selection.candidate_set import build_candidate_set, validate_candidate_set
from runtime_selection.contract import CapabilityMatch, RuntimeSelectionPlan, validate_plan
from runtime_selection.icd import discover_configurations, rank_measured_candidates


def test_icd_flows_through_candidate_set_and_selection_contract():
    discovered = discover_configurations(
        model={"id": "bonsai-27b", "context_length": 65536},
        runtime_profiles=[
            {
                "runtime": "cafe-llama.cpp",
                "runtime_revision": "pr-ptq1-mmv",
                "kernel": "ptq1-mmV",
                "quantization": "PTQ1_0",
                "context_length": 65536,
                "gpu_layers": 99,
                "kv_cache": "f16",
                "flash_attention": True,
                "speculation": "draft-mtp",
                "draft_tokens": 1,
            }
        ],
    )
    raw = [candidate.to_dict() | {
        "model_id": candidate.configuration["model_ref"],
        "name": "Ternary Bonsai 2 27B",
    } for candidate in discovered]

    candidate_set = build_candidate_set(
        hardware={"gpu": {"name": "fixture-gpu", "vram_gb": 12}},
        raw_candidates=raw,
        source="icd",
        source_version="inference-configuration-discovery.v1",
    )
    validate_candidate_set(candidate_set)

    configuration = candidate_set["candidates"][0]["configuration"]
    assert configuration["kernel"] == "ptq1-mmV"
    assert candidate_set["candidates"][0]["configuration_id"]

    plan = RuntimeSelectionPlan(
        runtime_id=configuration["runtime"],
        adapter_id="llama_cpp.v1",
        model_ref=configuration["model_ref"],
        capability_match=CapabilityMatch(
            architecture=True,
            model_format=True,
            quantization=True,
            hardware=True,
            memory=True,
        ),
        constraints={"configuration_id": candidate_set["candidates"][0]["configuration_id"]},
    )
    validate_plan(plan.to_dict())


def test_icd_measurement_feedback_can_select_the_exact_candidate():
    discovered = discover_configurations(
        model={"id": "bonsai-27b", "context_length": 8192},
        runtime_profiles=[
            {"runtime": "cafe-llama.cpp", "kernel": "baseline"},
            {"runtime": "cafe-llama.cpp", "kernel": "ptq1-mmV"},
        ],
    )
    candidates = [candidate.to_dict() for candidate in discovered]
    measurements = [
        {
            "configuration_id": candidates[0]["configuration_id"],
            "evidence_type": "measured",
            "measured_tps": 20.0,
        },
        {
            "configuration_id": candidates[1]["configuration_id"],
            "evidence_type": "measured",
            "measured_tps": 40.0,
        },
    ]
    ranked = rank_measured_candidates(candidates, measurements)
    assert ranked[0]["configuration_id"] == candidates[1]["configuration_id"]
    assert ranked[0]["selection_status"] == "MEASURED"


def test_icd_ods_like_multidimensional_search_is_deterministic_and_measurement_pure():
    """Exercise the ODS-shaped cafe runtime search space without executing it."""
    profile = {
        "runtime": "cafe-llama.cpp",
        "runtime_revision": "pr-ptq1-mmv",
        "kernel": "ptq1-mmV",
        "quantization": "PTQ1_0",
        "context_length": 8192,
        "gpu_layers": 99,
        "kv_cache": "f16",
        "flash_attention": True,
        "speculation": "draft-mtp",
        "draft_tokens": 1,
        "batch": 1,
    }
    capabilities = {
        "kernel": ["baseline", "ptq1-mmV"],
        "context": [4096, 8192],
        "kv_cache": ["f16", "q8_0"],
        "gpu_layers": [60, 99],
        "speculation": ["none", "draft-mtp"],
    }

    first = discover_configurations(
        model={"id": "bonsai-27b", "context_length": 8192},
        runtime_profiles=[profile],
        capabilities=capabilities,
    )
    second = discover_configurations(
        model={"id": "bonsai-27b", "context_length": 8192},
        runtime_profiles=[profile],
        capabilities=capabilities,
    )

    assert len(first) == 32
    assert [c.configuration_id for c in first] == [c.configuration_id for c in second]
    assert len({c.configuration_id for c in first}) == len(first)

    forbidden = {"tokens_per_second", "measured_tps", "benchmark_result", "measurement"}
    for candidate in first:
        configuration = candidate.configuration
        assert not forbidden.intersection(configuration)
        assert configuration["runtime"] == "cafe-llama.cpp"
        assert configuration["model_ref"] == "bonsai-27b"
        assert configuration["kernel"] in {"baseline", "ptq1-mmV"}
        assert configuration["context"] in {4096, 8192}
        assert configuration["kv_cache"] in {"f16", "q8_0"}
        assert configuration["gpu_layers"] in {60, 99}
        assert configuration["speculation"] in {"none", "draft-mtp"}

    candidates = [c.to_dict() for c in first]
    winner = candidates[-1]
    measurements = [
        {
            "configuration_id": winner["configuration_id"],
            "evidence_type": "estimated",
            "measured_tps": 999.0,
        },
        {
            "configuration_id": winner["configuration_id"],
            "evidence_type": "measured",
            "measured_tps": 77.0,
        },
        {
            "configuration_id": candidates[0]["configuration_id"],
            "evidence_type": "measured",
            "measured_tps": 12.0,
        },
    ]
    ranked = rank_measured_candidates(candidates, measurements)

    assert [item["configuration_id"] for item in ranked] == [
        winner["configuration_id"],
        candidates[0]["configuration_id"],
    ]
    assert ranked[0]["measured_tps"] == 77.0
    assert ranked[0]["selection_status"] == "MEASURED"
