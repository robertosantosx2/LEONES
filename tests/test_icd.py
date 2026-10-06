import pytest

from runtime_selection.icd import (
    SCHEMA_VERSION,
    ConfigurationCandidate,
    configuration_signature,
    discover_configurations,
    rank_measured_candidates,
    validate_configuration,
)


def test_configuration_signature_is_stable():
    a = {"runtime": "cafe-llama.cpp", "context": 65536, "model_ref": "bonsai"}
    b = {"context": 65536, "model_ref": "bonsai", "runtime": "cafe-llama.cpp"}
    assert configuration_signature(a) == configuration_signature(b)


def test_configuration_rejects_execution_and_measurement_fields():
    with pytest.raises(ValueError):
        validate_configuration({
            "runtime": "cafe-llama.cpp",
            "model_ref": "bonsai",
            "tokens_per_second": 42,
        })


def test_discovery_preserves_runtime_profile_as_compatibility_source():
    candidates = discover_configurations(
        model={"id": "bonsai-27b", "context_length": 65536},
        runtime_profiles=[{
            "runtime": "cafe-llama.cpp",
            "runtime_revision": "pr-ptq1-mmv",
            "kernel": "ptq1-mmV",
            "context_length": 65536,
            "gpu_layers": 99,
            "kv_cache": "f16",
            "flash_attention": True,
            "speculation": "draft-mtp",
            "draft_tokens": 1,
        }],
    )
    assert len(candidates) == 1
    payload = candidates[0].to_dict()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["execution_authorized"] is False
    assert payload["measurement_required"] is True
    assert payload["configuration"]["kernel"] == "ptq1-mmV"


def test_capabilities_expand_configuration_space():
    candidates = discover_configurations(
        model={"id": "m", "context_length": 8192},
        runtime_profiles=[{"runtime": "cafe-llama.cpp"}],
        capabilities={"flash_attention": [True, False], "kv_cache": ["f16", "q8_0"]},
    )
    assert len(candidates) == 4


def test_discovery_deduplicates_equivalent_profiles():
    profile = {"runtime": "cafe-llama.cpp", "context_length": 65536}
    candidates = discover_configurations(model={"id": "m"}, runtime_profiles=[profile, dict(profile)])
    assert len(candidates) == 1


def test_measured_feedback_ranks_only_matching_measured_configurations():
    candidates = [
        ConfigurationCandidate({"runtime": "a", "model_ref": "m", "context": 8192}).to_dict(),
        ConfigurationCandidate({"runtime": "a", "model_ref": "m", "context": 65536}).to_dict(),
    ]
    measurements = [
        {"configuration_id": candidates[0]["configuration_id"], "evidence_type": "measured", "measured_tps": 10},
        {"configuration_id": candidates[1]["configuration_id"], "evidence_type": "estimated", "measured_tps": 100},
    ]
    ranked = rank_measured_candidates(candidates, measurements)
    assert [x["measured_tps"] for x in ranked] == [10.0]
