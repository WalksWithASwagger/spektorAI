"""Tests for human-readable run story timelines."""

from whisperforge_core import run_story


def _step_by_id(story: list[dict[str, str]], step_id: str) -> dict[str, str]:
    return next(step for step in story if step["id"] == step_id)


def test_build_run_story_summarizes_completed_exported_run():
    story = run_story.build_run_story({
        "status": "completed",
        "metadata": {
            "source": "wispr_flow",
            "filename": "capture.txt",
            "capture": {"source": "wispr_flow", "title": "Morning kickoff"},
            "settings": {"rag_mode": "auto"},
        },
        "stages": [
            {"stage": "transcription"},
            {"stage": "retrieval_inspector"},
            {"stage": "session_output"},
            {"stage": "scorecard"},
        ],
        "exports": [
            {"kind": "markdown", "value": "/tmp/run.md"},
            {"kind": "notion", "value": "https://notion.so/run"},
        ],
    })

    assert _step_by_id(story, "capture")["detail"] == "Wispr Flow input: Morning kickoff"
    assert _step_by_id(story, "transcription")["status"] == "complete"
    assert _step_by_id(story, "context")["status"] == "complete"
    assert _step_by_id(story, "generation")["status"] == "complete"
    assert _step_by_id(story, "review")["status"] == "complete"
    assert _step_by_id(story, "export")["detail"] == "Recorded exports: Markdown, Notion."


def test_build_run_story_uses_external_capture_metadata_for_text_source():
    story = run_story.build_run_story(
        {
            "status": "completed",
            "metadata": {"filename": "capture.txt", "settings": {"rag_mode": "never"}},
            "stages": [{"stage": "transcription"}],
            "exports": [],
        },
        capture_metadata={
            "source": "wispr_flow",
            "title": "Fresh capture",
            "status": "completed",
        },
    )

    assert _step_by_id(story, "capture")["detail"] == "Wispr Flow input: Fresh capture"
    assert _step_by_id(story, "transcription")["detail"] == (
        "Text input used; transcription was not needed."
    )


def test_build_run_story_marks_failure_without_export_as_waiting():
    story = run_story.build_run_story({
        "status": "failed",
        "error": "model timeout",
        "metadata": {"source": "upload", "filename": "talk.mp3"},
        "stages": [{"stage": "transcription"}],
        "exports": [],
    })

    assert _step_by_id(story, "generation") == {
        "id": "generation",
        "label": "Composition",
        "status": "error",
        "detail": "model timeout",
        "timestamp": "",
    }
    assert _step_by_id(story, "export")["status"] == "waiting"


def test_build_run_story_includes_handoff_when_recipe_or_export_exists():
    waiting_story = run_story.build_run_story({
        "status": "completed",
        "metadata": {
            "source": "paste",
            "recipe": {"effective_settings": {"handoff_targets": ["github", "linear"]}},
        },
        "stages": [{"stage": "session_output"}],
        "exports": [],
    })

    assert _step_by_id(waiting_story, "handoff")["status"] == "waiting"
    assert "github, linear" in _step_by_id(waiting_story, "handoff")["detail"]

    complete_story = run_story.build_run_story({
        "status": "completed",
        "metadata": {"source": "paste"},
        "stages": [{"stage": "session_output"}],
        "exports": [{"kind": "handoff_draft", "value": "/tmp/handoff.md"}],
    })

    assert _step_by_id(complete_story, "handoff")["status"] == "complete"
