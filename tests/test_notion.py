"""Tests for whisperforge_core.notion — block chunker and ContentBundle layout.

The 1900-char chunker is load-bearing: Notion rejects >2000-char rich_text
blocks. These tests pin that behavior so nobody quietly loosens it.
"""

import pytest

from whisperforge_core import notion


class TestChunkTextForNotion:
    def test_empty_string_returns_empty_list(self):
        assert notion.chunk_text_for_notion("") == []

    def test_short_text_single_chunk(self):
        assert notion.chunk_text_for_notion("hello world") == ["hello world"]

    def test_exactly_1900_chars_single_chunk(self):
        text = "a" * 1900
        chunks = notion.chunk_text_for_notion(text)
        assert len(chunks) == 1
        assert len(chunks[0]) == 1900

    def test_1901_chars_splits_into_two(self):
        text = "a" * 1901
        chunks = notion.chunk_text_for_notion(text)
        assert len(chunks) == 2
        assert len(chunks[0]) == 1900
        assert len(chunks[1]) == 1

    def test_10000_chars_splits_into_six_chunks(self):
        text = "b" * 10_000
        chunks = notion.chunk_text_for_notion(text)
        # ceil(10000/1900) == 6
        assert len(chunks) == 6
        assert sum(len(c) for c in chunks) == 10_000
        assert all(len(c) <= 1900 for c in chunks)

    def test_unicode_preserved(self):
        text = "café " * 500  # ~2500 chars
        chunks = notion.chunk_text_for_notion(text)
        assert "".join(chunks) == text
        # Notion counts chars, so unicode bytes aren't relevant
        assert all(len(c) <= 1900 for c in chunks)

    def test_no_block_exceeds_notion_limit(self):
        """Guard against any future chunk_size regression above 2000."""
        text = "x" * 50_000
        chunks = notion.chunk_text_for_notion(text)
        assert all(len(c) < 2000 for c in chunks), "Notion would reject a block >=2000 chars"


class TestContentBundleBlocks:
    def test_minimal_bundle_builds_metadata_only(self):
        bundle = notion.ContentBundle(title="Test")
        blocks = notion.build_blocks(bundle)
        # At minimum: divider + heading + 4 metadata paragraphs
        assert any(b["type"] == "heading_2" for b in blocks)
        paragraphs = [b for b in blocks if b["type"] == "paragraph"]
        assert len(paragraphs) >= 4  # filename, created, models, tokens

    def test_full_bundle_includes_every_section(self):
        bundle = notion.ContentBundle(
            title="Full",
            transcript="T" * 100,
            wisdom="W" * 100,
            outline="O" * 100,
            social_content="S" * 100,
            image_prompts="I" * 100,
            article="A" * 100,
            summary="brief summary",
            tags=["a", "b"],
            audio_filename="file.m4a",
            models_used=["OpenAI gpt-4", "OpenAI Whisper-1"],
        )
        blocks = notion.build_blocks(bundle)
        toggle_labels = [
            b["toggle"]["rich_text"][0]["text"]["content"]
            for b in blocks if b["type"] == "toggle"
        ]
        assert "Transcription" in toggle_labels
        assert "Wisdom" in toggle_labels
        assert "Socials" in toggle_labels
        assert "Image Prompts" in toggle_labels
        assert "Outline" in toggle_labels
        assert "Draft Post" in toggle_labels
        assert "Original Audio" in toggle_labels

    def test_long_transcript_uses_chunked_paragraphs(self):
        bundle = notion.ContentBundle(title="Long", transcript="z" * 5000)
        blocks = notion.build_blocks(bundle)
        transcription_toggles = [
            b for b in blocks
            if b["type"] == "toggle"
            and b["toggle"]["rich_text"][0]["text"]["content"] == "Transcription"
        ]
        assert len(transcription_toggles) == 1
        paragraphs = transcription_toggles[0]["toggle"]["children"]
        # 5000 / 1900 = 3 chunks
        assert len(paragraphs) == 3
        for p in paragraphs:
            assert len(p["paragraph"]["rich_text"][0]["text"]["content"]) <= 1900


class TestEstimateTokens:
    def test_empty_bundle_has_overhead(self):
        tokens = notion.estimate_tokens(notion.ContentBundle(title=""))
        assert tokens == 1000  # 0 content + 1000 overhead

    def test_token_count_scales_with_content(self):
        short = notion.estimate_tokens(notion.ContentBundle(title="", transcript="a" * 40))
        long = notion.estimate_tokens(notion.ContentBundle(title="", transcript="a" * 4000))
        assert long > short
        # 4000 chars @ 4 chars/token = 1000 tokens, plus 1000 overhead
        assert 1900 <= long <= 2100
