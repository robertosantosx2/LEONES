from scripts.model_selector import eligibility


def _row(level="T2", **extra):
    row = {
        "model_id": "evidence-demo",
        "model_name": "Evidence Demo",
        "technical_profile_level": level,
        "runtime": "llama.cpp",
        "weight_memory_gb": "6",
    }
    row.update(extra)
    return row


def test_h10_accepts_t2_for_preliminary_hardware_viability():
    ok, reasons, evidence = eligibility(
        _row(), workload="chat", hardware="cpu-only", ram_gb=16,
        vram_gb=0, context_tokens=8192, required_runtime="llama.cpp"
    )
    assert ok is True
    assert "passes use-case, hardware, runtime and optimization gates" in reasons
    assert evidence["evidence_level"] == "T2"
    assert evidence["context_supported"] is None
    assert evidence["context_recommended"] is None


def test_h10_keeps_unknown_context_unknown():
    ok, _, evidence = eligibility(
        _row(), workload="chat", hardware="cpu-only", ram_gb=16,
        vram_gb=0, context_tokens=16384, required_runtime="llama.cpp"
    )
    assert ok is True
    assert evidence["context_supported"] is None
    assert evidence["context_target"] == 16384
    assert evidence["context_recommended"] is None


def test_h10_rejects_t1_before_hardware_recommendation():
    ok, reasons, evidence = eligibility(
        _row("T1"), workload="chat", hardware="cpu-only", ram_gb=16,
        vram_gb=0, required_runtime="llama.cpp"
    )
    assert ok is False
    assert "technical evidence level T1 is below T2" in reasons
    assert evidence == {}
