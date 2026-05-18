"""Tests for knowledge-base inventory and health signals."""

from datetime import datetime, timezone

import pytest

from whisperforge_core import config, kb_audit


@pytest.fixture
def tmp_prompts_dir(tmp_path, monkeypatch):
    prompts_dir = tmp_path / "prompts"
    monkeypatch.setattr(config, "PROMPTS_DIR", prompts_dir)
    monkeypatch.setattr(kb_audit, "PROMPTS_DIR", prompts_dir)
    return prompts_dir


def test_missing_kb_reports_warning(tmp_prompts_dir):
    audit = kb_audit.audit_profile("alice")

    assert audit.documents == []
    assert audit.warnings[0].code == "missing_kb"


def test_inventory_records_role_tokens_and_modified_date(tmp_prompts_dir):
    kb = tmp_prompts_dir / "alice" / "knowledge_base"
    kb.mkdir(parents=True)
    (kb / "voice-style.md").write_text("voice " * 120)
    (kb / "worldview.txt").write_text("world " * 80)

    audit = kb_audit.audit_profile("alice")

    assert [doc.role for doc in audit.documents] == ["voice", "worldview"]
    assert audit.total_tokens > 0
    assert audit.documents[0].modified_at.endswith("Z")


def test_duplicate_empty_private_and_stale_warnings(tmp_prompts_dir):
    kb = tmp_prompts_dir / "alice" / "knowledge_base"
    kb.mkdir(parents=True)
    (kb / "private-token.md").write_text("same")
    (kb / "copy.md").write_text("same")
    (kb / "empty.md").write_text("")

    audit = kb_audit.audit_profile(
        "alice",
        now=datetime(2027, 1, 1, tzinfo=timezone.utc),
    )
    codes = {warning.code for warning in audit.warnings}

    assert "duplicate_content" in codes
    assert "empty_file" in codes
    assert "private_marker" in codes
    assert "stale_file" in codes


def test_to_dict_includes_summary(tmp_prompts_dir):
    kb = tmp_prompts_dir / "alice" / "knowledge_base"
    kb.mkdir(parents=True)
    (kb / "notes.md").write_text("note " * 50)

    data = kb_audit.audit_profile("alice").to_dict()

    assert data["summary"]["documents"] == 1
    assert data["documents"][0]["name"] == "notes"
