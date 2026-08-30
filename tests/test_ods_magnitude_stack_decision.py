from runtime_selection.stack_decision import decide_stack


def test_none_when_direct_runtime_is_sufficient():
    assert decide_stack(direct_runtime_supported=True).stack == "none"


def test_ods_for_deployment_only():
    assert decide_stack(needs_deployment=True).stack == "ods"


def test_magnitude_for_agent_only():
    assert decide_stack(needs_agent=True).stack == "magnitude"


def test_combined_stack_when_both_capabilities_are_required():
    assert decide_stack(needs_deployment=True, needs_agent=True).stack == "ods+magnitude"


def test_direct_runtime_does_not_override_explicit_capability_need():
    assert decide_stack(direct_runtime_supported=True, needs_agent=True).stack == "magnitude"
