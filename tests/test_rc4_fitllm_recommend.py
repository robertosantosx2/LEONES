from types import SimpleNamespace

from scripts import rc4_fitllm_recommend as recommender


def feed(*ids):
    return {
        "schema": "leones.rc4.model-evidence.v1",
        "hardware": {"ram_gb": 16, "vram_gb": None},
        "sources": {
            "huggingface": {"models_considered": len(ids)},
            "artificial_analysis": {"models_available": len(ids), "intelligence_index_version": 4.0},
        },
        "fitllm_input": {
            "max_models": 100,
            "model_count": len(ids),
            "model_evidence": [
                {
                    "model_id": model_id,
                    "evidence_rank": rank,
                    "evidence_level": "estimated",
                    "hf": {"model_id": model_id, "revision": f"rev-{rank}"},
                    "artificial_analysis": {"name": model_id, "evaluations": {}},
                }
                for rank, model_id in enumerate(ids, 1)
            ],
        },
    }


def fake_llmfit(models):
    return SimpleNamespace(
        version="1.1.10",
        command=("llmfit", "recommend", "--json", "--limit", "100", "--use-case", "coding"),
        models=tuple(models),
    )


def test_feed_is_capped_at_100_and_three_candidates_are_estimated(monkeypatch):
    evidence = feed(*(f"org/model-{i}" for i in range(101)))
    calls = []

    monkeypatch.setattr(recommender.llmfit_mod, "executable", lambda: "/usr/bin/llmfit")
    monkeypatch.setattr(
        recommender.llmfit_mod,
        "run_recommend",
        lambda **kwargs: calls.append(kwargs) or fake_llmfit(
            [{"name": f"org/model-{i}", "score": 90 - i} for i in range(5)]
        ),
    )

    result = recommender.recommend(user_intent=["programming"], evidence_feed=evidence)

    assert result["status"] == "ok"
    assert result["candidate_count"] == 3
    assert result["evidence"]["model_count"] == 100
    assert calls[0]["limit"] == 100
    assert calls[0]["use_case"] == "coding"
    assert all(row["kind"] == "ESTIMATED" for row in result["recommendations"])
    assert result["execution_authorized"] is False
    assert result["measured"] is False


def test_multiple_user_intents_query_llmfit_for_each_purpose(monkeypatch):
    evidence = feed(
        "org/coding-model",
        "org/reasoning-model",
        "org/shared-model",
        "org/third-model",
    )
    calls = []

    monkeypatch.setattr(
        recommender.llmfit_mod,
        "executable",
        lambda: "/usr/bin/llmfit",
    )

    def fake_run(**kwargs):
        calls.append(kwargs)
        if kwargs["use_case"] == "coding":
            models = [
                {"name": "org/coding-model", "score": 90},
                {"name": "org/third-model", "score": 80},
            ]
        else:
            models = [
                {"name": "org/reasoning-model", "score": 95},
                {"name": "org/third-model", "score": 85},
            ]
        return fake_llmfit(models)

    monkeypatch.setattr(
        recommender.llmfit_mod,
        "run_recommend",
        fake_run,
    )

    result = recommender.recommend(
        user_intent=["programming", "reasoning"],
        evidence_feed=evidence,
    )

    assert result["status"] == "ok"
    assert len(calls) == 2
    assert [call["use_case"] for call in calls] == [
        "coding",
        "reasoning",
    ]
    assert calls[0]["limit"] == 100
    assert calls[1]["limit"] == 100
    assert [
        row["model_id"] for row in result["recommendations"]
    ] == [
        "org/coding-model",
        "org/third-model",
        "org/reasoning-model",
    ]
    assert result["candidate_count"] == 3
    assert result["user_intent"]["purposes"] == [
        "programming",
        "reasoning",
    ]
    assert result["execution_authorized"] is False
    assert result["measurement_authorized"] is False
    assert result["measured"] is False


def test_llmfit_results_outside_evidence_are_excluded(monkeypatch):
    evidence = feed("org/model-a", "org/model-b", "org/model-c")
    monkeypatch.setattr(recommender.llmfit_mod, "executable", lambda: "/usr/bin/llmfit")
    monkeypatch.setattr(
        recommender.llmfit_mod,
        "run_recommend",
        lambda **kwargs: fake_llmfit(
            [
                {"name": "outside/model", "score": 100},
                {"name": "org/model-a", "score": 90},
                {"name": "org/model-b", "score": 80},
                {"name": "org/model-c", "score": 70},
            ]
        ),
    )

    result = recommender.recommend(user_intent=["programming"], evidence_feed=evidence)

    assert result["status"] == "ok"
    assert [row["model_id"] for row in result["recommendations"]] == [
        "org/model-a",
        "org/model-b",
        "org/model-c",
    ]
    assert result["selection_boundary"] == "evidence_backed_intersection"


def test_fewer_than_three_intersections_is_insufficient_without_padding(monkeypatch):
    evidence = feed("org/model-a", "org/model-b", "org/model-c")
    monkeypatch.setattr(recommender.llmfit_mod, "executable", lambda: "/usr/bin/llmfit")
    monkeypatch.setattr(
        recommender.llmfit_mod,
        "run_recommend",
        lambda **kwargs: fake_llmfit(
            [{"name": "org/model-a"}, {"name": "outside/model"}]
        ),
    )

    result = recommender.recommend(user_intent=["reasoning"], evidence_feed=evidence)

    assert result["status"] == "insufficient"
    assert result["candidate_count"] == 1
    assert result["recommendations"][0]["model_id"] == "org/model-a"
    assert result["execution_authorized"] is False


def test_empty_user_intent_is_rejected():
    try:
        recommender.recommend(user_intent=[], evidence_feed=feed("org/model-a"))
    except ValueError as exc:
        assert "at least one" in str(exc)
    else:
        raise AssertionError("empty RC4 user intent must fail")
