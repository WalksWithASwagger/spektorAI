"""Tests for deterministic SongForge creative packs."""

import json
from pathlib import Path

from whisperforge_core import songforge

FIXTURE = Path(__file__).with_name("fixtures") / "songforge_eval.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_songforge_pack_has_required_outputs_and_source_notes():
    pack = songforge.build_pack(
        "The capture talks about community trust, creative pressure, and making signal return.",
        {"voice.md": "The voice should be direct, warm, and grounded in source receipts."},
    )

    assert pack["themes"]
    assert pack["motifs"]
    assert pack["emotional_arc"]
    assert pack["structure_variants"]
    assert pack["lyric_draft"]
    assert pack["spoken_word"]
    assert pack["music_prompt_pack"]["structure"]
    assert all(variant["source_notes"] for variant in pack["structure_variants"])
    assert all(variant["guardrails"] for variant in pack["structure_variants"])
    assert pack["originality_guardrails"]
    assert any(note["source"] == "KB: voice.md" for note in pack["source_notes"])


def test_songforge_safety_policy_rejects_artist_imitation():
    pack = songforge.build_pack("Make this source into a song.")

    assert "do not imitate living artists" in pack["safety_note"]
    assert "soundalike" in " ".join(pack["originality_guardrails"])
    assert "living-artist imitation" in pack["music_prompt_pack"]["avoid"]
    assert "soundalike" in " ".join(pack["music_prompt_pack"]["avoid"])


def test_songforge_fixture_pins_pack_shape():
    fixture = _fixture()
    pack = songforge.build_pack(
        fixture["transcript"],
        fixture.get("knowledge_base") or {},
    )

    assert sorted(pack) == fixture["expected_pack_keys"]
    assert (
        [variant["name"] for variant in pack["structure_variants"]]
        == fixture["expected_structure_variants"]
    )
    assert pack["originality_guardrails"] == fixture["expected_originality_guardrails"]
    markdown = songforge.render_markdown(pack)
    for expected in fixture["expected_markdown"]:
        assert expected in markdown


def test_songforge_markdown_renders_creative_outputs_and_guardrails():
    markdown = songforge.render_markdown(songforge.build_pack("A voice memo about turning memory into music."))

    assert "## Originality Guardrails" in markdown
    assert "## Structure Variants" in markdown
    assert "## Lyric Draft" in markdown
    assert "## Spoken-Word Variant" in markdown
    assert "## Music Prompt Pack" in markdown
    assert "## Source Notes" in markdown
