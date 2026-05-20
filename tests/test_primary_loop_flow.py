"""Integration coverage for the primary local run loop."""

from types import SimpleNamespace

from ui import dialogs, input as input_mod, output as output_mod, pipeline as pipeline_mod
from whisperforge_core import adapters as adapters_mod
from whisperforge_core import captures
from whisperforge_core import pipeline as core_pipeline
from whisperforge_core import run_artifacts


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class FakeStatus:
    def write(self, _message: str) -> None:
        return None

    def update(self, **_kwargs) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def test_primary_loop_run_then_reopen_restores_output(tmp_path, monkeypatch):
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")

    state = FakeSessionState({
        "pending_input": input_mod.PendingInput(
            source="wispr_flow",
            payload="Here is a Wispr Flow paste that should become a run.",
            filename="wispr-flow.txt",
        ),
        "_submit_mode": "full_pipeline",
        "pipeline_running": True,
        "pipeline_stage_idx": 0,
        "selected_user": None,
        "ai_provider": "Anthropic",
        "ai_model": "claude-haiku-4-5",
        "cleanup_enabled": True,
        "chapters_enabled": True,
        "agentic_drafting": False,
        "fact_check_enabled": False,
        "images_enabled": False,
        "image_style": "kk",
        "image_aspect": "16:9",
        "image_model": "gemini-2.5-flash-image",
        "article_length": "Standard",
        "rag_mode": "auto",
        "compare_provider": "OpenAI",
        "compare_model": "gpt-4o-mini",
        "selected_personas": [],
        "active_recipe": None,
        "active_recipe_id": None,
        "recipe_effective_settings": None,
        "auto_save_notion": True,
        "capture_id": None,
    })

    fake_st = SimpleNamespace(
        session_state=state,
        status=lambda *_args, **_kwargs: FakeStatus(),
        toast=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(pipeline_mod, "st", fake_st)
    monkeypatch.setattr(dialogs, "st", fake_st)

    def fake_run_pipeline(transcript, provider, model, **kwargs):
        progress = kwargs.get("progress")
        checkpoint = kwargs.get("checkpoint")
        if progress:
            progress(0.3, "Extracting wisdom...")
            progress(1.0, "Done")
        if checkpoint:
            checkpoint("wisdom", {"wisdom": "A grounded insight."})
            checkpoint("article", {"article": "Long-form article draft."})
        assert transcript.startswith("Here is a Wispr Flow paste")
        assert provider == "Anthropic"
        assert model == "claude-haiku-4-5"
        return core_pipeline.PipelineResult(
            wisdom="A grounded insight.",
            outline="1. Hook\n2. Body\n3. Close",
            social_posts="Social draft",
            image_prompts="Image prompt draft",
            article="Long-form article draft.",
            chapters=[{"title": "Intro", "summary": "Start", "start_seconds": 0}],
            article_compare="Alternate comparison draft.",
            compare_label="OpenAI gpt-4o-mini",
        )

    fake_adapters = adapters_mod.Adapters(
        transcriber=SimpleNamespace(transcribe_detailed=lambda *_args, **_kwargs: None),
        processor=SimpleNamespace(run_pipeline=fake_run_pipeline),
        storage=SimpleNamespace(save=lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(pipeline_mod.adapters_mod, "get_adapters", lambda: fake_adapters)
    monkeypatch.setattr(pipeline_mod, "_build_scorecard_summary", lambda _s: {
        "verdict_label": "Ready",
        "average_score": 86,
        "dimensions": [],
    })
    monkeypatch.setattr(pipeline_mod, "_ensure_capture", lambda _pending, _run_id: None)

    def fake_save_to_notion():
        run_id = state["run_id"]
        run_artifacts.record_export(run_id, "notion", "https://notion.so/primary-loop")
        return "https://notion.so/primary-loop"

    monkeypatch.setattr(output_mod, "_save_to_notion", fake_save_to_notion)

    pipeline_mod._execute_run()

    run_id = state.get("run_id")
    assert run_id
    assert state["pipeline_running"] is False
    assert state["pipeline_stage_idx"] == 8
    assert state["article"] == "Long-form article draft."
    assert state["last_notion_url"] == "https://notion.so/primary-loop"

    manifest = run_artifacts.load_manifest(run_id)
    assert manifest["status"] == "completed"
    assert any(
        stage.get("stage") == "session_output"
        for stage in manifest.get("stages", [])
    )
    assert any(
        item.get("kind") == "notion" and item.get("value") == "https://notion.so/primary-loop"
        for item in manifest.get("exports", [])
    )

    state["article"] = ""
    state["wisdom"] = ""
    state["outline"] = ""
    state["social_content"] = ""
    state["image_prompts"] = ""
    state["last_notion_url"] = None
    state["pipeline_stage_idx"] = 0

    assert dialogs._reopen_run(run_id) is True
    assert state["article"] == "Long-form article draft."
    assert state["wisdom"] == "A grounded insight."
    assert state["compare_label"] == "OpenAI gpt-4o-mini"
    assert state["last_notion_url"] == "https://notion.so/primary-loop"


def test_mark_capture_status_refreshes_run_manifest_capture_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(captures, "CAPTURES_DIR", tmp_path / "captures")

    record = captures.create_capture(
        capture_id="cap-1",
        source="wispr_flow",
        filename="wispr.txt",
        title="Capture title",
        text="Real owner text.",
    )
    captures.attach_run(record.capture_id, "run-1", status="running")
    run_artifacts.start_run("run-1", {"capture": captures.run_metadata(record.capture_id)})

    state = FakeSessionState({
        "run_id": "run-1",
        "capture_id": record.capture_id,
    })
    pipeline_mod._mark_capture_status(state, "completed")

    manifest = run_artifacts.load_manifest("run-1")
    capture_meta = (manifest.get("metadata") or {}).get("capture") or {}
    assert capture_meta.get("capture_id") == "cap-1"
    assert capture_meta.get("status") == "completed"
