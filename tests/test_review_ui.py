"""Small helper tests for Review tab presentation polish."""

from ui import review


def test_run_story_step_markdown_uses_readable_status_and_timestamp():
    rendered = review._run_story_step_markdown({
        "label": "Capture",
        "status": "complete",
        "detail": "Wispr Flow input: Morning kickoff",
        "timestamp": "2026-05-21T17:04:15Z",
    })

    assert rendered == (
        "- **Capture** · `Complete` · 2026-05-21 17:04 UTC  \n"
        "  Wispr Flow input: Morning kickoff"
    )


def test_handoff_preview_download_helpers_are_markdown_safe():
    preview = {
        "title": "Handoff: Tighten week-two demo cadence",
        "body": "## Context\n\nShip the smallest useful thing.",
    }

    assert review._handoff_preview_filename(preview["title"]) == (
        "handoff-tighten-week-two-demo-cadence.md"
    )
    assert review._handoff_preview_markdown(preview).startswith(
        "# Handoff: Tighten week-two demo cadence\n\n## Context"
    )
