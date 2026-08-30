import pytest

from scripts.integrations.ods_adapter import ODSAdapter
from scripts.integrations.magnitude_adapter import MagnitudeAdapter


@pytest.mark.parametrize("adapter_cls,ref", [
    (ODSAdapter, "v2.6.0"),
    (MagnitudeAdapter, "fixed-ref"),
])
def test_benchmark_requires_real_measurement(adapter_cls, ref):
    adapter = adapter_cls(ref)

    with pytest.raises(ValueError):
        adapter.benchmark({
            "execution_authorized": True,
            "runtime": {"name": "test", "adapter": "test"},
            "model_id": "test-model",
            "quantization": "Q4_K_M",
            "measured": {},
        })
