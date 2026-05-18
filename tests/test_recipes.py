"""Tests for prompt recipe manifests and effective settings."""

import pytest

from whisperforge_core import config, recipes


@pytest.fixture
def tmp_prompts_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(recipes, "PROMPTS_DIR", tmp_path)
    return tmp_path


def test_builtin_recipes_cover_required_workflows():
    loaded = recipes.list_recipes()

    assert {"article_with_receipts", "brief_social_pack", "issue_handoff", "songforge_prompt_pack"} <= set(loaded)
    assert loaded["article_with_receipts"].defaults["kb_mode"] == "auto"
    assert "github" in loaded["issue_handoff"].handoff_targets
    assert "songforge_prompt_pack" in loaded["songforge_prompt_pack"].output_sections


def test_profile_recipe_file_overrides_builtin(tmp_prompts_dir):
    recipe_dir = tmp_prompts_dir / "alice" / "recipes"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "brief_social_pack.yaml").write_text(
        "name: Alice Brief\n"
        "description: Profile override\n"
        "inputs: [wispr_flow]\n"
        "stages: [wisdom_extraction, social_media]\n"
        "defaults:\n"
        "  provider: OpenAI\n"
        "  model: gpt-4o-mini\n"
        "  kb_mode: always\n"
        "output_sections: [social_content]\n"
        "eval_checks: [source_receipts]\n"
        "handoff_targets: [markdown]\n"
    )

    loaded = recipes.list_recipes("alice")

    recipe = loaded["brief_social_pack"]
    assert recipe.name == "Alice Brief"
    assert recipe.source == "profile:brief_social_pack.yaml"
    assert recipe.defaults["model"] == "gpt-4o-mini"


def test_profile_manifest_recipes_override_recipe_files(tmp_prompts_dir):
    user = tmp_prompts_dir / "alice"
    recipe_dir = user / "recipes"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "operator_brief.yaml").write_text(
        "name: File version\n"
        "stages: [wisdom_extraction]\n"
    )
    (user / "profile.yaml").write_text(
        "recipes:\n"
        "  operator_brief:\n"
        "    name: Manifest version\n"
        "    stages: [outline_creation]\n"
        "    defaults:\n"
        "      article_length: Brief\n"
    )

    loaded = recipes.list_recipes("alice")

    assert loaded["operator_brief"].name == "Manifest version"
    assert loaded["operator_brief"].stages == ["outline_creation"]
    assert loaded["operator_brief"].source == "profile:profile.yaml"


def test_effective_settings_maps_manifest_defaults_to_ui_keys():
    recipe = recipes.Recipe(
        id="client_brief",
        name="Client Brief",
        defaults={
            "provider": "Anthropic",
            "model": "claude-sonnet-4-5",
            "kb_mode": "always",
            "cleanup": True,
            "chapters": False,
            "fact_check": True,
        },
        stages=["wisdom_extraction"],
        output_sections=["article"],
        eval_checks=["source_receipts"],
        handoff_targets=["linear"],
    )

    effective = recipes.effective_settings(
        recipe,
        {
            "ai_provider": "OpenAI",
            "ai_model": "gpt-4o-mini",
            "rag_mode": "auto",
            "article_length": "Standard",
        },
    )

    assert effective["settings"]["ai_provider"] == "Anthropic"
    assert effective["settings"]["ai_model"] == "claude-sonnet-4-5"
    assert effective["settings"]["rag_mode"] == "always"
    assert effective["settings"]["cleanup_enabled"] is True
    assert effective["settings"]["chapters_enabled"] is False
    assert effective["settings"]["fact_check_enabled"] is True
    assert effective["handoff_targets"] == ["linear"]
