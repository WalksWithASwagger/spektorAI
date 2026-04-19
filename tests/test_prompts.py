"""Tests for whisperforge_core.prompts — user/KB discovery + override precedence."""

from pathlib import Path

import pytest

from whisperforge_core import config, prompts


@pytest.fixture
def tmp_prompts_dir(tmp_path, monkeypatch):
    """Point PROMPTS_DIR at a fresh tmp dir for each test."""
    monkeypatch.setattr(config, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(prompts, "PROMPTS_DIR", tmp_path)
    return tmp_path


class TestListUsers:
    def test_returns_default_when_dir_missing(self, tmp_path, monkeypatch):
        missing = tmp_path / "nope"
        monkeypatch.setattr(prompts, "PROMPTS_DIR", missing)
        assert prompts.list_users() == ["default_user"]
        # Side-effect: directory gets created
        assert missing.exists()

    def test_lists_user_directories(self, tmp_prompts_dir):
        (tmp_prompts_dir / "alice").mkdir()
        (tmp_prompts_dir / "bob").mkdir()
        (tmp_prompts_dir / ".hidden").mkdir()
        assert prompts.list_users() == ["alice", "bob"]

    def test_ignores_files(self, tmp_prompts_dir):
        (tmp_prompts_dir / "alice").mkdir()
        (tmp_prompts_dir / "loose.md").write_text("not a user")
        assert prompts.list_users() == ["alice"]


class TestKnowledgeBase:
    def test_empty_when_no_kb_folder(self, tmp_prompts_dir):
        (tmp_prompts_dir / "alice").mkdir()
        assert prompts.load_knowledge_base("alice") == {}

    def test_loads_md_and_txt(self, tmp_prompts_dir):
        kb = tmp_prompts_dir / "alice" / "knowledge_base"
        kb.mkdir(parents=True)
        (kb / "voice_guide.md").write_text("friendly tone")
        (kb / "style.txt").write_text("short sentences")
        (kb / "ignored.pdf").write_text("wrong type")
        loaded = prompts.load_knowledge_base("alice")
        assert loaded == {"Voice Guide": "friendly tone", "Style": "short sentences"}


class TestPromptPrecedence:
    def test_custom_prompt_overrides_md(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        user.mkdir()
        (user / "wisdom_extraction.md").write_text("MD version")
        custom = user / "custom_prompts"
        custom.mkdir()
        (custom / "wisdom_extraction.txt").write_text("CUSTOM version")
        loaded = prompts.load_user_prompts("alice")
        assert loaded["wisdom_extraction"] == "CUSTOM version"

    def test_md_used_when_no_custom(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        user.mkdir()
        (user / "wisdom_extraction.md").write_text("MD version")
        loaded = prompts.load_user_prompts("alice")
        assert loaded["wisdom_extraction"] == "MD version"

    def test_get_prompt_falls_back_to_default(self, tmp_prompts_dir):
        users_prompts = {"alice": {}}
        result = prompts.get_prompt("alice", "wisdom_extraction", users_prompts)
        # Falls back to DEFAULT_PROMPTS
        assert "insights" in result.lower() or "wisdom" in result.lower()


class TestSaveCustomPrompt:
    def test_writes_file_to_custom_prompts(self, tmp_prompts_dir):
        ok = prompts.save_custom_prompt("alice", "wisdom_extraction", "my override")
        assert ok is True
        written = tmp_prompts_dir / "alice" / "custom_prompts" / "wisdom_extraction.txt"
        assert written.read_text() == "my override"
