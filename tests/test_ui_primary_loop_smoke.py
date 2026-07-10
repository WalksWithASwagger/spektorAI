"""Rendered UI smoke for the primary paste -> run -> output flow."""

from pathlib import Path
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

from ui import dialogs as dialogs_mod
from ui import output as output_mod
from ui import pipeline as pipeline_mod
from ui import sidebar as sidebar_mod
from whisperforge_core import adapters as adapters_mod
from whisperforge_core import cost as cost_mod
from whisperforge_core import pipeline as core_pipeline
from whisperforge_core import run_artifacts


class SessionStateProxy:
    def __init__(self, state):
        self._state = state

    def __getitem__(self, key):
        return self._state[key]

    def __setitem__(self, key, value):
        self._state[key] = value

    def __getattr__(self, key):
        return self._state[key]

    def __setattr__(self, key, value):
        if key == "_state":
            object.__setattr__(self, key, value)
            return
        self._state[key] = value

    def get(self, key, default=None):
        try:
            return self._state[key]
        except Exception:
            return default


def _handoff_notes(scorecard: dict) -> list[str]:
    for dimension in scorecard.get("dimensions", []):
        if dimension.get("id") == "handoff_readiness":
            return [str(note) for note in dimension.get("notes", [])]
    return []


def test_ui_primary_loop_smoke_paste_run_and_artifacts(monkeypatch, tmp_path):
    cost_mod.reset()
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(sidebar_mod, "discover_ollama_models", lambda: {})
    monkeypatch.setattr(pipeline_mod, "_inspect_retrieval", lambda *_a, **_k: None)
    monkeypatch.setattr(output_mod.llm, "generate_title", lambda _t: "UI Smoke Run")
    monkeypatch.setattr(output_mod.llm, "generate_summary", lambda _t: "UI smoke summary.")
    monkeypatch.setattr(output_mod.llm, "generate_tags", lambda _t, max_tags=5: ["ui-smoke"])

    def fake_run_pipeline(transcript, provider, model, **kwargs):
        progress = kwargs.get("progress")
        checkpoint = kwargs.get("checkpoint")
        if progress:
            progress(0.3, "Extracting wisdom...")
            progress(1.0, "Done")
        if checkpoint:
            checkpoint("wisdom", {"wisdom": "A grounded insight."})
        assert transcript == "Primary loop smoke transcript from Wispr Flow."
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
        transcriber=SimpleNamespace(transcribe_detailed=lambda *_a, **_k: None),
        processor=SimpleNamespace(run_pipeline=fake_run_pipeline),
        storage=SimpleNamespace(save=lambda *_a, **_k: "https://notion.so/ui-smoke"),
    )
    monkeypatch.setattr(pipeline_mod.adapters_mod, "get_adapters", lambda: fake_adapters)

    def fake_save_to_notion():
        run_id = pipeline_mod.st.session_state.get("run_id")
        if run_id:
            run_artifacts.record_export(run_id, "notion", "https://notion.so/ui-smoke")
        return "https://notion.so/ui-smoke"

    monkeypatch.setattr(output_mod, "_save_to_notion", fake_save_to_notion)

    app = AppTest.from_file(str(Path("app.py").resolve()), default_timeout=20)
    app.run()

    app.text_area(key="in_paste").input(
        "Primary loop smoke transcript from Wispr Flow."
    ).run()

    pending = app.session_state["pending_input"]
    assert pending.source == "wispr_flow"
    assert pending.payload == "Primary loop smoke transcript from Wispr Flow."
    assert app.button(key="btn_feeling_lucky").proto.disabled is False

    app.button(key="btn_feeling_lucky").click().run()

    run_id = app.session_state["run_id"]
    assert run_id
    assert app.session_state["pipeline_running"] is False
    assert app.session_state["article"] == "Long-form article draft."
    assert app.session_state["last_notion_url"] == "https://notion.so/ui-smoke"
    assert {"📝 Article", "🧭 Review"}.issubset({tab.label for tab in app.tabs})
    markdown_text = "\n".join(str(item.value) for item in app.markdown)
    assert "Run story" in markdown_text
    assert "Recorded exports: Notion." in markdown_text

    manifest = run_artifacts.load_manifest(run_id)
    assert manifest.get("status") == "completed"
    assert any(
        stage.get("stage") == "session_output"
        for stage in manifest.get("stages", [])
    )
    assert any(
        item.get("kind") == "notion" and item.get("value") == "https://notion.so/ui-smoke"
        for item in manifest.get("exports", [])
    )

    app.button(key="save_md").click().run()

    markdown_path = app.session_state["_last_md_path"]
    assert markdown_path
    assert Path(markdown_path).exists()

    manifest = run_artifacts.load_manifest(run_id)
    assert any(
        item.get("kind") == "markdown" and item.get("value") == markdown_path
        for item in manifest.get("exports", [])
    )
    notes = _handoff_notes(app.session_state["scorecard_summary"])
    assert any("Recorded exports:" in note for note in notes)
    assert all("No export has been recorded yet." not in note for note in notes)

    scorecard_stage = run_artifacts.load_stage_payload(run_id, "scorecard")
    scorecard_notes = _handoff_notes(scorecard_stage)
    assert any("Recorded exports:" in note for note in scorecard_notes)

    session_output = run_artifacts.load_stage_payload(run_id, "session_output")
    output_notes = _handoff_notes(session_output.get("scorecard_summary") or {})
    assert any("Recorded exports:" in note for note in output_notes)

    app.session_state["article"] = ""
    app.session_state["wisdom"] = ""
    app.run()

    # AppTest can expose dialog controls but may not dispatch dialog-button
    # callbacks reliably, so execute the same reopen helper directly. This also
    # keeps the primary smoke out of Streamlit's data_editor/PyArrow path, which
    # is covered elsewhere and has crashed CI in the dialog harness.
    monkeypatch.setattr(
        dialogs_mod, "st", SimpleNamespace(session_state=SessionStateProxy(app.session_state))
    )
    assert dialogs_mod._reopen_run(run_id) is True
    assert app.session_state["article"] == "Long-form article draft."
    assert app.session_state["wisdom"] == "A grounded insight."
    assert app.session_state["last_notion_url"] == "https://notion.so/ui-smoke"
