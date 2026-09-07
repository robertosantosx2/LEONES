from scripts.rc4_user_choice import (
    ModelCost,
    aggregate_model_costs,
    build_choice_envelope,
    disk_gate,
    validate_model_selection,
    validate_solution,
)


def test_multiple_models_have_no_artificial_three_limit():
    selected = validate_model_selection(["a", "b", "c", "d", "e", "a"])
    assert selected == ["a", "b", "c", "d", "e"]


def test_disk_gate_blocks_when_required_space_does_not_fit():
    gate = disk_gate(free_bytes=9, model_cost_bytes=6, solution_cost_bytes=4)
    assert gate["status"] == "BLOCKED"
    assert gate["install_allowed"] is False
    assert gate["partial_install_allowed"] is False


def test_unknown_cost_never_passes():
    gate = disk_gate(free_bytes=100, model_cost_bytes=None, solution_cost_bytes=4)
    assert gate["status"] == "UNKNOWN"
    assert gate["install_allowed"] is False


def test_aggregate_costs_all_selected_models():
    costs = [
        ModelCost("a", disk_bytes=10, runtime_bytes=2, dependency_bytes=1, data_bytes=1, safety_margin_bytes=1),
        ModelCost("b", disk_bytes=20, runtime_bytes=2, dependency_bytes=1, data_bytes=1, safety_margin_bytes=1),
    ]
    total = aggregate_model_costs(costs)
    assert total["model_count"] == 2
    assert total["disk_bytes"] == 30
    assert total["total_install_bytes"] == 40


def test_choice_envelope_keeps_selection_separate_from_consent():
    envelope = build_choice_envelope(
        purposes=["programming", "research"],
        model_ids=["a", "b", "c", "d"],
        solution="both",
        free_disk_bytes=100,
        model_cost={"total_install_bytes": 40},
        solution_cost={"total_bytes": 20},
    )
    assert envelope["models"]["selected"] == ["a", "b", "c", "d"]
    assert envelope["models"]["artificial_limit"] is None
    assert envelope["solution"]["selection"] == "both"
    assert envelope["cost"]["aggregate"]["status"] == "PASS"
    assert envelope["consent"] == {"purpose": False, "models": False, "solution": False, "install": False}
    assert envelope["install"]["authorized"] is False


def test_shared_components_are_deducted_once():
    gate = disk_gate(
        free_bytes=100,
        model_cost_bytes=40,
        solution_cost_bytes=20,
        shared_component_bytes=5,
    )
    assert gate["required_bytes"] == 55
    assert gate["remaining_bytes"] == 45


def test_solution_validation():
    assert validate_solution(" BOTH ") == "both"
