"""Tests for agentic handoff draft exports."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "agentic"))

from common import load_contract  # noqa: E402
from issue_lint import lint_issue  # noqa: E402
from whisperforge_core import handoffs, run_artifacts


def test_issue_draft_contains_required_sections_and_lints_agent_ready():
    draft = handoffs.build_issue_draft(
        title="Turn capture into follow-up queue",
        source_text="Capture says we need a weekly follow-up queue for unresolved ideas.",
        source_kind="capture",
        source_title="Weekly ops capture",
        recipe={"recipe_name": "Issue and handoff brief"},
        scorecard={"verdict_label": "Review", "average_score": 72},
    )

    for section in handoffs.REQUIRED_SECTIONS:
        assert f"## {section}" in draft.body
    result = lint_issue(draft.body, ["agent:ready"], load_contract(Path(__file__).resolve().parents[1]))
    assert result["ok"], result["message"]


def test_issue_draft_handles_selected_output_source():
    draft = handoffs.build_issue_draft(
        title="Improve article handoff",
        source_text="Article draft asks for stronger acceptance criteria and tests.",
        source_kind="selected output",
        source_title="Article",
    )

    assert "Drafted from WhisperForge selected output: Article" in draft.body
    assert "- [ ] Confirm the requested outcome" in draft.body
    assert "Automatic GitHub or Linear issue creation" in draft.body


def test_persist_draft_writes_markdown_and_run_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")
    run_artifacts.start_run("run-1", {"mode": "full_pipeline"})
    draft = handoffs.build_issue_draft(
        title="Persist me",
        source_text="A compact source brief.",
    )

    path = handoffs.persist_draft("run-1", draft)

    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("# Persist me")
    manifest = run_artifacts.load_manifest("run-1")
    assert manifest["exports"][0]["kind"] == "handoff_draft"
    stage = json.loads((tmp_path / "runs" / "run-1" / "stages" / "handoff_draft.json").read_text())
    assert stage["payload"]["path"] == str(path)
