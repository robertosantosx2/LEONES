"""RC4 FitLLM recommender — soft dependency and authorization invariants."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_recommend_unavailable_without_binary():
    mod = _load("rc4_fitllm_recommend", "scripts/rc4_fitllm_recommend.py")
    with mock.patch("runtime_selection.llmfit.executable", return_value=None):
        env = mod.recommend(user_intent=["coding", "research"])
    assert env["status"] == "unavailable"
    assert env["execution_authorized"] is False
    assert env["measurement_authorized"] is False
    assert env["measured"] is False
    assert env["user_choice_required"] is True
    assert env["fitllm_required_for_boot"] is False
    assert env["kind"] == "ESTIMATED"
    assert env["candidate_count"] == 0
    assert env["recommendations"] == []
    assert env["user_intent"]["required"] is True
    assert env["user_intent"]["selection_mode"] == "multiple"
    assert env["user_intent"]["purposes"] == ["programming", "research"]


def test_recommend_ok_returns_exactly_three_estimated_candidates():
    mod = _load("rc4_fitllm_recommend", "scripts/rc4_fitllm_recommend.py")
    from runtime_selection.llmfit import LLMFitResult

    fake = LLMFitResult(
        command=("llmfit", "recommend", "--json", "--limit", "3"),
        version="test",
        system={},
        models=[
            {"id": "demo-1", "score": 3},
            {"id": "demo-2", "score": 2},
            {"id": "demo-3", "score": 1},
            {"id": "demo-4", "score": 0},
        ],
        raw={},
    )
    with mock.patch("runtime_selection.llmfit.executable", return_value="/usr/bin/llmfit"):
        with mock.patch("runtime_selection.llmfit.run_recommend", return_value=fake) as run:
            env = mod.recommend(user_intent=["coding", "research"])
    run.assert_called_once()
    assert run.call_args.kwargs["use_case"] == "coding"
    assert env["status"] == "ok"
    assert env["candidate_count"] == 3
    assert [x["model_id"] for x in env["recommendations"]] == ["demo-1", "demo-2", "demo-3"]
    assert all(x["kind"] == "ESTIMATED" for x in env["recommendations"])
    assert env["execution_authorized"] is False
    assert env["measurement_authorized"] is False
    assert env["measured"] is False


def test_recommend_does_not_fabricate_missing_third_candidate():
    mod = _load("rc4_fitllm_recommend", "scripts/rc4_fitllm_recommend.py")
    from runtime_selection.llmfit import LLMFitResult

    fake = LLMFitResult(
        command=("llmfit", "recommend", "--json", "--limit", "3"),
        version="test",
        system={},
        models=[{"id": "demo-1"}, {"id": "demo-2"}],
        raw={},
    )
    with mock.patch("runtime_selection.llmfit.executable", return_value="/usr/bin/llmfit"):
        with mock.patch("runtime_selection.llmfit.run_recommend", return_value=fake):
            env = mod.recommend(user_intent=["coding", "research"])
    assert env["status"] == "insufficient"
    assert env["candidate_count"] == 2
    assert len(env["recommendations"]) == 2
    assert "no se fabrica" in env["message"]


def test_component_cost_catalog_and_prompts():
    cost_mod = _load("rc4_component_cost", "scripts/rc4_component_cost.py")
    life = _load("rc4_install_lifecycle", "scripts/rc4_install_lifecycle.py")
    for cid in life.all_installable():
        c = cost_mod.get_cost(cid)
        assert c is not None, cid
        lines = cost_mod.install_prompt_lines(cid, lang="es")
        assert any("Disco" in x or "COSTE" in x for x in lines)
        assert cost_mod.uninstall_prompt_lines(cid, lang="ja")


def test_post_stack_uninstall_offer_opt_in():
    life = _load("rc4_install_lifecycle", "scripts/rc4_install_lifecycle.py")
    offer = life.post_stack_fitllm_uninstall_offer(stack="ods")
    assert offer["opt_in_required"] is True
    assert offer["silent_uninstall_forbidden"] is True
    assert offer["offer_uninstall"] == "fitllm"
