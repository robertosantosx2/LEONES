from leones.router_simple import Decision


def test_auto_run_pipeline_is_wired(monkeypatch, tmp_path):
    from leones import auto_run

    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")

    monkeypatch.setattr(auto_run, "candidates_from_atlas", lambda _: [object()])
    monkeypatch.setattr(auto_run, "route", lambda *_: Decision(str(model), "llama-cli", "test"))
    monkeypatch.setattr(auto_run, "validate", lambda *_: None)
    monkeypatch.setattr(auto_run, "run", lambda *args: "answer")

    assert auto_run.execute("atlas.sqlite", "hello") == "answer"
