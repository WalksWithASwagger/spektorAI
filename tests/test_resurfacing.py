"""Tests for report-only resurfacing digests."""

import json
from datetime import datetime, timezone

from whisperforge_core import captures, resurfacing, run_artifacts


def _routing_digest():
    sections = {name: [] for name in resurfacing.DIGEST_SECTIONS}
    sections["Unresolved follow-ups"].append({
        "title": "Follow up with Maya",
        "source": "capture:cap-1",
        "detail": "Capture status is `captured`.",
        "link": "/tmp/cap-1.json",
    })
    return {
        "generated_at": "2026-05-18T00:00:00Z",
        "mode": "report-only",
        "sections": sections,
    }


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


def test_digest_route_without_approval_stays_report_only(tmp_path):
    queue_path = tmp_path / "followups.jsonl"

    result = resurfacing.route_digest(
        _routing_digest(),
        destination="followup_queue",
        approved=False,
        queue_path=str(queue_path),
    )

    assert result.success is True
    assert result.dry_run is True
    assert result.details["approval_required"] is True
    assert not queue_path.exists()


def test_digest_route_approved_followup_queue_writes(tmp_path, monkeypatch):
    queue_path = tmp_path / "followups.jsonl"
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = resurfacing.route_digest(
        _routing_digest(),
        destination="followup_queue",
        approved=True,
        queue_path=str(queue_path),
    )

    record = json.loads(queue_path.read_text(encoding="utf-8").splitlines()[0])
    assert result.success is True
    assert result.dry_run is False
    assert record["title"] == "WhisperForge resurfacing digest 2026-05-18"
    assert "Mode: report-only" in record["body"]
    assert "Follow up with Maya" in record["body"]


def test_digest_route_approved_dry_run_skips_notion_draft_write(tmp_path, monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = resurfacing.route_digest(
        _routing_digest(),
        destination="notion_page_draft",
        approved=True,
        dry_run=True,
        notion_draft_dir=str(tmp_path),
    )

    assert result.success is True
    assert result.dry_run is True
    assert list(tmp_path.iterdir()) == []


def test_digest_route_missing_notion_draft_config_is_visible(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_NOTION_DRAFT_DIR", raising=False)

    result = resurfacing.route_digest(
        _routing_digest(),
        destination="notion_task_draft",
        approved=True,
    )

    assert result.success is False
    assert result.dry_run is True
    assert "WHISPERFORGE_HANDOFF_NOTION_DRAFT_DIR" in (result.error or "")


def test_digest_filters_demo_and_smoke_captures_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(captures, "CAPTURES_DIR", tmp_path / "captures")
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")

    captures.create_capture(
        capture_id="cap-real",
        source="wispr_flow",
        filename="real.txt",
        title="Real capture",
        text="Owner planning note for a real workflow.",
        metadata={"created_by": "streamlit_input"},
    )
    captures.create_capture(
        capture_id="cap-demo",
        source="wispr_flow",
        filename="demo.txt",
        title="Demo capture",
        text="Seeded demo text for cold-start data.",
        metadata={"created_by": "demo_seed"},
    )
    captures.create_capture(
        capture_id="cap-smoke",
        source="wispr_flow",
        filename="smoke.txt",
        title="Primary loop smoke transcript from Wispr Flow.",
        text="Primary loop smoke transcript from Wispr Flow.",
        metadata={"created_by": "streamlit_input"},
    )

    run_artifacts.start_run("run-real", {"capture": {"capture_id": "cap-real"}})
    run_artifacts.write_stage("run-real", "session_output", {
        "article": "# Real output\n\nBody",
        "wisdom": "Real insight.",
    })
    run_artifacts.write_stage("run-real", "scorecard", {
        "average_score": 91,
        "verdict_label": "Ready",
    })
    run_artifacts.mark_status("run-real", "completed")

    run_artifacts.start_run("run-demo", {"capture": {"capture_id": "cap-demo"}})
    run_artifacts.write_stage("run-demo", "session_output", {
        "article": "# Demo output\n\nBody",
        "wisdom": "Demo insight.",
    })
    run_artifacts.write_stage("run-demo", "scorecard", {
        "average_score": 92,
        "verdict_label": "Ready",
    })
    run_artifacts.mark_status("run-demo", "completed")

    digest = resurfacing.build_digest()
    sections = digest["sections"]
    notable_sources = {entry["source"] for entry in sections["Notable captures"]}
    strong_sources = {entry["source"] for entry in sections["Strong outputs"]}

    assert digest["capture_filter"] == "default"
    assert "capture:cap-real" in notable_sources
    assert "capture:cap-demo" not in notable_sources
    assert "capture:cap-smoke" not in notable_sources
    assert "run:run-real" in strong_sources
    assert "run:run-demo" not in strong_sources


def test_digest_can_include_nonprod_captures_when_requested(tmp_path, monkeypatch):
    monkeypatch.setattr(captures, "CAPTURES_DIR", tmp_path / "captures")
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")

    captures.create_capture(
        capture_id="cap-demo",
        source="wispr_flow",
        filename="demo.txt",
        title="Demo capture",
        text="Seeded demo text for cold-start data.",
        metadata={"created_by": "demo_seed"},
    )

    digest = resurfacing.build_digest(include_nonprod=True)
    notable_sources = {entry["source"] for entry in digest["sections"]["Notable captures"]}

    assert digest["capture_filter"] == "all"
    assert "capture:cap-demo" in notable_sources


def test_weekly_recaps_group_capture_and_run_metadata():
    capture_records = [
        captures.CaptureRecord(
            capture_id="cap-ai",
            source="paste",
            title="AI notes",
            filename="ai.txt",
            created_at="2026-05-12T10:00:00Z",
            metadata={"topics": ["AI", "Community"]},
        ),
        captures.CaptureRecord(
            capture_id="cap-design",
            source="wispr_flow",
            title="Design notes",
            filename="design.txt",
            status="completed",
            created_at="2026-05-05T10:00:00Z",
            metadata={"tags": "Design"},
        ),
    ]
    manifests = [
        {
            "run_id": "run-ai",
            "status": "completed",
            "created_at": "2026-05-13T10:00:00Z",
            "metadata": {"source": "paste", "recipe": {"name": "AI Brief"}},
        },
        {
            "run_id": "run-draft",
            "status": "running",
            "created_at": "2026-05-06T10:00:00Z",
            "metadata": {"keywords": ["Design"]},
        },
    ]

    recaps = resurfacing.build_weekly_recaps(capture_records, manifests)

    assert recaps[0]["title"] == "2026-W20"
    assert recaps[0]["detail"] == (
        "1 captures, 1 runs, 1 completed runs, 1 unresolved items. "
        "Top topics: ai, ai brief, community."
    )
    assert recaps[1]["title"] == "2026-W19"
    assert "1 captures, 1 runs, 0 completed runs, 1 unresolved items" in recaps[1]["detail"]


def test_topic_evolution_summarizes_first_latest_and_totals():
    capture_records = [
        captures.CaptureRecord(
            capture_id="cap-early",
            source="paste",
            title="Early AI",
            filename="early.txt",
            created_at="2026-05-04T10:00:00Z",
            metadata={"topics": ["AI"]},
        ),
        captures.CaptureRecord(
            capture_id="cap-late",
            source="paste",
            title="Late AI",
            filename="late.txt",
            created_at="2026-05-12T10:00:00Z",
            metadata={"tags": ["AI", "Governance"]},
        ),
    ]
    manifests = [
        {
            "run_id": "run-late",
            "status": "completed",
            "created_at": "2026-05-13T10:00:00Z",
            "metadata": {"topics": ["Governance"], "recipe": {"name": "AI"}},
        },
    ]

    evolution = resurfacing.build_topic_evolution(capture_records, manifests)

    assert evolution[0] == {
        "title": "ai",
        "detail": "First seen 2026-W19; latest 2026-W20 with 2 signals; 3 total signals across 2 weeks.",
    }
    assert evolution[1] == {
        "title": "governance",
        "detail": "First seen 2026-W20; latest 2026-W20 with 2 signals; 2 total signals across 1 week.",
    }


def test_write_digest_creates_markdown_file(tmp_path, monkeypatch):
    monkeypatch.setattr(captures, "CAPTURES_DIR", tmp_path / "captures")
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")

    path = resurfacing.write_digest(tmp_path / "digests")

    assert path.exists()
    assert path.name.endswith("-resurfacing-digest.md")
