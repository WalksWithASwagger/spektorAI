"""Integration tests for the run reopen flow used in the Runs dialog."""

from types import SimpleNamespace

import pytest

from ui import dialogs
from whisperforge_core import run_artifacts


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def tmp_runs_dir(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", runs)
    return runs


def test_reopen_run_restores_primary_output_state(tmp_runs_dir, monkeypatch):
    run_id = "run-1"
    run_artifacts.start_run(run_id, {
        "source": "paste",
        "recipe": {"recipe_name": "Issue handoff"},
    })
    run_artifacts.write_stage(run_id, "transcription", {
        "text": "Transcript text from paste input.",
        "segments": [{"start": 0.0, "end": 1.2, "text": "Transcript text"}],
    })
    run_artifacts.write_stage(run_id, "retrieval_inspector", {
        "stages": {"wisdom_extraction": []},
        "engaged": True,
    })
    run_artifacts.write_stage(run_id, "scorecard", {
        "verdict_label": "Ready",
        "average_score": 88,
        "dimensions": [],
    })
    run_artifacts.write_stage(run_id, "session_output", {
        "wisdom": "Key grounded insight.",
        "outline": "1. Hook\n2. Body\n3. Close",
        "social_content": "Post draft",
        "image_prompts": "Prompt draft",
        "article": "# Draft Article\n\nBody",
        "chapters": [{"title": "Intro", "summary": "Start", "start_seconds": 0}],
        "fact_check_flags": [],
        "generated_images": ["/tmp/image.png"],
        "article_compare": "Alternate article",
        "compare_label": "alternate",
        "persona_articles": [{"name": "Operator", "text": "Persona draft"}],
        "songforge": {"mode": "songforge", "title": "SongForge draft"},
        "scorecard_summary": {"verdict_label": "Ready", "average_score": 88},
    })
    run_artifacts.record_export(run_id, "notion", "https://notion.so/run-1")
    run_artifacts.mark_status(run_id, "completed")

    fake_st = SimpleNamespace(session_state=FakeSessionState())
    monkeypatch.setattr(dialogs, "st", fake_st)

    ok = dialogs._reopen_run(run_id)

    assert ok is True
    state = fake_st.session_state
    assert state["run_id"] == run_id
    assert state["pipeline_running"] is False
    assert state["pipeline_stage_idx"] == 8
    assert state["transcription"] == "Transcript text from paste input."
    assert state["article"] == "# Draft Article\n\nBody"
    assert state["wisdom"] == "Key grounded insight."
    assert state["article_compare"] == "Alternate article"
    assert state["compare_label"] == "alternate"
    assert state["persona_articles"] == [{"name": "Operator", "text": "Persona draft"}]
    assert state["songforge"] == {"mode": "songforge", "title": "SongForge draft"}
    assert state["scorecard_summary"]["average_score"] == 88
    assert state["last_notion_url"] == "https://notion.so/run-1"


def test_reopen_run_returns_false_for_partial_run_without_output_stage(tmp_runs_dir, monkeypatch):
    run_artifacts.start_run("run-2", {"source": "paste"})
    run_artifacts.write_stage("run-2", "transcription", {"text": "Only transcript"})
    run_artifacts.mark_status("run-2", "running")

    fake_st = SimpleNamespace(session_state=FakeSessionState())
    monkeypatch.setattr(dialogs, "st", fake_st)

    ok = dialogs._reopen_run("run-2")

    assert ok is False
    assert fake_st.session_state == {}
