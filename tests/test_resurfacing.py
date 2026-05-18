"""Tests for report-only resurfacing digests."""

from datetime import datetime, timezone

from whisperforge_core import captures, resurfacing, run_artifacts


def test_digest_groups_captures_runs_and_source_links(tmp_path, monkeypatch):
    monkeypatch.setattr(captures, "CAPTURES_DIR", tmp_path / "captures")
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")
    captures.create_capture(
        capture_id="cap-1",
        source="wispr_flow",
        filename="wispr.txt",
        title="Follow up with Maya",
        text="Maya asked for a follow-up on the AI workshop brief.",
    )
    run_artifacts.start_run("run-1", {"source": "paste"})
    run_artifacts.write_stage("run-1", "session_output", {
        "article": "# Strong draft\n\nBody",
        "wisdom": "Reusable insight about community trust.",
    })
    run_artifacts.write_stage("run-1", "scorecard", {
        "average_score": 88,
        "verdict_label": "Ready",
    })
    run_artifacts.mark_status("run-1", "completed")

    digest = resurfacing.build_digest(now=datetime(2026, 5, 18, tzinfo=timezone.utc))

    sections = digest["sections"]
    assert sections["Notable captures"][0]["source"] == "capture:cap-1"
    assert sections["Unresolved follow-ups"][0]["source"] == "capture:cap-1"
    assert "captured" in sections["Unresolved follow-ups"][0]["detail"]
    assert sections["Strong outputs"][0]["source"] == "run:run-1"
    assert sections["Stale drafts"][0]["source"] == "run:run-1"
    assert "Reusable insight" in sections["Reusable source nuggets"][-1]["detail"]


def test_render_markdown_is_report_only_and_has_all_sections():
    digest = {
        "generated_at": "2026-05-18T00:00:00Z",
        "sections": {name: [] for name in resurfacing.DIGEST_SECTIONS},
    }

    markdown = resurfacing.render_markdown(digest)

    assert "Mode: report-only" in markdown
    for section in resurfacing.DIGEST_SECTIONS:
        assert f"## {section}" in markdown


def test_write_digest_creates_markdown_file(tmp_path, monkeypatch):
    monkeypatch.setattr(captures, "CAPTURES_DIR", tmp_path / "captures")
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")

    path = resurfacing.write_digest(tmp_path / "digests")

    assert path.exists()
    assert path.name.endswith("-resurfacing-digest.md")
