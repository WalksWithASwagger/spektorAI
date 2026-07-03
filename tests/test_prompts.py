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

    def test_governance_ignores_files_and_labels_canonical_anchors(self, tmp_prompts_dir):
        kb = tmp_prompts_dir / "alice" / "knowledge_base"
        kb.mkdir(parents=True)
        (kb / "voice.md").write_text("canonical tone")
        (kb / "notes.md").write_text("usable notes")
        (kb / "old.md").write_text("ignored notes")
        (kb / "governance.yaml").write_text(
            "canonical_files:\n"
            "  - voice.md\n"
            "ignored_files:\n"
            "  - old.md\n"
        )

        loaded = prompts.load_knowledge_base("alice")

        assert list(loaded) == ["Canonical Voice Anchor: Voice", "Notes"]
        assert "Old" not in loaded

    def test_generation_warning_summarizes_unresolved_governance(self, tmp_prompts_dir):
        kb = tmp_prompts_dir / "alice" / "knowledge_base"
        kb.mkdir(parents=True)
        (kb / "private-token.md").write_text("local secret")

        warning = prompts.knowledge_base_generation_warning("alice")

        assert "unresolved KB governance" in warning
        assert "private-token.md" in warning


class TestKnowledgeBaseWriteTarget:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("voice", "voice.md"),
            ("voice guide", "voice guide.md"),
            ("voice.md", "voice.md"),
            ("notes.txt", "notes.md"),
            ("release.v1", "release.v1.md"),
        ],
    )
    def test_normalizes_safe_names(self, tmp_prompts_dir, name, expected):
        target = prompts.knowledge_base_write_target("alice", name)

        assert target == tmp_prompts_dir / "alice" / "knowledge_base" / expected

    @pytest.mark.parametrize(
        "name",
        ["", "   ", "../evil", "folder/evil", "folder\\evil", ".hidden", "..", "bad:name"],
    )
    def test_rejects_unsafe_names(self, tmp_prompts_dir, name):
        with pytest.raises(ValueError):
            prompts.knowledge_base_write_target("alice", name)

    def test_write_target_preserves_replace_behavior(self, tmp_prompts_dir):
        target = prompts.knowledge_base_write_target("alice", "voice")
        target.parent.mkdir(parents=True)

        target.write_text("first")
        prompts.knowledge_base_write_target("alice", "voice.md").write_text("second")

        assert target.read_text() == "second"


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

    def test_profile_manifest_prompt_overrides_custom_prompt(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        user.mkdir()
        custom = user / "custom_prompts"
        custom.mkdir()
        (custom / "article_writing.txt").write_text("CUSTOM version")
        (user / "profile.yaml").write_text(
            "prompts:\n"
            "  article_writing: MANIFEST version\n"
        )

        loaded = prompts.load_user_prompts("alice")

        assert loaded["article_writing"] == "MANIFEST version"

    def test_profile_manifest_prompt_can_reference_file(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        user.mkdir()
        (user / "manifest_prompt.md").write_text("from file")
        (user / "profile.yaml").write_text(
            "prompts:\n"
            "  social_media:\n"
            "    file: manifest_prompt.md\n"
        )

        loaded = prompts.load_user_prompts("alice")

        assert loaded["social_media"] == "from file"


class TestProfiles:
    def test_load_profile_preserves_profiles_without_manifest(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        user.mkdir()
        (user / "summary.md").write_text("profile prompt")

        profile = prompts.load_profile("alice")

        assert profile["user"] == "alice"
        assert profile["display_name"] == "alice"
        assert profile["manifest"] == {}
        assert profile["prompts"]["summary"] == "profile prompt"

    def test_load_profile_uses_manifest_display_name(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        user.mkdir()
        (user / "profile.yaml").write_text("display_name: Alice Example\n")

        profile = prompts.load_profile("alice")

        assert profile["display_name"] == "Alice Example"
        assert profile["profile_os"]["display_name"] == "Alice Example"

    def test_profile_os_loads_additive_project_defaults_and_targets(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        kb = user / "knowledge_base"
        kb.mkdir(parents=True)
        (kb / "voice.md").write_text("voice notes")
        (user / "profile.yaml").write_text(
            "display_name: Alice Example\n"
            "project:\n"
            "  name: Launch Notes\n"
            "defaults:\n"
            "  provider: Anthropic\n"
            "  kb_mode: auto\n"
            "kb_packs:\n"
            "  launch:\n"
            "    files: [knowledge_base/voice.md]\n"
            "privacy:\n"
            "  notes: Internal only\n"
            "handoff_targets: [github, markdown]\n"
        )

        profile = prompts.load_profile_os("alice")

        assert profile["project"]["name"] == "Launch Notes"
        assert profile["defaults"]["provider"] == "Anthropic"
        assert profile["kb_packs"][0]["files"] == ["knowledge_base/voice.md"]
        assert profile["handoff_targets"] == ["github", "markdown"]
        assert profile["validation"] == []

    def test_profile_validation_flags_missing_files_and_bad_defaults(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        user.mkdir()
        (user / "profile.yaml").write_text(
            "defaults:\n"
            "  imaginary: true\n"
            "kb_packs:\n"
            "  missing:\n"
            "    files: [knowledge_base/missing.md]\n"
        )

        issues = prompts.validate_profile_manifest("alice")

        assert {issue["kind"] for issue in issues} == {
            "unsupported_default",
            "missing_file",
        }

    def test_profile_summary_explains_effective_configuration(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        user.mkdir()
        (user / "profile.yaml").write_text(
            "display_name: Alice\n"
            "project:\n"
            "  name: Field Notes\n"
            "handoff_targets: [linear]\n"
        )

        summary = prompts.profile_summary("alice")

        assert "Profile: Alice" in summary
        assert "Project: Field Notes" in summary
        assert "Handoff targets: linear" in summary

class TestPersonas:
    def test_lists_builtin_personas_without_user(self, tmp_prompts_dir):
        personas = prompts.list_personas()

        assert "Industry analyst" in personas

    def test_loads_user_persona_files(self, tmp_prompts_dir):
        personas_dir = tmp_prompts_dir / "alice" / "personas"
        personas_dir.mkdir(parents=True)
        (personas_dir / "Field reporter.md").write_text("Write from the scene.")

        personas = prompts.list_personas("alice")

        assert personas["Field reporter"] == "Write from the scene."

    def test_manifest_personas_override_file_personas(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        personas_dir = user / "personas"
        personas_dir.mkdir(parents=True)
        (personas_dir / "Field reporter.md").write_text("file directive")
        (user / "profile.yaml").write_text(
            "personas:\n"
            "  Field reporter: manifest directive\n"
            "  Strategy memo:\n"
            "    directive: Write like a sharp operator.\n"
        )

        personas = prompts.list_personas("alice")

        assert personas["Field reporter"] == "manifest directive"
        assert personas["Strategy memo"] == "Write like a sharp operator."

    def test_manifest_personas_accept_list_entries(self, tmp_prompts_dir):
        user = tmp_prompts_dir / "alice"
        user.mkdir()
        (user / "profile.yaml").write_text(
            "personas:\n"
            "  - name: Builder note\n"
            "    directive: Make it practical and concrete.\n"
        )

        personas = prompts.list_personas("alice")

        assert personas["Builder note"] == "Make it practical and concrete."


class TestSaveCustomPrompt:
    def test_writes_file_to_custom_prompts(self, tmp_prompts_dir):
        ok = prompts.save_custom_prompt("alice", "wisdom_extraction", "my override")
        assert ok is True
        written = tmp_prompts_dir / "alice" / "custom_prompts" / "wisdom_extraction.txt"
        assert written.read_text() == "my override"
