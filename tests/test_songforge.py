"""Tests for deterministic SongForge creative packs."""

from whisperforge_core import songforge


def test_songforge_pack_has_required_outputs_and_source_notes():
    pack = songforge.build_pack(
        "The capture talks about community trust, creative pressure, and making signal return.",
        {"voice.md": "The voice should be direct, warm, and grounded in source receipts."},
    )

    assert pack["themes"]
    assert pack["motifs"]
    assert pack["emotional_arc"]
    assert pack["lyric_draft"]
    assert pack["spoken_word"]
    assert pack["music_prompt_pack"]["structure"]
    assert any(note["source"] == "KB: voice.md" for note in pack["source_notes"])


def test_songforge_safety_policy_rejects_artist_imitation():
    pack = songforge.build_pack("Make this source into a song.")

    assert "do not imitate living artists" in pack["safety_note"]
    assert "living-artist imitation" in pack["music_prompt_pack"]["avoid"]
    assert "soundalike" in " ".join(pack["music_prompt_pack"]["avoid"])


def test_songforge_markdown_renders_three_creative_outputs():
    markdown = songforge.render_markdown(songforge.build_pack("A voice memo about turning memory into music."))

    assert "## Lyric Draft" in markdown
    assert "## Spoken-Word Variant" in markdown
    assert "## Music Prompt Pack" in markdown
    assert "## Source Notes" in markdown
